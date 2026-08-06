"""WorkWeek FastMCP Standalone Server (/work-week/mcp/).

Exposes employee profiles and leave management workflows via Streamable HTTP MCP.
Conforms to enterprise_services_openapi.json and SDD.md Section 5.1.
"""

from typing import Any, Dict
from ..tools import workweek_tool


class WorkWeekFastMCPServer:
    """Stateless Streamable HTTP FastMCP server implementation for WorkWeek."""

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
                            "name": "get_current_employee_id",
                            "description": "Resolves the employee ID of the authenticated user session.",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                        {
                            "name": "get_employee_balances",
                            "description": "Fetches remaining and used Vacation and Sick leave balances for an employee.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"employee_id": {"type": "string"}},
                            },
                        },
                        {
                            "name": "request_time_off",
                            "description": "Submits a leave request with balance & chronological date checks.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "employee_id": {"type": "string"},
                                    "start_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                                    "end_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                                    "leave_type": {"type": "string", "enum": ["Vacation", "Sick"]},
                                    "days": {"type": "number"},
                                },
                                "required": ["employee_id", "start_date", "end_date", "leave_type"],
                            },
                        },
                        {
                            "name": "update_personal_info",
                            "description": "Updates personal contact details (address and phone).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "employee_id": {"type": "string"},
                                    "address": {"type": "string"},
                                    "phone": {"type": "string"},
                                },
                                "required": ["employee_id", "address", "phone"],
                            },
                        },
                        {
                            "name": "get_personal_info",
                            "description": "Retrieves employee work details and contact info.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"employee_id": {"type": "string"}},
                            },
                        },
                        {
                            "name": "cancel_leave_request",
                            "description": "Cancels a leave request and refunds days.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "employee_id": {"type": "string"},
                                    "request_id": {"type": "integer"},
                                },
                                "required": ["employee_id", "request_id"],
                            },
                        },
                    ]
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name == "get_current_employee_id":
                result = workweek_tool.get_current_employee_id()
            elif tool_name == "get_employee_balances":
                result = workweek_tool.get_employee_balances(**args)
            elif tool_name == "request_time_off":
                result = workweek_tool.request_time_off(**args)
            elif tool_name == "update_personal_info":
                result = workweek_tool.update_personal_info(**args)
            elif tool_name == "get_personal_info":
                result = workweek_tool.get_personal_info(**args)
            elif tool_name == "cancel_leave_request":
                result = workweek_tool.cancel_leave_request(**args)
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
            if "profile" in uri:
                emp_id = uri.split("/")[-2] if "profile" in uri else "EMP-1002"
                info = workweek_tool.get_personal_info(emp_id)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"contents": [info]}}
            elif "timeoff" in uri:
                emp_id = uri.split("/")[-2] if "timeoff" in uri else "EMP-1002"
                bal = workweek_tool.get_employee_balances(emp_id)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"contents": [bal]}}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32600, "message": "Invalid or unsupported Request."},
        }
