ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE} AS base

ARG SKIP_SYS_DEPS=false

RUN if [ "$SKIP_SYS_DEPS" = "false" ]; then \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libxml2-dev libxslt-dev libxml2-utils \
        nodejs npm libreoffice-writer libreoffice-calc libreoffice-impress fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/* && \
    printf '#!/bin/sh\ncat\n' > /usr/bin/xmllint && \
    chmod +x /usr/bin/xmllint && \
    npm install -g @anthropic-ai/claude-code; \
fi

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple/
ARG SKIP_PIP_INSTALL=false

COPY vendor /app/vendor
COPY requirements.txt .
RUN if [ "$SKIP_PIP_INSTALL" = "false" ]; then \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --index-url ${PIP_INDEX_URL} -r requirements.txt; \
fi

# Install the vendored pure-Python HWPX library without invoking pip's build isolation.
RUN cp -r /app/vendor/python_hwpx-6.3.0/hwpx /usr/local/lib/python3.12/site-packages/hwpx \
 && cp -r /app/vendor/python_hwpx-6.3.0/python_hwpx-6.3.0.dist-info /usr/local/lib/python3.12/site-packages/

COPY app /app/app
COPY scripts/hwp /usr/local/bin/hwp
COPY docs/third-party/hwp-cli-LICENSE.txt /usr/local/share/licenses/hwp-cli/LICENSE
RUN chmod +x /usr/local/bin/hwp
ENV HWP_FONT_DIR=/usr/share/fonts/opentype/noto

RUN useradd -m appuser
USER appuser

EXPOSE 8000
ENV PORT=8000 \
    HOST=0.0.0.0

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
