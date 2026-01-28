# Multi-stage build for smaller image
FROM python:3.12-slim AS base

# 1) System deps (build + runtime) — keep minimal
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# 2) Workdir
WORKDIR /app

# 3) Copy dependency manifests first for cache
COPY requirements.txt .

# 4) Install deps
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 5) Copy app
COPY app /app/app

# 6) Security: run as non-root
RUN useradd -m appuser
USER appuser

# 7) Expose & default command
EXPOSE 8000
ENV PORT=8000 \
    HOST=0.0.0.0

# FastAPI with Uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]