#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
ROOT_ENV_FILE="${SCRIPT_DIR}/../.env"
BACKEND_ENV_FILE="${SCRIPT_DIR}/../app/secret/.env"

# 키체인에서 최신 OAuth 토큰 추출
NEW_TOKEN=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['claudeAiOauth']['accessToken'])")

if [ -z "$NEW_TOKEN" ]; then
  echo "[$(date)] ERROR: 토큰 추출 실패 - claude 로그인 필요"
  exit 1
fi

# 루트 .env 파일에서 토큰 교체
if [ -f "$ROOT_ENV_FILE" ]; then
  sed -i '' "s|CLAUDE_CODE_OAUTH_TOKEN=.*|CLAUDE_CODE_OAUTH_TOKEN=${NEW_TOKEN}|" "$ROOT_ENV_FILE"
fi

# 백엔드 .env 파일에서 토큰 교체
if [ -f "$BACKEND_ENV_FILE" ]; then
  sed -i '' "s|CLAUDE_CODE_OAUTH_TOKEN=.*|CLAUDE_CODE_OAUTH_TOKEN=${NEW_TOKEN}|" "$BACKEND_ENV_FILE"
fi

# backend, pilot 컨테이너 재시작
cd "${SCRIPT_DIR}/.." && docker-compose up -d --force-recreate backend pilot > /dev/null 2>&1

echo "[$(date)] 토큰 갱신 완료"
