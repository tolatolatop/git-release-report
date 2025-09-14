import pandas as pd
from . import core


def list_commits(repo_path: str, old_commit: str, new_commit: str) -> pd.DataFrame:
    """
    列出仓库中的commit

    Args:
        repo_path: 仓库路径
        old_commit: 第一个提交
        new_commit: 第二个提交

    Returns:
        pd.DataFrame: commit数据框
    """
    return pd.DataFrame([commit.to_dict() for commit in core.list_commits(repo_path, old_commit, new_commit)])


def list_commit_stats(repo_path: str, commit_id: str) -> pd.DataFrame:
    """
    列出仓库中的commit统计信息

    Args:
        repo_path: 仓库路径
        commit_id: 提交id

    Returns:
        pd.DataFrame: commit统计信息数据框
    """
    return pd.DataFrame([commit_stat.to_dict() for commit_stat in core.get_commit_stats(repo_path, commit_id)])
