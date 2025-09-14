import pandas as pd
from . import core


def list_commits(repo_path: str, rev_1: str, rev_2: str) -> pd.DataFrame:
    """
    列出仓库中的commit

    Args:
        repo_path: 仓库路径
        rev_1: 第一个提交
        rev_2: 第二个提交

    Returns:
        pd.DataFrame: commit数据框
    """
    return pd.DataFrame([commit.to_dict() for commit in core.list_commits(repo_path, rev_1, rev_2)])