#!/bin/bash
# InstaPoetBot Web — 啟動腳本
# 用法：bash start.sh [port]
# 預設 port: 8000

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8000}"

cd "$SCRIPT_DIR"

# 如果有 venv 就啟用
if [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "🚀 InstaPoetBot 啟動中，port: $PORT"
echo "   開啟瀏覽器：http://localhost:$PORT"
echo ""

uvicorn web.main:app --host 0.0.0.0 --port "$PORT" --reload
