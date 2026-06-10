#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python -m ruff check .
python -m pytest "$@"

if [[ "${MARDAS_RENDER_SMOKE:-0}" == "1" ]]; then
  tmp_pdf="${TMPDIR:-/tmp}/mardas-md2pdf-smoke.pdf"
  mrs-md2pdf GUIDE.en.md -o "$tmp_pdf" --toc --profile github --timeout-ms "${MARDAS_TIMEOUT_MS:-180000}"
  test -s "$tmp_pdf"
fi
