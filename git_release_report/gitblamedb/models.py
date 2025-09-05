from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, PrimaryKeyConstraint, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Commit(Base):
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

    __table_args__ = (
        UniqueConstraint('repo_name', 'sha', name='uq_commit_repo_sha'),
    )


class FileCache(Base):
    __tablename__ = 'file_cache'
    id = Column(Integer, primary_key=True)
    repo_name = Column(String(255), nullable=False)
    file_path = Column(String(2048), nullable=False)
    last_modified = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint('repo_name', 'file_path',
                         name='uq_filecache_repo_path'),
    )


class BlameLine(Base):
    __tablename__ = 'blame_lines'
    id = Column(Integer, primary_key=True)
    repo_name = Column(String(255), nullable=False)
    file_path = Column(String(2048), nullable=False)
    line_number = Column(Integer, nullable=False)
    commit_sha = Column(String(40), nullable=False)

    __table_args__ = (
        UniqueConstraint('repo_name', 'file_path', 'line_number',
                         name='uq_blameline_repo_path_line'),
    )
