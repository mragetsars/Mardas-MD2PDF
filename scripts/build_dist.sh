#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

rm -rf dist

if [[ "${MARDAS_BUILD_NO_ISOLATION:-0}" == "1" ]]; then
  python -m build --no-isolation --skip-dependency-check
else
  python -m build
fi
