#!/usr/bin/env bash
# AFAC2026 Track-1 — dependency install.
# Idempotent; uses relative paths only (audit-contract requirement).
set -euo pipefail

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

echo "[init_env] using interpreter: $($PY --version 2>&1)"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt

echo "[init_env] done. Run the pipeline with:"
echo "    $PY main.py --input samples/AFAC2026.xlsx -o outputs/"
