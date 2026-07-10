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

wheel_path="$(find dist -maxdepth 1 -type f -name '*.whl' -print -quit)"
if [[ -z "$wheel_path" ]]; then
  echo "Release gate failed: wheel artifact was not produced." >&2
  exit 1
fi

verify_venv="$(mktemp -d "${TMPDIR:-/tmp}/mardas-md2pdf-release-venv.XXXXXX")"
project_smoke="$(mktemp -d "${TMPDIR:-/tmp}/mardas-md2pdf-project-smoke.XXXXXX")"
cleanup_release_gate() {
  rm -rf "$verify_venv" "$project_smoke" "$tmp_pdf"
}
trap cleanup_release_gate EXIT

python -m venv "$verify_venv"
venv_python="$verify_venv/bin/python"
venv_bin="$verify_venv/bin"
if [[ "${OS:-}" == "Windows_NT" ]]; then
  venv_python="$verify_venv/Scripts/python.exe"
  venv_bin="$verify_venv/Scripts"
fi

"$venv_python" -m pip install --disable-pip-version-check "$wheel_path"
"$venv_python" -m pip check
"$venv_bin/mrs-md2pdf" --version
"$venv_bin/mrs-md2pdf" --help >/dev/null
"$venv_bin/mrs-md2pdf" --list-styles >/dev/null
"$venv_bin/mrs-md2pdf" init "$project_smoke"
printf '%s\n' '# Project command smoke' > "$project_smoke/report.md"
"$venv_bin/mrs-md2pdf" validate "$project_smoke/report.md" --format json > "$project_smoke/validate.json"
"$venv_bin/mrs-md2pdf" explain-config "$project_smoke/report.md" --format json > "$project_smoke/explain.json"
"$venv_bin/mrs-md2pdf" doctor "$project_smoke/report.md" --format json > "$project_smoke/doctor.json"
"$venv_python" - "$project_smoke" <<'PY_PROJECT'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
for name in ("validate", "explain", "doctor"):
    payload = json.loads((root / f"{name}.json").read_text(encoding="utf-8"))
    if not payload.get("ok"):
        raise SystemExit(f"Project command smoke failed: {name}")
PY_PROJECT
"$venv_bin/mrs-md2pdf-gui" --version
"$venv_python" - <<'PY'
from importlib import resources

assets = resources.files("mardas_md2pdf") / "assets"
required = [
    "gui.html",
    "style-modern.css",
    "style-github.css",
    "style-textbook.css",
    "style-academic.css",
    "mardas-md2pdf-mark.svg",
    "mathjax/tex-svg-full.js",
]
missing = [name for name in required if not (assets / name).is_file()]
if missing:
    raise SystemExit(f"Missing packaged assets: {', '.join(missing)}")
PY

(
  cd dist
  rm -f CHECKSUMS.sha256
  sha256sum ./*.whl ./*.tar.gz > CHECKSUMS.sha256
)
