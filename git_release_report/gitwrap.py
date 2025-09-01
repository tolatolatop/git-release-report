from __future__ import annotations
from git import Repo
from typing import Iterable, List


class GitWrap:
    def __init__(self, repo_path: str):
        self.repo = Repo(repo_path)
        assert not self.repo.bare
        self.git = self.repo.git

    def merge_base(self, a: str, b: str) -> str:
        return self.git.merge_base(a, b).strip()

    def iter_commits_range(self, spec: str):
        return self.repo.iter_commits(spec)

    def diff_raw(self, old: str, new: str, ignore_ws: bool, rename: int, copy: int,
                 include: List[str], exclude: List[str], unified0: bool = True) -> str:
        args = [old, new, "-M", f"--find-renames={rename}%",
                "-C", f"--find-copies={copy}%", "--numstat", "--patch"]
        if ignore_ws:
            args.append("-w")
        if unified0:
            args.append("-U0")
        args.append("--")
        args.extend(include or ["."])
        for ex in exclude or []:
            args.append(f":(exclude){ex}")
        return self.git.diff(*args)

    def blame_porcelain(self, rev: str, path: str, start: int, end: int, ignore_ws: bool) -> str:
        args = [rev, "--line-porcelain", "-L", f"{start},{end}", "--", path]
        if ignore_ws:
            args.insert(1, "-w")
            args.insert(2, "-M")
            args.insert(3, "-C")
        return self.git.blame(*args)

    def log_numstat_no_merges(self, spec: str) -> str:
        return self.git.log(spec, "--no-merges", "--numstat", "--format=%H|%an|%ae")

    def blame_reverse_supported(self) -> bool:
        try:
            self.git.blame("--help")
            return True
        except Exception:
            return False

    def blame_reverse(self, old: str, new: str, path: str, ignore_ws: bool) -> str:
        # git blame --reverse OLD..NEW -- path
        args = ["--reverse", f"{old}..{new}"]
        if ignore_ws:
            args.insert(0, "-w")
            args.insert(1, "-M")
            args.insert(2, "-C")
        args.extend(["--", path])
        return self.git.blame(*args)
