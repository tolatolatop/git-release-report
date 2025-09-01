from __future__ import annotations
from collections import defaultdict
from typing import Dict, List
from .writers import write_csv, write_json, write_md, write_commits_survival_json
from ..models import AnalysisResult, BlameAtom


def aggregate_contributors_commit_based(commits, log_stats):
    # placeholder: already computed in survival.introduced part if needed
    return {}


def aggregate_contributors_blame(line_blames: List, ignore_bots):
    counter = defaultdict(int)
    for lb in line_blames:
        for a in lb.atoms:
            key = f"{a.author} <{a.email}>"
            if ignore_bots and ignore_bots(key):
                continue
            counter[key] += 1
    return dict(sorted(counter.items(), key=lambda x: x[1], reverse=True))


def emit_all(result: AnalysisResult, out_dir: str):
    write_json(result, out_dir)
    write_commits_survival_json(result, out_dir)
    # CSV examples
    # ... more writers below
    write_md(result, out_dir)
