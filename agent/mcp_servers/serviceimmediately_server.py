"""ServiceImmediately FastMCP Standalone Server (/service-immediately/mcp/).

Exposes ITSM/HRSD ticket management workflows via Streamable HTTP MCP.
Conforms to enterprise_services_openapi.json and SDD.md Section 5.1.
"""

from typing import Any, Dict
from ..tools import serviceimmediately_tool


class ServiceImmediatelyFastMCPServer:
    """Stateless Streamable HTTP FastMCP server implementation for ServiceImmediately."""

    def __init__(self, mcp_token: str = "mcp_your_token_here"):
        self.mcp_token = mcp_token

    def verify_auth(self, headers: Dict[str, str]) -> bool:
        """Verifies custom X-MCP-Token header."""
        token = headers.get("X-MCP-Token") or headers.get("x-mcp-token")
        return token == self.mcp_token if self.mcp_token else True

    async def handle_jsonrpc(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Handles standard JSON-RPC 2.0 MCP requests."""
        if not self.verify_auth(headers):
            return {
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "error": {"code": 401, "message": "Unauthorized: Invalid or missing X-MCP-Token header."},
            }

        method = payload.get("method")
        params = payload.get("params", {})
        req_id = payload.get("id")

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "list_tickets",
                            "description": "Lists all incident tickets requested by a specific employee.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"employee_id": {"type": "string"}},
                            },
                        },
                        {
                            "name": "get_ticket_details",
                            "description": "Fetches ticket details, priority, and complete comment timeline.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"ticket_id": {"type": "string"}},
                                "required": ["ticket_id"],
                            },
                        },
                        {
                            "name": "create_ticket",
                            "description": "Submits a new incident ticket with duplicate mitigation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "requested_by": {"type": "string"},
                                    "category": {"type": "string"},
                                    "short_description": {"type": "string"},
                                    "priority": {"type": "string"},
                                    "assignment_group": {"type": "string"},
                                },
                                "required": ["requested_by", "category", "short_description"],
                            },
                        },
                        {
                            "name": "add_ticket_comment",
                            "description": "Appends a comment to the ticket activity log.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "ticket_id": {"type": "string"},
                                    "author": {"type": "string"},
                                    "comment": {"type": "string"},
                                },
                                "required": ["ticket_id", "author", "comment"],
                            },
                        },
                        {
                            "name": "update_ticket_status",
                            "description": "Updates ticket state machine (New -> In Progress -> Resolved -> Closed).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "ticket_id": {"type": "string"},
                                    "status": {"type": "string"},
                                    "resolution_notes": {"type": "string"},
                                    "updated_by": {"type": "string"},
                                },
                                "required": ["ticket_id", "status"],
                            },
                        },
                    ]
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name == "list_tickets":
                result = serviceimmediately_tool.list_tickets(**args)
            elif tool_name == "get_ticket_details":
                result = serviceimmediately_tool.get_ticket_details(**args)
            elif tool_name == "create_ticket":
                result = serviceimmediately_tool.create_ticket(**args)
            elif tool_name == "add_ticket_comment":
                result = serviceimmediately_tool.add_ticket_comment(**args)
            elif tool_name == "update_ticket_status":
                result = serviceimmediately_tool.update_ticket_status(**args)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method '{tool_name}' not found."},
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": str(result)}]},
            }

        elif method == "resources/read":
            uri = params.get("uri", "")
            tid = uri.split("/")[-1] if "tickets" in uri else "INC123456"
            details = serviceimmediately_tool.get_ticket_details(tid)
            return {"jsonrpc": "2.0", "id": req_id, "result": {"contents": [details]}}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32600, "message": "Invalid or unsupported Request."},
        }
