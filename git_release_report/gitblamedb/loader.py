"""
Git Blame数据库加载器
支持快速初始化git blame数据库，扫描指定路径的git仓库并存储blame信息
"""

import os
import re
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Iterator
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .models import (
    Repository, Commit, File, BlameLine,
    DatabaseManager, get_db_session
)


@dataclass
class BlameResult:
    """Git blame结果数据结构"""
    file_path: str
    line_number: int
    content: str
    commit_sha: str
    author_name: str
    author_email: str
    authored_time: datetime
    is_merge_line: bool = False


class GitBlameLoader:
    """Git Blame数据库加载器"""

    def __init__(self, database_url: str, batch_size: int = 1000, log_file: str = "analyze-failed.log"):
        """
        初始化加载器

        Args:
            database_url: 数据库连接URL
            batch_size: 批量插入大小
            log_file: 错误日志文件路径
        """
        self.database_url = database_url
        self.batch_size = batch_size
        self.log_file = log_file
        self.db_manager = DatabaseManager(database_url)
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('GitBlameLoader')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            # 控制台处理器 - 只显示INFO和WARNING级别
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上级别
            logger.addHandler(console_handler)

            # 分析失败文件处理器 - 只记录ERROR级别到文件
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.ERROR)  # 只记录错误级别到文件
            logger.addHandler(file_handler)

        return logger

    def _log_analysis_error(self, file_path: str, error: Exception, context: str = ""):
        """
        记录分析错误的详细信息到日志文件

        Args:
            file_path: 文件路径
            error: 异常对象
            context: 错误上下文信息
        """
        import traceback

        # 在控制台显示简化的错误信息
        simple_error_msg = f"分析失败 {file_path}: {str(error)}"
        self.logger.warning(simple_error_msg)

        # 详细信息只写入文件
        error_details = {
            'file_path': file_path,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc()
        }

        # 格式化详细错误信息
        detailed_error_msg = f"""
=== 分析失败详情 ===
文件路径: {error_details['file_path']}
错误类型: {error_details['error_type']}
错误信息: {error_details['error_message']}
上下文: {error_details['context']}
时间戳: {error_details['timestamp']}
堆栈跟踪:
{error_details['traceback']}
=== 结束 ===
"""

        # 创建专门的文件logger，只写入文件
        file_logger = logging.getLogger('GitBlameLoader.FileOnly')
        file_logger.setLevel(logging.ERROR)

        # 清除现有处理器，只保留文件处理器
        file_logger.handlers.clear()
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        file_logger.addHandler(file_handler)
        file_logger.propagate = False  # 不传播到父logger

        # 写入详细错误信息到文件
        file_logger.error(detailed_error_msg)

    def load_repository(
        self,
        repo_path: str,
        file_filter_regex: Optional[str] = None,
        repo_name: Optional[str] = None,
        repo_url: Optional[str] = None,
        force_reload: bool = False
    ) -> bool:
        """
        加载单个仓库的blame信息到数据库

        Args:
            repo_path: 仓库路径
            file_filter_regex: 文件过滤正则表达式
            repo_name: 仓库名称（可选，默认使用路径名）
            repo_url: 仓库URL（可选）
            force_reload: 是否强制重新加载所有文件

        Returns:
            bool: 是否加载成功
        """
        try:
            repo_path = os.path.abspath(repo_path)

            if not os.path.exists(repo_path):
                self.logger.error(f"仓库路径不存在: {repo_path}")
                return False

            if not os.path.exists(os.path.join(repo_path, '.git')):
                self.logger.error(f"不是有效的git仓库: {repo_path}")
                return False

            # 获取仓库信息
            if not repo_name:
                repo_name = os.path.basename(repo_path)

            if not repo_url:
                repo_url = self._get_remote_url(repo_path)

            self.logger.info(f"开始加载仓库: {repo_name} ({repo_path})")

            # 创建数据库会话
            session = self.db_manager.get_session()

            try:
                # 创建或获取仓库记录
                repository = self._get_or_create_repository(
                    session, repo_name, repo_path, repo_url
                )

                # 获取所有需要分析的文件
                files_to_analyze = self._get_files_to_analyze(
                    repo_path, file_filter_regex
                )

                self.logger.info(f"找到 {len(files_to_analyze)} 个文件需要分析")

                # 清理已删除文件的记录
                if not force_reload:
                    self._cleanup_deleted_files(
                        session, repository, files_to_analyze)

                # 分析每个文件的blame信息
                total_lines = 0
                for file_path in files_to_analyze:
                    try:
                        lines_count = self._analyze_file_blame(
                            session, repository, repo_path, file_path, force_reload
                        )
                        total_lines += lines_count
                        self.logger.debug(f"分析文件 {file_path}: {lines_count} 行")
                    except Exception as e:
                        self._log_analysis_error(file_path, e, "文件分析主循环")
                        continue

                session.commit()
                self.logger.info(f"仓库加载完成: {total_lines} 行blame信息")
                return True

            except Exception as e:
                session.rollback()
                self.logger.error(f"加载仓库失败: {e}")
                return False
            finally:
                session.close()

        except Exception as e:
            self.logger.error(f"加载仓库时发生错误: {e}")
            return False

    def _get_or_create_repository(
        self,
        session: Session,
        name: str,
        path: str,
        url: Optional[str]
    ) -> Repository:
        """获取或创建仓库记录"""
        repository = session.query(Repository).filter(
            Repository.name == name,
            Repository.path == path
        ).first()

        if not repository:
            repository = Repository(
                name=name,
                path=path,
                url=url,
                description=f"Git仓库: {name}"
            )
            session.add(repository)
            session.flush()
            self.logger.info(f"创建新仓库记录: {name}")
        else:
            self.logger.info(f"使用现有仓库记录: {name}")

        return repository

    def _get_remote_url(self, repo_path: str) -> Optional[str]:
        """获取仓库的远程URL"""
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def _get_files_to_analyze(
        self,
        repo_path: str,
        file_filter_regex: Optional[str]
    ) -> List[str]:
        """获取需要分析的文件列表"""
        try:
            # 使用git ls-files获取所有跟踪的文件
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            files = result.stdout.strip().split('\n')
            files = [f for f in files if f.strip()]  # 过滤空行

            # 应用文件过滤
            if file_filter_regex:
                pattern = re.compile(file_filter_regex)
                files = [f for f in files if pattern.search(f)]

            return files

        except subprocess.CalledProcessError as e:
            error_msg = f"获取文件列表失败: {e}"
            self.logger.error(error_msg)
            return []

    def _cleanup_deleted_files(
        self,
        session: Session,
        repository: Repository,
        current_files: List[str]
    ) -> int:
        """
        清理已删除文件的记录

        Args:
            session: 数据库会话
            repository: 仓库对象
            current_files: 当前存在的文件列表

        Returns:
            int: 清理的文件数量
        """
        try:
            # 获取数据库中该仓库的所有文件
            db_files = session.query(File).filter(
                File.repository_id == repository.id
            ).all()

            deleted_count = 0
            for db_file in db_files:
                if db_file.path not in current_files:
                    # 文件已删除，清理相关记录
                    self.logger.debug(f"清理已删除文件: {db_file.path}")

                    # 删除blame记录
                    session.query(BlameLine).filter(
                        BlameLine.file_id == db_file.id
                    ).delete()

                    # 删除文件记录
                    session.delete(db_file)
                    deleted_count += 1

            if deleted_count > 0:
                session.flush()
                self.logger.info(f"清理了 {deleted_count} 个已删除文件的记录")

            return deleted_count

        except Exception as e:
            error_msg = f"清理已删除文件失败: {e}"
            self.logger.error(error_msg)
            return 0

    def _analyze_file_blame(
        self,
        session: Session,
        repository: Repository,
        repo_path: str,
        file_path: str,
        force_reload: bool = False
    ) -> int:
        """分析单个文件的blame信息"""
        try:
            # 检查文件是否存在
            full_path = os.path.join(repo_path, file_path)
            if not os.path.exists(full_path):
                return 0

            # 获取文件信息
            file_stat = os.stat(full_path)
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

            # 检查是否需要跳过该文件
            if not force_reload and self._should_skip_file(session, repository, file_path, file_mtime):
                self.logger.debug(f"跳过未修改的文件: {file_path}")
                return 0

            # 获取或创建文件记录
            file_record = self._get_or_create_file(
                session, repository, file_path, file_stat
            )

            # 执行git blame
            blame_results = self._run_git_blame(repo_path, file_path)

            # 批量插入blame行
            return self._insert_blame_lines(
                session, repository, file_record, blame_results
            )

        except Exception as e:
            self._log_analysis_error(file_path, e, "文件blame分析")
            return 0

    def _should_skip_file(
        self,
        session: Session,
        repository: Repository,
        file_path: str,
        file_mtime: datetime
    ) -> bool:
        """
        检查是否应该跳过该文件

        Args:
            session: 数据库会话
            repository: 仓库对象
            file_path: 文件路径
            file_mtime: 文件修改时间

        Returns:
            bool: 是否应该跳过该文件
        """
        try:
            # 查询数据库中该文件的记录
            file_record = session.query(File).filter(
                File.repository_id == repository.id,
                File.path == file_path
            ).first()

            if not file_record:
                # 文件不存在于数据库中，需要处理
                return False

            # 检查文件修改时间
            if file_record.last_modified and file_mtime <= file_record.last_modified:
                # 文件修改时间小于等于数据库记录时间，跳过
                return True

            # 检查是否有blame记录
            blame_count = session.query(BlameLine).filter(
                BlameLine.repository_id == repository.id,
                BlameLine.file_id == file_record.id
            ).count()

            if blame_count > 0:
                # 有blame记录且文件未修改，跳过
                return True

            # 需要处理该文件
            return False

        except Exception as e:
            error_msg = f"检查文件跳过条件失败 {file_path}: {e}"
            self.logger.error(error_msg)
            # 出错时默认不跳过，继续处理
            return False

    def _get_or_create_file(
        self,
        session: Session,
        repository: Repository,
        file_path: str,
        file_stat: os.stat_result
    ) -> File:
        """获取或创建文件记录"""
        file_record = session.query(File).filter(
            File.repository_id == repository.id,
            File.path == file_path
        ).first()

        file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

        if not file_record:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1]

            file_record = File(
                repository_id=repository.id,
                path=file_path,
                name=file_name,
                extension=file_ext,
                size=file_stat.st_size,
                is_binary=self._is_binary_file(file_path),
                last_modified=file_mtime
            )
            session.add(file_record)
            session.flush()
        else:
            # 更新现有文件记录的修改时间和大小
            file_record.last_modified = file_mtime
            file_record.size = file_stat.st_size
            file_record.updated_at = datetime.now()
            session.flush()

        return file_record

    def _is_binary_file(self, file_path: str) -> bool:
        """判断是否为二进制文件"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except:
            return False

    def _run_git_blame(self, repo_path: str, file_path: str) -> List[BlameResult]:
        """执行git blame命令并解析结果"""
        try:
            # 使用git blame获取详细信息
            cmd = [
                'git', 'blame', '--line-porcelain', file_path
            ]

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            return self._parse_blame_output(result.stdout)

        except subprocess.CalledProcessError as e:
            error_msg = f"git blame执行失败 {file_path}: {e}"
            self.logger.error(error_msg)
            return []

    def _parse_blame_output(self, output: str) -> List[BlameResult]:
        """解析git blame输出"""
        results = []
        lines = output.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # 解析blame行信息
            parts = line.split()
            if len(parts) < 4:
                i += 1
                continue

            commit_sha = parts[0]
            original_line = int(parts[1])
            current_line = int(parts[2])
            line_count = int(parts[3])

            # 解析后续的元数据
            author_name = ""
            author_email = ""
            authored_time = None
            is_merge_line = False

            j = i + 1
            while j < len(lines) and not lines[j].startswith('\t'):
                meta_line = lines[j].strip()
                if meta_line.startswith('author '):
                    author_name = meta_line[7:]
                elif meta_line.startswith('author-mail '):
                    author_email = meta_line[12:].strip('<>')
                elif meta_line.startswith('author-time '):
                    timestamp = int(meta_line[12:])
                    authored_time = datetime.fromtimestamp(timestamp)
                elif meta_line.startswith('boundary'):
                    is_merge_line = True
                j += 1

            # 获取行内容
            if j < len(lines) and lines[j].startswith('\t'):
                content = lines[j][1:]  # 移除开头的tab

                # 创建blame结果
                blame_result = BlameResult(
                    file_path="",  # 将在调用处设置
                    line_number=current_line,
                    content=content,
                    commit_sha=commit_sha,
                    author_name=author_name,
                    author_email=author_email,
                    authored_time=authored_time or datetime.now(),
                    is_merge_line=is_merge_line
                )
                results.append(blame_result)

            i = j + 1

        return results

    def _insert_blame_lines(
        self,
        session: Session,
        repository: Repository,
        file_record: File,
        blame_results: List[BlameResult]
    ) -> int:
        """批量插入blame行数据"""
        if not blame_results:
            return 0

        # 获取所有需要的提交记录
        commit_shas = list(set(r.commit_sha for r in blame_results))
        commits_map = self._get_or_create_commits(
            session, repository, commit_shas)

        # 准备批量插入数据
        blame_lines = []
        for result in blame_results:
            commit = commits_map.get(result.commit_sha)
            if not commit:
                continue

            blame_line = BlameLine(
                repository_id=repository.id,
                file_id=file_record.id,
                commit_id=commit.id,
                line_number=result.line_number,
                content=result.content,
                is_merge_line=result.is_merge_line,
                original_line_number=result.line_number,
                original_file_path=file_record.path
            )
            blame_lines.append(blame_line)

        # 批量插入
        try:
            session.add_all(blame_lines)
            session.flush()
            return len(blame_lines)
        except IntegrityError:
            # 如果存在重复，逐个插入
            inserted_count = 0
            for blame_line in blame_lines:
                try:
                    session.add(blame_line)
                    session.flush()
                    inserted_count += 1
                except IntegrityError:
                    session.rollback()
                    continue
            return inserted_count

    def _get_or_create_commits(
        self,
        session: Session,
        repository: Repository,
        commit_shas: List[str]
    ) -> Dict[str, Commit]:
        """获取或创建提交记录"""
        commits_map = {}

        # 查询现有提交
        existing_commits = session.query(Commit).filter(
            Commit.repository_id == repository.id,
            Commit.sha.in_(commit_shas)
        ).all()

        for commit in existing_commits:
            commits_map[commit.sha] = commit

        # 创建缺失的提交记录
        missing_shas = [sha for sha in commit_shas if sha not in commits_map]
        for sha in missing_shas:
            commit_info = self._get_commit_info(repository.path, sha)
            if commit_info:
                commit = Commit(
                    repository_id=repository.id,
                    sha=sha,
                    short_sha=sha[:8],
                    author_name=commit_info['author_name'],
                    author_email=commit_info['author_email'],
                    committer_name=commit_info['committer_name'],
                    committer_email=commit_info['committer_email'],
                    authored_time=commit_info['authored_time'],
                    committed_time=commit_info['committed_time'],
                    message=commit_info['message'],
                    is_merge=commit_info['is_merge'],
                    on_mainline=True
                )
                session.add(commit)
                session.flush()
                commits_map[sha] = commit

        return commits_map

    def _get_commit_info(self, repo_path: str, commit_sha: str) -> Optional[Dict]:
        """获取提交的详细信息"""
        try:
            cmd = [
                'git', 'show', '--format=fuller', '--no-patch', commit_sha
            ]

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            return self._parse_commit_info(result.stdout)

        except subprocess.CalledProcessError:
            return None

    def _parse_commit_info(self, output: str) -> Optional[Dict]:
        """解析提交信息"""
        lines = output.strip().split('\n')
        if len(lines) < 10:
            return None

        try:
            # 解析提交信息
            commit_info = {}
            for line in lines:
                if line.startswith('commit '):
                    continue
                elif line.startswith('Author: '):
                    author = line[8:]
                    if ' <' in author:
                        name, email = author.split(' <', 1)
                        commit_info['author_name'] = name.strip()
                        commit_info['author_email'] = email.rstrip('>')
                    else:
                        commit_info['author_name'] = author
                        commit_info['author_email'] = ''
                elif line.startswith('AuthorDate: '):
                    date_str = line[12:]
                    commit_info['authored_time'] = datetime.fromisoformat(
                        date_str.replace(' ', 'T')
                    )
                elif line.startswith('Commit: '):
                    committer = line[8:]
                    if ' <' in committer:
                        name, email = committer.split(' <', 1)
                        commit_info['committer_name'] = name.strip()
                        commit_info['committer_email'] = email.rstrip('>')
                    else:
                        commit_info['committer_name'] = committer
                        commit_info['committer_email'] = ''
                elif line.startswith('CommitDate: '):
                    date_str = line[12:]
                    commit_info['committed_time'] = datetime.fromisoformat(
                        date_str.replace(' ', 'T')
                    )
                elif line.startswith('Merge: '):
                    commit_info['is_merge'] = True
                elif line.startswith('    ') and 'message' not in commit_info:
                    commit_info['message'] = line[4:]

            # 设置默认值
            commit_info.setdefault('is_merge', False)
            commit_info.setdefault('message', '')

            return commit_info

        except Exception:
            return None

    def close(self):
        """关闭数据库连接"""
        self.db_manager.close()


def load_git_blame_database(
    repo_path: str,
    database_url: str,
    file_filter_regex: Optional[str] = None,
    repo_name: Optional[str] = None,
    repo_url: Optional[str] = None,
    force_reload: bool = False,
    log_file: str = "analyze-failed.log"
) -> bool:
    """
    便捷函数：加载git blame数据库

        Args:
        repo_path: 仓库路径
        database_url: 数据库连接URL
        file_filter_regex: 文件过滤正则表达式
        repo_name: 仓库名称
        repo_url: 仓库URL
        force_reload: 是否强制重新加载所有文件
        log_file: 错误日志文件路径

    Returns:
        bool: 是否加载成功
    """
    loader = GitBlameLoader(database_url, log_file=log_file)
    try:
        return loader.load_repository(
            repo_path, file_filter_regex, repo_name, repo_url, force_reload
        )
    finally:
        loader.close()
