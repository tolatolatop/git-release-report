import pytest
from git import Repo
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
    assert commit_df.iloc[0]['is_merge'] == True
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


def test_list_diff_info(repo_path, old_commit, new_commit):
    diff_info_df = ndfb.list_diff_info(repo_path, old_commit[:-1], new_commit)
    assert len(diff_info_df) == 1154
    assert diff_info_df['old_sha'].iloc[0] == 'dfd4b508c8c6'
    assert diff_info_df['new_sha'].iloc[0] == 'f83a4f2a4d8c'
    assert diff_info_df['a_path'].iloc[2] == 'Documentation/ABI/testing/sysfs-devices-system-cpu'
    assert diff_info_df['b_path'].iloc[2] == 'Documentation/ABI/testing/sysfs-devices-system-cpu'
    assert diff_info_df['change_type'].iloc[2] == 'M'


def test_list_blame_lines(repo_path, old_commit, new_commit):
    blame_lines_df = ndfb.list_blame_lines(repo_path, 'fs/erofs/erofs_fs.h')
    assert len(blame_lines_df) == 466
    assert blame_lines_df['sha'].iloc[0] == '29b24f6ca112d168ae17c66343464a2581c573e0'
    assert blame_lines_df['line_number'].iloc[0] == 1
    assert blame_lines_df['file_path'].iloc[0] == 'fs/erofs/erofs_fs.h'
    assert blame_lines_df['repo_path'].iloc[0] == repo_path
    # 因为new_commit是merge commit，可能没有对应的blame信息
    assert blame_lines_df['sha'].str.contains(new_commit).values.sum() == 0

    commit_df = ndfb.list_merge_commits(repo_path, new_commit)
    commit_id = "1fcf686def190"
    assert commit_df['sha'].str.contains(commit_id).values.sum() > 0
    assert blame_lines_df['sha'].str.contains(commit_id).values.sum() > 0

