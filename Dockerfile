# =============================================================================
# Project Elevate: Enterprise HR & IT Agentic Solution — Production Dockerfile
# =============================================================================

# --- Stage 1: Build & Dependency Resolution ---
FROM python:3.12-slim AS builder

WORKDIR /app

ARG PIP_INDEX_URL=""
ARG UV_INDEX_URL=""

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    UV_INDEX_URL=${UV_INDEX_URL}

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, deterministic dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency manifests
COPY pyproject.toml .

# Create virtual environment and install production dependencies
RUN uv venv /opt/venv && \
    uv pip install --no-cache --python /opt/venv/bin/python \
    google-adk \
    google-genai \
    pydantic \
    httpx \
    python-dotenv \
    pyyaml

# --- Stage 2: Hardened Runtime Container ---
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

# Security: Create non-root system user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10000 -g appgroup -s /bin/bash -m appuser

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source code and policy knowledge base
COPY --chown=appuser:appgroup agent/ /app/agent/
COPY --chown=appuser:appgroup knowledge/ /app/knowledge/
COPY --chown=appuser:appgroup pyproject.toml /app/

# Switch to non-root user
USER appuser

# Healthcheck probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "from agent.agent import root_agent; assert root_agent is not None" || exit 1

EXPOSE 8080

# Entrypoint runs interactive or web server mode
ENTRYPOINT ["python3", "-m", "agent.agent"]
CMD ["--interactive"]
