#!/usr/bin/env bash
# Same contract as PowerShell; Python performs shared parsing and orchestration.
set -euo pipefail
cd "$(dirname "$0")"
TASK_PYTHON="${HORIZON_PYTHON:-}"
if [[ -z "$TASK_PYTHON" && -f .env ]]; then
    while IFS='=' read -r key value; do
        if [[ "$key" == HORIZON_PYTHON && -n "$value" ]]; then TASK_PYTHON="${value%$'\r'}"; fi
    done < .env
fi
if [[ -z "$TASK_PYTHON" ]]; then
    if [[ -x .venv/bin/python ]]; then TASK_PYTHON=.venv/bin/python
    elif [[ -x .venv/Scripts/python.exe ]]; then TASK_PYTHON=.venv/Scripts/python.exe
    else TASK_PYTHON=python3; fi
fi
exec "$TASK_PYTHON" -m python_src.runner "$@"
