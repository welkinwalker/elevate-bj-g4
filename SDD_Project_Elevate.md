# **MVP SOLUTION DESIGN DOCUMENT**

# **Document Control**

## **Document Metadata**

| Field | Value |
| :---- | :---- |
| Author(s) | Solution Architecture Team |
| Date | 2026-08-05 |
| Status | Approved |
| Target Audience | Enterprise Architecture, HR Engineering, IT Operations, Security & Compliance |

## **Revision History**

| Version | Date | Author | Description of Change |
| :---- | :---- | :---- | :---- |
| 0.1 | 2026-08-05 | Solution Architecture Team | Initial outline setup |
| 1.0 | 2026-08-05 | Solution Architecture Team | Complete MVP 1 design incorporating FastMCP integration specs from `openapi.json` |
| 1.1 | 2026-08-05 | Solution Architecture Team | Incorporated confirmed architectural selections: Google Cloud Model Armor, Vertex AI Search RAG, and Agent Platform Agent Runtime Session Service |

---

# **1. Executive Summary & Scope Boundaries**

## **1.1. Business Overview & Context**
Enterprise employees currently experience friction and high turnaround times when navigating disconnected backend UIs (WorkWeek for HCM, ServiceImmediately for ITSM) and static HR policy repositories. Simultaneously, HR and IT helpdesks face significant Tier 1 ticket loads for routine queries. 

The **HR Agentic Solution (MVP 1)** introduces a secure, AI-driven virtual assistant designed to:
* **Deflect Tier 1 HR/IT Inquiries:** Achieve a $\ge 40\%$ reduction in routine ticket volume within 6 months.
* **Enable Conversational Transactions:** Execute core self-service actions (leave submission, contact updates, ticket tracking) conversationally.
* **Demonstrate Cross-System Orchestration:** Multi-step intent resolution chaining Policy RAG, WorkWeek HCM, and ServiceImmediately ITSM.
* **Enforce Zero-Trust AI Security:** Guarantee 100% auditability, bounded tool execution via MCP, prompt injection interception, and zero policy/data leakage using Google Cloud Model Armor.

## **1.2. Scope Boundaries**

| Feature / Domain | In-Scope (MVP 1) | Out-of-Scope (MVP 1) |
| :--- | :--- | :--- |
| **User Interface** | Web-based Chat Interface / Enterprise Chat Integration | Voice UI, native mobile apps |
| **Knowledge Base** | **Vertex AI Search / Agent Builder**: Static HR Policy Docs (Leave, Expense, Remote Work, Code of Conduct) | Dynamic intranet pages, uncategorized docs |
| **HCM Integration** | **WorkWeek via FastMCP**: Profile metadata, PTO balance check, Leave booking/cancellation, Address/Phone update | Payroll processing, performance reviews, compensation data |
| **ITSM Integration** | **ServiceImmediately via FastMCP**: Ticket status/details query, Incident ticket creation, Comment timeline, Status lifecycle updates | Change management, asset management, IT provisioning |
| **Orchestration** | Multi-system workflows (UC-2.1 Equipment, UC-2.2 Medical Leave, UC-2.3 Relocation) | Third-party ERPs, CRM integrations |
| **Security & Auth** | **Google Cloud Model Armor** for prompt injection & PII masking; Service PAT in `X-MCP-Token` header | Full Enterprise SSO / Okta SAML (future state) |
| **Session Memory** | **Agent Platform Agent Runtime Session Service** for multi-turn state management | External custom session databases |

## **1.3. Target Architecture Overview**

The solution leverages Google ADK (Agent Development Kit) running on Google Cloud Agent Platform Agent Runtime, backed by Agent Runtime Session Service and Streamable HTTP FastMCP toolsets (`McpToolset`), protected by Google Cloud Model Armor.

```mermaid
graph TD
    User(["Employee / User UI"]) -->|Web Chat Request| UI["Conversational Chat Frontend"]
    UI -->|HTTP Request| ModelArmor["Google Cloud Model Armor"]
    
    subgraph Governance["Governance & Safety Layer"]
        ModelArmor -->|1. Prompt Sanitization| PromptGuard["Prompt Injection & Jailbreak Defense"]
        ModelArmor -->|2. Data Masking| PIIRedactor["PII & SPII Redaction"]
    end

    PromptGuard -->|Sanitized User Prompt| Runtime["Agent Platform Agent Runtime"]

    subgraph Agentic Orchestration Layer
        Runtime -->|Session Management| SessionStore[("Agent Runtime Session Service")]
        Runtime -->|Intent Classification| Supervisor["Supervisor Agent"]
        Supervisor -->|Policy Query| PolicyAgent["Vertex AI Search RAG Tool"]
        Supervisor -->|WorkWeek MCP| WorkWeekMCP["WorkWeek FastMCP Server"]
        Supervisor -->|ServiceImmediately MCP| ServiceMCP["ServiceImmediately FastMCP Server"]
    end

    subgraph Backend["Enterprise Backend Services (openapi.json)"]
        PolicyAgent -->|Semantic Search| PolicyKB[("Vertex AI Agent Builder Policy Index")]
        WorkWeekMCP -->|Streamable HTTP /work-week/mcp/| WWBackend[("WorkWeek HCM System")]
        ServiceMCP -->|Streamable HTTP /service-immediately/mcp/| SIMBackend[("ServiceImmediately ITSM System")]
    end

    Runtime -->|Raw Model Response| OutputArmor["Model Armor Output Guard"]
    OutputArmor -->|Toxicity Check & Citation Links| UI
```

## **1.4. Alternatives Considered**

| Architectural Pattern | Evaluated Alternative | Selected Choice & Rationale |
| :--- | :--- | :--- |
| **Backend Integration** | Direct REST Endpoint Calling | **Streamable HTTP MCP Servers (`FastMCP`)**: Provides standardized tool discovery, strict type schema enforcement, stateless transport, and built-in ADK compatibility via `McpToolset`. |
| **Safety Interceptor** | Custom Regex / In-Prompt Rules | **Google Cloud Model Armor**: Enterprise-grade defense against prompt injection, jailbreaking, PII leakage, and toxic outputs within the $< 300\text{ms}$ SLA budget (`NFR-2.1`). |
| **Knowledge Base (RAG)** | Custom Vector DB (FAISS/Chroma) | **Vertex AI Search / Agent Builder**: Fully managed document ingestion from Cloud Storage, semantic chunking, and automatic deep-link citation generation (`FR-5.1` - `FR-5.4`). |
| **Session Memory** | Redis / Firestore with TTL | **Agent Platform Agent Runtime Session Service**: Native session persistence and dialog turn management within Google Cloud's Agent Platform ecosystem (`FR-2.2`). |

---

# **2. Production-Ready Future State Design**

The production target architecture expands MVP 1 into a highly scalable, enterprise-grade deployment:
1. **Identity & Auth Federation**: Transition from `X-MCP-Token` header authentication to Enterprise SSO (Okta / Entra ID) via Google Cloud Identity-Aware Proxy (IAP), automatically injecting `x-goog-authenticated-user-email` headers.
2. **Multi-Tenancy & Fleet Management**: Scale MCP server instances using Google Cloud Run with auto-scaling (0-100 instances), registered in Agent Registry for enterprise fleet management.
3. **Dynamic Knowledge Base Sync**: Automated Cloud Storage event triggers triggering Document AI and Vertex AI Search indexing for sub-15 minute document sync SLAs (`FR-5.5`).
4. **Asynchronous Streaming**: Implement Server-Sent Events (SSE) / WebSockets for real-time response streaming to reduce perceived latency below $1.5\text{s}$.

---

# **3. System Flows, Sequence Diagrams & Agent Design**

## **3.1. Agent Design**
The core system uses a **Supervisor Agent** running on Agent Runtime, orchestrating three specialized tool sets:
* **Vertex AI Search Policy Tool**: Performs semantic vector search against policy documents in Cloud Storage, returning grounded answers with deep-link citations.
* **WorkWeek MCP Toolset** (`/work-week/mcp/`): Exposes `get_current_employee_id`, `get_employee_balances`, `request_time_off`, `update_personal_info`, `get_personal_info`, and `cancel_leave_request`.
* **ServiceImmediately MCP Toolset** (`/service-immediately/mcp/`): Exposes `list_tickets`, `create_ticket`, `add_ticket_comment`, and `update_ticket_status`.

---

## **3.2. Sequence Diagrams**

### **UC-1.1: Policy Q&A Flow**
```mermaid
sequenceDiagram
    autonumber
    actor Employee
    participant UI as Chat UI
    participant Armor as Google Cloud Model Armor
    participant Agent as ADK Agent / Runtime
    participant RAG as Vertex AI Search

    Employee->>UI: "What is the company's bereavement leave policy?"
    UI->>Armor: Inspect Input (Prompt Injection Check)
    Armor-->>UI: Sanitized Input
    UI->>Agent: Process Query
    Agent->>RAG: Hybrid Search ("bereavement leave policy")
    RAG-->>Agent: Relevant Excerpts + Document Metadata
    Agent->>Armor: Validate Output (Grounding & Citation Check)
    Armor-->>Agent: Approved Output
    Agent-->>UI: Grounded Answer + Clickable Citation Link
    UI-->>Employee: Display Answer with Deep Link
```

### **UC-1.2: HR Self-Service - PTO Submission**
```mermaid
sequenceDiagram
    autonumber
    actor Employee
    participant Agent as ADK Agent / Runtime
    participant WW as "WorkWeek FastMCP (/work-week/mcp/)"
    participant WW_DB as WorkWeek HCM Database

    Employee->>Agent: "Submit PTO for next Thursday and Friday."
    Agent->>WW: get_current_employee_id()
    WW-->>Agent: employee_id = "EMP-1002"
    Agent->>WW: get_employee_balances("EMP-1002")
    WW->>WW_DB: Query PTO Balances
    WW_DB-->>WW: Vacation Balance: 40 hrs (5 days)
    WW-->>Agent: Remaining Vacation Days = 5
    Agent->>Agent: Validate Request (2 days requested <= 5 available, dates valid)
    Agent->>WW: request_time_off("EMP-1002", "2026-08-13", "2026-08-14", "Vacation", 2)
    WW->>WW_DB: Deduct 2 days & Create TimeOff Record
    WW_DB-->>WW: Success (Request ID: 501)
    WW-->>Agent: Confirmation Payload
    Agent-->>Employee: "Your 2-day Vacation request (Aug 13-14) is confirmed. Balance remaining: 3 days."
```

### **UC-2.1: Cross-System Orchestration - Equipment Procurement**
```mermaid
sequenceDiagram
    autonumber
    actor Employee
    participant Agent as ADK Agent / Runtime
    participant RAG as Vertex AI Search
    participant WW as WorkWeek FastMCP
    participant SI as ServiceImmediately FastMCP

    Employee->>Agent: "Can you verify my remote status and order a home office monitor?"
    Agent->>RAG: Query Remote Work Policy
    RAG-->>Agent: Policy Excerpt: Remote employees eligible for home office monitor
    Agent->>WW: get_personal_info(employee_id)
    WW-->>Agent: {address: "123 Tech Way, London", role: "Remote Software Engineer"}
    Agent->>Agent: Verify Remote Eligibility == True
    Agent->>SI: create_ticket(requested_by, category="Hardware", short_description="Home Office Monitor Request", priority="4 - Low")
    SI-->>Agent: {ticket_id: "INC-98231", state: "New"}
    Agent-->>Employee: "Verified remote status. Hardware request INC-98231 created in ServiceImmediately for shipping to 123 Tech Way."
```

---

# **4. Security, Governance & Identity**

## **4.1. Authentication Boundaries**
In production, backend services bypass IAP and require a custom **Personal Access Token (PAT)** header to satisfy Google Frontend (GFE) proxy requirements:
```http
X-MCP-Token: mcp_your_token_here
```

ADK agents configure connection parameters statelessly using custom HTTP headers with environment-scoped Service PATs, while passing user `employee_id` context into tool invocations for tenant isolation:
```python
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

workweek_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://mock-saas.aishprabhat.demo.altostrat.com/work-week/mcp/",
        headers={"X-MCP-Token": "mcp_your_token_here"}
    )
)

serviceimmediately_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://mock-saas.aishprabhat.demo.altostrat.com/service-immediately/mcp/",
        headers={"X-MCP-Token": "mcp_your_token_here"}
    )
)
```

## **4.2. Tenant Isolation Rules**
* **Identity Context Verification**: Every FastMCP resource query (`workweek://employees/{employee_id}/profile`) and tool call (`get_employee_balances`) verifies caller identity against the authenticated session context.
* **Cross-User Data Block**: Users attempting to pass another user's `employee_id` will receive an immediate `403 Forbidden` / access denied error.

## **4.3. Safety Interceptor Pipeline & Guardrails**

```mermaid
graph LR
    UserPrompt[User Prompt] --> ModelArmor{Google Cloud Model Armor}
    ModelArmor -->|Jailbreak / Injection| BlockInput[Block & Log Audit Event]
    ModelArmor -->|Passed| AgentExec[Agent Runtime Execution & MCP Tool Calls]
    AgentExec --> OutputArmor{Model Armor Output Guard}
    OutputArmor -->|Toxicity / Hallucination| BlockOutput[Redact & Fallback]
    OutputArmor -->|PII Detected| MaskPII[Redact SPII]
    MaskPII --> FinalResponse[User Response]
```

1. **Google Cloud Model Armor Protection (`FR-1.3`)**: Intercepts prompt injection, jailbreak attempts, and off-topic interactions before reaching agent models.
2. **Output Validation (`FR-1.3`)**: Validates model output against grounded retrieved context to guarantee 0% hallucinated policies.
3. **Data Masking (`FR-1.4`)**: Model Armor redacts SSNs, phone numbers, and addresses from log files and history.
4. **Audit Logging (`FR-1.2`, `NFR-1.2`)**: Logs all tool calls with `automation_source: "Agentic_HR_Assistant"`, caller ID, execution status, and timestamp.

---

# **5. Integration Details & Error Handling**

## **5.1. FastMCP Tool Specifications**

### **1. WorkWeek FastMCP Server (`/work-week/mcp/`)**

| Tool Name | Parameters | Description & Validation Rules |
| :--- | :--- | :--- |
| `get_current_employee_id()` | None | Resolves the authenticated user's `employee_id`. |
| `get_employee_balances` | `employee_id: str` | Returns accrued, used, and remaining Vacation/Sick leave balances. |
| `request_time_off` | `employee_id: str`, `start_date: str`, `end_date: str`, `leave_type: str`, `days: float` | Books time off. Dates must be `YYYY-MM-DD`. Validates $start \le end$, start $\ge$ today, and $days \le remaining\_balance$. |
| `update_personal_info` | `employee_id: str`, `address: str`, `phone: str` | Updates home address ($\ge 5$ chars) and phone number (regex `^\+?[\d\s\-()]{7,20}$`). |
| `get_personal_info` | `employee_id: str` | Retrieves personal address and phone details. |
| `cancel_leave_request` | `employee_id: str`, `request_id: int` | Cancels a pending/approved request and refunds remaining leave days. |

### **2. ServiceImmediately FastMCP Server (`/service-immediately/mcp/`)**

| Tool Name | Parameters | Description & Validation Rules |
| :--- | :--- | :--- |
| `list_tickets` | `employee_id: str` | Retrieves all incident tickets requested by the employee. |
| `create_ticket` | `requested_by: str`, `category: str`, `short_description: str`, `priority: str`, `assignment_group: str` | Creates incident. Rejects duplicate submissions within 5 mins. Priority `'1 - Critical'` requires outage/downtime keywords. |
| `add_ticket_comment` | `ticket_id: str`, `author: str`, `comment: str` | Appends comment to ticket activity log timeline. |
| `update_ticket_status` | `ticket_id: str`, `status: str`, `resolution_notes: str`, `updated_by: str` | Enforces state machine: `New -> In Progress/Closed`, `In Progress -> Resolved/Closed`, `Resolved -> In Progress/Closed`. Closed tickets are immutable. |

---

## **5.2. Error Handling & Fallback Matrix**

| Failure Scenario | Root Cause | Fallback Behavior & User Message |
| :--- | :--- | :--- |
| **Transient Network Timeout / 5xx** | Backend service glitch | Automatic exponential backoff retry (up to 3 attempts). If persistent: *"WorkWeek is temporarily unavailable. Please try again shortly."* |
| **Insufficient PTO Balance** | Business rule violation | Agent intercepts error: *"Request declined: You requested 5 days, but only have 2 days remaining."* |
| **Invalid Ticket State Transition** | State machine violation | Agent catches state rule: *"Ticket INC-123 is Closed and cannot be updated."* |
| **Partial Cross-System Failure** | Step 1 succeeds, Step 2 fails | Log failure with tracking reference ID (`NFR-4.3`). User notified: *"Leave request submitted in WorkWeek, but ticket creation in ServiceImmediately failed. Reference ID: LOG-8812. Please contact IT support."* |

---

# **6. Cost Estimation & FinOps**

| Variable | Cost Driver | Optimization Strategy |
| :--- | :--- | :--- |
| **Model Inference** | Gemini 3.5 / 3.6 Flash input/output token usage | Prompt caching for policy system prompts; concise system instructions. |
| **Vector Search** | Vertex AI Search document indexing | Chunk size optimization; hybrid search index. |
| **MCP Compute** | Cloud Run CPU/Memory per HTTP request | Scale-to-zero Cloud Run instances during off-peak hours. |
| **Safety Interceptor** | Google Cloud Model Armor API calls | Single-pass evaluation pipeline per conversation turn. |

---

# **7. Deployment & Delivery Plan**

```mermaid
gantt
    title MVP 1 Phased Delivery Plan
    dateFormat  YYYY-MM-DD
    section Phase 1: Foundation
    Environment Setup & Terraform        :2026-08-06, 5d
    MCP Toolset Integration & Testing    :2026-08-09, 7d
    section Phase 2: Agent Development
    Supervisor Agent & Vertex RAG        :2026-08-16, 8d
    Google Cloud Model Armor Integration  :2026-08-20, 6d
    section Phase 3: Validation
    Cross-System Flow Integration Tests   :2026-08-24, 6d
    UAT Benchmark & Security Scan         :2026-08-28, 5d
    section Phase 4: Launch
    Production Deployment & Rollout       :2026-09-02, 3d
```

---

# **8. Assumptions, Constraints, Risk & Mitigations**

| Category | Risk / Constraint | Mitigation Strategy |
| :--- | :--- | :--- |
| **Constraint** | FastMCP headers require `X-MCP-Token` due to GFE proxy rules. | Pre-configure `StreamableHTTPConnectionParams` with exact header specs in ADK config. |
| **Risk** | Duplicate ticket submission during network retries. | FastMCP server enforces 5-minute deduplication window on identical short descriptions. |
| **Risk** | Latency breach ($>10\text{s}$) due to sequential tool calls. | Execute independent tool calls asynchronously using Python `asyncio.gather`. |
| **Assumption** | Policy documents remain static during MVP 1. | Knowledge base manual re-index script provided for scheduled updates (`FR-5.5`). |

---

# **9. Quality Evaluation & UAT Framework**

| Evaluation Category | Target Metric / Benchmark | Verification Method |
| :--- | :--- | :--- |
| **Policy Q&A Accuracy** | $\ge 95\%$ accuracy; 0% policy hallucination | Run 100-question ground-truth evaluation set via LLM-as-judge. |
| **Transaction Integrity** | $100\%$ transaction correctness | Automated test suite verifying WorkWeek & ServiceImmediately DB state changes. |
| **Prompt Injection Defense** | $100\%$ detection of jailbreak test cases | Execute OWASP LLM Top 10 benchmark injection attacks via Model Armor. |
| **Response Latency** | $< 10.0\text{s}$ average response time; safety overhead $< 300\text{ms}$ | Latency tracing via Cloud Trace telemetry. |
| **Audit Log Coverage** | $100\%$ coverage of actions with origin metadata | Log audit parser verifying `automation_source` fields in BigQuery. |

---

# **10. Confirmed Design Choices & Decisions**

| # | Topic / Question | Confirmed Architecture Selection | Status |
| :- | :--- | :--- | :--- |
| **D-1** | **Partial Cross-System Failure** | Log partial failure with a tracking reference ID and notify user with manual follow-up instructions (`NFR-4.3`). | Approved |
| **D-2** | **MCP Token Credentials** | Pre-provisioned Service PAT in `X-MCP-Token` header; user `employee_id` passed in tool context. | Approved |
| **D-3** | **Safety Interceptor** | **Google Cloud Model Armor** for prompt injection defense, jailbreak prevention, PII masking, and output toxicity filtering (`FR-1.3`, `FR-1.4`). | Approved |
| **D-4** | **Knowledge Base (RAG)** | **Vertex AI Search / Agent Builder Knowledge Base** with Cloud Storage ingestion, semantic chunking, and deep links (`FR-5.1` - `FR-5.4`). | Approved |
| **D-5** | **Session Memory State** | **Google Cloud Agent Platform Agent Runtime Session Service** for multi-turn state management (`FR-2.2`). | Approved |