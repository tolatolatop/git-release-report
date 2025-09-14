import pytest
from git_release_report.gitblamedb.models import create_sqlite_engine
from git_release_report.gitblamedb.models import init_db
from git_release_report.gitblamedb.models import get_session
from git_release_report.gitblamedb.core import create_blame_repo
from git_release_report.gitblamedb.core import load_data_by_repo_name
from git_release_report.gitblamedb import models
from git_release_report.gitblamedb.core import get_commit
from git_release_report.gitblamedb.core import get_diff_info
from git_release_report.gitblamedb.core import get_commit_stats

@pytest.fixture
def session():
    engine = create_sqlite_engine(':memory:')
    init_db(engine)
    session = get_session(engine)
    yield session
    session.close()


def test_create_blame_repo(session):
    file_cache, blame_lines, commits = create_blame_repo(
        'tests/test_repo', r'^package\.json$', session)
    assert len(file_cache) == 1
    assert file_cache[0].file_path == 'package.json'
    assert len(commits) == 150
    commit_ids = [commit.sha for commit in commits]
    assert "8f35cc4768393b25468416829e980d7550619fb1" in commit_ids
    assert len(blame_lines) == 240
    assert blame_lines[0].file_path == 'package.json'
    assert blame_lines[0].line_number == 1
    assert blame_lines[0].commit_sha == "8f35cc4768393b25468416829e980d7550619fb1"


def test_to_commit_model():
    commit = get_commit('tests/test_repo', '8f35cc4768393b25468416829e980d7550619fb1')
    res = commit.to_dict()
    assert res["sha"] == "8f35cc4768393b25468416829e980d7550619fb1"


def test_diff_info():
    commit_stats = get_commit_stats('tests/test_repo', '6f9e2ae3907')
    assert len(commit_stats) == 5
    assert commit_stats[0].filepath == 'ThirdPartyNotices.txt'

    diffs = get_diff_info('tests/test_repo', '8f35cc4768393b25468416829e980d7550619fb1', '6f9e2ae3907')
    assert len(diffs) == 5
    assert diffs[0].a_path == 'ThirdPartyNotices.txt'
    assert diffs[1].a_path == 'build/lib/typescript/OSSREADME.json'
    assert diffs[1].change_type == "A"
    assert diffs[1].b_path == 'build/lib/typescript/OSSREADME.json'