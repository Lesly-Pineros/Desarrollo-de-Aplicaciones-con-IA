#!/usr/bin/env bash
set -euo pipefail

# Resolve the repository from this script, so callers can run it from any cwd.
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  APP_PYTHON="$REPO_ROOT/.venv/bin/python"
elif [[ -n "${INVESTIQ_PYTHON:-}" ]]; then
  APP_PYTHON="$INVESTIQ_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  APP_PYTHON="$(command -v python3)"
else
  APP_PYTHON="$(command -v python)"
fi

exec "$APP_PYTHON" -m streamlit run "$REPO_ROOT/src/investiq/app.py" "$@"
