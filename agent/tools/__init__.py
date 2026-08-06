"""Tools package for Project Elevate Agent."""

from .rag_tool import vertex_search_policies
from .serviceimmediately_tool import (
    add_ticket_comment,
    create_ticket,
    get_ticket_details,
    list_tickets,
    update_ticket_status,
)
from .workweek_tool import (
    cancel_leave_request,
    get_current_employee_id,
    get_employee_balances,
    get_personal_info,
    request_time_off,
    update_personal_info,
)

ALL_TOOLS = [
    # WorkWeek HCM tools
    get_current_employee_id,
    get_employee_balances,
    request_time_off,
    update_personal_info,
    get_personal_info,
    cancel_leave_request,
    # ServiceImmediately ITSM tools
    list_tickets,
    get_ticket_details,
    create_ticket,
    add_ticket_comment,
    update_ticket_status,
    # Policy RAG tool
    vertex_search_policies,
]

__all__ = [
    "ALL_TOOLS",
    "get_current_employee_id",
    "get_employee_balances",
    "request_time_off",
    "update_personal_info",
    "get_personal_info",
    "cancel_leave_request",
    "list_tickets",
    "get_ticket_details",
    "create_ticket",
    "add_ticket_comment",
    "update_ticket_status",
    "vertex_search_policies",
]
