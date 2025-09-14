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


def list_merge_commits(repo_path: str, commit_id: str) -> pd.DataFrame:
    """
    列出仓库中的merge commit

    Args:
        repo_path: 仓库路径
        commit_id: 提交id

    Returns:
        pd.DataFrame: merge commit数据框
    """
    return pd.DataFrame([commit.to_dict() for commit in core.list_commits(repo_path, f"{commit_id}^1", f"{commit_id}^2")])


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


def list_diff_info(repo_path: str, old_commit: str, new_commit: str) -> pd.DataFrame:
    """
    列出仓库中的diff信息

    Args:
        repo_path: 仓库路径
        old_commit: 第一个提交
        new_commit: 第二个提交

    Returns:
        pd.DataFrame: diff信息数据框
    """
    return pd.DataFrame([diff_info.to_dict() for diff_info in core.get_diff_info(repo_path, old_commit, new_commit)])


def list_blame_lines(repo_path: str, file_path: str) -> pd.DataFrame:
    """
    列出仓库中的blame信息

    Args:
        repo_path: 仓库路径
        file_path: 文件路径

    Returns:
        pd.DataFrame: blame信息数据框
    """

    df = pd.DataFrame([blame_line for blame_line in core.get_file_blame(repo_path, file_path)], columns=['sha', 'line_number'])
    df['repo_path'] = repo_path
    df['file_path'] = file_path
    return df
