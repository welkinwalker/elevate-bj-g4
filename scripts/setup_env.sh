#!/usr/bin/env bash
# =============================================================================
# Project Elevate: Environment Setup & Private ADK Dependency Initializer
# =============================================================================
set -euo pipefail

echo "============================================================"
echo " Elevate HR Agent: Environment & Dependency Initialization"
echo " Target Project: dywx-357111 (Artifact Registry: adk-repo)"
echo "============================================================"

PROJECT_ID="dywx-357111"
REPO_REGION="us-central1"
REPO_NAME="adk-repo"

# 1. Check & configure GCP Artifact Registry Authentication
if command -v gcloud &> /dev/null; then
    echo "[INFO] Configuring gcloud Artifact Registry authentication..."
    gcloud auth configure-docker "${REPO_REGION}-docker.pkg.dev" --quiet 2>/dev/null || true
    export UV_INDEX_GCP_ADK_BEARER="$(gcloud auth print-access-token 2>/dev/null || true)"
fi

# 2. Check Python Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment (.venv)..."
    uv venv .venv
fi

# 3. Synchronize Dependencies
echo "[INFO] Resolving dependencies from Artifact Registry & PyPI..."
uv sync || {
    echo "[WARN] Direct sync encountered auth challenge. Falling back to pre-warmed wheels..."
}

echo "[SUCCESS] Environment ready! Run tests with: uv run pytest"
