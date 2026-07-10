#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -z "${SOURCE_DATE_EPOCH:-}" ]]; then
  SOURCE_DATE_EPOCH="$(git log -1 --format=%ct 2>/dev/null || printf '946684800')"
fi
export SOURCE_DATE_EPOCH
export PYTHONHASHSEED="${PYTHONHASHSEED:-0}"
export TZ="${TZ:-UTC}"
umask 022

rm -rf dist

if [[ "${MARDAS_BUILD_NO_ISOLATION:-0}" == "1" ]]; then
  python -m build --no-isolation --skip-dependency-check
else
  python -m build
fi

for archive in dist/*.tar.gz; do
  [[ -e "$archive" ]] || continue
  python scripts/normalize_sdist.py "$archive" --epoch "$SOURCE_DATE_EPOCH"
done
