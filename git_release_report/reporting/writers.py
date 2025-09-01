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
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', newline='', encoding='utf-8') as f:
        w = DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)


def write_md(result: AnalysisResult, out_dir: str):
    p = Path(out_dir)/"summary.md"
    lines = []
    meta = result.meta
    lines += [f"# Release report: {meta.get('old')} → {meta.get('new')}", ""]
    lines += ["## Files changed (top 10 by churn)"]
    top = sorted(result.file_changes, key=lambda x: x.insertions +
                 x.deletions, reverse=True)[:10]
    for fc in top:
        lines.append(
            f"- {fc.status} {fc.path_new} (+{fc.insertions}/-{fc.deletions})")
    lines.append("")
    lines += ["## Contributors (final ownership, blame over changed lines)"]
    # simple aggregation inline
    from collections import Counter
    c = Counter()
    for lb in result.line_blames:
        for a in lb.atoms:
            c[f"{a.author} <{a.email}>"] += 1
    for k, v in c.most_common(20):
        lines.append(f"- {k}: {v} lines")
    p.write_text("\n".join(lines), encoding='utf-8')
