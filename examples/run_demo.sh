#!/usr/bin/env bash
set -euo pipefail
release-report --repo . --old HEAD~50 --new HEAD --out ./out
cat out/summary.md | head -n 40
