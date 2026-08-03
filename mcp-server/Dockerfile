ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ARG SKIP_PIP_INSTALL=false
ARG PIP_INDEX_URL=https://pypi.org/simple/

WORKDIR /app

COPY mcp-server/requirements.txt .
RUN if [ "$SKIP_PIP_INSTALL" = "false" ]; then \
        pip install --no-cache-dir --index-url ${PIP_INDEX_URL} -r requirements.txt; \
    fi

COPY mcp-server/server.py .

EXPOSE 8002

CMD ["python", "server.py"]
