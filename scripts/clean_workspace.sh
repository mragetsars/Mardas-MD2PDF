#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

remove_patches=0
if [[ "${1:-}" == "--patches" ]]; then
  remove_patches=1
fi

find . -type d \( \
  -name '__pycache__' -o \
  -name '.pytest_cache' -o \
  -name '.ruff_cache' -o \
  -name '*.egg-info' \
\) -prune -exec rm -rf {} +

rm -rf build dist htmlcov .coverage
rm -f output.pdf
find . -maxdepth 1 -type f -name 'er.name*' -delete

if [[ "$remove_patches" == "1" ]]; then
  rm -rf patches
fi

printf 'Workspace cleanup complete.\n'
