from __future__ import annotations
from collections import defaultdict
from .gitwrap import GitWrap
from .models import SurvivalStat


def compute_survival(g: GitWrap, old: str, new: str, paths: list[str], ignore_ws: bool):
    by_commit = defaultdict(SurvivalStat)
    by_author = defaultdict(SurvivalStat)

    # introduced_lines by commit/author from log --numstat (rough; commit-based)
    raw = g.log_numstat_no_merges(f"{old}..{new}")
    last_tag = None
    for ln in raw.splitlines():
        if '|' in ln and ln.count('|') == 2 and ln.startswith(tuple('0123456789abcdef')):
            sha, an, ae = ln.split('|')
            last_tag = (sha, an, ae)
        elif '\t' in ln and last_tag:
            ins = ln.split('\t')[0]
            try:
                ins_i = int(ins)
            except ValueError:
                ins_i = 0
            sha, an, ae = last_tag
            by_commit[sha].introduced_lines += ins_i
            by_author[f"{an} <{ae}>"] .introduced_lines += ins_i

    # survived_lines using blame --reverse if available; otherwise fallback to final blame filter
    for p in paths:
        try:
            braw = g.blame_reverse(old, new, p, ignore_ws)
        except Exception:
            braw = ''
        sha = an = ae = None
        for ln in (braw.splitlines() if braw else []):
            if len(ln) >= 40 and all(c in '0123456789abcdef' for c in ln[:40]) and ln[40] == ' ':
                sha = ln[:40]
            elif ln.startswith('author '):
                an = ln[7:]
            elif ln.startswith('author-mail '):
                ae = ln.split('<', 1)[-1].rstrip('>')
            elif ln.startswith('\t'):
                if sha and an and ae:
                    by_commit[sha].survived_lines += 1
                    by_author[f"{an} <{ae}>"].survived_lines += 1
    return by_commit, by_author
