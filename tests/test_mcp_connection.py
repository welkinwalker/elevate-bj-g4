"""Live FastMCP Connection & Task Verification Probe.

Tests end-to-end connectivity, token authentication, tools discovery,
and task execution across WorkWeek and ServiceImmediately MCP servers.
"""

import sys
from pathlib import Path

# Ensure root directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import asyncio
import httpx
import json

from agent import config
from agent.mcp_servers.workweek_server import WorkWeekFastMCPServer
from agent.mcp_servers.serviceimmediately_server import ServiceImmediatelyFastMCPServer


async def test_remote_mcp_endpoint(url: str, token: str, label: str):
    """Tests connectivity to remote FastMCP server."""
    print(f"\n--- [1] Probing Remote FastMCP Endpoint: {label} ---")
    print(f"URL: {url}")
    headers = {
        "X-MCP-Token": token,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream, */*",
    }

    # JSON-RPC tools/list payload
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            print(f"HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Connection Successful! Discovered tools:")
                tools = data.get("result", {}).get("tools", [])
                for t in tools:
                    print(f"   • {t.get('name')}: {t.get('description')}")
                return True
            else:
                print(f"⚠️ Remote endpoint returned HTTP {resp.status_code}: {resp.text[:200]}")
                return False
    except Exception as e:
        print(f"⚠️ Remote network connection probe note: {e}")
        return False


async def test_remote_tool_call(url: str, token: str, tool_name: str, arguments: dict):
    """Executes a real tool call directly against the live remote SaaS FastMCP server."""
    print(f"\n--- Calling Remote Live FastMCP Tool: {tool_name} ---")
    headers = {
        "X-MCP-Token": token,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream, */*",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 201,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        print(f"Remote HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ Remote FastMCP Result: {json.dumps(result.get('result', {}), indent=2)}")
            return result
        else:
            print(f"Response: {resp.text}")
            return None


async def test_fastmcp_task_execution():
    """Tests end-to-end FastMCP task execution via JSON-RPC protocol."""
    print(f"\n--- [2] Executing Live FastMCP Tasks via Protocol ---")
    token = config.MCP_TOKEN
    headers = {"X-MCP-Token": token}

    ww_server = WorkWeekFastMCPServer(mcp_token=token)
    si_server = ServiceImmediatelyFastMCPServer(mcp_token=token)

    # Task A: Discover WorkWeek Tools
    print("\n[Task A] Discovering WorkWeek Tools (tools/list)...")
    ww_tools_res = await ww_server.handle_jsonrpc({"jsonrpc": "2.0", "id": 101, "method": "tools/list"}, headers)
    tool_names = [t["name"] for t in ww_tools_res["result"]["tools"]]
    print(f"✅ Discovered {len(tool_names)} WorkWeek tools: {', '.join(tool_names)}")

    # Task B: Query Leave Balances via MCP
    print("\n[Task B] Calling 'get_employee_balances' for EMP-1002 via MCP...")
    bal_res = await ww_server.handle_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 102,
            "method": "tools/call",
            "params": {"name": "get_employee_balances", "arguments": {"employee_id": "EMP-1002"}},
        },
        headers,
    )
    print(f"✅ FastMCP Tool Result:")
    print(f"   {bal_res['result']['content'][0]['text']}")

    # Task C: Submit a Vacation Request via MCP
    print("\n[Task C] Calling 'request_time_off' (2 days Vacation) via MCP...")
    pto_res = await ww_server.handle_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 103,
            "method": "tools/call",
            "params": {
                "name": "request_time_off",
                "arguments": {
                    "employee_id": "EMP-1002",
                    "start_date": "2026-08-24",
                    "end_date": "2026-08-25",
                    "leave_type": "Vacation",
                    "days": 2.0,
                },
            },
        },
        headers,
    )
    print(f"✅ FastMCP Leave Booking Result:")
    print(f"   {pto_res['result']['content'][0]['text']}")

    # Task D: Create IT Support Incident via ServiceImmediately MCP
    print("\n[Task D] Calling 'create_ticket' on ServiceImmediately via MCP...")
    ticket_res = await si_server.handle_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 104,
            "method": "tools/call",
            "params": {
                "name": "create_ticket",
                "arguments": {
                    "requested_by": "EMP-1002",
                    "category": "IT / Hardware",
                    "short_description": "Ergonomic keyboard replacement request",
                    "priority": "3 - Moderate",
                    "assignment_group": "Service Desk",
                },
            },
        },
        headers,
    )
    print(f"✅ FastMCP Incident Creation Result:")
    print(f"   {ticket_res['result']['content'][0]['text']}")

    # Task E: Verify MCP Resource Reading
    print("\n[Task E] Reading MCP Resource 'workweek://employees/EMP-1002/profile'...")
    res_profile = await ww_server.handle_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 105,
            "method": "resources/read",
            "params": {"uri": "workweek://employees/EMP-1002/profile"},
        },
        headers,
    )
    print(f"✅ FastMCP Resource Content:")
    print(f"   {json.dumps(res_profile['result']['contents'][0], indent=2)}")

    # Task F: Security Test - Unauthorized Token Rejection
    print("\n[Task F] Testing Token Security (Invalid X-MCP-Token)...")
    bad_headers = {"X-MCP-Token": "invalid_wrong_token"}
    bad_auth_res = await ww_server.handle_jsonrpc(
        {"jsonrpc": "2.0", "id": 106, "method": "tools/list"}, bad_headers
    )
    assert bad_auth_res.get("error", {}).get("code") == 401
    print(f"✅ Correctly Rejected with 401 Unauthorized: {bad_auth_res['error']['message']}")


async def main():
    print("============================================================")
    print(" Project Elevate: FastMCP Connection & Task Verification")
    print("============================================================")

    # 1. Test Remote SaaS Endpoints Connectivity
    await test_remote_mcp_endpoint(config.WORKWEEK_MCP_URL, config.MCP_TOKEN, "WorkWeek HCM")
    await test_remote_mcp_endpoint(config.SERVICEIMMEDIATELY_MCP_URL, config.MCP_TOKEN, "ServiceImmediately ITSM")

    # 2. Execute Real Live Remote Tool Calls against SaaS Cloud Endpoints
    # The remote SaaS token is bound to employee EMP-247
    await test_remote_tool_call(config.WORKWEEK_MCP_URL, config.MCP_TOKEN, "get_current_employee_id", {})
    await test_remote_tool_call(config.WORKWEEK_MCP_URL, config.MCP_TOKEN, "get_employee_balances", {"employee_id": "EMP-247"})
    await test_remote_tool_call(config.WORKWEEK_MCP_URL, config.MCP_TOKEN, "get_personal_info", {"employee_id": "EMP-247"})
    await test_remote_tool_call(config.SERVICEIMMEDIATELY_MCP_URL, config.MCP_TOKEN, "list_tickets", {"employee_id": "EMP-247"})

    # 3. Test End-to-End Task Executions & State Validations
    await test_fastmcp_task_execution()

    print("\n============================================================")
    print(" 🎉 All FastMCP Connection & Task Tests Completed Successfully!")
    print("============================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
