#!/bin/bash
# 수동으로 main 브랜치 최신 커밋을 main-latest 태그로 빌드해 Harbor에 push하는 스크립트.
# backoffice_run.groovy(배포 파이프라인)의 기본 TAG 값이 "main-latest"이므로,
# 이 스크립트로 만든 이미지를 그대로 배포 파이프라인에서 pull-run 하면 됩니다.
#
# Jenkins 크리덴셜(Git_account: GIT_USER/GIT_TOKEN)과 동일한 이름의 환경변수를 그대로 씁니다.
#
# 사용법: (빌드 서버 — Harbor·git 서버 접근 가능한 곳에서 실행)
#   GIT_SERVER=<사내 git 서버 주소> BO_GIT_REPO=<org>/<repo>.git \
#   GIT_USER=<git 계정> GIT_TOKEN=<git 토큰> \
#     ./build_main_latest.sh
#
# 아래 변수들은 환경변수로 덮어쓸 수 있고, 안 주면 기본값을 씁니다.

set -e

HARBOR_URL="${HARBOR_URL:-10.32.50.26}"
GIT_SERVER="${GIT_SERVER:?GIT_SERVER 환경변수를 설정하세요 (예: github.com 또는 사내 git 서버 주소)}"
BO_GIT_REPO="${BO_GIT_REPO:?BO_GIT_REPO 환경변수를 설정하세요 (예: moonsumhi/jira-weekly-schedule-reporter)}"
GIT_USER="${GIT_USER:?GIT_USER 환경변수를 설정하세요 (Jenkins Git_account 크리덴셜의 아이디)}"
GIT_TOKEN="${GIT_TOKEN:?GIT_TOKEN 환경변수를 설정하세요 (Jenkins Git_account 크리덴셜의 토큰/비밀번호)}"
GIT_REPO="http://${GIT_USER}:${GIT_TOKEN}@${GIT_SERVER}/${BO_GIT_REPO}"
BRANCH="${BRANCH:-main}"
TAG="${TAG:-latest}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.org/simple/}"
VITE_LIBRECHAT_URL="${VITE_LIBRECHAT_URL:-}"
REMOTE_DIR="${REMOTE_DIR:-/tmp/backoffice-manual-build}"

SAFE_BRANCH="${BRANCH//\//-}"
IMAGE_TAG="${SAFE_BRANCH}-${TAG}"

echo "===== 0. 대상 이미지 태그: ${IMAGE_TAG} ====="

echo "===== 1. 기존 디렉토리 삭제 ====="
rm -rf "${REMOTE_DIR}"

echo "===== 2. Git Clone ====="
git clone -b "${BRANCH}" "${GIT_REPO}" "${REMOTE_DIR}"
cd "${REMOTE_DIR}"
echo "체크아웃된 커밋:"
git log -1 --oneline

echo "===== 3. Harbor 로그인 ====="
echo "Harbor 계정 정보를 입력하세요 (docker login 프롬프트)"
docker login "${HARBOR_URL}" --tls-verify=false

echo "===== 4. 이미지 빌드 ====="
docker build --pull -f "${REMOTE_DIR}/Dockerfile" \
  --build-arg BASE_IMAGE="${HARBOR_URL}/dev/python-base:3.12-slim" \
  --build-arg SKIP_SYS_DEPS=true \
  --build-arg PIP_INDEX_URL="${PIP_INDEX_URL}" \
  -t "${HARBOR_URL}/dev/jira-reporter-backend:${IMAGE_TAG}" \
  "${REMOTE_DIR}/"

docker build --pull -f "${REMOTE_DIR}/frontend/optool/Dockerfile" \
  --build-arg NODE_BASE_IMAGE="${HARBOR_URL}/dev/node-base:22-alpine" \
  --build-arg NGINX_BASE_IMAGE="${HARBOR_URL}/dev/nginx:alpine" \
  --build-arg SKIP_NPM_INSTALL=true \
  --build-arg VITE_LIBRECHAT_URL="${VITE_LIBRECHAT_URL}" \
  -t "${HARBOR_URL}/dev/jira-reporter-frontend:${IMAGE_TAG}" \
  "${REMOTE_DIR}/"

docker build --pull -f "${REMOTE_DIR}/mcp-server/Dockerfile" \
  --build-arg BASE_IMAGE="${HARBOR_URL}/dev/python-base:3.12-slim" \
  --build-arg SKIP_PIP_INSTALL=true \
  -t "${HARBOR_URL}/dev/jira-reporter-mcp:${IMAGE_TAG}" \
  "${REMOTE_DIR}/"

echo "===== 5. Push ====="
docker push "${HARBOR_URL}/dev/jira-reporter-frontend:${IMAGE_TAG}" --tls-verify=false
docker push "${HARBOR_URL}/dev/jira-reporter-backend:${IMAGE_TAG}" --tls-verify=false
docker push "${HARBOR_URL}/dev/jira-reporter-mcp:${IMAGE_TAG}" --tls-verify=false
docker logout "${HARBOR_URL}"

echo "===== 완료: ${IMAGE_TAG} 이미지 3종 push 완료 ====="
