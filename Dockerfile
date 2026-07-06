ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE} AS base

ARG SKIP_SYS_DEPS=false

RUN if [ "$SKIP_SYS_DEPS" = "false" ]; then \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libxml2-dev libxslt-dev libxml2-utils \
        nodejs npm libreoffice-writer libreoffice-calc fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/* && \
    printf '#!/bin/sh\ncat\n' > /usr/bin/xmllint && \
    chmod +x /usr/bin/xmllint && \
    npm install -g @anthropic-ai/claude-code; \
fi

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple/
ARG PIP_TRUSTED_HOST=

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
    --index-url ${PIP_INDEX_URL} \
    ${PIP_TRUSTED_HOST:+--trusted-host ${PIP_TRUSTED_HOST}} \
    -r requirements.txt

COPY app /app/app

RUN useradd -m appuser
USER appuser

EXPOSE 8000
ENV PORT=8000 \
    HOST=0.0.0.0

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
