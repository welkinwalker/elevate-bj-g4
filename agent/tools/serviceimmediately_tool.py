"""ServiceImmediately (ITSM/HRSD) Toolset implementation.

Conforms to:
- enterprise_services_openapi.json (/service-immediately/mcp/)
- SDD.md Section 3.2, 4.1, 5.1
- BRD FR-4.1, FR-4.2, FR-4.3
"""

import datetime
import json
import time
from typing import Any
import httpx

from .. import config
from ..guardrails import ModelArmorGuard


def _call_remote_itsm_mcp(method_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    """Invokes live remote ServiceImmediately FastMCP server via JSON-RPC 2.0."""
    url = config.SERVICEIMMEDIATELY_MCP_URL
    token = config.MCP_TOKEN
    if not url or not token or token == "mcp_your_token_here":
        return None

    headers = {
        "X-MCP-Token": token,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream, */*",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": "tools/call",
        "params": {
            "name": method_name,
            "arguments": arguments,
        },
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if "result" in data and not data.get("result", {}).get("isError"):
                    return data["result"]
    except Exception:
        pass
    return None


# =============================================================================
# In-Memory State Store (ServiceImmediately High-Fidelity Mock)
# =============================================================================
class ServiceImmediatelyStateStore:
    def __init__(self):
        self.current_caller_id = config.DEFAULT_EMPLOYEE_ID
        self.tickets: dict[str, dict[str, Any]] = {
            "INC0000944": {
                "ticket_id": "INC0000944",
                "requested_by": "EMP-247",
                "category": "Inquiry / Help",
                "short_description": "Onboarding setup and badges configuration",
                "priority": "3 - Moderate",
                "state": "New",
                "assignment_group": "Service Desk",
                "created_at": "2026-08-05T07:56:36Z",
                "updated_at": "2026-08-05T07:56:36Z",
                "comments": [
                    {
                        "author": "EMP-247",
                        "comment": "Onboarding badge and workstation access setup requested.",
                        "timestamp": "2026-08-05T07:56:36Z",
                    }
                ],
                "resolution_notes": "",
            },
            "INC123456": {
                "ticket_id": "INC123456",
                "requested_by": "EMP-1002",
                "category": "IT / Network",
                "short_description": "VPN connection dropping intermittently",
                "priority": "3 - Moderate",
                "state": "In Progress",
                "assignment_group": "Network Team",
                "created_at": "2026-08-06T08:00:00Z",
                "updated_at": "2026-08-06T08:30:00Z",
                "comments": [
                    {
                        "author": "EMP-1002",
                        "comment": "VPN drops every 10-15 minutes when connected to EU gateway.",
                        "timestamp": "2026-08-06T08:00:00Z",
                    },
                    {
                        "author": "Network Admin",
                        "comment": "Investigating gateway logs for packet loss. Patch scheduled for 18:00 UTC.",
                        "timestamp": "2026-08-06T08:30:00Z",
                    },
                ],
                "resolution_notes": "",
            },
            "INC-10293": {
                "ticket_id": "INC-10293",
                "requested_by": "EMP-1002",
                "category": "IT / Hardware",
                "short_description": "Secondary monitor flickering",
                "priority": "4 - Low",
                "state": "New",
                "assignment_group": "Service Desk",
                "created_at": "2026-08-06T10:00:00Z",
                "updated_at": "2026-08-06T10:00:00Z",
                "comments": [],
                "resolution_notes": "",
            },
            "INC-88901": {
                "ticket_id": "INC-88901",
                "requested_by": "EMP-1003",
                "category": "HRSD / Payroll",
                "short_description": "Direct deposit routing update inquiry",
                "priority": "3 - Moderate",
                "state": "Resolved",
                "assignment_group": "Payroll Operations",
                "created_at": "2026-08-01T09:00:00Z",
                "updated_at": "2026-08-02T14:00:00Z",
                "comments": [
                    {
                        "author": "Payroll Specialist",
                        "comment": "Bank routing verification confirmed and updated in payroll portal.",
                        "timestamp": "2026-08-02T14:00:00Z",
                    }
                ],
                "resolution_notes": "Routing change confirmed with employee bank.",
            },
        }
        self.last_ticket_creation: dict[str, float] = {}

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        return self.tickets.get(ticket_id)


_store = ServiceImmediatelyStateStore()

VALID_STATES = ["New", "In Progress", "On Hold", "Resolved", "Closed", "Canceled"]
VALID_TRANSITIONS = {
    "New": ["In Progress", "Canceled"],
    "In Progress": ["On Hold", "Resolved", "Canceled"],
    "On Hold": ["In Progress", "Canceled"],
    "Resolved": ["Closed", "In Progress"],
    "Closed": [],
    "Canceled": [],
}


def set_active_caller_context(employee_id: str) -> None:
    """Sets the active caller identity for ITSM/HRSD ticket interactions."""
    _store.current_caller_id = employee_id


# =============================================================================
# Tool Functions Exposed to ADK Supervisor Agent
# =============================================================================
def list_tickets(employee_id: str | None = None) -> dict[str, Any]:
    """Lists all ServiceImmediately incident tickets requested by a specific employee.

    Args:
        employee_id: Employee ID (e.g. 'EMP-247'). If omitted, defaults to active session caller.
    """
    target_id = employee_id or _store.current_caller_id

    # 1. RBAC Isolation Check
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        _store.current_caller_id, target_id
    )
    if not allowed:
        return {"status": "error", "error_code": "403_FORBIDDEN", "message": rbac_msg}

    # 2. Try Remote Live FastMCP Call if EMP-247
    if target_id == "EMP-247":
        remote_res = _call_remote_itsm_mcp("list_tickets", {"employee_id": target_id})
        if remote_res and "content" in remote_res:
            txt = remote_res["content"][0].get("text", "")
            try:
                tickets_list = json.loads(txt)
                if isinstance(tickets_list, list):
                    return {
                        "status": "success",
                        "employee_id": target_id,
                        "count": len(tickets_list),
                        "tickets": tickets_list,
                    }
            except Exception:
                pass

    # 3. Local Store
    user_tickets = [
        t for t in _store.tickets.values() if t["requested_by"] == target_id
    ]

    return {
        "status": "success",
        "employee_id": target_id,
        "count": len(user_tickets),
        "tickets": user_tickets,
    }


def get_ticket_details(ticket_id: str) -> dict[str, Any]:
    """Fetches full details, priority, and timeline for a ticket."""
    ticket = _store.get_ticket(ticket_id)
    if not ticket:
        return {
            "status": "error",
            "error_code": "404_NOT_FOUND",
            "message": f"Ticket '{ticket_id}' not found in ServiceImmediately.",
        }

    return {
        "status": "success",
        "ticket_id": ticket["ticket_id"],
        "requested_by": ticket["requested_by"],
        "category": ticket["category"],
        "short_description": ticket["short_description"],
        "priority": ticket["priority"],
        "state": ticket["state"],
        "assignment_group": ticket["assignment_group"],
        "created_at": ticket["created_at"],
        "updated_at": ticket["updated_at"],
        "comments": ticket["comments"],
        "resolution_notes": ticket["resolution_notes"],
        "ticket": ticket,
    }


def create_ticket(
    requested_by: str,
    category: str,
    short_description: str,
    priority: str = "3 - Moderate",
    assignment_group: str = "Service Desk",
) -> dict[str, Any]:
    """Creates a new incident ticket in ServiceImmediately."""
    # 1. RBAC Isolation Check
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        _store.current_caller_id, requested_by
    )
    if not allowed:
        return {"status": "error", "error_code": "403_FORBIDDEN", "message": rbac_msg}

    # 2. Priority & Category Validation
    valid_priorities = ["1 - Critical", "2 - High", "3 - Moderate", "4 - Low"]
    if priority not in valid_priorities:
        return {
            "status": "error",
            "error_code": "INVALID_PRIORITY",
            "message": f"Priority '{priority}' is invalid. Must be one of: {', '.join(valid_priorities)}",
        }

    # 3. Duplicate Ticket Mitigation (5 minutes)
    dedup_key = f"{requested_by}:{category}:{short_description}"
    now_ts = time.time()
    last_ts = _store.last_ticket_creation.get(dedup_key, 0)
    if (now_ts - last_ts) < 300 and last_ts > 0:
        # Find the existing ticket
        for t in reversed(list(_store.tickets.values())):
            if (
                t["requested_by"] == requested_by
                and t["category"] == category
                and t["short_description"] == short_description
            ):
                return {
                    "status": "success",
                    "duplicate_mitigated": True,
                    "ticket_id": t["ticket_id"],
                    "state": t["state"],
                    "message": (
                        f"Existing open ticket {t['ticket_id']} found for identical issue created recently. "
                        "Duplicate submission mitigated."
                    ),
                }

    _store.last_ticket_creation[dedup_key] = now_ts

    # 4. Call Remote Live FastMCP Server if EMP-247
    if requested_by == "EMP-247":
        _call_remote_itsm_mcp(
            "create_ticket",
            {
                "requested_by": requested_by,
                "category": category,
                "short_description": short_description,
                "priority": priority,
                "assignment_group": assignment_group,
            },
        )

    # 5. Local State Execution
    ticket_num = len(_store.tickets) + 1000
    ticket_id = f"INC-{ticket_num}"
    now_iso = datetime.datetime.now(datetime.UTC).isoformat()

    new_ticket = {
        "ticket_id": ticket_id,
        "requested_by": requested_by,
        "category": category,
        "short_description": short_description,
        "priority": priority,
        "state": "New",
        "assignment_group": assignment_group,
        "created_at": now_iso,
        "updated_at": now_iso,
        "comments": [],
        "resolution_notes": "",
    }
    _store.tickets[ticket_id] = new_ticket

    return {
        "status": "success",
        "ticket_id": ticket_id,
        "requested_by": requested_by,
        "category": category,
        "short_description": short_description,
        "priority": priority,
        "state": "New",
        "assignment_group": assignment_group,
        "message": f"Incident ticket {ticket_id} successfully created with priority '{priority}' and assigned to '{assignment_group}'.",
    }


def add_ticket_comment(
    ticket_id: str, author: str, comment: str
) -> dict[str, Any]:
    """Appends a comment/note to the activity log of a ServiceImmediately ticket."""
    if _store.current_caller_id == "EMP-247":
        _call_remote_itsm_mcp(
            "add_ticket_comment",
            {"ticket_id": ticket_id, "author": author, "comment": comment},
        )

    ticket = _store.get_ticket(ticket_id)
    if not ticket:
        return {
            "status": "error",
            "error_code": "404_NOT_FOUND",
            "message": f"Ticket '{ticket_id}' not found in ServiceImmediately.",
        }

    now_iso = datetime.datetime.now(datetime.UTC).isoformat()
    ticket["comments"].append(
        {"author": author, "comment": comment, "timestamp": now_iso}
    )
    ticket["updated_at"] = now_iso

    return {
        "status": "success",
        "ticket_id": ticket_id,
        "comment_added": comment,
        "author": author,
        "timestamp": now_iso,
    }


def update_ticket_status(
    ticket_id: str,
    status: str,
    resolution_notes: str | None = None,
    updated_by: str = "ITIL System",
) -> dict[str, Any]:
    """Updates the lifecycle state of a ServiceImmediately ticket."""
    ticket = _store.get_ticket(ticket_id)
    if not ticket:
        return {
            "status": "error",
            "error_code": "404_NOT_FOUND",
            "message": f"Ticket '{ticket_id}' not found in ServiceImmediately.",
        }

    current_state = ticket["state"]
    if status not in VALID_STATES:
        return {
            "status": "error",
            "error_code": "INVALID_STATE",
            "message": f"State '{status}' is invalid. Valid states: {', '.join(VALID_STATES)}",
        }

    allowed_transitions = VALID_TRANSITIONS.get(current_state, [])
    if status not in allowed_transitions:
        return {
            "status": "error",
            "error_code": "INVALID_STATE_TRANSITION",
            "message": f"Illegal state transition from '{current_state}' to '{status}'. Allowed: {', '.join(allowed_transitions)}",
        }

    if _store.current_caller_id == "EMP-247":
        _call_remote_itsm_mcp(
            "update_ticket_status",
            {
                "ticket_id": ticket_id,
                "status": status,
                "resolution_notes": resolution_notes or "",
            },
        )

    now_iso = datetime.datetime.now(datetime.UTC).isoformat()
    ticket["state"] = status
    ticket["updated_at"] = now_iso
    if resolution_notes:
        ticket["resolution_notes"] = resolution_notes

    return {
        "status": "success",
        "ticket_id": ticket_id,
        "new_state": status,
        "resolution_notes": resolution_notes or "",
        "updated_at": now_iso,
    }
