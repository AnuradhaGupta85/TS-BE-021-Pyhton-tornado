#!/usr/bin/env bash
set -e
export PYTHONUNBUFFERED=1
export PORT="${PORT:-21435}"
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r requirements.txt -q
exec python3 main.py
