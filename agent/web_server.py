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
from .tools.workweek_tool import (
    get_personal_info,
    get_employee_balances,
    get_leave_requests,
    set_active_caller_context,
)
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


@app.get("/.well-known/agent-card.json")
@app.get("/a2a/app/.well-known/agent-card.json")
async def get_agent_card():
    """Exposes Agent-to-Agent (A2A) Agent Card specification for Gemini Enterprise."""
    return {
        "name": "elevate-hr-it-assistant",
        "displayName": "Project Elevate HR & IT Assistant",
        "display_name": "Project Elevate HR & IT Assistant",
        "description": "Autonomous enterprise virtual assistant for HR policy inquiries, WorkWeek PTO self-service, and ServiceImmediately IT support tickets.",
        "version": "1.0.0",
        "protocol": "a2a",
        "protocolVersion": "1.0.0",
        "url": "https://elevate-agent.dywx-357111.a.run.app/api/chat",
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "supportedInputModes": ["text"],
        "supportedOutputModes": ["text"],
        "skills": [
            {
                "id": "hr_policy_qa",
                "name": "HR & IT Policy Q&A",
                "description": "Query enterprise HR and IT knowledge base policies with verified deep-link citations.",
                "tags": ["hr", "policy", "rag", "citations"],
            },
            {
                "id": "workweek_self_service",
                "name": "WorkWeek HCM Self-Service",
                "description": "Retrieve vacation/sick leave balances, profile information, and submit time off requests in WorkWeek.",
                "tags": ["hcm", "workweek", "pto", "leave", "profile"],
            },
            {
                "id": "serviceimmediately_itsm",
                "name": "ServiceImmediately IT Support",
                "description": "Create, view, update, and manage IT support incidents and service requests in ServiceImmediately.",
                "tags": ["itsm", "it", "tickets", "serviceimmediately", "incidents"],
            },
        ],
        "capabilities": {
            "streaming": False,
            "tools": [
                {
                    "name": "vertex_search_policies",
                    "description": "Query enterprise HR and IT knowledge base policies with verified deep-link citations.",
                },
                {
                    "name": "get_employee_balances",
                    "description": "Retrieve vacation, sick, and floating holiday balances from WorkWeek.",
                },
                {
                    "name": "request_time_off",
                    "description": "Submit paid time off or sick leave requests in WorkWeek.",
                },
                {
                    "name": "get_personal_info",
                    "description": "View employee profile, contact details, and manager reporting line in WorkWeek.",
                },
                {
                    "name": "update_personal_info",
                    "description": "Update address and emergency contact details in WorkWeek.",
                },
                {
                    "name": "get_leave_requests",
                    "description": "Query existing time-off and leave requests from WorkWeek.",
                },
                {
                    "name": "list_tickets",
                    "description": "List IT support and service request tickets in ServiceImmediately.",
                },
                {
                    "name": "get_ticket_details",
                    "description": "Retrieve status, category, priority, and updates for a ServiceImmediately ticket.",
                },
                {
                    "name": "create_ticket",
                    "description": "Create a new IT support incident in ServiceImmediately.",
                },
                {
                    "name": "update_ticket_status",
                    "description": "Update the state of a ServiceImmediately incident following ITIL lifecycle transitions.",
                },
                {
                    "name": "add_ticket_comment",
                    "description": "Append a note or update comment to an active ServiceImmediately incident.",
                },
            ],
        },
        "authentication": {
            "type": "none",
        },
    }


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

    # Fetch updated balances, leave requests, and tickets for live sidebar refresh
    balances = get_employee_balances(user_id)
    leave_requests = get_leave_requests(user_id)
    tickets = list_tickets(user_id)

    return {
        "status": "success",
        "response": response_text,
        "user_id": user_id,
        "session_id": session_id,
        "balances": balances.get("balances", {}),
        "leave_requests": leave_requests.get("leave_requests", []),
        "tickets": tickets.get("tickets", []),
    }


@app.get("/api/profile")
async def profile_endpoint(user_id: Optional[str] = None):
    """Fetches profile metadata, leave balances, and leave history for active employee."""
    uid = user_id or config.DEFAULT_EMPLOYEE_ID
    set_active_caller_context(uid)
    profile = get_personal_info(uid)
    balances = get_employee_balances(uid)
    leave_requests = get_leave_requests(uid)
    return {
        "profile": profile,
        "balances": balances.get("balances", {}),
        "leave_requests": leave_requests.get("leave_requests", []),
    }


@app.get("/api/leave-requests")
async def leave_requests_endpoint(user_id: Optional[str] = None):
    """Fetches leave requests from WorkWeek for active employee."""
    uid = user_id or config.DEFAULT_EMPLOYEE_ID
    set_active_caller_context(uid)
    return get_leave_requests(uid)


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
    leave_requests = get_leave_requests(payload.user_id)
    tickets = list_tickets(payload.user_id)
    return {
        "status": "success",
        "user_id": payload.user_id,
        "profile": profile,
        "balances": balances.get("balances", {}),
        "leave_requests": leave_requests.get("leave_requests", []),
        "tickets": tickets.get("tickets", []),
    }


def start_server(host: str = "0.0.0.0", port: int = 8080):
    """Starts the FastAPI Web UI server."""
    uvicorn.run("agent.web_server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    start_server()
