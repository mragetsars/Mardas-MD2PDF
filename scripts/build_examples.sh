#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

timeout_ms="${MARDAS_TIMEOUT_MS:-180000}"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1735689600}"
mkdir -p examples

python -m mardas_md2pdf.cli docs/guides/GUIDE.en.md \
  -o examples/GUIDE.en.pdf \
  --toc \
  --style github --palette blue --mode light \
  --timeout-ms "$timeout_ms"

python -m mardas_md2pdf.cli docs/guides/GUIDE.fa.md \
  -o examples/GUIDE.fa.pdf \
  --toc \
  --style modern --palette blue --mode light \
  --timeout-ms "$timeout_ms"
