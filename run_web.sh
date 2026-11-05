#!/usr/bin/env bash
set -euo pipefail

# La ubicación del repo se calcula desde el script, también en otra máquina.
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

if [[ -n "${INVESTIQ_PYTHON:-}" ]]; then
  APP_PYTHON="$INVESTIQ_PYTHON"
elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  APP_PYTHON="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  APP_PYTHON="$(command -v python3)"
else
  APP_PYTHON="$(command -v python)"
fi

# El checkout funciona incluso antes de reinstalar la entrada de consola.
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$APP_PYTHON" -m investiq.web.server "$@"
