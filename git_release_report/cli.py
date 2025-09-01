from __future__ import annotations
import click
import time
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
@click.option('--repo', required=True, help='Git 仓库路径')
@click.option('--old', required=True, help='旧版本引用 (如: v1.2.0, HEAD~10)')
@click.option('--new', required=True, help='新版本引用 (如: v1.3.0, HEAD)')
@click.option('--preset', default='all', help='分析预设: all|A|B|C|D|E|F')
@click.option('--include', multiple=True, help='包含的路径模式 (可多次指定)')
@click.option('--exclude', multiple=True, help='排除的路径模式 (可多次指定)')
@click.option('--ignore-ws/--no-ignore-ws', default=True, help='忽略空白字符差异')
@click.option('--rename', default=90, type=int, help='重命名检测阈值 (百分比)')
@click.option('--copy', default=80, type=int, help='复制检测阈值 (百分比)')
@click.option('--first-parent/--no-first-parent', default=False, help='仅跟踪主线提交')
@click.option('--mailmap', default=None, help='邮件映射文件路径')
@click.option('--bot-filter', default=None, help='机器人过滤正则表达式')
@click.option('--out', 'out_dir', default='out', help='输出目录')
def main(**kwargs):
    """
    Git 发布报告生成工具

    分析两个 Git 版本之间的差异，生成详细的发布报告，包括：
    - 文件变更统计
    - 贡献者分析 (基于提交和 blame)
    - 代码存活率分析
    - 合并提交分析
    - 重命名/复制/删除文件跟踪

    输出文件：
    - analysis.json: 完整的结构化数据
    - summary.md: 人类可读的发布报告
    - 各种 CSV 文件: 详细的统计数据

    示例：
        release-report --repo . --old v1.2.0 --new v1.3.0 --out ./reports
        release-report --repo /path/to/repo --old HEAD~50 --new HEAD --include "src/" --exclude "test/"
    """
    start_time = time.time()
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
    raw = g.diff_raw(opts.old, opts.new, opts.ignore_ws, opts.rename,
                     opts.copy_thresh, list(opts.include), list(opts.exclude))
    file_changes = parse_diff(raw)

    # 3) blame per hunk (final ownership of changed lines)
    line_blames = []
    for fc in file_changes:
        if fc.is_binary or not fc.hunks or not fc.path_new:
            continue
        for h in fc.hunks:
            if h.new_len <= 0:
                continue
            lb = blame_block(g, opts.new, fc.path_new, h.new_start,
                             h.new_start + h.new_len - 1, opts.ignore_ws)
            line_blames.append(lb)

    # 4) survival stats (commit/author level)
    paths = collect_paths_from_file_changes(file_changes)
    by_commit, by_author = compute_survival(
        g, opts.old, opts.new, paths, opts.ignore_ws)

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

    # 计算并显示耗时
    elapsed_time = time.time() - start_time
    con.log(f"[green]Done[/] → {opts.out} (耗时: {elapsed_time:.2f} 秒)")


if __name__ == '__main__':
    main()
