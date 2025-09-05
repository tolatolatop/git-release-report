import os
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
