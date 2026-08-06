"""Tools package for Project Elevate Agent."""

from .workweek_tool import (
    get_current_employee_id,
    get_employee_balances,
    request_time_off,
    update_personal_info,
    get_personal_info,
    cancel_leave_request,
)
from .serviceimmediately_tool import (
    list_tickets,
    get_ticket_details,
    create_ticket,
    add_ticket_comment,
    update_ticket_status,
)
from .rag_tool import vertex_search_policies

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
