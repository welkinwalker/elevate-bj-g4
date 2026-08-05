# Project Elevate - HR Agentic Solution (MVP 1)

**Project Elevate** is a secure, enterprise-grade AI virtual assistant designed to automate Tier 1 HR/IT inquiries and facilitate conversational self-service transactions across core enterprise platforms.

## 📚 Core Documentation & Specifications

* **[`BRD.md`](file:///Users/waliang/Code/elevate-bj-g4/BRD.md)**: Business Requirements Document detailing project scope, Tier 1 deflection targets, functional requirements, and use cases (UC-1.1 through UC-2.3).
* **[`SDD.md`](file:///Users/waliang/Code/elevate-bj-g4/SDD.md)**: Solution Design Document covering system architecture, sequence diagrams, safety guardrails, error handling, and deployment roadmap.
* **[`enterprise_services_openapi.json`](file:///Users/waliang/Code/elevate-bj-g4/enterprise_services_openapi.json)**: OpenAPI 3.1 specification for standard REST endpoints and mounted FastMCP servers (`/work-week/mcp/` and `/service-immediately/mcp/`).

## 🛠️ Key Architectural Components

1. **Agent Orchestration**: Built with the **Google ADK (Agent Development Kit)** running on **Agent Platform Agent Runtime**, utilizing **Agent Runtime Session Service** for multi-turn state management.
2. **Enterprise System Tooling via FastMCP**:
   * **WorkWeek (HCM)**: Employee profile metadata, leave balance retrieval (`get_employee_balances`), time-off booking (`request_time_off`), and personal contact updates (`update_personal_info`).
   * **ServiceImmediately (ITSM)**: Incident ticket queries (`list_tickets`), incident creation (`create_ticket`), timeline comments, and status transitions (`update_ticket_status`).
3. **Safety & Governance**: Integrated with **Google Cloud Model Armor** for real-time prompt injection interception, jailbreak defense, toxicity filtering, and SPII redaction.
4. **Policy Knowledge Base (RAG)**: Powered by **Vertex AI Search / Agent Builder** to deliver grounded answers derived from HR policy documents with clickable deep-link citations.

## 🔒 Security & Authentication
* FastMCP server calls authenticate via custom `X-MCP-Token` headers.
* User identity context (`employee_id`) is strictly validated per request turn to enforce single-tenant isolation rules.
