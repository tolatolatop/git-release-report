import pytest
import logging
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


def test_compare_commits(repo_path, old_commit, new_commit):
    result = compare_commits(repo_path, old_commit, new_commit)
    assert len(result['commits_df']) == 223
    # assert len(result.commits_stats_df) == 17718
    assert len(result['diff_info_df']) == 231
    # 大约2分钟
    assert len(result['blame_lines_df']) == 543180
