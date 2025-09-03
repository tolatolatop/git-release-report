"""
Git Blame数据库模型
使用SQLAlchemy实现git blame信息的持久化存储
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    Index,
    UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.sql import func

Base = declarative_base()


class Repository(Base):
    """仓库信息表"""
    __tablename__ = 'repositories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment='仓库名称')
    path = Column(String(500), nullable=False, comment='仓库路径')
    url = Column(String(500), comment='仓库URL')
    description = Column(Text, comment='仓库描述')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(),
                        onupdate=func.now(), comment='更新时间')

    # 关系
    commits = relationship(
        "Commit", back_populates="repository", cascade="all, delete-orphan")
    files = relationship("File", back_populates="repository",
                         cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_repo_name', 'name'),
        Index('idx_repo_path', 'path'),
        UniqueConstraint('name', 'path', name='uq_repo_name_path'),
    )


class Commit(Base):
    """提交信息表"""
    __tablename__ = 'commits'

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey(
        'repositories.id'), nullable=False)
    sha = Column(String(40), nullable=False, comment='提交SHA')
    short_sha = Column(String(8), comment='短SHA')
    author_name = Column(String(255), nullable=False, comment='作者姓名')
    author_email = Column(String(255), nullable=False, comment='作者邮箱')
    committer_name = Column(String(255), nullable=False, comment='提交者姓名')
    committer_email = Column(String(255), nullable=False, comment='提交者邮箱')
    authored_time = Column(DateTime, nullable=False, comment='作者时间')
    committed_time = Column(DateTime, nullable=False, comment='提交时间')
    message = Column(Text, comment='提交信息')
    is_merge = Column(Boolean, default=False, comment='是否为合并提交')
    on_mainline = Column(Boolean, default=False, comment='是否在主线上')
    created_at = Column(DateTime, default=func.now(), comment='记录创建时间')

    # 关系
    repository = relationship("Repository", back_populates="commits")
    blame_lines = relationship(
        "BlameLine", back_populates="commit", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_commit_sha', 'sha'),
        Index('idx_commit_repo_sha', 'repository_id', 'sha'),
        Index('idx_commit_author', 'author_name', 'author_email'),
        Index('idx_commit_time', 'authored_time'),
        UniqueConstraint('repository_id', 'sha', name='uq_commit_repo_sha'),
    )


class File(Base):
    """文件信息表"""
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey(
        'repositories.id'), nullable=False)
    path = Column(String(1000), nullable=False, comment='文件路径')
    name = Column(String(255), comment='文件名')
    extension = Column(String(20), comment='文件扩展名')
    size = Column(Integer, comment='文件大小(字节)')
    is_binary = Column(Boolean, default=False, comment='是否为二进制文件')
    last_modified = Column(DateTime, comment='最后修改时间')
    created_at = Column(DateTime, default=func.now(), comment='记录创建时间')
    updated_at = Column(DateTime, default=func.now(),
                        onupdate=func.now(), comment='记录更新时间')

    # 关系
    repository = relationship("Repository", back_populates="files")
    blame_lines = relationship(
        "BlameLine", back_populates="file", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_file_path', 'path'),
        Index('idx_file_repo_path', 'repository_id', 'path'),
        Index('idx_file_extension', 'extension'),
        Index('idx_file_modified', 'last_modified'),
        UniqueConstraint('repository_id', 'path', name='uq_file_repo_path'),
    )


class BlameLine(Base):
    """Git Blame行信息表"""
    __tablename__ = 'blame_lines'

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey(
        'repositories.id'), nullable=False)
    file_id = Column(Integer, ForeignKey('files.id'), nullable=False)
    commit_id = Column(Integer, ForeignKey('commits.id'), nullable=False)

    line_number = Column(Integer, nullable=False, comment='行号')
    content = Column(Text, comment='行内容')
    is_merge_line = Column(Boolean, default=False, comment='是否为合并行')

    # 原始blame信息
    original_line_number = Column(Integer, comment='原始行号')
    original_file_path = Column(String(1000), comment='原始文件路径')

    # 时间戳
    blamed_at = Column(DateTime, default=func.now(), comment='blame分析时间')
    created_at = Column(DateTime, default=func.now(), comment='记录创建时间')

    # 关系
    repository = relationship("Repository")
    file = relationship("File", back_populates="blame_lines")
    commit = relationship("Commit", back_populates="blame_lines")

    # 索引
    __table_args__ = (
        Index('idx_blame_repo_file_line',
              'repository_id', 'file_id', 'line_number'),
        Index('idx_blame_commit', 'commit_id'),
        Index('idx_blame_line_number', 'line_number'),
        Index('idx_blame_blamed_at', 'blamed_at'),
        UniqueConstraint('repository_id', 'file_id',
                         'line_number', name='uq_blame_repo_file_line'),
    )


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, database_url: str = "sqlite:///git_blame.db"):
        """
        初始化数据库管理器

        Args:
            database_url: 数据库连接URL
        """
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            echo=False,  # 设置为True可以看到SQL语句
            pool_pre_ping=True,  # 连接池预检查
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """删除所有表"""
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()


# 全局数据库管理器实例
db_manager = DatabaseManager()


def get_db_session() -> Session:
    """获取数据库会话的便捷函数"""
    return db_manager.get_session()


def init_database(database_url: str = "sqlite:///git_blame.db"):
    """
    初始化数据库

    Args:
        database_url: 数据库连接URL
    """
    global db_manager
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()


def close_database():
    """关闭数据库连接"""
    global db_manager
    db_manager.close()
