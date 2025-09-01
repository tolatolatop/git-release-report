from __future__ import annotations
from typing import List
from .models import CommitInfo

# v0.1: we only list merge commits present in range; v0.2: analyze merge-resolved lines via blame to merge sha.


def list_merges(commits: dict[str, CommitInfo]) -> List[CommitInfo]:
    return [c for c in commits.values() if c.is_merge]
