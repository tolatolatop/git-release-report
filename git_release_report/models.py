from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class ReleaseSpec:
    repo_path: str
    old: str
    new: str
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    ignore_ws: bool = True
    rename_thresh: int = 90
    copy_thresh: int = 80
    first_parent: bool = False
    mailmap: Optional[str] = None
    bot_filter: Optional[str] = None
    out_dir: str = "out"


@dataclass
class CommitInfo:
    sha: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    authored_time: int
    committed_time: int
    parents: List[str]
    is_merge: bool
    on_mainline: bool = False


@dataclass
class Hunk:
    old_start: int
    old_len: int
    new_start: int
    new_len: int


@dataclass
class FileChange:
    path_old: Optional[str]
    path_new: Optional[str]
    status: str  # A/M/D/R/C/T
    similarity: Optional[int] = None
    is_binary: bool = False
    insertions: int = 0
    deletions: int = 0
    hunks: List[Hunk] = field(default_factory=list)


@dataclass
class BlameAtom:
    author: str
    email: str
    commit_sha: str
    is_merge_line: bool = False


@dataclass
class LineBlameBlock:
    path: str
    new_start: int
    new_len: int
    atoms: List[BlameAtom]


@dataclass
class SurvivalStat:
    introduced_lines: int = 0
    survived_lines: int = 0


@dataclass
class AnalysisResult:
    commits: Dict[str, CommitInfo]
    file_changes: List[FileChange]
    line_blames: List[LineBlameBlock]
    survival_by_commit: Dict[str, SurvivalStat]
    survival_by_author: Dict[str, SurvivalStat]
    merges: List[CommitInfo]
    meta: Dict[str, str] = field(default_factory=dict)
