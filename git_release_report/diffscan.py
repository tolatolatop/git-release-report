from __future__ import annotations
import re
from typing import List
from .models import FileChange, Hunk

RE_DIFF_HDR = re.compile(r"^diff --git a/(.*?) b/(.*?)$")
RE_BINARY = re.compile(r"^Binary files .* and .* differ$")
RE_STATUS = re.compile(r"^(rename|copy) from (.*)$|^create mode|^delete mode")
RE_SUMMARY_R = re.compile(r"^rename (?:from|to) ")
RE_HUNK = re.compile(
    r"^@@ -(?P<o1>\d+)(?:,(?P<ol>\d+))? \+(?P<n1>\d+)(?:,(?P<nl>\d+))? @@")

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
            if cur:
                out.append(cur)
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
                o1 = int(hm.group('o1'))
                ol = int(hm.group('ol') or '1')
                n1 = int(hm.group('n1'))
                nl = int(hm.group('nl') or '1')
                cur.hunks.append(Hunk(o1, ol, n1, nl))
            # numstat lines appear before patches as separate section; we re-scan at end
        i += 1
    if cur:
        out.append(cur)

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
