"""Project Elevate: Web Server & Interactive UI API.

Provides an enterprise web dashboard for chatting with the ADK Supervisor Agent,
monitoring real-time WorkWeek PTO balances, and tracking ServiceImmediately tickets.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from . import config
from .agent import _run_query_async
from .tools.workweek_tool import get_personal_info, get_employee_balances, set_active_caller_context
from .tools.serviceimmediately_tool import list_tickets, set_active_caller_context as set_itsm_caller_context


app = FastAPI(title="Project Elevate Web Portal", version="1.0.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = config.DEFAULT_EMPLOYEE_ID
    session_id: Optional[str] = "web_session_001"


class SwitchUserRequest(BaseModel):
    user_id: str


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the main web dashboard."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="UI index.html not found.")
    return FileResponse(index_file)


@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    """Processes user chat queries through Model Armor, ADK Runner, and enterprise toolsets."""
    user_id = payload.user_id or config.DEFAULT_EMPLOYEE_ID
    session_id = payload.session_id or f"web_session_{user_id}"

    response_text = await _run_query_async(
        query=payload.message,
        user_id=user_id,
        session_id=session_id,
    )

    # Fetch updated balances and tickets for live sidebar refresh
    balances = get_employee_balances(user_id)
    tickets = list_tickets(user_id)

    return {
        "status": "success",
        "response": response_text,
        "user_id": user_id,
        "session_id": session_id,
        "balances": balances.get("balances", {}),
        "tickets": tickets.get("tickets", []),
    }


@app.get("/api/profile")
async def profile_endpoint(user_id: Optional[str] = None):
    """Fetches profile metadata and leave balances for active employee."""
    uid = user_id or config.DEFAULT_EMPLOYEE_ID
    set_active_caller_context(uid)
    profile = get_personal_info(uid)
    balances = get_employee_balances(uid)
    return {
        "profile": profile,
        "balances": balances.get("balances", {}),
    }


@app.get("/api/tickets")
async def tickets_endpoint(user_id: Optional[str] = None):
    """Fetches incident tickets for active employee."""
    uid = user_id or config.DEFAULT_EMPLOYEE_ID
    set_itsm_caller_context(uid)
    return list_tickets(uid)


@app.post("/api/switch-user")
async def switch_user_endpoint(payload: SwitchUserRequest):
    """Switches active session employee context for multi-tenant testing."""
    set_active_caller_context(payload.user_id)
    set_itsm_caller_context(payload.user_id)
    profile = get_personal_info(payload.user_id)
    balances = get_employee_balances(payload.user_id)
    tickets = list_tickets(payload.user_id)
    return {
        "status": "success",
        "user_id": payload.user_id,
        "profile": profile,
        "balances": balances.get("balances", {}),
        "tickets": tickets.get("tickets", []),
    }


def start_server(host: str = "0.0.0.0", port: int = 8080):
    """Starts the FastAPI Web UI server."""
    uvicorn.run("agent.web_server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    start_server()
