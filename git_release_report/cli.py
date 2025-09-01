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
    raw = g.diff_raw(opts.old, opts.new, opts.ignore_ws, opts.rename,
                     opts.copy, list(opts.include), list(opts.exclude))
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
    con.log(f"[green]Done[/] → {opts.out}")


if __name__ == '__main__':
    main()
