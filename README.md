# Project Elevate - HR Agentic Solution (MVP 1)

**Project Elevate** is a secure, enterprise-grade AI virtual assistant designed to automate Tier 1 HR/IT inquiries and facilitate conversational self-service transactions across core enterprise platforms.

## 📚 Core Documentation & Specifications

* **[`BRD.md`](file:///usr/local/google/home/levichen/Documents/brd2sdd/elevate-bj-g4/BRD.md)**: Business Requirements Document detailing project scope, Tier 1 deflection targets, functional requirements, and use cases (UC-1.1 through UC-2.3).
* **[`SDD.md`](file:///usr/local/google/home/levichen/Documents/brd2sdd/elevate-bj-g4/SDD.md)**: Solution Design Document covering system architecture, sequence diagrams, safety guardrails, error handling, and deployment roadmap.
* **[`enterprise_services_openapi.json`](file:///usr/local/google/home/levichen/Documents/brd2sdd/elevate-bj-g4/enterprise_services_openapi.json)**: OpenAPI 3.1 specification for standard REST endpoints and mounted FastMCP servers (`/work-week/mcp/` and `/service-immediately/mcp/`).
* **[`tests/eval/evaluation_report.md`](file:///usr/local/google/home/levichen/Documents/brd2sdd/elevate-bj-g4/tests/eval/evaluation_report.md)**: Evaluation & Quality Benchmark Report detailing evaluation approach, metrics, dataset schemas, and developer runbooks.

## 🛠️ Key Architectural Components

1. **Agent Orchestration**: Built with the **Google ADK (Agent Development Kit)** running on **Agent Platform Agent Runtime**, utilizing **Agent Runtime Session Service** for multi-turn state management.
2. **Enterprise System Tooling via FastMCP**:
   * **WorkWeek (HCM)**: Employee profile metadata, leave balance retrieval (`get_employee_balances`), time-off booking (`request_time_off`), and personal contact updates (`update_personal_info`).
   * **ServiceImmediately (ITSM)**: Incident ticket queries (`list_tickets`), incident creation (`create_ticket`), timeline comments, and status transitions (`update_ticket_status`).
3. **Safety & Governance**: Integrated with **Google Cloud Model Armor** for real-time prompt injection interception, jailbreak defense, toxicity filtering, and SPII redaction.
4. **Policy Knowledge Base (RAG)**: Powered by **Vertex AI Search / Agent Builder** to deliver grounded answers derived from HR policy documents with clickable deep-link citations.

## 🧪 Evaluation Suite (`agents-cli` Format)
Evaluation assets conform to the [`agents-cli`](https://github.com/google/agents-cli) standard located in `tests/eval/`:
* **[`eval_config.yaml`](file:///usr/local/google/home/levichen/Documents/brd2sdd/elevate-bj-g4/tests/eval/eval_config.yaml)**: Configuration for built-in Agent Platform metrics and custom evaluators (`policy_citation_integrity`, `cross_system_orchestration_integrity`, `spii_leakage_detector`).
* **[`datasets/eval-data.json`](file:///usr/local/google/home/levichen/Documents/brd2sdd/elevate-bj-g4/tests/eval/datasets/eval-data.json)**: Single-turn benchmark for Policy Q&A (`UC-1.1`), WorkWeek queries (`UC-1.2`), ServiceImmediately queries (`UC-1.3`), prompt injection defense, and input validation.
* **[`datasets/eval-multi-turn.json`](file:///usr/local/google/home/levichen/Documents/brd2sdd/elevate-bj-g4/tests/eval/datasets/eval-multi-turn.json)**: Multi-turn conversational trajectories and cross-system orchestration (`UC-2.1` Equipment, `UC-2.2` Medical Leave, `UC-2.3` Relocation).

```bash
# Run evaluations locally using agents-cli
agents-cli eval grade --traces tests/eval/datasets/eval-multi-turn.json --config tests/eval/eval_config.yaml
```

## 🔒 Security & Authentication
* FastMCP server calls authenticate via custom `X-MCP-Token` headers.
* User identity context (`employee_id`) is strictly validated per request turn to enforce single-tenant isolation rules.
