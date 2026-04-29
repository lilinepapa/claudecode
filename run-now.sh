#!/bin/bash
# 즉시 1회 실행 스크립트 (테스트용)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

[ -d ".venv" ] && source .venv/bin/activate

mkdir -p logs data

MODE="${1:-post}"

if [ "$MODE" = "plan" ]; then
  echo "📅 주간 계획 수립 실행..."
  python main.py --plan-now
else
  echo "📝 오늘 포스트 발행 실행..."
  python main.py --run-now
fi
