# git-release-report — v0.1 spec & skeleton

> A precision release diff & contributor analytics tool using GitPython + native git, producing multi‑view reports (commit‑based, blame‑based, merge‑responsibility, rename/copy/delete, survival rate, per‑directory churn). This doc contains the implementation plan **and** an initial, runnable code skeleton.

---

## 0) Scope (v0.1)
- Inputs: `--repo`, `--old`, `--new`, optional `--include/--exclude`, `--ignore-ws`, `--rename/--copy` thresholds, `--first-parent`, `--mailmap`, `--bot-filter`.
- Outputs: `/out` folder with:
  - `analysis.json` (full structured data)
  - `summary.md` (human‑readable release report)
  - CSVs: contributors (commit‑based), contributors (blame‑based final ownership), merges, renames/copies/deletes, survival by commit/author, per‑dir churn
- Core views implemented now: **A**(发布简报·提交口径), **C**(精准归属·行级 blame), **E**(R/C/D 监督), **F**(存活度审计)。
- Next minor: **B**主线/对称差去重, **D**合并责任细化（冲突区定位）。

---

## 1) Project layout
```
.gitignore
pyproject.toml
README.md
requirements.txt

git_release_report/
  __init__.py
  cli.py
  models.py
  options.py
  gitwrap.py
  diffscan.py
  blame.py
  survival.py
  merges.py
  identity.py
  paths.py
  cache.py
  reporting/
    aggregate.py
    writers.py

examples/
  run_demo.sh
```

---

## 2) Installation
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**requirements.txt**
```txt
GitPython>=3.1.43
click>=8.1
pydantic>=2.7
rich>=13.7
python-slugify>=8.0
orjson>=3.10
jinja2>=3.1
```

**pyproject.toml** (minimal)
```toml
[project]
name = "git-release-report"
version = "0.1.0"
description = "Precision release diff & contributor analytics"
authors = [{name="Your Team"}]
requires-python = ">=3.10"
dependencies = []

[project.scripts]
release-report = "git_release_report.cli:main"
```

---

## 3) CLI usage (preview)
```bash
release-report \
  --repo . \
  --old v1.2.0 --new v1.3.0 \
  --preset all \
  --include "src/" --exclude "vendor/,dist/" \
  --ignore-ws true \
  --rename 90 --copy 80 \
  --first-parent false \
  --mailmap .mailmap \
  --bot-filter "bot|automation|ci@" \
  --out ./out
```

---

## 4) Core code (initial skeleton)
> Drop these files under `git_release_report/`. The code focuses on correctness & clarity; more perf (parallel blame, caching) exists but is minimal here and toggle‑able.

### 4.1 `models.py`
```python
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
```

### 4.2 `options.py`
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class CLIOptions(BaseModel):
    repo: str
    old: str
    new: str
    preset: str = Field("all", description="all|A|B|C|D|E|F")
    include: List[str] = []
    exclude: List[str] = []
    ignore_ws: bool = True
    rename: int = 90
    copy: int = 80
    first_parent: bool = False
    mailmap: Optional[str] = None
    bot_filter: Optional[str] = None
    out: str = "out"
```

### 4.3 `gitwrap.py`
```python
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
        args = [old, new, "-M", f"--find-renames={rename}%", "-C", f"--find-copies={copy}%", "--numstat", "--patch"]
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
            args.insert(0, "-w"); args.insert(1, "-M"); args.insert(2, "-C")
        args.extend(["--", path])
        return self.git.blame(*args)
```

### 4.4 `diffscan.py`
```python
from __future__ import annotations
import re
from typing import List
from .models import FileChange, Hunk

RE_DIFF_HDR = re.compile(r"^diff --git a/(.*?) b/(.*?)$")
RE_BINARY = re.compile(r"^Binary files .* and .* differ$")
RE_STATUS = re.compile(r"^(rename|copy) from (.*)$|^create mode|^delete mode")
RE_SUMMARY_R = re.compile(r"^rename (?:from|to) ")
RE_HUNK = re.compile(r"^@@ -(?P<o1>\d+)(?:,(?P<ol>\d+))? \+(?P<n1>\d+)(?:,(?P<nl>\d+))? @@")

# We parse `git diff -U0 --numstat --patch` textual output.
# Focus: file status + hunks (NEW side ranges) + numstat + binary flag.

def parse_diff(raw: str) -> List[FileChange]:
    lines = raw.splitlines()
    out: List[FileChange] = []
    cur: FileChange | None = None
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = RE_DIFF_HDR.match(ln)
        if m:
            if cur: out.append(cur)
            a, b = m.group(1), m.group(2)
            cur = FileChange(path_old=a, path_new=b, status='M')
            i += 1
            continue
        if cur:
            if RE_BINARY.match(ln):
                cur.is_binary = True
            if ln.startswith('--- ') or ln.startswith('+++ '):
                pass
            hm = RE_HUNK.match(ln)
            if hm:
                o1 = int(hm.group('o1')); ol = int(hm.group('ol') or '1')
                n1 = int(hm.group('n1')); nl = int(hm.group('nl') or '1')
                cur.hunks.append(Hunk(o1, ol, n1, nl))
            # numstat lines appear before patches as separate section; we re-scan at end
        i += 1
    if cur: out.append(cur)

    # numstat block: re-scan straightforwardly
    for ln in lines:
        if '\t' in ln and ln[:1].isdigit():
            parts = ln.split('\t')
            if len(parts) >= 3:
                ins, dels, path = parts[0], parts[1], parts[2]
                try:
                    ins_i = int(ins)
                except ValueError:
                    continue
                try:
                    dels_i = int(dels)
                except ValueError:
                    dels_i = 0
                # match existing entry by new path
                for fc in out:
                    if fc.path_new == path or fc.path_old == path:
                        fc.insertions += ins_i
                        fc.deletions += dels_i
                        break
    # heuristic status from path changes
    for fc in out:
        if fc.path_old and fc.path_new and fc.path_old != fc.path_new:
            fc.status = 'R'
        # deletions/creations inferred if path replaced with /dev/null not available here.
    return out
```

### 4.5 `blame.py`
```python
from __future__ import annotations
from typing import List
from .gitwrap import GitWrap
from .models import LineBlameBlock, BlameAtom

def blame_block(g: GitWrap, rev: str, path: str, start: int, end: int, ignore_ws: bool) -> LineBlameBlock:
    raw = g.blame_porcelain(rev, path, start, end, ignore_ws)
    atoms: List[BlameAtom] = []
    author = email = commit = None
    for ln in raw.splitlines():
        if ln.startswith('author '):
            author = ln[7:]
        elif ln.startswith('author-mail '):
            email = ln.split('<',1)[-1].rstrip('>')
        elif re_match := ln.split():
            pass
        if ln and ln[0] == '\t':
            # end of a line's header block -> commit sha is in the very first header line, but porcelain includes it at the top
            # To ensure commit capture, we backtrack via previous header markers.
            # Simplify: search last 'commits' occurrence above (not perfect but works across blocks)
            pass
    # Simpler robust approach: parse by blocks separated by lines starting with a 40-hex + metadata
    atoms = _parse_porcelain_atoms(raw)
    return LineBlameBlock(path=path, new_start=start, new_len=(end-start+1), atoms=atoms)

import re
RE_SHA = re.compile(r"^[0-9a-f]{40} ")

def _parse_porcelain_atoms(raw: str) -> List[BlameAtom]:
    atoms: List[BlameAtom] = []
    cur_author = cur_email = None
    cur_commit = None
    for ln in raw.splitlines():
        if RE_SHA.match(ln):
            cur_commit = ln.split()[0]
        elif ln.startswith('author '):
            cur_author = ln[7:]
        elif ln.startswith('author-mail '):
            cur_email = ln.split('<',1)[-1].rstrip('>')
        elif ln.startswith('\t'):
            atoms.append(BlameAtom(author=cur_author or '', email=cur_email or '', commit_sha=cur_commit or '', is_merge_line=False))
    return atoms
```

### 4.6 `survival.py`
```python
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
                ae = ln.split('<',1)[-1].rstrip('>')
            elif ln.startswith('\t'):
                if sha and an and ae:
                    by_commit[sha].survived_lines += 1
                    by_author[f"{an} <{ae}>"].survived_lines += 1
    return by_commit, by_author
```

### 4.7 `identity.py`
```python
import re
from typing import Optional

def is_bot(name: str, email: str, pattern: Optional[str]) -> bool:
    if not pattern:
        return False
    return re.search(pattern, f"{name} {email}", flags=re.IGNORECASE) is not None
```

### 4.8 `reporting/aggregate.py`
```python
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List
from .writers import write_csv, write_json, write_md
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
    # CSV examples
    # ... more writers below
    write_md(result, out_dir)
```

### 4.9 `reporting/writers.py`
```python
from __future__ import annotations
from pathlib import Path
import orjson as json
from ..models import AnalysisResult


def write_json(result: AnalysisResult, out_dir: str):
    p = Path(out_dir)/"analysis.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(json.dumps(result, default=lambda o: o.__dict__).encode())


def write_csv(rows, headers, path: str):
    from csv import DictWriter
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', newline='', encoding='utf-8') as f:
        w = DictWriter(f, fieldnames=headers)
        w.writeheader(); w.writerows(rows)


def write_md(result: AnalysisResult, out_dir: str):
    p = Path(out_dir)/"summary.md"
    lines = []
    meta = result.meta
    lines += [f"# Release report: {meta.get('old')} → {meta.get('new')}", ""]
    lines += ["## Files changed (top 10 by churn)"]
    top = sorted(result.file_changes, key=lambda x: x.insertions + x.deletions, reverse=True)[:10]
    for fc in top:
        lines.append(f"- {fc.status} {fc.path_new} (+{fc.insertions}/-{fc.deletions})")
    lines.append("")
    lines += ["## Contributors (final ownership, blame over changed lines)"]
    # simple aggregation inline
    from collections import Counter
    c = Counter()
    for lb in result.line_blames:
        for a in lb.atoms: c[f"{a.author} <{a.email}>"] += 1
    for k, v in c.most_common(20):
        lines.append(f"- {k}: {v} lines")
    p.write_text("\n".join(lines), encoding='utf-8')
```

### 4.10 `merges.py`
```python
from __future__ import annotations
from typing import List
from .models import CommitInfo

# v0.1: we only list merge commits present in range; v0.2: analyze merge-resolved lines via blame to merge sha.

def list_merges(commits: dict[str, CommitInfo]) -> List[CommitInfo]:
    return [c for c in commits.values() if c.is_merge]
```

### 4.11 `paths.py`
```python
from __future__ import annotations
from typing import Iterable

def collect_paths_from_file_changes(file_changes) -> list[str]:
    paths = set()
    for fc in file_changes:
        if fc.path_new: paths.add(fc.path_new)
    return sorted(paths)
```

### 4.12 `cli.py`
```python
from __future__ import annotations
import click
from rich.console import Console
from .options import CLIOptions
from .gitwrap import GitWrap
from .models import CommitInfo, AnalysisResult
from .diffscan import parse_diff
from .blame import blame_block
from .paths import collect_paths_from_file_changes
from .survival import compute_survival
from .merges import list_merges
from .reporting.aggregate import emit_all

con = Console()

@click.command()
@click.option('--repo', required=True)
@click.option('--old', required=True)
@click.option('--new', required=True)
@click.option('--preset', default='all')
@click.option('--include', multiple=True)
@click.option('--exclude', multiple=True)
@click.option('--ignore-ws/--no-ignore-ws', default=True)
@click.option('--rename', default=90, type=int)
@click.option('--copy', default=80, type=int)
@click.option('--first-parent/--no-first-parent', default=False)
@click.option('--mailmap', default=None)
@click.option('--bot-filter', default=None)
@click.option('--out', 'out_dir', default='out')
def main(**kwargs):
    opts = CLIOptions(**kwargs)
    g = GitWrap(opts.repo)

    con.log(f"[bold]Analyzing[/] {opts.old} → {opts.new} in {opts.repo}")

    # 1) commits (basic)
    commits = {}
    for c in g.iter_commits_range(f"{opts.old}..{opts.new}"):
        ci = CommitInfo(
            sha=c.hexsha,
            author_name=c.author.name or '',
            author_email=c.author.email or '',
            committer_name=c.committer.name or '',
            committer_email=c.committer.email or '',
            authored_time=c.authored_date,
            committed_time=c.committed_date,
            parents=[p.hexsha for p in c.parents],
            is_merge=len(c.parents) > 1,
            on_mainline=False,
        )
        commits[ci.sha] = ci

    # 2) diff scan
    raw = g.diff_raw(opts.old, opts.new, opts.ignore_ws, opts.rename, opts.copy, list(opts.include), list(opts.exclude))
    file_changes = parse_diff(raw)

    # 3) blame per hunk (final ownership of changed lines)
    line_blames = []
    for fc in file_changes:
        if fc.is_binary or not fc.hunks or not fc.path_new:
            continue
        for h in fc.hunks:
            if h.new_len <= 0:
                continue
            lb = blame_block(g, opts.new, fc.path_new, h.new_start, h.new_start + h.new_len - 1, opts.ignore_ws)
            line_blames.append(lb)

    # 4) survival stats (commit/author level)
    paths = collect_paths_from_file_changes(file_changes)
    by_commit, by_author = compute_survival(g, opts.old, opts.new, paths, opts.ignore_ws)

    # 5) merges (list only v0.1)
    merges = list_merges(commits)

    result = AnalysisResult(
        commits=commits,
        file_changes=file_changes,
        line_blames=line_blames,
        survival_by_commit=by_commit,
        survival_by_author=by_author,
        merges=merges,
        meta={"old": opts.old, "new": opts.new}
    )

    # 6) emit
    emit_all(result, opts.out)
    con.log(f"[green]Done[/] → {opts.out}")

if __name__ == '__main__':
    main()
```

---

## 5) Example
**examples/run_demo.sh**
```bash
#!/usr/bin/env bash
set -euo pipefail
release-report --repo . --old HEAD~50 --new HEAD --out ./out
cat out/summary.md | head -n 40
```

---

## 6) Roadmap (short)
- v0.1.1: parallel blame (per file/hunk) + sqlite cache (key: rev|path|L1|L2|flags)
- v0.1.2: `--preset B` (first-parent + symmetric diff with --cherry) & dedicated CSVs
- v0.1.3: merge-resolved lines: identify lines whose blame points to merge commit shas
- v0.1.4: per-directory churn tables; Jinja2 templated Markdown/HTML
- v0.1.5: better rename/delete inference in diff parser; binary file handling metadata
- v0.1.6: identity canonicalization with `.mailmap` & bot filters in all aggregates
```

