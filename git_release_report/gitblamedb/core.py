import os
import time
import re
import subprocess as sp
from typing import List, Tuple
from git import Repo, Commit
from .models import Commit as CommitModel
from .models import BlameLine as BlameLineModel
from .models import FileCache as FileCacheModel
from .models import RepoData
from .models import load_data_by_repo_name
from sqlalchemy.orm import Session


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
    output: str = repo.git.ls_tree(repo.head.commit.hexsha,
                                   '--full-tree', '--name-only')
    paths = [
        path
        for path in output.strip().splitlines()
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


def get_file_blame(repo_path: str, file_path: str) -> List[Tuple[str, int]]:
    info_match = re.compile(
        r'^(?P<commit_sha>[\^0-9a-f]+)\s+\(.*?(?P<line_number>\d+)\)', re.MULTILINE
    )
    repo = Repo(repo_path)
    output = repo.git.blame('-l', '-w', '-M', '-C', '--', file_path)
    info_matches = info_match.findall(output)
    return [(match[0], int(match[1])) for match in info_matches]


def to_commit_model(repo_name: str, commit: Commit) -> CommitModel:
    return CommitModel(
        repo_name=repo_name,
        sha=commit.hexsha,
        commit_message=commit.message,
        commit_time=commit.authored_date,
        author_name=commit.author.name,
        author_email=commit.author.email,
        committer_name=commit.committer.name,
        committer_email=commit.committer.email,
    )


def to_blame_line_model(repo_name: str, file_path: str, blame: Tuple[str, int]) -> BlameLineModel:
    return BlameLineModel(
        repo_name=repo_name,
        file_path=file_path,
        line_number=blame[1],
        commit_sha=blame[0],
    )


def to_file_cache_model(repo_name: str, file_path: str) -> FileCacheModel:
    return FileCacheModel(
        repo_name=repo_name,
        file_path=file_path,
        last_modified=get_file_last_modified(repo_name, file_path),
    )


def filter_by_last_modified(repo_data: RepoData, file_paths: List[FileCacheModel]) -> List[FileCacheModel]:
    out = []
    for file_path in file_paths:
        if file_path not in repo_data.file_cache:
            out.append(file_path)
        elif file_path.last_modified <= repo_data.file_cache[file_path.file_path].last_modified:
            out.append(file_path)
        else:
            pass
    return out


def create_blame_repo(repo_path: str, regex: str, sess: Session):
    repo_name = os.path.basename(repo_path)
    file_paths = list_files(repo_path, regex)
    file_cache = [
        to_file_cache_model(repo_name, file_path)
        for file_path in file_paths
    ]
    repo_data = load_data_by_repo_name(sess, repo_name, [FileCacheModel])
    file_cache = filter_by_last_modified(repo_data, file_cache)

    blame_lines = []
    for f in file_cache:
        blame_lines.extend(get_file_blame(repo_path, f.file_path))

    blame_lines = [
        to_blame_line_model(repo_name, f.file_path, blame)
        for blame in blame_lines
    ]

    commit_id_set = set()
    for blame_line in blame_lines:
        commit_id_set.add(blame_line.commit_sha)

    repo = Repo(repo_path)
    commits = [repo.commit(commit_id) for commit_id in commit_id_set]
    commits = [to_commit_model(repo_name, commit) for commit in commits]

    return file_cache, blame_lines, commits
