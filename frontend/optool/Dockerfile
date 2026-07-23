ARG NODE_BASE_IMAGE=node:22-alpine
ARG NGINX_BASE_IMAGE=nginx:alpine

# Stage 1: Build
FROM ${NODE_BASE_IMAGE} AS builder

ARG SKIP_NPM_INSTALL=false
ARG NPM_REGISTRY=""

WORKDIR /app
COPY frontend/optool/ .

RUN if [ "$SKIP_NPM_INSTALL" = "false" ]; then \
    npm install -g @quasar/cli && \
    npm install --legacy-peer-deps; \
elif [ -n "$NPM_REGISTRY" ]; then \
    npm install -g @quasar/cli --registry=$NPM_REGISTRY && \
    npm install --legacy-peer-deps --registry=$NPM_REGISTRY; \
fi

RUN npx quasar build

# Stage 2: Serve
FROM ${NGINX_BASE_IMAGE}
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/dist/spa /usr/share/nginx/html
COPY frontend/optool/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
