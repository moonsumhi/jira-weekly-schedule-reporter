ARG NODE_BASE_IMAGE=node:22-alpine
ARG NGINX_BASE_IMAGE=nginx:alpine

# Stage 1: Build
FROM ${NODE_BASE_IMAGE} AS builder

ARG SKIP_NPM_INSTALL=false
ARG NPM_REGISTRY=""
ARG VITE_LIBRECHAT_URL=""
ENV VITE_LIBRECHAT_URL=$VITE_LIBRECHAT_URL

WORKDIR /app
# 내부망 베이스 이미지에 남은 이전 소스를 제거하고 설치된 node_modules는 재사용한다.
RUN rm -rf /app/src
COPY frontend/optool/ .
# 빌드 전 드롭다운과 EoS/EoL 스냅샷의 누락 여부를 검증하기 위해 함께 복사한다.
COPY app/data/eos_map_snapshot.json ./data/eos_map_snapshot.json

# Docker Desktop에서 esbuild 실행 파일 교체 직후 발생하는 ETXTBSY를 피한다.
# 공식 플랫폼 바이너리를 지정하면 설치 스크립트가 하드링크 교체를 생략한다.
RUN export ESBUILD_BINARY_PATH="/app/node_modules/@esbuild/linux-$(node -p 'process.arch')/bin/esbuild"; \
    if [ "$SKIP_NPM_INSTALL" = "false" ]; then \
    npm install -g @quasar/cli && \
    npm install --legacy-peer-deps; \
elif [ -n "$NPM_REGISTRY" ]; then \
    npm install -g @quasar/cli --registry=$NPM_REGISTRY && \
    npm install --legacy-peer-deps --registry=$NPM_REGISTRY; \
fi

RUN npm run build

# Stage 2: Serve
FROM ${NGINX_BASE_IMAGE}
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/dist/spa /usr/share/nginx/html
COPY frontend/optool/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
