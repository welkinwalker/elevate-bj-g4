"""Configuration for Project Elevate Agent."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
_root_dir = Path(__file__).resolve().parent.parent
load_dotenv(_root_dir / ".env")

APP_NAME: str = os.getenv("APP_NAME", "elevate-hr-agent")

# Model configuration: latest-generation gemini-3.5-flash
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# FastMCP Server Endpoints
WORKWEEK_MCP_URL: str = os.getenv(
    "WORKWEEK_MCP_URL",
    "https://mock-saas.aishprabhat.demo.altostrat.com/work-week/mcp/",
)
SERVICEIMMEDIATELY_MCP_URL: str = os.getenv(
    "SERVICEIMMEDIATELY_MCP_URL",
    "https://mock-saas.aishprabhat.demo.altostrat.com/service-immediately/mcp/",
)
MCP_TOKEN: str = os.getenv("MCP_TOKEN", "mcp_your_token_here")

# Tenant / Identity defaults
DEFAULT_EMPLOYEE_ID: str = os.getenv("DEFAULT_EMPLOYEE_ID", "EMP-1002")

# Offline/Dev Local Mock Fallback toggle
ENABLE_LOCAL_MOCK_FALLBACK: bool = (
    os.getenv("ENABLE_LOCAL_MOCK_FALLBACK", "true").lower() == "true"
)

# Private Registry & Dependency Mirrors (Dev/Corp Airlock support)
PIP_INDEX_URL: str = os.getenv("PIP_INDEX_URL", "")
UV_INDEX_URL: str = os.getenv("UV_INDEX_URL", "")
ARTIFACT_REGISTRY_URL: str = os.getenv("ARTIFACT_REGISTRY_URL", "")

# Knowledge base directory
KNOWLEDGE_DIR: Path = _root_dir / "knowledge"

# Vertex AI Search settings
GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
VERTEX_AI_SEARCH_LOCATION: str = os.getenv("VERTEX_AI_SEARCH_LOCATION", "global")
VERTEX_AI_DATA_STORE_ID: str = os.getenv(
    "VERTEX_AI_DATA_STORE_ID", "hr-policies-elevate-store"
)
VERTEX_AI_SEARCH_ENGINE_ID: str = os.getenv(
    "VERTEX_AI_SEARCH_ENGINE_ID", "hr-policies-elevate-engine"
)

# Model Armor settings
MODEL_ARMOR_TEMPLATE_ID: str = os.getenv("MODEL_ARMOR_TEMPLATE_ID", "elevate-safety-template")
MODEL_ARMOR_ENDPOINT: str = os.getenv("MODEL_ARMOR_ENDPOINT", "")
