#!/usr/bin/env bash
# Usage: scripts/run.sh stack.finder run   — loads .env and uses the repo's venv.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; [ -f .env ] && source .env; set +a
mkdir -p data
exec .venv/bin/python -m "$@"
