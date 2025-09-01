from __future__ import annotations
from pathlib import Path
import orjson as json
from ..models import AnalysisResult


def write_json(result: AnalysisResult, out_dir: str):
    p = Path(out_dir)/"analysis.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(json.dumps(result, default=lambda o: o.__dict__))


def write_csv(rows, headers, path: str):
    from csv import DictWriter
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', newline='', encoding='utf-8') as f:
        w = DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)


def write_commits_survival_json(result: AnalysisResult, out_dir: str):
    """
    生成按提交顺序排序的代码存活率 JSON 报告

    Args:
        result: 分析结果
        out_dir: 输出目录
    """
    p = Path(out_dir) / "commits_survival.json"
    p.parent.mkdir(parents=True, exist_ok=True)

    # 构建提交存活率数据
    commits_data = []

    # 按提交时间排序 (从旧到新)
    sorted_commits = sorted(result.commits.values(),
                            key=lambda x: x.authored_time)

    for commit in sorted_commits:
        survival_stat = result.survival_by_commit.get(commit.sha)

        commit_data = {
            "sha": commit.sha,
            "author_name": commit.author_name,
            "author_email": commit.author_email,
            "committer_name": commit.committer_name,
            "committer_email": commit.committer_email,
            "authored_time": commit.authored_time,
            "committed_time": commit.committed_time,
            "is_merge": commit.is_merge,
            "parents": commit.parents,
            "introduced_lines": survival_stat.introduced_lines if survival_stat else 0,
            "survived_lines": survival_stat.survived_lines if survival_stat else 0,
            "survival_rate": (
                round(survival_stat.survived_lines /
                      survival_stat.introduced_lines, 4)
                if survival_stat and survival_stat.introduced_lines > 0
                else 0.0
            )
        }
        commits_data.append(commit_data)

    # 构建完整的报告数据
    report_data = {
        "meta": {
            "old_version": result.meta.get("old"),
            "new_version": result.meta.get("new"),
            "total_commits": len(commits_data),
            "total_introduced_lines": sum(c["introduced_lines"] for c in commits_data),
            "total_survived_lines": sum(c["survived_lines"] for c in commits_data),
            "overall_survival_rate": (
                round(
                    sum(c["survived_lines"] for c in commits_data) /
                    sum(c["introduced_lines"] for c in commits_data), 4
                )
                if sum(c["introduced_lines"] for c in commits_data) > 0
                else 0.0
            )
        },
        "commits": commits_data
    }

    p.write_bytes(json.dumps(report_data, default=lambda o: o.__dict__))


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
