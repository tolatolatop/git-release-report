import pytest
from git_release_report.gitblamedb.models import create_sqlite_engine
from git_release_report.gitblamedb.models import init_db
from git_release_report.gitblamedb.models import get_session
from git_release_report.gitblamedb.core import create_blame_repo


@pytest.fixture
def session():
    engine = create_sqlite_engine(':memory:')
    init_db(engine)
    session = get_session(engine)
    yield session
    session.close()


def test_create_blame_repo(session):
    create_blame_repo('tests/test_repo', r'.*\.md', session)
