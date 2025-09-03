"""
Git Blame数据库使用示例
演示如何使用SQLAlchemy模型存储和查询git blame信息
"""

from datetime import datetime
from .models import (
    Repository,
    Commit,
    File,
    BlameLine,
    get_db_session,
    init_database
)


def example_usage():
    """使用示例"""

    # 初始化数据库
    init_database("sqlite:///example_git_blame.db")

    # 获取数据库会话
    session = get_db_session()

    try:
        # 1. 创建仓库记录
        repo = Repository(
            name="example-repo",
            path="/path/to/example-repo",
            url="https://github.com/user/example-repo.git",
            description="示例仓库"
        )
        session.add(repo)
        session.flush()  # 获取ID

        # 2. 创建提交记录
        commit = Commit(
            repository_id=repo.id,
            sha="a1b2c3d4e5f6789012345678901234567890abcd",
            short_sha="a1b2c3d4",
            author_name="张三",
            author_email="zhangsan@example.com",
            committer_name="张三",
            committer_email="zhangsan@example.com",
            authored_time=datetime(2024, 1, 15, 10, 30, 0),
            committed_time=datetime(2024, 1, 15, 10, 35, 0),
            message="添加新功能",
            is_merge=False,
            on_mainline=True
        )
        session.add(commit)
        session.flush()

        # 3. 创建文件记录
        file_record = File(
            repository_id=repo.id,
            path="src/main.py",
            name="main.py",
            extension="py",
            size=1024,
            is_binary=False,
            last_modified=datetime(2024, 1, 15, 10, 30, 0)
        )
        session.add(file_record)
        session.flush()

        # 4. 创建blame行记录
        blame_lines = [
            BlameLine(
                repository_id=repo.id,
                file_id=file_record.id,
                commit_id=commit.id,
                line_number=1,
                content="# -*- coding: utf-8 -*-",
                is_merge_line=False,
                original_line_number=1,
                original_file_path="src/main.py"
            ),
            BlameLine(
                repository_id=repo.id,
                file_id=file_record.id,
                commit_id=commit.id,
                line_number=2,
                content="import os",
                is_merge_line=False,
                original_line_number=2,
                original_file_path="src/main.py"
            ),
            BlameLine(
                repository_id=repo.id,
                file_id=file_record.id,
                commit_id=commit.id,
                line_number=3,
                content="def main():",
                is_merge_line=False,
                original_line_number=3,
                original_file_path="src/main.py"
            )
        ]

        for blame_line in blame_lines:
            session.add(blame_line)

        # 提交事务
        session.commit()

        print("✅ 数据插入成功！")

        # 5. 查询示例
        print("\n📊 查询示例：")

        # 查询所有仓库
        repositories = session.query(Repository).all()
        print(f"仓库数量: {len(repositories)}")

        # 查询特定仓库的提交
        commits = session.query(Commit).filter(
            Commit.repository_id == repo.id
        ).all()
        print(f"提交数量: {len(commits)}")

        # 查询特定文件的blame信息
        blame_info = session.query(BlameLine).join(File).filter(
            File.path == "src/main.py"
        ).all()
        print(f"blame行数: {len(blame_info)}")

        # 查询特定作者的提交
        author_commits = session.query(Commit).filter(
            Commit.author_name == "张三"
        ).all()
        print(f"张三的提交数: {len(author_commits)}")

        # 复杂查询：查询特定时间范围内的blame信息
        from datetime import datetime, timedelta
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        recent_blame = session.query(BlameLine).join(Commit).filter(
            Commit.authored_time >= start_date,
            Commit.authored_time <= end_date
        ).all()
        print(f"2024年的blame行数: {len(recent_blame)}")

    except Exception as e:
        session.rollback()
        print(f"❌ 错误: {e}")
    finally:
        session.close()


def query_examples():
    """查询示例"""
    session = get_db_session()

    try:
        # 1. 按文件类型统计blame信息
        from sqlalchemy import func
        file_stats = session.query(
            File.extension,
            func.count(BlameLine.id).label('line_count')
        ).join(BlameLine).group_by(File.extension).all()

        print("📈 按文件类型统计:")
        for ext, count in file_stats:
            print(f"  {ext or '无扩展名'}: {count} 行")

        # 2. 按作者统计提交数
        author_stats = session.query(
            Commit.author_name,
            func.count(Commit.id).label('commit_count')
        ).group_by(Commit.author_name).all()

        print("\n👥 按作者统计提交数:")
        for author, count in author_stats:
            print(f"  {author}: {count} 次提交")

        # 3. 查询最近修改的文件
        recent_files = session.query(File).order_by(
            File.last_modified.desc()
        ).limit(5).all()

        print("\n📁 最近修改的文件:")
        for file in recent_files:
            print(f"  {file.path} (修改于: {file.last_modified})")

    except Exception as e:
        print(f"❌ 查询错误: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    example_usage()
    query_examples()
