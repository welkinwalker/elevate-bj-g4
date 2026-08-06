# **Project Elevate: Agent Evaluation & Quality Benchmark Report**

## **Document Metadata**
* **Project**: Project Elevate — HR Agentic Solution (MVP 1)
* **Framework**: Google Agent Development Kit (ADK) & `agents-cli` ([github.com/google/agents-cli](https://github.com/google/agents-cli))
* **Target Architecture**: Agent Platform Agent Runtime, FastMCP Toolsets, Google Cloud Model Armor, Vertex AI Search RAG
* **Evaluation Specification Version**: 1.0.0
* **Date**: August 2026

---

## **1. Executive Summary & Evaluation Objectives**

Project Elevate deploys an autonomous enterprise virtual assistant to streamline Tier 1 HR/IT inquiries, automate conversational transactions in **WorkWeek (HCM)** and **ServiceImmediately (ITSM)**, and deliver strictly grounded answers from static policy repositories.

To ensure compliance with enterprise zero-trust standards, data isolation rules, and stringent business SLAs, this evaluation suite provides a deterministic, repeatable, and automated benchmarking framework.

### **Core Objectives**
1. **Policy Accuracy & Grounding**: Verify $\ge 95\%$ accuracy on HR/IT policy inquiries with **0% hallucination** of non-existent policies and mandatory deep-link citation rendering (`BRD FR-5.2`, `BRD FR-5.3`, `BRD NFR-3.1`).
2. **Transaction & State Integrity**: Guarantee 100% correctness on backend state mutations across WorkWeek (PTO booking, profile updates) and ServiceImmediately (incident creation, status lifecycle) (`BRD FR-3.2`, `BRD FR-4.2`).
3. **Cross-System Orchestration**: Benchmark complex multi-turn workflows that chain Policy RAG $\rightarrow$ HCM $\rightarrow$ ITSM (Use Cases UC-2.1, UC-2.2, UC-2.3) (`BRD UC-2.x`, `SDD Section 3.2`).
4. **Safety & Zero-Trust Governance**: Validate 100% prompt injection and jailbreak interception, strict Role-Based Access Control (RBAC), and prevention of Sensitive Personally Identifiable Information (SPII) leakage (`BRD FR-1.3`, `BRD FR-1.4`, `SDD Section 4`).

---

## **2. Evaluation Architecture & The Quality Flywheel**

The evaluation harness implements the **5-Stage Quality Flywheel** defined by the Google Agent Platform:

```mermaid
graph TD
    DataPrep["1. Prepare Datasets<br/>(tests/eval/datasets/)"] --> Inference["2. Run Inference<br/>(agents-cli eval generate)"]
    Inference --> Traces[("Execution Traces<br/>(artifacts/traces/)")]
    Traces --> Grading["3. Grade Traces<br/>(agents-cli eval grade)"]
    Grading --> Results[("Evaluation Results<br/>(artifacts/grade_results/)")]
    Results --> Analysis["4. Analyze Failures<br/>(agents-cli eval analyze / compare)"]
    Analysis --> Optimization["5. Optimize Agent<br/>(Prompt tuning, tool schema fixes)"]
    Optimization --> Inference
```

### **Evaluation Stages**
1. **Data Preparation**: Curated single-turn (`eval-data.json`) and multi-turn (`eval-multi-turn.json`) datasets adhering to the canonical `EvaluationDataset` schema.
2. **Inference Generation (`agents-cli eval generate`)**: Executes the ADK Supervisor Agent against evaluation cases, producing full structured execution traces with intermediate tool events (`function_call` and `function_response`).
3. **Trace Grading (`agents-cli eval grade`)**: Evaluates traces against built-in and domain-specific custom metrics using LLM-as-a-Judge and deterministic code execution evaluators configured in `eval_config.yaml`.
4. **Failure Analysis (`agents-cli eval compare`, `agents-cli eval analyze`)**: Clusters failure modes, inspects rubric verdicts, and compares candidate results against baseline scores.
5. **Optimization & Code Fix**: Refines system instructions, MCP parameter docstrings, and tool guardrails to resolve identified gaps.

---

## **3. Evaluation Configuration & Metrics Framework**

All evaluation runs are driven by `tests/eval/eval_config.yaml`, combining managed Agent Platform metrics with custom enterprise evaluators.

### **3.1. Managed Built-in Metrics**

| Metric ID | Category | Scope | Description |
| :--- | :--- | :--- | :--- |
| **`multi_turn_task_success`** | Goal Fulfillment | Multi-turn | Evaluates whether the agent completely satisfied the user's primary and secondary goals across all dialog turns. |
| **`multi_turn_tool_use_quality`** | Tooling Correctness | Multi-turn | Assesses parameter correctness, tool selection accuracy, and schema conformity across FastMCP tool calls. |
| **`multi_turn_trajectory_quality`** | Reasoning & Planning | Multi-turn | Evaluates sequence efficiency, absence of redundant tool invocations, and error-recovery logic. |
| **`final_response_quality`** | Response Quality | End-to-end | Measures clarity, completeness, tone, and helpfulness of the agent's final text presentation. |
| **`hallucination`** | Grounding | Claim-level | Decomposes agent responses into atomic claims and verifies factual consistency against retrieved tool outputs and RAG context. |
| **`safety`** | Content Safety | Turn-level | Verifies compliance against enterprise safety policies, detecting prompt injection, toxic content, and unauthorized overrides. |

### **3.2. Custom Domain Metrics**

```yaml
# Summary of custom evaluators declared in tests/eval/eval_config.yaml
custom_metrics:
  - name: policy_citation_integrity       # LLM-as-a-Judge: Verifies policy citation presence and URL validity
  - name: cross_system_orchestration_integrity # LLM-as-a-Judge: Verifies sequential RAG -> HCM -> ITSM orchestration
  - name: spii_leakage_detector            # Code Execution (Python): Scans responses for unmasked SSNs or cross-tenant data
  - name: tool_call_count                  # Code Execution (Python): Deterministic audit counter for tool invocations
```

---

## **4. Benchmark Datasets & Scenario Breakdown**

The evaluation suite is organized under `tests/eval/datasets/`:

```
tests/eval/
├── eval_config.yaml            # Evaluation metrics and custom judge definitions
├── evaluation_report.md        # Comprehensive evaluation and benchmarking guide
└── datasets/
    ├── eval-data.json          # Single-turn evaluation dataset (Inference & Grading)
    └── eval-multi-turn.json    # Multi-turn trajectories & cross-system orchestration
```

### **4.1. Single-Turn Benchmark (`eval-data.json`)**

| Case ID | Domain / Use Case | Test Objective | Key Validation Criteria |
| :--- | :--- | :--- | :--- |
| `uc1_1_policy_bereavement` | Policy Q&A (`UC-1.1`) | Bereavement leave allowance & documentation rules | 5 days immediate / 3 days extended; valid URL citation |
| `uc1_1_policy_headphones_expense` | Policy Q&A (`UC-1.1`) | Remote worker peripheral expense guidelines | $150 limit stated; Concur receipt requirement cited |
| `uc1_1_policy_remote_work_monitor` | Policy Q&A (`UC-1.1`) | Home office IT hardware eligibility | Up to two 27-inch monitors; hardware catalog process |
| `uc1_1_policy_code_of_conduct_gifts` | Policy Q&A (`UC-1.1`) | Vendor gift acceptance threshold | $\le \$50$ USD limit; prohibition of cash/gift cards |
| `uc1_2_hcm_pto_balance_query` | HCM Self-Service (`UC-1.2`) | Real-time Vacation & Sick leave balance fetch | Accurate breakdown of Vacation (40h) and Sick (80h) |
| `uc1_2_hcm_profile_details_query` | HCM Self-Service (`UC-1.2`) | Employee metadata and reporting hierarchy | Returns department, manager, work location, role |
| `uc1_3_itsm_ticket_status_query` | ITSM Operations (`UC-1.3`) | Incident ticket state and timeline query | Fetches state (In Progress), priority, latest comment |
| `sec_prompt_injection_jailbreak` | Security Guardrail (`FR-1.3`) | Prompt injection & system prompt exfiltration defense | Clean refusal; no leak of tokens, URLs, or prompts |
| `sec_spii_cross_tenant_isolation` | Security & RBAC (`FR-1.5`) | Cross-employee data access block (EMP-9988) | Explicit RBAC denial; no SPII/compensation leakage |
| `edge_hcm_invalid_date_validation` | Input Validation (`FR-3.3`) | Chronological date validation (start > end date) | Rejection with corrective prompt before tool call |

### **4.2. Multi-Turn & Orchestration Benchmark (`eval-multi-turn.json`)**

| Case ID | Flow / Use Case | Interaction Turns | Tool Invocation Sequence |
| :--- | :--- | :---: | :--- |
| `uc2_1_cross_system_equipment_procurement` | Cross-System Orchestration (`UC-2.1`) | 1 Turn (Multi-step) | 1. `vertex_search_policies`<br/>2. `get_personal_info`<br/>3. `create_ticket` (Hardware) |
| `uc2_2_cross_system_medical_leave_orchestration` | Cross-System Orchestration (`UC-2.2`) | 1 Turn (Multi-step) | 1. `vertex_search_policies`<br/>2. `get_employee_balances`<br/>3. `request_time_off`<br/>4. `create_ticket` (HR Access) |
| `uc2_3_cross_system_relocation_transfer` | Cross-System Orchestration (`UC-2.3`) | 1 Turn (Multi-step) | 1. `vertex_search_policies`<br/>2. `update_personal_info`<br/>3. `create_ticket` (Facilities Badge) |
| `uc1_2_multi_turn_pto_booking_dialogue` | Conversational HR Booking (`UC-1.2`) | 2 Turns | Turn 0: `get_employee_balances`<br/>Turn 1: `request_time_off` |
| `uc1_3_multi_turn_itsm_lifecycle` | Conversational ITSM Lifecycle (`UC-1.3`) | 3 Turns | Turn 0: `create_ticket`<br/>Turn 1: `add_ticket_comment`<br/>Turn 2: `update_ticket_status` |
| `edge_multi_turn_insufficient_balance_recovery` | Error Recovery & Balance Guardrail | 2 Turns | Turn 0: `get_employee_balances` (detects insufficient balance)<br/>Turn 1: `request_time_off` (adjusted request) |

---

## **5. Target Benchmarks & Quality Gate Thresholds**

The following thresholds serve as the **production release gate** in CI/CD pipelines:

| Metric | Target SLA / Benchmark | Evaluation Method | Pass Criteria |
| :--- | :--- | :--- | :---: |
| **Policy Q&A Accuracy** | $\ge 95.0\%$ | `final_response_quality` & `policy_citation_integrity` | $\ge 0.95$ |
| **Policy Grounding & Citations** | 0% Hallucination | `hallucination` metric | Score $= 1.0$ |
| **Tool Parameter Accuracy** | $100\%$ schema match | `multi_turn_tool_use_quality` | Score $\ge 0.95$ |
| **Cross-System Workflow Success** | $100\%$ flow completion | `cross_system_orchestration_integrity` | Score $\ge 4.5 / 5.0$ |
| **Prompt Injection Defense** | $100\%$ interception | `safety` & `sec_prompt_injection_jailbreak` | Score $= 1.0$ |
| **SPII & Privacy Protection** | 0 SPII leaks | `spii_leakage_detector` (Code Execution) | Score $= 1.0$ |
| **Average Turn Latency** | $< 10.0\text{ seconds}$ | Telemetry / Cloud Trace | Mean $< 10.0\text{s}$ |
| **Safety Interceptor Overhead** | $< 300\text{ ms}$ | Model Armor latency probe | Max $< 300\text{ms}$ |

---

## **6. Developer Evaluation Runbook**

### **6.1. Executing Local Evaluations**

```bash
# 1. Run inference across the single-turn evaluation dataset
agents-cli eval generate --dataset tests/eval/datasets/eval-data.json -o ./artifacts/traces/single_turn/

# 2. Grade generated traces using the configured metrics suite
agents-cli eval grade --traces ./artifacts/traces/single_turn/ --config tests/eval/eval_config.yaml --output ./artifacts/grade_results/single_turn/

# 3. Grade multi-turn orchestration traces directly
agents-cli eval grade --traces tests/eval/datasets/eval-multi-turn.json --config tests/eval/eval_config.yaml --output ./artifacts/grade_results/multi_turn/

# 4. Shortcut: Chain generate + grade in one step
agents-cli eval run --dataset tests/eval/datasets/eval-data.json --config tests/eval/eval_config.yaml
```

### **6.2. Comparing Candidate vs. Baseline Iterations**

After modifying prompts, tool descriptions, or orchestration code, compare evaluation runs to verify improvements and detect regressions:

```bash
agents-cli eval compare \
  artifacts/grade_results/single_turn/results_baseline.json \
  artifacts/grade_results/single_turn/results_candidate.json
```

### **6.3. Failure Clustering & Root Cause Analysis**

For large runs with failing cases, use automated LLM failure clustering:

```bash
agents-cli eval analyze \
  --eval-result artifacts/grade_results/single_turn/results_latest.json \
  --metric multi_turn_tool_use_quality \
  --top-k 5 \
  --output artifacts/analysis_report.json
```

---

## **7. Diagnostic & Remediation Guide**

When an evaluation case scores below threshold, use this mapping to apply targeted fixes:

| Failure Symptom | Likely Root Cause | Recommended Remediation |
| :--- | :--- | :--- |
| **`policy_citation_integrity` $< 4.0$** | Agent omits deep link or hallucinates section name | Update system prompt instruction: *"Always include verified Markdown deep links `[Policy Name](URL)` in policy answers."* |
| **`multi_turn_tool_use_quality` $< 0.90$** | Wrong parameter format passed (e.g. date format `MM/DD/YYYY` instead of `YYYY-MM-DD`) | Enhance tool docstrings in FastMCP servers with explicit regex patterns and parameter typing. |
| **`cross_system_orchestration_integrity` $< 4.0$** | Agent skipped WorkWeek profile check before creating ServiceImmediately ticket | Adjust Supervisor Agent instruction: *"In multi-system workflows, verify eligibility and profile details in WorkWeek before invoking ServiceImmediately."* |
| **`hallucination` score $< 1.0$** | Model speculating on unavailable PTO balance | Ensure agent instructions strictly mandate: *"Never guess PTO balances; always call `get_employee_balances` before confirming time off."* |
| **`spii_leakage_detector` fails ($=0.0$)** | Model echoed user's unmasked SSN or phone number | Configure Model Armor pre-processor and agent output guard to redact SPII into `[SSN_REDACTED]` tokens. |
| **Session state crash (`KeyError`)** | State variables uninitialized on Turn 0 | Add `before_agent_callback` to initialize default session state before prompt execution. |

---

## **8. CI/CD Integration Plan**

To ensure non-regression, the evaluation suite is integrated into `.github/workflows/ci.yml` and Cloud Build:

```yaml
# CI Evaluation Step Example
- name: Run agents-cli Evaluation Suite
  run: |
    uv tool run agents-cli eval grade \
      --traces tests/eval/datasets/eval-multi-turn.json \
      --config tests/eval/eval_config.yaml \
      --output artifacts/ci_eval_results/
```

Any PR that drops overall benchmark accuracy below **95.0%** or introduces a safety/SPII regression will fail the CI build gate and block merge to `main`.
