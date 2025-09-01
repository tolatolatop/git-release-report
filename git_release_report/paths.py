from __future__ import annotations
from typing import Iterable


def collect_paths_from_file_changes(file_changes) -> list[str]:
    paths = set()
    for fc in file_changes:
        if fc.path_new:
            paths.add(fc.path_new)
    return sorted(paths)
