#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python -m ruff check .

if [[ "${MARDAS_RENDER_SMOKE:-0}" == "1" ]]; then
  tmp_pdf="${TMPDIR:-/tmp}/mardas-md2pdf-smoke.pdf"
  python -m mardas_md2pdf.cli docs/guides/GUIDE.en.md -o "$tmp_pdf" --toc --style github --palette blue --mode light --timeout-ms "${MARDAS_TIMEOUT_MS:-180000}" --progress off
  test -s "$tmp_pdf"
  MARDAS_RENDER_SMOKE=0 python -m pytest "$@"
else
  python -m pytest "$@"
fi
