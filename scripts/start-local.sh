#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir/backend"

if [[ ! -f .env ]]; then
  echo "Missing backend/.env. Copy backend/.env.example and set local secrets." >&2
  exit 1
fi
if [[ ! -f ../frontend/dist/index.html || ! -d ../frontend/dist/assets ]]; then
  echo "Frontend build missing. Run npm run build in frontend/." >&2
  exit 1
fi
if [[ ! -f payroll_tracker.db ]]; then
  echo "Database missing. Run 'uv run alembic upgrade head' in backend/ first." >&2
  exit 1
fi

set -a
source .env
set +a
unset DATABASE_URL

if [[ "${1:-}" != "--no-browser" ]]; then
  (
    for _ in {1..30}; do
      if python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/", timeout=1)' >/dev/null 2>&1; then
        if command -v wslview >/dev/null 2>&1; then
          wslview http://127.0.0.1:8000/ >/dev/null 2>&1 || true
        elif command -v xdg-open >/dev/null 2>&1; then
          xdg-open http://127.0.0.1:8000/ >/dev/null 2>&1 || true
        fi
        exit 0
      fi
      sleep 1
    done
  ) &
fi

exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
