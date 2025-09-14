from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, PrimaryKeyConstraint, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session
from dataclasses import dataclass
from collections import defaultdict
from typing import List, TypeVar, Generic, Dict, Iterator, Type
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine as create_engine_func

Base = declarative_base()

# 定义类型变量
T = TypeVar('T')


class Model:
    _unique_fields__ = []

    def to_dict(self):
        out = dict((key, value) for key, value in self.__dict__.items() if not key.startswith('_'))
        if "id" not in out:
            out["id"] = -1
        return out

class Commit(Base, Model):
    __tablename__ = 'commits'
    id = Column(Integer, primary_key=True)
    repo_name = Column(String(255), nullable=False)
    sha = Column(String(40), unique=True, nullable=False)
    commit_message = Column(Text, nullable=False)
    commit_time = Column(Integer, nullable=False)
    author_name = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    committer_name = Column(String(255), nullable=False)
    committer_email = Column(String(255), nullable=False)
    is_merge = Column(Boolean, nullable=False)

    _unique_fields__ = ['repo_name', 'sha']

    __table_args__ = (
        UniqueConstraint(*_unique_fields__, name='uq_commit_repo_sha'),
    )


class DiffInfo(Base, Model):
    __tablename__ = 'diff_info'
    id = Column(Integer, primary_key=True)
    repo_name = Column(String(255), nullable=False)
    old_sha = Column(String(40), nullable=False)
    new_sha = Column(String(40), nullable=False)
    a_path = Column(String(2048), nullable=False)
    b_path = Column(String(2048), nullable=False)
    change_type = Column(String(1), nullable=False)
    

class CommitStat(Base, Model):
    __tablename__ = 'commit_stat'
    id = Column(Integer, primary_key=True)
    repo_name = Column(String(255), nullable=False)
    sha = Column(String(40), nullable=False)
    filepath = Column(String(2048), nullable=False)
    change_type = Column(String(1), nullable=False)
    add_lines = Column(Integer, nullable=False)
    del_lines = Column(Integer, nullable=False)

class FileCache(Base, Model):
    __tablename__ = 'file_cache'
    id = Column(Integer, primary_key=True)
    repo_name = Column(String(255), nullable=False)
    file_path = Column(String(2048), nullable=False)
    last_modified = Column(DateTime, nullable=False)

    _unique_fields__ = ['repo_name', 'file_path']

    __table_args__ = (
        UniqueConstraint(*_unique_fields__,
                         name='uq_filecache_repo_path'),
    )


class BlameLine(Base, Model):
    __tablename__ = 'blame_lines'
    id = Column(Integer, primary_key=True)
    repo_name = Column(String(255), nullable=False)
    file_path = Column(String(2048), nullable=False)
    line_number = Column(Integer, nullable=False)
    sha = Column(String(40), nullable=False)

    _unique_fields__ = ['repo_name', 'file_path', 'line_number']

    __table_args__ = (
        UniqueConstraint(*_unique_fields__,
                         name='uq_blameline_repo_path_line'),
    )


@dataclass
class RepoData:
    repo_name: str
    commits: Dict[str, Commit]
    file_cache: Dict[str, FileCache]
    blame_lines: Dict[str, Dict[int, BlameLine]]

    def filter(self, inputs: List[T]) -> List[T]:
        """泛型过滤函数，根据repo_name过滤输入列表"""
        if len(inputs) == 0:
            return []
        data_one = inputs[0]
        if isinstance(data_one, Commit):
            return list(self.filter_commits(inputs))
        elif isinstance(data_one, FileCache):
            return list(self.filter_file_cache(inputs))
        elif isinstance(data_one, BlameLine):
            return list(self.filter_blame_lines(inputs))
        else:
            raise ValueError(f"Unknown type: {type(data_one)}")

    def filter_commits(self, inputs: List[Commit]) -> Iterator[Commit]:
        for input in inputs:
            if input.sha not in self.commits:
                yield input

    def filter_file_cache(self, inputs: List[FileCache]) -> Iterator[FileCache]:
        for input in inputs:
            if input.file_path not in self.file_cache:
                yield input

    def filter_blame_lines(self, inputs: List[BlameLine]) -> Iterator[BlameLine]:
        for input in inputs:
            if input.file_path not in self.blame_lines or input.line_number not in self.blame_lines[input.file_path]:
                yield input


def load_data_by_repo_name(session: Session, repo_name: str, exclude: List[Type[Model]]) -> RepoData:
    if Commit not in exclude:
        commits = session.query(Commit).filter(
            Commit.repo_name == repo_name).all()
    else:
        commits = []
    commits_dict = {commit.sha: commit for commit in commits}

    if FileCache not in exclude:
        file_cache = session.query(FileCache).filter(
            FileCache.repo_name == repo_name).all()
    else:
        file_cache = []
    file_cache_dict = {
        file_cache.file_path: file_cache for file_cache in file_cache}

    if BlameLine not in exclude:
        blame_lines = session.query(BlameLine).filter(
            BlameLine.repo_name == repo_name).all()
    else:
        blame_lines = []

    blame_lines_dict = defaultdict(dict)
    for blame_line in blame_lines:
        blame_lines_dict[blame_line.file_path][blame_line.line_number] = blame_line
    return RepoData(repo_name, commits_dict, file_cache_dict, blame_lines_dict)


def init_db(engine: Engine):
    Base.metadata.create_all(engine)


def get_session(engine: Engine):
    return Session(engine)


def create_engine(db_url: str):
    return create_engine_func(db_url)


def create_sqlite_engine(db_path: str):
    return create_engine_func(f'sqlite:///{db_path}')
