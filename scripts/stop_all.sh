#!/usr/bin/env bash
# Stop the gmaps-leads stack: tmux session + postgres container.
# Data is preserved (docker volume pgdata is not removed).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SESSION="gmaps-leads"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[stop_all] killing tmux session '$SESSION'"
  tmux kill-session -t "$SESSION"
else
  echo "[stop_all] no tmux session '$SESSION' running"
fi

echo "[stop_all] stopping postgres container"
docker compose stop db

echo "[stop_all] done (data preserved in docker volume 'pgdata')"
