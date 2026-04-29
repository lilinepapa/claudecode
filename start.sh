#!/bin/bash
# 네이버 블로그 에이전트 시작 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# .env 파일 확인
if [ ! -f ".env" ]; then
  echo "❌ .env 파일이 없습니다. .env.example을 참고해 .env를 만들어주세요."
  exit 1
fi

# Python 가상환경 확인 및 생성
if [ ! -d ".venv" ]; then
  echo "📦 가상환경 생성 중..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# 의존성 설치
echo "📦 의존성 확인 중..."
pip install -q -r requirements.txt

# Playwright 브라우저 설치
if ! python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(); p.stop()" 2>/dev/null; then
  echo "🌐 Playwright Chromium 설치 중..."
  playwright install chromium
fi

# claude CLI 확인
if ! command -v claude &>/dev/null; then
  echo "❌ claude CLI가 설치되어 있지 않습니다."
  echo "   설치: npm install -g @anthropic-ai/claude-code"
  echo "   로그인: claude"
  exit 1
fi

# 로그 디렉토리 생성
mkdir -p logs data

echo ""
echo "✅ 커리어그래퍼 박민산 블로그 에이전트 시작"
echo "   - 매주 목요일 08:00: 주간 콘텐츠 계획 수립"
echo "   - 매일 09:00: 네이버 블로그 자동 발행"
echo "   - 종료: Ctrl+C"
echo ""

python main.py
