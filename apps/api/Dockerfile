# syntax=docker/dockerfile:1.6
#
# ClaimGuard API container.
#
# Strategy:
#   * Python 3.12 slim base (~ 100 MB)
#   * uv for dependency management - same as local dev, no pip
#   * Model caches (Huggingface, sentence-transformers) live on a named
#     docker volume so the 1 GB+ E5 + BGE-Reranker downloads survive
#     container rebuilds
#   * Code is COPY'd late so dependency-only changes hit the build cache

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1
ENV HF_HOME=/models
ENV SENTENCE_TRANSFORMERS_HOME=/models/sentence-transformers
ENV TRANSFORMERS_CACHE=/models/transformers
ENV PATH=/app/.venv/bin:$PATH
ENV PYTHONPATH=/app

# System libs the wheels need at runtime: libgomp for torch/sentence-
# transformers, libpq for psycopg, curl for healthchecks.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libpq5 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv at a pinned version that matches local dev.
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /usr/local/bin/uv

WORKDIR /app

# 1. Dependency layer - changes rarely.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. App code layer - changes on every commit.
COPY app ./app
COPY scripts ./scripts
COPY data ./data

# Install the project itself (uv sync was --no-install-project above).
RUN uv sync --frozen --no-dev

# Pre-create the models dir so the volume mount keeps the same UID.
RUN mkdir -p /models

EXPOSE 8000

# Healthcheck hits the FastAPI ``/health`` endpoint. ``start-period``
# is generous because the first request loads E5 (~ 440 MB) and BGE
# (~ 568 MB) into RAM; subsequent restarts read from the model volume.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Single uvicorn worker on purpose: the in-process E5 + BGE models eat
# ~ 1.5 GB RAM together; a second worker would double that without
# meaningful throughput gains. Scale by adding replicas behind Caddy
# if you ever need it.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
