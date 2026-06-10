#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

timeout_ms="${MARDAS_TIMEOUT_MS:-180000}"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1735689600}"
mkdir -p examples

mrs-md2pdf GUIDE.en.md \
  -o examples/GUIDE.en.pdf \
  --toc \
  --profile github \
  --timeout-ms "$timeout_ms"

mrs-md2pdf GUIDE.fa.md \
  -o examples/GUIDE.fa.pdf \
  --toc \
  --profile persian-report \
  --timeout-ms "$timeout_ms"
