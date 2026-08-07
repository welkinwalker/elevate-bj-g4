"""WorkWeek (HCM) Toolset implementation.

Conforms to:
- enterprise_services_openapi.json (/work-week/mcp/)
- SDD.md Section 3.2, 4.1, 5.1
- BRD FR-3.1, FR-3.2, FR-3.3, FR-3.4
"""

import datetime
import json
import re
import time
from typing import Any
import httpx

from .. import config
from ..guardrails import ModelArmorGuard


def _call_remote_workweek_mcp(method_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    """Invokes live remote WorkWeek FastMCP server via JSON-RPC 2.0."""
    url = config.WORKWEEK_MCP_URL
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
# In-Memory State Store (High-fidelity Mock for Testing & Offline Execution)
# =============================================================================
class WorkWeekStateStore:
    def __init__(self):
        self.current_caller_id = config.DEFAULT_EMPLOYEE_ID
        self.employees = {
            "EMP-247": {
                "employee_id": "EMP-247",
                "name": "Levichen Employee",
                "email": "levichen@company.internal",
                "department": "Cloud Solutions Engineering",
                "role": "Senior Customer Solutions Engineer",
                "work_location": "Singapore Office (80 Pasir Panjang Rd)",
                "manager": "Director of Solutions Architecture",
                "hire_date": "2022-01-15",
                "address": "Singapore Office, 80 Pasir Panjang Rd, Singapore",
                "phone": "+65-6521-0000",
                "leave_balances": {
                    "vacation": {
                        "category": "Vacation",
                        "accrued_days": 20.0,
                        "used_days": 5.0,
                        "remaining_days": 15.0,
                        "remaining_hours": 120.0,
                    },
                    "sick": {
                        "category": "Sick",
                        "accrued_days": 10.0,
                        "used_days": 0.0,
                        "remaining_days": 10.0,
                        "remaining_hours": 80.0,
                    },
                },
                "leave_requests": [
                    {
                        "request_id": 869,
                        "start_date": "2026-06-01",
                        "end_date": "2026-06-05",
                        "leave_type": "Vacation",
                        "days": 5.0,
                        "status": "Approved",
                    }
                ],
            },
            "EMP-1002": {
                "employee_id": "EMP-1002",
                "name": "Alex Taylor",
                "email": "alex.taylor@company.internal",
                "department": "Cloud Engineering",
                "role": "Staff Software Engineer",
                "work_location": "London (Remote)",
                "manager": "Sarah Jenkins (VP of Infrastructure)",
                "hire_date": "2023-03-15",
                "address": "123 Tech Way, London",
                "phone": "+44 20 7946 0912",
                "leave_balances": {
                    "vacation": {
                        "category": "Vacation",
                        "accrued_days": 15.0,
                        "used_days": 10.0,
                        "remaining_days": 5.0,
                        "remaining_hours": 40.0,
                    },
                    "sick": {
                        "category": "Sick",
                        "accrued_days": 12.0,
                        "used_days": 2.0,
                        "remaining_days": 10.0,
                        "remaining_hours": 80.0,
                    },
                },
                "leave_requests": [
                    {
                        "request_id": 401,
                        "start_date": "2026-07-01",
                        "end_date": "2026-07-05",
                        "leave_type": "Vacation",
                        "days": 5.0,
                        "status": "Approved",
                    }
                ],
            },
            "EMP-1003": {
                "employee_id": "EMP-1003",
                "name": "Maria Santos",
                "email": "maria.santos@company.internal",
                "department": "Marketing Operations",
                "role": "Marketing Director",
                "work_location": "Singapore (Onsite)",
                "manager": "David Chen (CMO)",
                "hire_date": "2021-08-01",
                "address": "88 Marina Blvd, Singapore",
                "phone": "+65 6789 0123",
                "leave_balances": {
                    "vacation": {
                        "category": "Vacation",
                        "accrued_days": 20.0,
                        "used_days": 6.0,
                        "remaining_days": 14.0,
                        "remaining_hours": 112.0,
                    },
                    "sick": {
                        "category": "Sick",
                        "accrued_days": 14.0,
                        "used_days": 1.0,
                        "remaining_days": 13.0,
                        "remaining_hours": 104.0,
                    },
                },
                "leave_requests": [],
            },
        }

    def get_employee(self, employee_id: str) -> dict[str, Any] | None:
        return self.employees.get(employee_id)


_store = WorkWeekStateStore()


def set_active_caller_context(employee_id: str) -> None:
    """Sets the authenticated employee identity context for the active session."""
    _store.current_caller_id = employee_id


def get_active_caller_context() -> str:
    """Returns the current active employee caller ID."""
    return _store.current_caller_id


# =============================================================================
# Tool Functions Exposed to ADK Supervisor Agent
# =============================================================================
def get_current_employee_id() -> dict[str, Any]:
    """Gets the employee ID of the authenticated user session.

    Returns:
        Dictionary containing authenticated employee_id and user profile metadata.
    """
    caller_id = _store.current_caller_id
    emp = _store.get_employee(caller_id)
    emp_name = emp["name"] if emp else "Authenticated Employee"
    return {
        "status": "success",
        "employee_id": caller_id,
        "authenticated_as": emp_name,
    }


def get_employee_balances(employee_id: str | None = None) -> dict[str, Any]:
    """Fetches remaining and used Vacation and Sick leave balances for an employee.

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

    # 2. Try Live Remote FastMCP Call (if targeting current remote tenant context)
    if target_id == "EMP-247" or target_id == _store.current_caller_id:
        remote_res = _call_remote_workweek_mcp("get_employee_balances", {"employee_id": target_id})
        if remote_res and "content" in remote_res:
            text_resp = remote_res["content"][0].get("text", "")
            if "Leave Balances" in text_resp or "Vacation" in text_resp:
                vac_rem, sick_rem = 15.0, 10.0
                vac_match = re.search(r"Vacation:\s*([\d.]+)\s*days\s*remaining\s*\(([\d.]+)/([\d.]+)\s*used\)", text_resp)
                sick_match = re.search(r"Sick:\s*([\d.]+)\s*days\s*remaining\s*\(([\d.]+)/([\d.]+)\s*used\)", text_resp)
                if vac_match and sick_match:
                    vac_rem, vac_used, vac_acc = float(vac_match.group(1)), float(vac_match.group(2)), float(vac_match.group(3))
                    sick_rem, sick_used, sick_acc = float(sick_match.group(1)), float(sick_match.group(2)), float(sick_match.group(3))
                    return {
                        "status": "success",
                        "employee_id": target_id,
                        "balances": {
                            "vacation": {
                                "accrued_days": vac_acc,
                                "used_days": vac_used,
                                "remaining_days": vac_rem,
                                "remaining_hours": vac_rem * 8.0,
                            },
                            "sick": {
                                "accrued_days": sick_acc,
                                "used_days": sick_used,
                                "remaining_days": sick_rem,
                                "remaining_hours": sick_rem * 8.0,
                            },
                        },
                        "summary": f"Vacation: {vac_rem * 8.0}h ({vac_rem} days) remaining; Sick: {sick_rem * 8.0}h ({sick_rem} days) remaining.",
                    }

    # 3. Local State
    emp = _store.get_employee(target_id)
    if not emp:
        return {
            "status": "error",
            "error_code": "404_NOT_FOUND",
            "message": f"Employee {target_id} not found in WorkWeek HCM.",
        }

    vacation = emp["leave_balances"]["vacation"]
    sick = emp["leave_balances"]["sick"]

    return {
        "status": "success",
        "employee_id": target_id,
        "balances": {
            "vacation": {
                "accrued_days": vacation["accrued_days"],
                "used_days": vacation["used_days"],
                "remaining_days": vacation["remaining_days"],
                "remaining_hours": vacation["remaining_hours"],
            },
            "sick": {
                "accrued_days": sick["accrued_days"],
                "used_days": sick["used_days"],
                "remaining_days": sick["remaining_days"],
                "remaining_hours": sick["remaining_hours"],
            },
        },
        "summary": (
            f"Vacation: {vacation['remaining_hours']}h ({vacation['remaining_days']} days) remaining; "
            f"Sick: {sick['remaining_hours']}h ({sick['remaining_days']} days) remaining."
        ),
    }


def request_time_off(
    employee_id: str,
    start_date: str,
    end_date: str,
    leave_type: str,
    days: float = 1.0,
) -> dict[str, Any]:
    """Submits a time-off (PTO/Sick) request in WorkWeek HCM after validation.

    Args:
        employee_id: Employee ID (e.g. 'EMP-247')
        start_date: Start date formatted as 'YYYY-MM-DD'
        end_date: End date formatted as 'YYYY-MM-DD'
        leave_type: 'Vacation' or 'Sick'
        days: Number of working days requested (e.g. 2.0)
    """
    # 1. RBAC Isolation Check
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        _store.current_caller_id, employee_id
    )
    if not allowed:
        return {"status": "error", "error_code": "403_FORBIDDEN", "message": rbac_msg}

    # 2. Date Format & Chronology Validation (BRD FR-3.3)
    date_regex = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(date_regex, start_date) or not re.match(date_regex, end_date):
        return {
            "status": "error",
            "error_code": "INVALID_DATE_FORMAT",
            "message": f"Dates must follow ISO-8601 'YYYY-MM-DD' format (got start={start_date}, end={end_date}).",
        }

    try:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as e:
        return {"status": "error", "error_code": "INVALID_DATE", "message": str(e)}

    if start_dt > end_dt:
        return {
            "status": "error",
            "error_code": "INVALID_CHRONOLOGY",
            "message": f"Start date ({start_date}) cannot be after end date ({end_date}).",
        }

    norm_leave_type = leave_type.capitalize()
    if norm_leave_type not in ["Vacation", "Sick"]:
        return {
            "status": "error",
            "error_code": "INVALID_LEAVE_TYPE",
            "message": f"Invalid leave type '{leave_type}'. Must be 'Vacation' or 'Sick'.",
        }

    # 3. Check Balance in Store
    emp = _store.get_employee(employee_id)
    if not emp:
        return {
            "status": "error",
            "error_code": "404_NOT_FOUND",
            "message": f"Employee {employee_id} not found in WorkWeek HCM.",
        }

    balance_key = norm_leave_type.lower()
    balance_record = emp["leave_balances"][balance_key]
    remaining_days = balance_record["remaining_days"]

    if days > remaining_days:
        return {
            "status": "error",
            "error_code": "INSUFFICIENT_BALANCE",
            "message": (
                f"Insufficient {norm_leave_type} balance. Requested: {days} days, "
                f"Available: {remaining_days} days."
            ),
        }

    # 4. Call Remote FastMCP Server Live if configured
    if employee_id == "EMP-247":
        _call_remote_workweek_mcp(
            "request_time_off",
            {
                "employee_id": employee_id,
                "start_date": start_date,
                "end_date": end_date,
                "leave_type": norm_leave_type,
                "days": days,
            },
        )

    # 5. Local State Deduction
    balance_record["used_days"] += days
    balance_record["remaining_days"] -= days
    balance_record["remaining_hours"] = balance_record["remaining_days"] * 8.0

    request_id = len(emp["leave_requests"]) + 501
    emp["leave_requests"].append(
        {
            "request_id": request_id,
            "start_date": start_date,
            "end_date": end_date,
            "leave_type": norm_leave_type,
            "days": days,
            "status": "Approved",
        }
    )

    return {
        "status": "success",
        "request_id": request_id,
        "employee_id": employee_id,
        "leave_type": norm_leave_type,
        "days_booked": days,
        "start_date": start_date,
        "end_date": end_date,
        "remaining_balance_days": balance_record["remaining_days"],
        "message": (
            f"Time off request {request_id} ({norm_leave_type}, {days} days from {start_date} to {end_date}) "
            f"successfully submitted and approved. Remaining balance: {balance_record['remaining_days']} days."
        ),
    }


def update_personal_info(
    employee_id: str, address: str | None = None, phone: str | None = None
) -> dict[str, Any]:
    """Updates personal contact details (home address and phone number) in WorkWeek HCM.

    Args:
        employee_id: Employee ID (e.g. 'EMP-247')
        address: New home address string
        phone: New telephone number string
    """
    # 1. RBAC Isolation Check
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        _store.current_caller_id, employee_id
    )
    if not allowed:
        return {"status": "error", "error_code": "403_FORBIDDEN", "message": rbac_msg}

    # 2. Validation
    if address and len(address.strip()) < 5:
        return {
            "status": "error",
            "error_code": "INVALID_ADDRESS",
            "message": "Home address must be at least 5 characters long.",
        }
    if phone and not re.match(r"^\+?[\d\s\-()]{7,20}$", phone.strip()):
        return {
            "status": "error",
            "error_code": "INVALID_PHONE",
            "message": "Invalid telephone format.",
        }

    # 3. Call Remote Live FastMCP if EMP-247
    if employee_id == "EMP-247":
        _call_remote_workweek_mcp(
            "update_personal_info",
            {
                "employee_id": employee_id,
                "address": address or "",
                "phone": phone or "",
            },
        )

    # 4. Local State Mutation
    emp = _store.get_employee(employee_id)
    if not emp:
        return {
            "status": "error",
            "error_code": "404_NOT_FOUND",
            "message": f"Employee {employee_id} not found in WorkWeek HCM.",
        }

    if address:
        emp["address"] = address
    if phone:
        emp["phone"] = phone

    return {
        "status": "success",
        "employee_id": employee_id,
        "updated_fields": {
            "address": emp["address"],
            "phone": emp["phone"],
        },
        "message": f"Personal info updated successfully for {emp['name']} ({employee_id}).",
    }


def get_personal_info(employee_id: str | None = None) -> dict[str, Any]:
    """Fetches personal contact details and employment metadata from WorkWeek HCM.

    Args:
        employee_id: Employee ID. If omitted, defaults to active session caller.
    """
    target_id = employee_id or _store.current_caller_id

    # 1. RBAC Isolation Check
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        _store.current_caller_id, target_id
    )
    if not allowed:
        return {"status": "error", "error_code": "403_FORBIDDEN", "message": rbac_msg}

    emp = _store.get_employee(target_id)
    if not emp:
        return {
            "status": "error",
            "error_code": "404_NOT_FOUND",
            "message": f"Employee {target_id} not found in WorkWeek HCM.",
        }

    return {
        "status": "success",
        "employee_id": target_id,
        "name": emp["name"],
        "email": emp["email"],
        "department": emp["department"],
        "role": emp["role"],
        "work_location": emp["work_location"],
        "manager": emp["manager"],
        "address": emp["address"],
        "phone": emp["phone"],
    }


def cancel_leave_request(employee_id: str, request_id: int) -> dict[str, Any]:
    """Cancels a pending or approved leave request and refunds the balance in WorkWeek HCM."""
    # 1. RBAC Isolation Check
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        _store.current_caller_id, employee_id
    )
    if not allowed:
        return {"status": "error", "error_code": "403_FORBIDDEN", "message": rbac_msg}

    # 2. Call Remote Live FastMCP if EMP-247
    if employee_id == "EMP-247":
        _call_remote_workweek_mcp(
            "cancel_leave_request",
            {"employee_id": employee_id, "request_id": request_id},
        )

    # 3. Local State
    emp = _store.get_employee(employee_id)
    if not emp:
        return {"status": "error", "message": f"Employee {employee_id} not found."}

    for req in emp["leave_requests"]:
        if req["request_id"] == request_id and req["status"] != "Cancelled":
            req["status"] = "Cancelled"
            b_key = req["leave_type"].lower()
            emp["leave_balances"][b_key]["used_days"] -= req["days"]
            emp["leave_balances"][b_key]["remaining_days"] += req["days"]
            emp["leave_balances"][b_key]["remaining_hours"] = emp["leave_balances"][b_key]["remaining_days"] * 8.0
            return {
                "status": "success",
                "employee_id": employee_id,
                "request_id": request_id,
                "message": f"Leave request {request_id} cancelled and {req['days']} days refunded.",
            }

    return {"status": "error", "message": f"Request {request_id} not found or already cancelled."}
