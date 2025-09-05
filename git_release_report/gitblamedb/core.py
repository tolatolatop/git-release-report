import os
import time
import re
import subprocess as sp
from typing import List
from git import Repo, Commit


def find_git_repos(root_dir: str, maxdepth: int = 3) -> List[str]:
    output = sp.check_output(
        [
            'find', '-L', root_dir, '-maxdepth',
            str(maxdepth + 1), '-type', 'd', '-name', '.git'
        ]
    )
    paths = [
        os.path.dirname(path)
        for path in output.decode('utf-8', errors='ignore').strip().splitlines()
    ]

    res = []
    for path in paths:
        try:
            repo = Repo(path)
            if repo.bare:
                continue
            res.append(path)
        except Exception:
            continue
    return


def list_files(repo_path: str, regex: str) -> List[str]:
    repo = Repo(repo_path)
    output = repo.git.ls_tree(repo.head.commit.hexsha,
                              '--full-tree', '--name-only')
    paths = [
        os.path.join(repo_path, path)
        for path in output.decode('utf-8', errors='ignore').strip().splitlines()
    ]

    res = []
    re_match = re.compile(regex)
    for path in paths:
        if re_match.match(path):
            res.append(path)
    return res


def get_file_last_modified(repo_path: str, file_path: str) -> float:
    try:
        return os.stat(os.path.join(repo_path, file_path)).st_mtime
    except Exception:
        return 9999999999
