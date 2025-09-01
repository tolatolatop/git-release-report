from __future__ import annotations
import re
from typing import List
from .gitwrap import GitWrap
from .models import LineBlameBlock, BlameAtom

RE_SHA = re.compile(r"^[0-9a-f]{40} ")


def blame_block(g: GitWrap, rev: str, path: str, start: int, end: int, ignore_ws: bool) -> LineBlameBlock:
    raw = g.blame_porcelain(rev, path, start, end, ignore_ws)
    atoms: List[BlameAtom] = []
    author = email = commit = None
    for ln in raw.splitlines():
        if ln.startswith('author '):
            author = ln[7:]
        elif ln.startswith('author-mail '):
            email = ln.split('<', 1)[-1].rstrip('>')
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
            cur_email = ln.split('<', 1)[-1].rstrip('>')
        elif ln.startswith('\t'):
            atoms.append(BlameAtom(author=cur_author or '', email=cur_email or '',
                         commit_sha=cur_commit or '', is_merge_line=False))
    return atoms
