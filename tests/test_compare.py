import pytest
import logging
from pathlib import Path
import json
import pandas as pd
from git_release_report.gitblamedb.logs import logger
from git_release_report.gitblamedb.compare import compare_commits

logger.setLevel(logging.DEBUG)

@pytest.fixture
def repo_path():
    return '.pytest_cache/test_repo'

@pytest.fixture
def old_commit():
    return '467360e29595^'

@pytest.fixture
def new_commit():
    return 'f83a4f2a4d8c'


def save_result(cache, key, result: dict):
    result = result.copy()
    cache_path = Path(f".pytest_cache/{key}")
    cache_path.mkdir(parents=True, exist_ok=True)
    for k, v in result.items():
        v.to_csv(cache_path / f"{k}.csv", index=False)
        result[k] = f"{k}.csv"
    cache.set(key, result)


def load_result(cache, key):
    cache_path = Path(f".pytest_cache/{key}")
    result = cache.get(key, {})
    for k, v in result.items():
        result[k] = pd.read_csv(cache_path / v, index_col=False)
    return result


def test_compare_commits(cache, repo_path, old_commit, new_commit):
    key = f"{old_commit[:-1]}_{new_commit}"
    result = load_result(cache, key)
    if len(result.keys()) == 0:
        result = compare_commits(repo_path, old_commit, new_commit)
        save_result(cache, key, result)
    assert len(result['commits_df']) == 223
    assert len(result['commits_stats_df']) == 968
    assert len(result['diff_info_df']) == 231
    # 大约2分钟
    assert len(result['blame_lines_df']) == 543180
