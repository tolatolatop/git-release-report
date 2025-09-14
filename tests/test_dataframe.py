import pytest
from git_release_report.gitblamedb.dataframe import list_commits


@pytest.fixture
def repo_path():
    return '.pytest_cache/test_repo'

@pytest.fixture
def old_commit():
    return 'dfd4b508c8c6'

@pytest.fixture
def new_commit():
    return 'f83a4f2a4d8c'

def test_list_commits(repo_path, old_commit, new_commit):
    commit_df = list_commits(repo_path, old_commit, new_commit)
    assert len(commit_df) == 1315
    assert commit_df['sha'].iloc[0] == 'f83a4f2a4d8c485922fba3018a64fc8f4cfd315f'
    assert commit_df['sha'].iloc[-1] == 'a2f54ff15c3bdc0132e20aae041607e2320dbd73'

