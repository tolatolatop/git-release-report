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
    commits_stats_df = list_commit_stats_with_mp(repo_path, commits_df)

    diff_info_df = dataframe.list_diff_info(repo_path, old_commit, new_commit)
    blame_lines_df = list_blame_lines_with_mp(repo_path, diff_info_df)
    combine_blame_df = pd.merge(blame_lines_df, commits_df, on='sha', how='inner')

    return {
        'commits_df': commits_df,
        'commits_stats_df': commits_stats_df,
        'blame_lines_df': blame_lines_df,
        'diff_info_df': diff_info_df,
        'combine_blame_df': combine_blame_df,
    }


def list_commit_stats_with_chunk(x: tuple[str, str]) -> pd.DataFrame:
    repo_path, commit_id = x
    logger.info(f"Processing chunk: {commit_id}")
    res = dataframe.list_commit_stats(repo_path, commit_id)
    logger.info(f"Processed chunk: {commit_id}")
    return res

def list_commit_stats_with_mp(repo_path: str, commits_df: pd.DataFrame) -> pd.DataFrame:
    """
    使用多进程列出仓库中的commit统计信息
    """
    tmp = []
    with mp.Pool(processes=mp.cpu_count()) as pool:
        tmp = pool.map(list_commit_stats_with_chunk, [(repo_path, x) for x in commits_df['sha'].tolist()])
    return pd.concat(tmp).reset_index(drop=True)


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
