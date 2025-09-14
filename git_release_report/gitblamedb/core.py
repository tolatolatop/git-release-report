import os
import time
import re
import subprocess as sp
from typing import List, Tuple
from git import Repo, Commit, Diff
from .models import Commit as CommitModel
from .models import BlameLine as BlameLineModel
from .models import FileCache as FileCacheModel
from .models import DiffInfo as DiffInfoModel
from .models import CommitStat as CommitStatModel
from .models import RepoData
from .models import load_data_by_repo_name
from sqlalchemy.orm import Session


def find_git_repos(root_dir: str, maxdepth: int = 3) -> List[str]:
    """
    查找git仓库

    Args:
        root_dir: 根目录
        maxdepth: 最大深度

    Returns:
        List[str]: git仓库列表
    """
    output = sp.check_output(
        [
            'find', '-L', root_dir, '-maxdepth',
            str(maxdepth + 1), '-type', 'd', '-name', '.git'
        ]
    )
    paths = [
        os.path.dirname(path)
        for path in output.decode('utf-8', errors='ignore').strip().splitlines()
    ]

    res = []
    for path in paths:
        try:
            repo = Repo(path)
            if repo.bare:
                continue
            res.append(path)
        except Exception:
            continue
    return


def list_files(repo_path: str, regex: str) -> List[str]:
    """
    列出仓库中的文件

    Args:
        repo_path: 仓库路径
        regex: 文件名匹配正则表达式

    Returns:
        List[str]: 文件列表
    """

    repo = Repo(repo_path)
    output: str = repo.git.ls_tree(repo.head.commit.hexsha,
                                   '--full-tree', '--name-only')
    paths = [
        path
        for path in output.strip().splitlines()
    ]

    res = []
    re_match = re.compile(regex)
    for path in paths:
        if re_match.match(path):
            res.append(path)
    return res


def get_file_last_modified(repo_path: str, file_path: str) -> float:
    """
    获取文件的最后修改时间

    Args:
        repo_path: 仓库路径
        file_path: 文件路径

    Returns:
        float: 最后修改时间
    """
    try:
        return os.stat(os.path.join(repo_path, file_path)).st_mtime
    except Exception:
        return 9999999999


def get_file_blame(repo_path: str, file_path: str) -> List[Tuple[str, int]]:
    """
    获取文件的blame信息

    Args:
        repo_path: 仓库路径
        file_path: 文件路径

    Returns:
        List[Tuple[str, int]]: 行号和commit_sha
    """
    info_match = re.compile(
        r'^(?P<commit_sha>[\^0-9a-f]+)\s+\(.*?(?P<line_number>\d+)\)', re.MULTILINE
    )
    repo = Repo(repo_path)
    output = repo.git.blame('-l', '-w', '-M', '-C', '--', file_path)
    info_matches = info_match.findall(output)
    if output.count('\n') != len(info_matches) - 1:
        num = [n for _, n in info_matches]
        raise ValueError(f"Invalid blame output: {output}\n{num}")

    root_id = None
    for commit_sha, _ in info_matches:
        if commit_sha.startswith('^'):
            root_id = repo.commit(commit_sha[1:]).hexsha
            break
    out = [(
        root_id if commit_sha.startswith('^') else commit_sha,
        int(line_number),
    ) for commit_sha, line_number in info_matches]
    return out


def to_commit_model(repo_name: str, commit: Commit) -> CommitModel:
    """
    将commit转换为commit模型

    Args:
        repo_name: 仓库名称
        commit: commit对象

    Returns:
        CommitModel: commit模型
    """
    return CommitModel(
        repo_name=repo_name,
        sha=commit.hexsha,
        commit_message=commit.message,
        commit_time=commit.authored_date,
        author_name=commit.author.name,
        author_email=commit.author.email,
        committer_name=commit.committer.name,
        committer_email=commit.committer.email,
        is_merge=commit.parents != 1,
    )


def to_blame_line_model(repo_name: str, file_path: str, blame: Tuple[str, int]) -> BlameLineModel:
    """
    将blame信息转换为blame模型

    Args:
        repo_name: 仓库名称
        file_path: 文件路径
        blame: 行号和commit_sha
    """
    return BlameLineModel(
        repo_name=repo_name,
        file_path=file_path,
        line_number=blame[1],
        commit_sha=blame[0],
    )


def to_file_cache_model(repo_name: str, file_path: str) -> FileCacheModel:
    """
    将文件转换为文件模型

    Args:
        repo_name: 仓库名称
        file_path: 文件路径
    """
    return FileCacheModel(
        repo_name=repo_name,
        file_path=file_path,
        last_modified=get_file_last_modified(repo_name, file_path),
    )


def filter_by_last_modified(repo_data: RepoData, file_paths: List[FileCacheModel]) -> List[FileCacheModel]:
    """
    根据最后修改时间过滤文件

    Args:
        repo_data: 仓库数据
        file_paths: 文件路径列表
    """
    out = []
    for file_path in file_paths:
        if file_path not in repo_data.file_cache:
            out.append(file_path)
        elif file_path.last_modified <= repo_data.file_cache[file_path.file_path].last_modified:
            out.append(file_path)
        else:
            pass
    return out


def create_blame_repo(repo_path: str, regex: str, sess: Session):
    """
    创建仓库的blame信息

    Args:
        repo_path: 仓库路径
        regex: 文件名匹配正则表达式
        sess: 数据库会话
    """
    repo_name = os.path.basename(repo_path)
    file_paths = list_files(repo_path, regex)
    file_cache = [
        to_file_cache_model(repo_name, file_path)
        for file_path in file_paths
    ]
    repo_data = load_data_by_repo_name(sess, repo_name, [FileCacheModel])
    file_cache = filter_by_last_modified(repo_data, file_cache)

    blame_lines = []
    for f in file_cache:
        blame_lines.extend(get_file_blame(repo_path, f.file_path))

    blame_lines = [
        to_blame_line_model(repo_name, f.file_path, blame)
        for blame in blame_lines
    ]

    commit_id_set = set()
    for blame_line in blame_lines:
        commit_id_set.add(blame_line.commit_sha)

    repo = Repo(repo_path)
    commits = [repo.commit(commit_id) for commit_id in commit_id_set]
    commits = [to_commit_model(repo_name, commit) for commit in commits]

    return file_cache, blame_lines, commits


def list_commits(repo_path: str, old_commit: str, new_commit: str) -> List[CommitModel]:
    """
    列出仓库中的commit

    Args:
        repo_path: 仓库路径
        old_commit: 第一个提交
        new_commit: 第二个提交

    Returns:
        List[CommitModel]: commit模型列表
    """
    repo_name = os.path.basename(repo_path)
    repo = Repo(repo_path)
    return [to_commit_model(repo_name, commit) for commit in repo.iter_commits(f"{old_commit}..{new_commit}")]


def get_commit(repo_path: str, commit_id: str) -> CommitModel:
    """
    获取commit

    Args:
        repo_path: 仓库路径
        commit_id: 提交id
    """
    repo = Repo(repo_path)
    return to_commit_model(os.path.basename(repo_path), repo.commit(commit_id))


def to_commit_stats_model(repo_name: str, commit_id: str, filepath: str, stat: dict) -> CommitStatModel:
    """
    将diff信息转换为commit统计模型
    """
    return CommitStatModel(
        repo_name=repo_name,
        commit_sha=commit_id,
        filepath=filepath,
        change_type=stat['change_type'],
        add_lines=stat['insertions'],
        del_lines=stat['deletions'],
    )


def get_commit_stats(repo_path: str, commit_id: str) -> List[CommitStatModel]:
    """
    获取commit统计信息

    Args:
        repo_path: 仓库路径
        commit_id: 提交id
    """
    repo_name = os.path.basename(repo_path)
    repo = Repo(repo_path)
    commit = repo.commit(commit_id)
    return [to_commit_stats_model(repo_name, commit.hexsha, file, stat)
        for file, stat in commit.stats.files.items()
    ]


def to_diff_info_model(repo_name: str, rev_1: str, rev_2: str, diff: Diff) -> DiffInfoModel:
    """
    将diff信息转换为diff模型
    """
    return DiffInfoModel(
        repo_name=repo_name,
        commit_sha=rev_1,
        a_path=diff.a_path,
        b_path=diff.b_path,
        change_type=diff.change_type,
    )



def get_diff_info(repo_path: str, rev_1: str, rev_2: str) -> List[DiffInfoModel]:
    """
    获取diff信息

    Args:
        repo_path: 仓库路径
        rev_1: 第一个提交
        rev_2: 第二个提交
    """ 
    repo_name = os.path.basename(repo_path)
    repo = Repo(repo_path)
    diff  = repo.commit(rev_1).diff(rev_2)
    return [to_diff_info_model(repo_name, rev_1, rev_2, diff) for diff in diff]
