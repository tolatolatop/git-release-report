from dataclasses import dataclass

import pandas as pd
import multiprocessing as mp
import numpy as np

from .logs import logger
from . import dataframe


@dataclass
class CompareResult:
    commits_df: pd.DataFrame
    commits_stats_df: pd.DataFrame


def compare_commits(repo_path: str, old_commit: str, new_commit: str) -> dict:
    """
    比较两个提交
    """
    commits_df = dataframe.list_commits(repo_path, old_commit, new_commit)
    # tmp = commits_df.apply(lambda x: dataframe.list_commit_stats(repo_path, x['sha']), axis=1)
    # commits_stats_df = pd.concat(tmp.values).reset_index(drop=True)
    commits_stats_df = None

    diff_info_df = dataframe.list_diff_info(repo_path, old_commit, new_commit)
    blame_lines_df = list_blame_lines_with_mp(repo_path, diff_info_df)

    return {
        'commits_df': commits_df,
        'commits_stats_df': commits_stats_df,
        'blame_lines_df': blame_lines_df,
        'diff_info_df': diff_info_df,
    }


def list_blame_lines_with_chunk(x: tuple[str, str]) -> pd.DataFrame:
    repo_path, file_path = x
    logger.info(f"Processing chunk: {file_path}")
    res = dataframe.list_blame_lines(repo_path, file_path)
    logger.info(f"Processed chunk: {file_path}")
    return res

def list_blame_lines_with_mp(repo_path: str, diff_info_df: pd.DataFrame) -> pd.DataFrame:
    """
    使用多进程列出仓库中的blame信息
    """
    tmp = []

    with mp.Pool(processes=mp.cpu_count()) as pool:
        chunks = [(repo_path, file_path) for file_path in diff_info_df['a_path'].tolist()]
        tmp = pool.map(list_blame_lines_with_chunk, chunks)
        blame_lines_df = pd.concat(tmp).reset_index(drop=True)
    return blame_lines_df
