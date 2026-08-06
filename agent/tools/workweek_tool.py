"""WorkWeek (HCM) Toolset implementation.

Conforms to:
- enterprise_services_openapi.json (/work-week/mcp/)
- SDD.md Section 3.2, 4.1, 5.1
- BRD FR-3.1, FR-3.2, FR-3.3, FR-3.4
"""

import re
import datetime
from typing import Dict, Any, Optional
import httpx

from .. import config
from ..guardrails import ModelArmorGuard


# =============================================================================
# In-Memory State Store (High-fidelity Mock for Testing & Offline Execution)
# =============================================================================
class WorkWeekStateStore:
    def __init__(self):
        self.employees = {
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
            }
        }
        self.next_request_id = 501

    def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        return self.employees.get(employee_id)


_store = WorkWeekStateStore()


# =============================================================================
# WorkWeek Tools (ADK & FastMCP Callable)
# =============================================================================
def get_current_employee_id() -> Dict[str, Any]:
    """Resolves the employee ID of the currently authenticated user session."""
    return {
        "status": "success",
        "employee_id": config.DEFAULT_EMPLOYEE_ID,
        "authenticated_as": "Alex Taylor",
    }


def get_employee_balances(employee_id: str = "EMP-1002") -> Dict[str, Any]:
    """Fetches remaining and used Vacation and Sick leave balances for an employee.

    Args:
        employee_id: Employee ID (e.g. 'EMP-1002').
    """
    # 1. RBAC Isolation Check
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        config.DEFAULT_EMPLOYEE_ID, employee_id
    )
    if not allowed:
        return {"status": "error", "error_code": "403_FORBIDDEN", "message": rbac_msg}

    # 2. Query State
    emp = _store.get_employee(employee_id)
    if not emp:
        return {
            "status": "error",
            "error_code": "404_NOT_FOUND",
            "message": f"Employee {employee_id} not found in WorkWeek HCM.",
        }

    vacation = emp["leave_balances"]["vacation"]
    sick = emp["leave_balances"]["sick"]

    return {
        "status": "success",
        "employee_id": employee_id,
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
) -> Dict[str, Any]:
    """Submits a time-off (PTO/Sick) request in WorkWeek HCM after validation.

    Args:
        employee_id: Employee ID (e.g. 'EMP-1002')
        start_date: Start date formatted as 'YYYY-MM-DD'
        end_date: End date formatted as 'YYYY-MM-DD'
        leave_type: 'Vacation' or 'Sick'
        days: Number of working days requested (e.g. 2.0)
    """
    # 1. RBAC Isolation Check
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        config.DEFAULT_EMPLOYEE_ID, employee_id
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
            "message": f"Validation Error: start_date ({start_date}) cannot be after end_date ({end_date}).",
        }

    # Normalize leave type
    norm_type = leave_type.capitalize()
    if norm_type not in ["Vacation", "Sick"]:
        return {
            "status": "error",
            "error_code": "INVALID_LEAVE_TYPE",
            "message": f"leave_type must be 'Vacation' or 'Sick' (got '{leave_type}').",
        }

    emp = _store.get_employee(employee_id)
    if not emp:
        return {"status": "error", "error_code": "404_NOT_FOUND", "message": f"Employee {employee_id} not found."}

    # 3. Balance Constraints Check (BRD FR-3.3)
    bal_key = "vacation" if norm_type == "Vacation" else "sick"
    current_balance = emp["leave_balances"][bal_key]["remaining_days"]

    if days > current_balance:
        return {
            "status": "error",
            "error_code": "INSUFFICIENT_BALANCE",
            "message": (
                f"Insufficient balance: Requested {days} days of {norm_type} leave, "
                f"but only {current_balance} days remain."
            ),
        }

    # 4. Mutate State & Deduct Balance
    emp["leave_balances"][bal_key]["remaining_days"] -= days
    emp["leave_balances"][bal_key]["remaining_hours"] -= days * 8.0
    emp["leave_balances"][bal_key]["used_days"] += days

    req_id = _store.next_request_id
    _store.next_request_id += 1

    record = {
        "request_id": req_id,
        "start_date": start_date,
        "end_date": end_date,
        "leave_type": norm_type,
        "days": days,
        "status": "Approved",
        "submitted_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    emp["leave_requests"].append(record)

    return {
        "status": "success",
        "request_id": req_id,
        "employee_id": employee_id,
        "leave_type": norm_type,
        "days_booked": days,
        "start_date": start_date,
        "end_date": end_date,
        "remaining_balance_days": emp["leave_balances"][bal_key]["remaining_days"],
        "message": (
            f"Time off request {req_id} ({norm_type}, {days} days from {start_date} to {end_date}) "
            f"successfully submitted and approved. Remaining balance: {emp['leave_balances'][bal_key]['remaining_days']} days."
        ),
    }


def update_personal_info(employee_id: str, address: str, phone: str) -> Dict[str, Any]:
    """Updates the employee's personal contact information (home address and phone number).

    Args:
        employee_id: Employee ID (e.g. 'EMP-1002')
        address: New home address (minimum 5 characters)
        phone: New phone number (must be valid phone format)
    """
    # 1. RBAC Check
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        config.DEFAULT_EMPLOYEE_ID, employee_id
    )
    if not allowed:
        return {"status": "error", "error_code": "403_FORBIDDEN", "message": rbac_msg}

    # 2. Syntax Guardrails (BRD FR-3.3)
    if len(address.strip()) < 5:
        return {
            "status": "error",
            "error_code": "INVALID_ADDRESS",
            "message": "Address must be at least 5 characters long.",
        }

    phone_clean = phone.strip()
    phone_pattern = r"^\+?[\d\s\-().]{7,25}$"
    if not re.match(phone_pattern, phone_clean):
        return {
            "status": "error",
            "error_code": "INVALID_PHONE",
            "message": f"Phone number '{phone}' does not conform to valid enterprise telephone format.",
        }

    emp = _store.get_employee(employee_id)
    if not emp:
        return {"status": "error", "error_code": "404_NOT_FOUND", "message": f"Employee {employee_id} not found."}

    # 3. Update Record
    emp["address"] = address.strip()
    emp["phone"] = phone_clean

    return {
        "status": "success",
        "employee_id": employee_id,
        "updated_address": emp["address"],
        "updated_phone": emp["phone"],
        "message": f"Contact details for {employee_id} updated successfully.",
    }


def get_personal_info(employee_id: str = "EMP-1002") -> Dict[str, Any]:
    """Fetches employee profile work details, home address, and contact number.

    Args:
        employee_id: Employee ID (e.g. 'EMP-1002')
    """
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        config.DEFAULT_EMPLOYEE_ID, employee_id
    )
    if not allowed:
        return {"status": "error", "error_code": "403_FORBIDDEN", "message": rbac_msg}

    emp = _store.get_employee(employee_id)
    if not emp:
        return {"status": "error", "error_code": "404_NOT_FOUND", "message": f"Employee {employee_id} not found."}

    return {
        "status": "success",
        "employee_id": employee_id,
        "name": emp["name"],
        "email": emp["email"],
        "department": emp["department"],
        "role": emp["role"],
        "work_location": emp["work_location"],
        "manager": emp["manager"],
        "address": emp["address"],
        "phone": emp["phone"],
    }


def cancel_leave_request(employee_id: str, request_id: int) -> Dict[str, Any]:
    """Cancels a pending or approved leave request and refunds the accrued days.

    Args:
        employee_id: Employee ID (e.g. 'EMP-1002')
        request_id: Numeric leave request ID to cancel
    """
    allowed, rbac_msg = ModelArmorGuard.check_rbac_isolation(
        config.DEFAULT_EMPLOYEE_ID, employee_id
    )
    if not allowed:
        return {"status": "error", "error_code": "403_FORBIDDEN", "message": rbac_msg}

    emp = _store.get_employee(employee_id)
    if not emp:
        return {"status": "error", "error_code": "404_NOT_FOUND", "message": f"Employee {employee_id} not found."}

    target = None
    for req in emp["leave_requests"]:
        if req["request_id"] == request_id and req["status"] != "Cancelled":
            target = req
            break

    if not target:
        return {
            "status": "error",
            "error_code": "REQUEST_NOT_FOUND",
            "message": f"Active leave request {request_id} not found for {employee_id}.",
        }

    target["status"] = "Cancelled"
    bal_key = "vacation" if target["leave_type"] == "Vacation" else "sick"
    emp["leave_balances"][bal_key]["remaining_days"] += target["days"]
    emp["leave_balances"][bal_key]["remaining_hours"] += target["days"] * 8.0
    emp["leave_balances"][bal_key]["used_days"] -= target["days"]

    return {
        "status": "success",
        "request_id": request_id,
        "message": f"Leave request {request_id} cancelled. {target['days']} days refunded to {target['leave_type']} balance.",
        "refunded_days": target["days"],
        "current_balance_days": emp["leave_balances"][bal_key]["remaining_days"],
    }
