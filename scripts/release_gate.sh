#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

run_visual_qa="${MARDAS_RELEASE_VISUAL_QA:-0}"
preflight_pages="${MARDAS_PREFLIGHT_PAGES:-1,2,3}"
preflight_timeout="${MARDAS_PREFLIGHT_TIMEOUT:-60}"

bash scripts/check.sh

tmp_pdf="${TMPDIR:-/tmp}/mardas-md2pdf-release-smoke.pdf"
timeout "${MARDAS_RELEASE_SMOKE_TIMEOUT:-240}" \
  python -m mardas_md2pdf.cli \
    docs/guides/GUIDE.en.md \
    -o "$tmp_pdf" \
    --toc \
    --style github \
    --palette blue \
    --mode light \
    --timeout-ms "${MARDAS_TIMEOUT_MS:-180000}" \
    --progress off
test -s "$tmp_pdf"

bash scripts/build_examples.sh
python scripts/check_pdf_preflight.py \
  examples/GUIDE.en.pdf \
  examples/GUIDE.fa.pdf \
  --pages "$preflight_pages" \
  --timeout "$preflight_timeout" \
  --output build/release/pdf-preflight.json

if [[ "$run_visual_qa" == "1" ]]; then
  python scripts/run_visual_qa_matrix.py \
    --output-dir build/release/visual-qa \
    --render-png \
    --raster-timeout "${MARDAS_RASTER_TIMEOUT:-60}" \
    --chunk-timeout "${MARDAS_CHUNK_TIMEOUT:-900}" \
    --resume \
    --clean
else
  python scripts/run_visual_qa_matrix.py \
    --output-dir build/release/visual-qa-smoke \
    --max-cases "${MARDAS_RELEASE_VISUAL_QA_CASES:-1}" \
    --render-png \
    --raster-timeout "${MARDAS_RASTER_TIMEOUT:-60}" \
    --chunk-timeout "${MARDAS_CHUNK_TIMEOUT:-180}" \
    --fail-fast \
    --clean
fi

bash scripts/build_dist.sh
