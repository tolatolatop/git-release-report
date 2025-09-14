import pytest
from git_release_report.gitblamedb import dataframe as ndfb
from git_release_report.gitblamedb.dataframe import list_commits


@pytest.fixture
def repo_path():
    return '.pytest_cache/test_repo'

@pytest.fixture
def old_commit():
    return 'dfd4b508c8c6^'

@pytest.fixture
def new_commit():
    return 'f83a4f2a4d8c'

def test_list_commits(repo_path, old_commit, new_commit):
    commit_df = list_commits(repo_path, old_commit, new_commit)
    assert len(commit_df) == 1340
    assert commit_df['sha'].iloc[0] == 'f83a4f2a4d8c485922fba3018a64fc8f4cfd315f'
    filter = commit_df['sha'].str.contains(old_commit[:-1]).values
    assert len(commit_df[filter].values) == 1


def test_list_commit_stats(repo_path, old_commit, new_commit):
    commit_stats_df = ndfb.list_commit_stats(repo_path, new_commit)
    assert len(commit_stats_df) == 5
    assert commit_stats_df['sha'].iloc[0] == 'f83a4f2a4d8c485922fba3018a64fc8f4cfd315f'
    assert commit_stats_df['filepath'].iloc[0] == 'fs/erofs/erofs_fs.h'
    assert commit_stats_df['change_type'].iloc[0] == 'M'
    assert commit_stats_df['add_lines'].iloc[0] == 5
    assert commit_stats_df['del_lines'].iloc[0] == 3
