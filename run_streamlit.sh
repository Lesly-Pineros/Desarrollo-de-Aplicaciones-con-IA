#!/usr/bin/env bash
set -euo pipefail

# Resolve the repository from this script, so callers can run it from any cwd.
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

if ! "$APP_PYTHON" -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('streamlit') else 1)"; then
  echo "Streamlit es una interfaz opcional. Para abrir la web principal, ejecuta: bash run_web.sh" >&2
  echo "Si necesitas esta alternativa, instala el extra: python -m pip install -e '.[legacy-ui]'" >&2
  exit 1
fi

exec "$APP_PYTHON" -m streamlit run "$REPO_ROOT/src/investiq/app.py" "$@"
