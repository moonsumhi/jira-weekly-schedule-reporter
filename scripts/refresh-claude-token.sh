#!/bin/bash
set -euo pipefail

ENV_FILE="$(dirname "$0")/../.env"

# 키체인에서 최신 OAuth 토큰 추출
NEW_TOKEN=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['claudeAiOauth']['accessToken'])")

if [ -z "$NEW_TOKEN" ]; then
  echo "[$(date)] ERROR: 토큰 추출 실패 - claude 로그인 필요"
  exit 1
fi

# .env 파일에서 토큰 교체
sed -i '' "s|CLAUDE_CODE_OAUTH_TOKEN=.*|CLAUDE_CODE_OAUTH_TOKEN=${NEW_TOKEN}|" "$ENV_FILE"

# pilot 컨테이너 재시작
cd "$(dirname "$0")/.." && docker-compose up -d --force-recreate pilot > /dev/null 2>&1

echo "[$(date)] 토큰 갱신 완료"
