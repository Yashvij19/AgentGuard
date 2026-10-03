# AgentGuard — Complete Implementation Plan

> **Goal**: Build and deploy a governance and execution-control layer for autonomous coding agents. The agent safely automates PR review and CI-failure fixes. Every proposed action flows through policy, risk, and budget checks before execution, with human approval gates and full observability — all on free-tier infrastructure ($0/month).

---

## Decisions (Resolved)

| # | Decision | Choice |
|---|---|---|
| 1 | **LLM Gateway** | Unified plugin-based LLM gateway with provider adapters. **Gemini free tier** = primary (heavy reasoning). **Groq free tier** = fast inference (classification, formatting). **NVIDIA NIM free tier** = additional provider. Generic plugin architecture — any OpenAI-compatible endpoint works. Uses **OpenTelemetry GenAI Semantic Conventions** (`gen_ai.system`, `gen_ai.request.model`) for cross-provider observability. |
| 2 | **Sandbox** | Both **E2B** (default) and **GitHub Actions** supported. E2B is the default runner; GH Actions is a configurable fallback. |
| 3 | **Policy Engine** | **OPA (Open Policy Agent) with Rego** — industry standard. Run in-process via `opa-python-client` or as a lightweight REST sidecar. |
| 4 | **Backend Hosting** | **Fly.io** free tier — better cold-start performance, global edge deployment. |
| 5 | **Database** | **Neon Postgres** — serverless, instant branching for dev/staging, generous free tier. |

---

## Engineering Rules & Coding Standards

> [!IMPORTANT]
> Every phase, every file, every PR must follow these rules. An AI agent building this project MUST NOT skip, simplify, or "shortcut" any of these patterns. If a rule is listed here, it is mandatory.

### 1. Architecture Patterns

| Pattern | Rule |
|---|---|
| **Dependency Injection (DI)** | Every service class receives its dependencies through constructor injection. Never instantiate collaborators inside a class. Use a composition root (`container.py`) to wire everything. |
| **Interface → Implementation** | Define an abstract base class (ABC / Protocol) first, then implement. Example: `PolicyEvaluator` (protocol) → `OPAPolicyEvaluator` (concrete). `LLMProvider` (protocol) → `GeminiProvider`, `GroqProvider`, `NVIDIANIMProvider`. This enables testing, swapping, and mocking. |
| **Plugin Architecture (LLM Gateway)** | LLM providers are plugins. Each provider implements the `LLMProvider` protocol. New providers are added by creating a new adapter class and registering it in the provider registry — zero changes to core gateway code. |
| **DRY (Don't Repeat Yourself)** | Shared logic goes into a utility module or a base class. If you copy-paste code, refactor immediately. |
| **Single Responsibility (SRP)** | One class = one reason to change. The `PolicyGateway` does not also track budgets — that's the `BudgetEngine`. The `LLMGateway` does not know provider specifics — each `LLMProvider` adapter handles that. |
| **Fail Closed** | Every authorization check defaults to `DENY` on error, missing config, timeout, or unknown input. Never silently allow. |
| **Explicit over Implicit** | No magic strings. Use enums for statuses, action types, decisions, provider names. Use dataclasses/Pydantic models for structured data — never raw dicts passed between layers. |
| **Repository Pattern** | All database access goes through repository classes (`RunRepository`, `LedgerRepository`). No raw SQL in service code. |
| **Result Pattern** | Service methods return explicit `Result[T, Error]` types or raise domain-specific exceptions — never return `None` to mean "failed". |
| **Strategy Pattern (Sandbox)** | Sandbox execution uses the Strategy pattern. `SandboxRunner` protocol with `E2BSandboxRunner` (default) and `GitHubActionsSandboxRunner` (fallback). Selected via configuration. |

### 2. Code Quality Rules

| Rule | Detail |
|---|---|
| **Type Hints Everywhere** | Every function signature, every variable. Use `mypy --strict` in CI. |
| **Pydantic Models for All External Data** | Webhook payloads, API responses, LLM outputs, Action Intents — all validated via Pydantic `BaseModel`. |
| **Async by Default** | FastAPI routes and service calls are `async`. Use `asyncio` for I/O-bound operations. Blocking calls (if unavoidable) go through `run_in_executor`. |
| **Structured Logging** | Use `structlog` with JSON output. Every log line includes `run_id`, `step`, `action`. No `print()` statements. |
| **Test Coverage ≥ 80%** | Unit tests for all services, integration tests for the webhook → policy → tool flow. Use `pytest` + `pytest-asyncio`. |
| **Docstrings on all public classes/methods** | Google-style docstrings. |
| **No hardcoded secrets** | All secrets via environment variables, loaded through `pydantic-settings`. |
| **Linting** | `ruff` for linting + formatting. Config in `pyproject.toml`. Zero warnings policy. |

### 3. Git & CI Rules

| Rule | Detail |
|---|---|
| **Conventional Commits** | `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:` prefixes. |
| **Branch per Feature** | `feature/phase-X-component-name` branches. |
| **CI Pipeline** | GitHub Actions: lint → type-check → test → build → deploy. Runs on every push. |
| **No direct pushes to `main`** | Everything through PRs (even solo — this demonstrates the workflow). |

---

## Project File Structure

> [!IMPORTANT]
> This is the **canonical** file structure. Every phase adds files into this structure. AI agents MUST create files in these exact locations. Do NOT create alternative structures.

```
AgentGuard/
├── .github/
│   └── workflows/
│       ├── ci.yml                          # Lint → type-check → test → build
│       └── deploy.yml                      # Auto-deploy to Fly.io on main
│
├── backend/                                # FastAPI backend (Python)
│   ├── pyproject.toml                      # Project metadata, dependencies, ruff/mypy config
│   ├── alembic.ini                         # Database migration config
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/                       # Migration scripts
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                         # FastAPI app factory, lifespan, middleware
│   │   ├── container.py                    # DI composition root — wires all dependencies
│   │   ├── config.py                       # pydantic-settings: all env vars, validated
│   │   │
│   │   ├── api/                            # HTTP layer — routes only, no business logic
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py             # FastAPI Depends() factories
│   │   │   ├── webhooks/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py               # POST /webhooks/github
│   │   │   │   └── schemas.py              # Request/response Pydantic models
│   │   │   ├── runs/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py               # GET /runs, GET /runs/{id}
│   │   │   │   └── schemas.py
│   │   │   ├── approvals/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py               # POST /approvals/{id}/approve|reject
│   │   │   │   └── schemas.py
│   │   │   ├── policies/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py               # GET/PUT /policies/{repo}
│   │   │   │   └── schemas.py
│   │   │   └── health/
│   │   │       ├── __init__.py
│   │   │       └── router.py               # GET /health
│   │   │
│   │   ├── domain/                         # Domain models — pure Python, no framework deps
│   │   │   ├── __init__.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── run.py                  # Run, RunStatus enum
│   │   │   │   ├── action_intent.py        # ActionIntent, ActionType enum
│   │   │   │   ├── decision_trace.py       # DecisionTrace model
│   │   │   │   ├── policy_decision.py      # PolicyDecision, Decision enum (ALLOW/DENY/REQUIRE_APPROVAL)
│   │   │   │   ├── approval.py             # Approval, ApprovalStatus enum
│   │   │   │   ├── policy.py               # PolicyConfig model (parsed YAML)
│   │   │   │   ├── run_event.py            # RunEvent, EventType enum
│   │   │   │   ├── webhook_delivery.py     # WebhookDelivery model
│   │   │   │   ├── provider_health.py      # ProviderHealth model
│   │   │   │   └── llm_config.py           # LLMProviderConfig, RoutingStrategy, TaskType enums
│   │   │   │
│   │   │   ├── protocols/                  # Abstract interfaces (Python Protocols / ABCs)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── policy_evaluator.py     # PolicyEvaluator protocol
│   │   │   │   ├── risk_scorer.py          # RiskScorer protocol
│   │   │   │   ├── budget_tracker.py       # BudgetTracker protocol
│   │   │   │   ├── tool_executor.py        # ToolExecutor protocol
│   │   │   │   ├── llm_provider.py         # LLMProvider protocol (the plugin interface)
│   │   │   │   ├── sandbox_runner.py       # SandboxRunner protocol
│   │   │   │   ├── github_client.py        # GitHubClient protocol
│   │   │   │   └── repository.py           # Generic Repository protocol
│   │   │   │
│   │   │   └── exceptions.py              # Domain-specific exception hierarchy
│   │   │
│   │   ├── services/                       # Business logic — orchestration layer
│   │   │   ├── __init__.py
│   │   │   ├── webhook_service.py          # Signature verify, idempotency check, dispatch
│   │   │   ├── run_coordinator.py          # Per-PR lock, commit-SHA binding, staleness
│   │   │   ├── policy_gateway.py           # Orchestrates OPA policy + risk + budget evaluation
│   │   │   ├── risk_engine.py              # Deterministic risk scoring
│   │   │   ├── budget_engine.py            # Token/cost/call budget enforcement
│   │   │   ├── tool_gateway.py             # Capability-scoped action dispatch
│   │   │   ├── llm_gateway.py              # Unified LLM gateway: routing, validation, retry, failover
│   │   │   ├── provider_registry.py        # Plugin registry: register/discover LLM providers
│   │   │   ├── approval_service.py         # Manage approval queue, approve/reject
│   │   │   ├── ledger_service.py           # Write to Action Ledger
│   │   │   └── observability_service.py    # OpenTelemetry span emission
│   │   │
│   │   ├── agent/                          # LangGraph agent workflow
│   │   │   ├── __init__.py
│   │   │   ├── workflow.py                 # LangGraph state machine definition
│   │   │   ├── state.py                    # AgentState TypedDict
│   │   │   ├── nodes/                      # One file per workflow node
│   │   │   │   ├── __init__.py
│   │   │   │   ├── plan.py
│   │   │   │   ├── investigate.py
│   │   │   │   ├── reproduce.py
│   │   │   │   ├── patch.py
│   │   │   │   ├── verify.py
│   │   │   │   └── report.py
│   │   │   └── prompts/                    # LLM prompt templates (Jinja2 or f-strings)
│   │   │       ├── __init__.py
│   │   │       ├── plan_prompt.py
│   │   │       ├── investigate_prompt.py
│   │   │       ├── patch_prompt.py
│   │   │       └── report_prompt.py
│   │   │
│   │   ├── infrastructure/                 # Concrete implementations of domain protocols
│   │   │   ├── __init__.py
│   │   │   ├── database/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── connection.py           # AsyncEngine, session factory (Neon Postgres)
│   │   │   │   ├── models.py               # SQLAlchemy ORM models (mapped to domain models)
│   │   │   │   └── repositories/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── run_repository.py
│   │   │   │       ├── webhook_repository.py
│   │   │   │       ├── event_repository.py
│   │   │   │       ├── policy_repository.py
│   │   │   │       ├── approval_repository.py
│   │   │   │       ├── ledger_repository.py
│   │   │   │       └── provider_health_repository.py
│   │   │   │
│   │   │   ├── github/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py               # Implements GitHubClient protocol
│   │   │   │   ├── webhook_validator.py     # HMAC signature verification
│   │   │   │   └── schemas.py              # GitHub API response models
│   │   │   │
│   │   │   ├── llm/                        # ===== UNIFIED LLM GATEWAY PLUGIN SYSTEM =====
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base_provider.py        # BaseLLMProvider ABC — shared logic for all providers
│   │   │   │   ├── providers/              # One adapter per LLM provider (plugin pattern)
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── gemini_provider.py  # Gemini adapter (primary, heavy reasoning)
│   │   │   │   │   ├── groq_provider.py    # Groq adapter (fast inference, classification)
│   │   │   │   │   ├── nvidia_nim_provider.py  # NVIDIA NIM adapter (free tier)
│   │   │   │   │   └── openai_compat_provider.py  # Generic OpenAI-compatible adapter
│   │   │   │   ├── output_validator.py     # JSON schema validation of LLM output
│   │   │   │   ├── circuit_breaker.py      # Circuit breaker state machine (per-provider)
│   │   │   │   ├── cost_calculator.py      # Per-provider token pricing + cost estimation
│   │   │   │   └── request_normalizer.py   # Normalizes all provider I/O to unified format
│   │   │   │
│   │   │   ├── policy/                     # ===== OPA/REGO POLICY ENGINE =====
│   │   │   │   ├── __init__.py
│   │   │   │   ├── opa_evaluator.py        # Implements PolicyEvaluator via OPA
│   │   │   │   ├── opa_client.py           # HTTP client for OPA REST API (sidecar mode)
│   │   │   │   ├── rego_compiler.py        # Compile YAML policy → Rego rules
│   │   │   │   └── rego/                   # Rego policy files
│   │   │   │       ├── main.rego           # Main policy entry point
│   │   │   │       ├── capabilities.rego   # Capability allow/deny/approval rules
│   │   │   │       ├── filesystem.rego     # Filesystem access rules
│   │   │   │       ├── commands.rego       # Command allow/deny rules
│   │   │   │       ├── network.rego        # Network access rules
│   │   │   │       └── sensitive.rego      # Sensitive action rules
│   │   │   │
│   │   │   ├── sandbox/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── e2b_runner.py           # DEFAULT: Implements SandboxRunner via E2B
│   │   │   │   └── github_actions_runner.py # FALLBACK: Implements SandboxRunner via GH Actions
│   │   │   │
│   │   │   └── observability/
│   │   │       ├── __init__.py
│   │   │       ├── tracing.py              # OpenTelemetry tracer setup
│   │   │       ├── genai_conventions.py    # OTel GenAI Semantic Conventions implementation
│   │   │       └── metrics.py              # Custom metrics (counters, histograms)
│   │   │
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── error_handler.py            # Global exception → HTTP response mapping
│   │       ├── request_id.py               # Attach correlation ID to every request
│   │       └── rate_limiter.py             # Rate limiting on webhook endpoint
│   │
│   └── tests/
│       ├── conftest.py                     # Shared fixtures, test DB, mock factories
│       ├── factories.py                    # Factory classes for test data generation
│       ├── unit/
│       │   ├── test_webhook_service.py
│       │   ├── test_opa_evaluator.py       # OPA/Rego policy evaluation tests
│       │   ├── test_risk_engine.py
│       │   ├── test_budget_engine.py
│       │   ├── test_policy_gateway.py
│       │   ├── test_llm_gateway.py         # Unified LLM gateway tests
│       │   ├── test_gemini_provider.py     # Gemini adapter tests
│       │   ├── test_groq_provider.py       # Groq adapter tests
│       │   ├── test_nvidia_nim_provider.py  # NIM adapter tests
│       │   ├── test_circuit_breaker.py     # Circuit breaker state transitions
│       │   ├── test_tool_gateway.py
│       │   ├── test_run_coordinator.py
│       │   └── test_action_intent.py
│       ├── integration/
│       │   ├── test_webhook_to_run.py
│       │   ├── test_policy_flow.py
│       │   ├── test_approval_flow.py
│       │   └── test_llm_gateway_failover.py  # Multi-provider failover integration test
│       └── e2e/
│           └── test_full_run.py
│
├── dashboard/                              # React frontend (Vite)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/
│   │   └── favicon.svg
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   ├── client.ts                   # Axios/fetch wrapper, base URL config
│       │   ├── runs.ts                     # API calls for runs
│       │   ├── approvals.ts               # API calls for approvals
│       │   └── policies.ts                # API calls for policies
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Header.tsx
│       │   │   ├── Sidebar.tsx
│       │   │   └── Layout.tsx
│       │   ├── runs/
│       │   │   ├── RunList.tsx
│       │   │   ├── RunDetail.tsx
│       │   │   ├── RunTimeline.tsx
│       │   │   └── RunStatusBadge.tsx
│       │   ├── approvals/
│       │   │   ├── ApprovalQueue.tsx
│       │   │   ├── ApprovalCard.tsx
│       │   │   └── ApprovalActions.tsx
│       │   ├── traces/
│       │   │   ├── DecisionTrace.tsx
│       │   │   └── TraceTimeline.tsx
│       │   ├── policies/
│       │   │   ├── PolicyEditor.tsx
│       │   │   └── PolicyViewer.tsx
│       │   └── common/
│       │       ├── StatusBadge.tsx
│       │       ├── CostDisplay.tsx
│       │       ├── JsonViewer.tsx
│       │       └── LoadingSpinner.tsx
│       ├── pages/
│       │   ├── DashboardPage.tsx
│       │   ├── RunsPage.tsx
│       │   ├── RunDetailPage.tsx
│       │   ├── ApprovalsPage.tsx
│       │   └── PoliciesPage.tsx
│       ├── hooks/
│       │   ├── useRuns.ts
│       │   ├── useApprovals.ts
│       │   └── usePolling.ts
│       ├── types/
│       │   └── index.ts                    # TypeScript interfaces mirroring backend models
│       └── styles/
│           ├── globals.css
│           └── variables.css
│
├── policies/                               # Default policy YAML files + Rego bundles
│   ├── example-policy.yaml                 # The concrete example from SDD Section 7
│   └── rego/                               # Compiled Rego policy bundles (generated from YAML)
│       └── .gitkeep
│
├── docs/
│   ├── architecture.md                     # High-level architecture doc
│   ├── api.md                              # API endpoint documentation
│   └── llm-gateway.md                      # LLM Gateway plugin architecture docs
│
├── docker-compose.yml                      # Local dev: Postgres + OPA sidecar + backend
├── Dockerfile                              # Backend container (Fly.io deployment)
├── fly.toml                                # Fly.io deployment configuration
├── Makefile                                # Common dev commands (make test, make lint, etc.)
├── README.md
└── .env.example                            # Template for required env vars
```

---

## Phase 1 — Foundation: Webhook Gateway, Run Coordinator & Basic Agent (Weeks 1–2)

### Phase 1 Goal
Establish the project skeleton, database schema, webhook ingestion pipeline, and a basic LangGraph agent that can receive a GitHub webhook, read a PR diff, and post an analysis comment. **No execution, no policy checks yet** — just the data pipeline from GitHub → backend → agent → GitHub comment.

### Phase 1 Architecture

```mermaid
graph LR
    GH[GitHub Webhook] --> WG[Webhook Gateway]
    WG --> IDB[(Idempotency Check<br>webhook_deliveries<br>Neon Postgres)]
    WG --> RC[Run Coordinator]
    RC --> LOCK[(Per-PR Lock<br>Neon Postgres advisory lock)]
    RC --> RDB[(Create Run<br>runs table)]
    RC --> AW[Agent Workflow<br>LangGraph]
    AW --> GHC[GitHub Client]
    GHC --> GH2[GitHub API<br>Read PR/Post Comment]
    AW --> EDB[(Run Events<br>run_events table)]
```

### Phase 1 Features — Exhaustive List

#### 1.1 Project Initialization
- **Python project** with `pyproject.toml` (Poetry or pip-tools), `ruff`, `mypy`, `pytest` configured
- **Alembic** initialized for database migrations
- **FastAPI** app factory in `main.py` with lifespan events (startup/shutdown), CORS middleware
- **`config.py`**: Pydantic Settings class loading all env vars:
  - `DATABASE_URL` — Neon Postgres connection string (with `?sslmode=require`)
  - `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY`, `GITHUB_WEBHOOK_SECRET`
  - `LLM_PROVIDERS_CONFIG` — JSON config for all LLM providers (used in Phase 3, but env var defined now):
    ```json
    {
      "providers": {
        "gemini": { "api_key": "...", "models": ["gemini-2.0-flash"], "role": "primary", "task_types": ["reasoning", "code_generation"] },
        "groq": { "api_key": "...", "models": ["llama-3.1-70b-versatile"], "role": "fallback", "task_types": ["classification", "formatting"] },
        "nvidia_nim": { "api_key": "...", "base_url": "https://integrate.api.nvidia.com/v1", "models": ["meta/llama-3.1-8b-instruct"], "role": "fallback", "task_types": ["reasoning"] }
      },
      "default_primary": "gemini",
      "default_fallback": "groq"
    }
    ```
  - `SANDBOX_PROVIDER` — `e2b` (default) or `github_actions`
  - `E2B_API_KEY` — E2B sandbox API key
  - `OPA_URL` — OPA sidecar URL (default: `http://localhost:8181`) or `embedded` for in-process
  - `FLY_APP_NAME` — Fly.io app name for deployment
- **`container.py`**: DI composition root — instantiates all services, repositories, clients and wires dependencies
- **`.env.example`**: Template with every required env var documented
- **`docker-compose.yml`**: PostgreSQL 16 + OPA sidecar for local development
  ```yaml
  services:
    postgres:
      image: postgres:16
      ports: ["5432:5432"]
      environment:
        POSTGRES_DB: agentguard
        POSTGRES_USER: agentguard
        POSTGRES_PASSWORD: dev_password
    opa:
      image: openpolicyagent/opa:latest
      ports: ["8181:8181"]
      command: "run --server --log-level debug /policies"
      volumes:
        - ./policies/rego:/policies
  ```
- **`fly.toml`**: Fly.io deployment config (app name, region, health check, env vars)
- **`Makefile`**: targets for `dev`, `test`, `lint`, `typecheck`, `migrate`, `seed`
- **CI pipeline** (`.github/workflows/ci.yml`): `ruff check` → `mypy` → `pytest` on every push

#### 1.2 Database Schema (Alembic Migration 001)
Create all core tables **upfront** on **Neon Postgres** so later phases just add columns, not restructure:

| Table | Columns | Notes |
|---|---|---|
| `runs` | `id (UUID PK)`, `repo (text)`, `pr_number (int)`, `head_sha (text)`, `trigger_type (enum: pull_request, check_suite)`, `status (enum: queued, running, paused, stale, completed, failed)`, `policy_version (int, nullable)`, `started_at`, `completed_at`, `total_tokens (int default 0)`, `total_cost_usd (decimal default 0)`, `created_at`, `updated_at` | Index on `(repo, pr_number, status)` for lock queries |
| `webhook_deliveries` | `id (UUID PK)`, `github_delivery_id (text UNIQUE)`, `event_type (text)`, `payload_summary (jsonb)`, `run_id (UUID FK nullable)`, `received_at` | `UNIQUE` constraint on `github_delivery_id` enforces idempotency |
| `run_events` | `id (UUID PK)`, `run_id (UUID FK)`, `step_name (text)`, `event_type (enum: decision, action_intent, tool_call, policy_decision, llm_call)`, `content (jsonb)`, `tokens_used (int default 0)`, `latency_ms (int default 0)`, `created_at` | Append-only, index on `run_id` |
| `policy_decisions` | `id (UUID PK)`, `run_id (UUID FK)`, `event_id (UUID FK)`, `action_requested (jsonb)`, `rule_matched (text)`, `risk_score (int)`, `decision (enum: allow, deny, require_approval)`, `policy_version (int)`, `opa_query_id (text nullable)`, `created_at` | `opa_query_id` links to OPA decision log. Populated in Phase 2 |
| `approvals` | `id (UUID PK)`, `run_id (UUID FK)`, `event_id (UUID FK)`, `status (enum: pending, approved, rejected)`, `action_intent (jsonb)`, `decision_trace (jsonb)`, `requested_at`, `decided_at`, `decided_by (text nullable)` | Populated in Phase 4 |
| `policies` | `id (UUID PK)`, `repo (text UNIQUE)`, `yaml_content (text)`, `rego_bundle (text)`, `parsed_content (jsonb)`, `version (int default 1)`, `created_at`, `updated_at` | `rego_bundle` stores compiled Rego. Populated in Phase 2 |
| `provider_health` | `id (UUID PK)`, `provider (text)`, `model (text)`, `window_start (timestamptz)`, `request_count (int)`, `error_count (int)`, `timeout_count (int)`, `avg_latency_ms (float)`, `circuit_state (text default 'closed')` | Tracks per-provider AND per-model. Populated in Phase 3 |

> [!NOTE]
> **Neon Postgres specifics**: Use `?sslmode=require` in the connection string. Neon supports connection pooling via their pooler endpoint — use the pooled connection string for the app, the direct connection for migrations. Neon's serverless driver auto-scales to zero on idle, which pairs well with Fly.io's free tier.

#### 1.3 Domain Models (Pydantic)
Create all domain models in `app/domain/models/`:

- **`run.py`**: `RunStatus` enum (`QUEUED`, `RUNNING`, `PAUSED`, `STALE`, `COMPLETED`, `FAILED`), `TriggerType` enum, `Run` Pydantic model
- **`action_intent.py`**: `ActionType` enum (`FILE_READ`, `FILE_WRITE`, `COMMAND_EXEC`, `NETWORK_REQUEST`, `GITHUB_API`, `LLM_CALL`), `ActionIntent` model with fields: `action`, `target`, `operation`, `reason`, `metadata`
- **`decision_trace.py`**: `DecisionTrace` model: `decision`, `evidence: list[str]`, `proposed_action: ActionIntent | None`, `policy_decision: PolicyDecision | None`, `execution: ExecutionResult | None`
- **`policy_decision.py`**: `Decision` enum (`ALLOW`, `DENY`, `REQUIRE_APPROVAL`), `PolicyDecision` model (includes `opa_query_id` for OPA decision linking)
- **`webhook_delivery.py`**: `WebhookDelivery` model
- **`run_event.py`**: `EventType` enum, `RunEvent` model
- **`approval.py`**: `ApprovalStatus` enum, `Approval` model
- **`policy.py`**: `PolicyConfig` model (structured representation of the YAML policy file — capabilities, filesystem rules, commands, risk weights, thresholds, budget)
- **`provider_health.py`**: `ProviderHealth` model (includes `circuit_state`)
- **`llm_config.py`**: LLM gateway configuration models:
  ```python
  class LLMProviderName(str, Enum):
      GEMINI = "gemini"
      GROQ = "groq"
      NVIDIA_NIM = "nvidia_nim"
      OPENAI_COMPAT = "openai_compat"  # Generic catch-all for any OpenAI-compatible API


  class TaskType(str, Enum):
      REASONING = "reasoning"  # Complex analysis, code generation
      CODE_GENERATION = "code_generation"
      CLASSIFICATION = "classification"  # Simple categorization, routing
      FORMATTING = "formatting"  # Output reformatting, summarization
      GENERAL = "general"  # Default/unspecified


  class RoutingStrategy(str, Enum):
      TASK_BASED = (
          "task_based"  # Route by task type (reasoning→Gemini, classification→Groq)
      )
      PRIMARY_FALLBACK = "primary_fallback"  # Primary with fallback on failure
      ROUND_ROBIN = "round_robin"  # Distribute across providers


  class LLMProviderConfig(BaseModel):
      name: LLMProviderName
      api_key: str
      base_url: str | None = None  # Required for NIM, optional for others
      models: list[str]
      role: Literal["primary", "fallback", "specialist"]
      task_types: list[TaskType]  # What task types this provider handles
      max_tokens: int = 4096
      temperature: float = 0.1
      timeout_seconds: int = 30
      max_retries: int = 3
      rate_limit_rpm: int | None = None  # Provider-specific rate limit


  class LLMGatewayConfig(BaseModel):
      providers: dict[LLMProviderName, LLMProviderConfig]
      routing_strategy: RoutingStrategy = RoutingStrategy.TASK_BASED
      default_primary: LLMProviderName = LLMProviderName.GEMINI
      default_fallback: LLMProviderName = LLMProviderName.GROQ
      output_validation_enabled: bool = True
      circuit_breaker_threshold: float = 0.5  # 50% error rate trips breaker
      circuit_breaker_window_seconds: int = 300  # 5-minute window
  ```

#### 1.4 Domain Protocols (Interfaces)
Create all protocol definitions in `app/domain/protocols/`:

- **`github_client.py`**: `GitHubClient` Protocol — methods: `get_pr_diff()`, `get_pr_files()`, `get_ci_logs()`, `post_comment()`, `create_commit()`, `get_file_content()`, `get_repo_tree()`
- **`llm_provider.py`**: `LLMProvider` Protocol — **the plugin interface for all LLM providers**:
  ```python
  class LLMProvider(Protocol):
      """Plugin interface for LLM providers. Implement this to add a new provider."""

      @property
      def name(self) -> LLMProviderName: ...
      @property
      def supported_task_types(self) -> list[TaskType]: ...
      async def generate(
          self,
          prompt: str,
          system_prompt: str | None = None,
          temperature: float = 0.1,
          max_tokens: int = 4096,
          response_format: type[BaseModel] | None = None,
      ) -> LLMResponse: ...
      async def generate_structured(
          self, prompt: str, response_model: type[T], system_prompt: str | None = None
      ) -> T: ...
      async def health_check(self) -> bool: ...
      def estimate_tokens(self, text: str) -> int: ...
      def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float: ...
  ```
- **`policy_evaluator.py`**: `PolicyEvaluator` Protocol — method: `evaluate(action_intent, policy_config, run_context) → PolicyDecision`
- **`risk_scorer.py`**: `RiskScorer` Protocol — method: `score(action_intent, policy_config) → RiskAssessment`
- **`budget_tracker.py`**: `BudgetTracker` Protocol — methods: `check(run_id) → BudgetStatus`, `record_usage(run_id, tokens, cost)`
- **`tool_executor.py`**: `ToolExecutor` Protocol — method: `execute(action_intent, credentials) → ExecutionResult`
- **`sandbox_runner.py`**: `SandboxRunner` Protocol — method: `run(command, files, timeout) → SandboxResult`
- **`repository.py`**: Generic `Repository[T]` Protocol — methods: `get(id)`, `save(entity)`, `list(filters)`

#### 1.5 Domain Exceptions
`app/domain/exceptions.py`:
```python
class AgentGuardError(Exception): ...


class WebhookValidationError(AgentGuardError): ...


class DuplicateDeliveryError(AgentGuardError): ...


class RunNotFoundError(AgentGuardError): ...


class ConcurrentRunError(AgentGuardError): ...


class StaleRunError(AgentGuardError): ...


class PolicyViolationError(AgentGuardError): ...


class BudgetExceededError(AgentGuardError): ...


class LLMProviderError(AgentGuardError): ...


class LLMOutputValidationError(LLMProviderError): ...


class LLMCircuitBreakerOpenError(LLMProviderError): ...


class LLMAllProvidersFailedError(LLMProviderError): ...


class SandboxExecutionError(AgentGuardError): ...


class OPAEvaluationError(AgentGuardError): ...


class PolicyCompilationError(AgentGuardError): ...
```

#### 1.6 Infrastructure: Database Layer
- **`connection.py`**: Create `AsyncEngine` + `async_sessionmaker` using `asyncpg` driver. Session-per-request pattern. **Neon-specific**: Use the pooled connection string (`-pooler` suffix) for the app, direct connection for Alembic migrations. Configure `ssl=require`.
- **`models.py`**: SQLAlchemy 2.0 declarative ORM models mapped to all tables above (using `Mapped[]` annotations).
- **Repositories** (Phase 1 implements):
  - `RunRepository`: `create()`, `get_by_id()`, `get_by_repo_pr()`, `update_status()`, `mark_stale()`
  - `WebhookRepository`: `record_delivery()` (insert, catch unique violation → `DuplicateDeliveryError`), `exists()`
  - `EventRepository`: `append()`, `get_events_for_run()`

#### 1.7 Infrastructure: GitHub Client
- **`client.py`**: Implements `GitHubClient` protocol using `httpx.AsyncClient`
  - Authenticates as a GitHub App (JWT → installation token)
  - Methods: `get_pr_diff()`, `get_pr_files()`, `get_ci_logs()`, `post_comment()`, `get_file_content()`
  - All responses validated through Pydantic schemas in `github/schemas.py`
- **`webhook_validator.py`**: HMAC-SHA256 signature verification of incoming webhook payloads

#### 1.8 Services: Webhook Service
`webhook_service.py`:
- Receives raw webhook payload + headers
- Calls `webhook_validator.verify_signature(payload, signature, secret)`
- Extracts `X-GitHub-Delivery` header → calls `webhook_repository.record_delivery()` — if duplicate, raises `DuplicateDeliveryError` (caught by error handler, returns 200 OK — idempotent)
- Parses event type (`pull_request`, `check_suite`) and relevant fields (repo, PR number, head SHA)
- Dispatches to `RunCoordinator`

#### 1.9 Services: Run Coordinator
`run_coordinator.py`:
- **Per-PR locking**: Uses Postgres advisory locks (`pg_try_advisory_xact_lock`) keyed on `hash(repo + pr_number)`. If lock can't be acquired, event is queued (status `QUEUED`).
- **Commit-SHA binding**: Every new `Run` records the `head_sha` at creation time.
- **Staleness detection**: Before executing, checks if `head_sha` still matches the PR's current head. If not, marks the run `STALE` and creates a new run for the current SHA.
- **Orchestration**: Creates the `Run` record, invokes the agent workflow, updates run status on completion/failure.

#### 1.10 Agent Workflow (LangGraph — Simplified for Phase 1)
In Phase 1, the agent runs a **simplified 3-node graph**: `Plan → Investigate → Report`
- **No Action Intents yet** (added in Phase 2) — the agent calls GitHub directly through the `GitHubClient`
- **State** (`state.py`): `AgentState` TypedDict with: `run_id`, `repo`, `pr_number`, `head_sha`, `pr_diff`, `file_tree`, `ci_logs`, `analysis`, `plan`, `events: list[RunEvent]`
- **Plan node**: LLM reads the PR diff/CI logs, produces a structured analysis plan
- **Investigate node**: LLM reads relevant files from the repo, analyzes the root cause
- **Report node**: LLM generates a summary comment, posts it to the PR via `GitHubClient`

> [!WARNING]
> Phase 1's agent calls tools directly (no policy checks). This is **intentionally** insecure — the Action Intent + Policy Gateway boundary is added in Phase 2. The purpose of Phase 1 is to validate the data pipeline (webhook → database → agent → GitHub comment).

#### 1.11 API Routes (Phase 1)
- `POST /webhooks/github` — Webhook ingestion endpoint
- `GET /health` — Health check (returns DB connectivity status + Neon connection pool stats)
- `GET /api/runs` — List runs (paginated)
- `GET /api/runs/{run_id}` — Get run detail with events

#### 1.12 Middleware
- **`error_handler.py`**: Maps domain exceptions to HTTP responses (`DuplicateDeliveryError` → 200, `RunNotFoundError` → 404, `OPAEvaluationError` → 500, etc.)
- **`request_id.py`**: Generates/propagates a `X-Request-ID` header for correlation

#### 1.13 Tests for Phase 1
- **Unit**: `test_webhook_service.py` (signature verify, idempotency), `test_run_coordinator.py` (locking, SHA binding, staleness)
- **Integration**: `test_webhook_to_run.py` (POST webhook → run created → events recorded)

### Phase 1 Deliverable
✅ A GitHub webhook triggers a run → the agent reads the PR diff → posts an analysis comment on the PR. Duplicate webhooks are safely ignored. Concurrent webhooks for the same PR are serialized. Everything is recorded in Neon Postgres.

---

## Phase 2 — Action Intent & OPA Policy Gateway (Weeks 3–4)

### Phase 2 Goal
Introduce the **core security boundary**: the Action Intent model and the Policy Gateway powered by **OPA (Open Policy Agent) with Rego**. Refactor the agent to emit Action Intents instead of calling tools directly. Every action now passes through OPA policy evaluation before execution.

### Phase 2 Architecture

```mermaid
graph LR
    AW[Agent Workflow] -->|emits| AI[Action Intent]
    AI --> PG[Policy Gateway]
    PG --> OPA[OPA Engine<br>Rego Rules]
    PG --> RE[Risk Engine<br>stub — always 0]
    PG --> BE[Budget Engine<br>stub — always OK]
    OPA --> |ALLOW / DENY| PG
    PG -->|ALLOW| EXEC[Direct Execution<br>via GitHubClient]
    PG -->|DENY| HALT[Agent Adapts or Halts]
    PG -->|REQUIRE_APPROVAL| PAUSE[Run Paused<br>Phase 4 completes this]
    AI --> LED[Action Ledger<br>policy_decisions table]
```

### Phase 2 Features — Exhaustive List

#### 2.1 Action Intent Implementation
- Finalize `ActionIntent` Pydantic model with all fields:
  ```python
  class ActionIntent(BaseModel):
      id: UUID
      run_id: UUID
      action: ActionType  # FILE_READ, FILE_WRITE, COMMAND_EXEC, etc.
      target: str  # e.g., "src/payment.py"
      operation: str  # e.g., "modify", "create", "delete", "execute"
      reason: str  # Agent's reason for this action
      metadata: dict[str, Any]  # Additional context (diff content, command args, etc.)
      created_at: datetime
  ```
- Create `ActionIntentBuilder` utility to construct intents from agent node outputs with validation

#### 2.2 OPA/Rego Policy System

##### 2.2.1 Rego Policy Files
Create Rego policy files in `infrastructure/policy/rego/`:

**`main.rego`** — Entry point:
```rego
package agentguard.policy

import data.agentguard.policy.capabilities
import data.agentguard.policy.filesystem
import data.agentguard.policy.commands
import data.agentguard.policy.network
import data.agentguard.policy.sensitive

# Default deny — fail closed
default decision = "DENY"

# DENY if any deny rule matches
decision = "DENY" {
    capabilities.denied
}
decision = "DENY" {
    commands.denied
}

# REQUIRE_APPROVAL if any approval rule matches (and not denied)
decision = "REQUIRE_APPROVAL" {
    not capabilities.denied
    not commands.denied
    capabilities.requires_approval
}
decision = "REQUIRE_APPROVAL" {
    not capabilities.denied
    not commands.denied
    sensitive.requires_approval
}

# ALLOW only if explicitly allowed and not denied/approval-required
decision = "ALLOW" {
    not capabilities.denied
    not commands.denied
    not capabilities.requires_approval
    not sensitive.requires_approval
    capabilities.allowed
    filesystem.allowed
    network.allowed
    commands.allowed
}

# Return matched rule for audit trail
matched_rule = rule {
    # ... returns the specific rule that matched
}
```

**`capabilities.rego`** — Capability rules:
```rego
package agentguard.policy.capabilities

denied {
    input.action_intent.capability == data.policy.capabilities.deny[_]
}

requires_approval {
    input.action_intent.capability == data.policy.capabilities.approval[_]
}

allowed {
    input.action_intent.capability == data.policy.capabilities.allow[_]
}
```

**`filesystem.rego`** — Filesystem access rules:
```rego
package agentguard.policy.filesystem

allowed {
    input.action_intent.action == "FILE_READ"
    glob.match(data.policy.filesystem.read[_], ["/"], input.action_intent.target)
}

allowed {
    input.action_intent.action == "FILE_WRITE"
    glob.match(data.policy.filesystem.write[_], ["/"], input.action_intent.target)
}
```

**`commands.rego`**, **`network.rego`**, **`sensitive.rego`** — Similar pattern for each rule category.

##### 2.2.2 OPA Evaluator
`infrastructure/policy/opa_evaluator.py` — Implements `PolicyEvaluator` protocol:
- **Two modes of operation**:
  1. **Sidecar mode** (production): Sends queries to OPA REST API (`POST /v1/data/agentguard/policy`)
  2. **Embedded mode** (testing): Uses `opa-python-client` or `regopy` to evaluate Rego in-process
- **Input construction**: Transforms `ActionIntent` + `PolicyConfig` into the OPA input document:
  ```json
  {
    "input": {
      "action_intent": {
        "action": "FILE_WRITE",
        "target": "src/payment.py",
        "capability": "github.create_commit",
        "operation": "modify"
      },
      "run_context": {
        "repo": "myorg/myrepo",
        "pr_number": 42
      }
    },
    "data": {
      "policy": { /* parsed YAML policy */ }
    }
  }
  ```
- **Fail-closed**: If OPA is unreachable, returns `DENY`. If OPA returns an error, returns `DENY`. If OPA returns no decision, returns `DENY`.
- Returns: `PolicyDecision` with `decision`, `matched_rule`, `opa_query_id`, `details`

##### 2.2.3 OPA Client
`infrastructure/policy/opa_client.py`:
- Async HTTP client for OPA REST API using `httpx`
- Endpoints: `POST /v1/data/{package}` (query), `PUT /v1/policies/{id}` (upload policy), `PUT /v1/data/{path}` (upload data)
- Health check: `GET /health`
- Connection pooling, retry on transient failures

##### 2.2.4 Rego Compiler
`infrastructure/policy/rego_compiler.py`:
- **Transforms YAML policy → OPA data document**: Takes the `PolicyConfig` (parsed from YAML) and converts it to the JSON format OPA expects as `data.policy`
- This means the YAML policy file from SDD Section 7 is the **source of truth** — Rego rules reference the data, and the data comes from YAML
- Validates the YAML → data transformation for completeness

#### 2.3 Policy Gateway (Orchestrator)
`policy_gateway.py`:
- Receives an `ActionIntent` + `run_id`
- Loads the `PolicyConfig` for the run's repo
- Calls (in order):
  1. `OPAEvaluator.evaluate()` → if `DENY`, short-circuit
  2. `RiskEngine.score()` → map score to decision via thresholds (stub in Phase 2: always returns score 0)
  3. `BudgetEngine.check()` → is the run within budget? (stub in Phase 2: always returns OK)
- Computes the **most restrictive** decision across all three engines
- Persists the decision to `policy_decisions` table (with `policy_version` and `opa_query_id`)
- Returns the final `PolicyDecision`
- **Critical invariant**: This method is the ONLY path from "agent wants to do X" to "X actually happens"

#### 2.4 Policy Configuration Parser
- **`PolicyConfig`** Pydantic model fully implemented: parses the YAML policy file (Section 7 of SDD) into structured, validated Python objects:
  - `capabilities: CapabilityConfig` (allow, approval, deny lists)
  - `filesystem: FilesystemConfig` (read/write glob patterns)
  - `network: NetworkConfig` (allowed domains)
  - `commands: CommandConfig` (allow/deny lists)
  - `resources: ResourceConfig` (max execution time, max files)
  - `risk_weights: dict[str, int]`
  - `risk_thresholds: RiskThresholdConfig`
  - `budget: BudgetConfig`
  - `sensitive_actions: list[SensitiveActionRule]`
- **Policy Repository**: `PolicyRepository` — `get_by_repo()`, `save()`, `get_version()`. On save, also compiles YAML → OPA data and pushes to OPA.
- **Policy versioning**: Every update increments the version number. The version used for each decision is recorded.

#### 2.5 Refactor Agent Workflow to Emit Action Intents
- Every agent node that needs to perform an action (read file, post comment, etc.) now:
  1. Constructs an `ActionIntent`
  2. Submits it to the `PolicyGateway`
  3. If `ALLOW` → executes the action
  4. If `DENY` → receives denial reason (including OPA matched rule), adjusts strategy (may propose narrower action)
  5. If `REQUIRE_APPROVAL` → pauses the run (full implementation in Phase 4; in Phase 2, treat as `DENY` with log)
- Expand the agent to the full 6-node graph: `Plan → Investigate → Reproduce → Patch → Verify → Report`
  - **Reproduce node** (stub): Logs intent to run tests but does not execute (sandbox in Phase 3)
  - **Patch node**: LLM proposes a code fix, emits `FILE_WRITE` Action Intent
  - **Verify node** (stub): Logs intent to verify but does not execute (sandbox in Phase 3)
- Each node also emits a `DecisionTrace` entry appended to `run_events`

#### 2.6 Action Ledger Writes
- Every `ActionIntent` + `PolicyDecision` (with OPA query ID) + execution result is written to `run_events` (event_type = `action_intent` | `policy_decision` | `tool_call`)
- This data forms the **Action Ledger** — the append-only audit trail

#### 2.7 Policy Management API
- `GET /api/policies/{repo}` — Get current policy for a repo (YAML + compiled Rego status)
- `PUT /api/policies/{repo}` — Update policy YAML (validates, compiles Rego, pushes to OPA, increments version, saves)
- `POST /api/policies/validate` — Parse and validate YAML + test-compile to Rego without saving
- `GET /api/policies/{repo}/rego` — Get the compiled Rego bundle for inspection

#### 2.8 Tests for Phase 2
- **Unit**: `test_opa_evaluator.py` (all rule types: capability, filesystem, command, network, sensitive actions, fail-closed cases, OPA unreachable → DENY), `test_policy_gateway.py` (orchestration, most-restrictive decision), `test_action_intent.py` (model validation), `test_rego_compiler.py` (YAML → OPA data transformation)
- **Integration**: `test_policy_flow.py` (webhook → agent emits intent → OPA evaluates → action executes or denied → ledger records)
- **Rego unit tests**: OPA supports native Rego testing (`opa test`) — write test cases for each policy rule

### Phase 2 Deliverable
✅ The agent proposes actions as structured Action Intents. Every intent passes through the OPA-powered Policy Gateway. Rego rules enforce capabilities, filesystem, commands, network, and sensitive action policies. Allowed actions execute; denied actions are blocked. Policy decisions (with OPA query IDs) are recorded with versioning. The security boundary is live.

---

## Phase 3 — Tool Gateway, Sandbox & Unified LLM Gateway (Weeks 5–6)

### Phase 3 Goal
Build the **execution layer**: the Tool Gateway (capability-scoped dispatch), sandboxed code execution (E2B default + GitHub Actions fallback), and the **Unified LLM Gateway** — a plugin-based, multi-provider LLM abstraction with task-based routing, output validation, retry, circuit breaker, failover, and OpenTelemetry GenAI Semantic Conventions.

### Phase 3 Architecture

```mermaid
graph TD
    PG[Policy Gateway<br>ALLOW] --> TG[Tool Gateway]
    TG --> |capability check| CAP{Capability Allowed?}
    CAP -->|github.*| GHC[GitHub Client]
    CAP -->|sandbox.*| SBX[Sandbox Runner]
    CAP -->|llm.*| LGW[Unified LLM Gateway]

    subgraph "Unified LLM Gateway (Plugin Architecture)"
        LGW --> ROUTE{Task-Based Router}
        ROUTE -->|reasoning / code_gen| GEM[Gemini Provider<br>gemini-2.0-flash]
        ROUTE -->|classification / formatting| GRQ[Groq Provider<br>llama-3.1-70b]
        ROUTE -->|fallback / reasoning| NIM[NVIDIA NIM Provider<br>llama-3.1-8b]
        ROUTE -->|any OpenAI-compatible| OAI[OpenAI-Compat<br>Generic Adapter]

        GEM --> VAL[Output Validator]
        GRQ --> VAL
        NIM --> VAL
        OAI --> VAL

        GEM --> CB[Circuit Breaker<br>per-provider]
        GRQ --> CB
        NIM --> CB
        OAI --> CB

        CB --> PH[(provider_health<br>per-provider + per-model)]
    end

    subgraph "OTel GenAI Semantic Conventions"
        LGW -.->|gen_ai.system<br>gen_ai.request.model<br>gen_ai.usage.prompt_tokens| OTEL[OpenTelemetry Spans]
    end

    subgraph "Sandbox (Strategy Pattern)"
        SBX --> E2B[E2B Runner<br>DEFAULT]
        SBX --> GHA[GitHub Actions Runner<br>FALLBACK]
    end
```

### Phase 3 Features — Exhaustive List

#### 3.1 Tool Gateway
`tool_gateway.py`:
- Receives an `ActionIntent` that has already been `ALLOW`ed by the Policy Gateway
- **Second capability check**: Verifies the action's capability is in the policy's `capabilities.allow` or `capabilities.approval` list (defense in depth — even if Policy Gateway allows, Tool Gateway re-verifies the specific capability)
- **Dispatcher**: Routes to the correct executor based on action type:
  - `GITHUB_API` → `GitHubClient`
  - `COMMAND_EXEC` → `SandboxRunner` (E2B by default)
  - `FILE_READ` / `FILE_WRITE` → `GitHubClient` (read/write via GitHub API, not local filesystem)
  - `LLM_CALL` → `LLMGateway`
- **Credential scoping**: Each executor receives only the minimum credentials needed (scoped installation token for GitHub, ephemeral token for E2B sandbox, API key for LLM — each provider has its own key)
- Returns `ExecutionResult` with `status`, `output`, `duration_ms`, `tokens_used`
- Records execution result to the Action Ledger

#### 3.2 Unified LLM Gateway (Plugin Architecture)

##### 3.2.1 LLM Gateway Service
`llm_gateway.py` — The central orchestrator for all LLM interactions:

```python
class LLMGateway:
    """Unified LLM gateway with plugin-based providers, task-based routing,
    output validation, retry, circuit breaking, and failover."""

    def __init__(
        self,
        config: LLMGatewayConfig,
        provider_registry: ProviderRegistry,
        output_validator: OutputValidator,
        circuit_breaker_manager: CircuitBreakerManager,
        provider_health_repo: ProviderHealthRepository,
        tracer: opentelemetry.trace.Tracer,
    ): ...

    async def generate(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        system_prompt: str | None = None,
        response_format: type[BaseModel] | None = None,
        run_id: UUID | None = None,
    ) -> LLMResponse:
        """Route to the best provider for the task type, with failover."""

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        task_type: TaskType = TaskType.GENERAL,
        system_prompt: str | None = None,
        run_id: UUID | None = None,
    ) -> T:
        """Generate and validate structured output as a Pydantic model."""
```

**Routing logic**:
1. Determine the best provider for the given `TaskType` using the `RoutingStrategy`:
   - `TASK_BASED`: Select the provider whose `task_types` includes the requested type. E.g., `TaskType.REASONING` → Gemini, `TaskType.CLASSIFICATION` → Groq
   - `PRIMARY_FALLBACK`: Always try the default primary first
   - `ROUND_ROBIN`: Distribute across healthy providers
2. Check the circuit breaker for the selected provider
3. If circuit breaker is open → select fallback provider (Groq → NIM → OpenAI-compat → fail)
4. Call the provider's `generate()` method
5. Validate output via `OutputValidator`
6. If output invalid → retry up to 2 times with a "fix your output" prompt
7. If provider error → retry with backoff → if all retries fail → failover to next provider
8. Record metrics to `provider_health` table
9. Emit OpenTelemetry span with GenAI Semantic Conventions

##### 3.2.2 Provider Registry (Plugin System)
`provider_registry.py`:
```python
class ProviderRegistry:
    """Registry for LLM provider plugins. New providers are added by
    implementing the LLMProvider protocol and registering here."""

    def __init__(self) -> None:
        self._providers: dict[LLMProviderName, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        """Register a new LLM provider plugin."""
        self._providers[provider.name] = provider

    def get(self, name: LLMProviderName) -> LLMProvider:
        """Get a registered provider by name."""

    def get_for_task(self, task_type: TaskType) -> list[LLMProvider]:
        """Get all providers that support a given task type, ordered by priority."""

    def list_providers(self) -> list[LLMProviderName]:
        """List all registered providers."""

    def health_check_all(self) -> dict[LLMProviderName, bool]:
        """Check health of all registered providers."""
```

##### 3.2.3 Provider Adapters (Plugins)

**`base_provider.py`** — Shared base class:
```python
class BaseLLMProvider(ABC):
    """Base class for all LLM provider adapters. Handles common logic:
    request/response normalization, token counting, cost estimation."""

    def __init__(self, config: LLMProviderConfig, http_client: httpx.AsyncClient): ...

    # Subclasses implement these:
    @abstractmethod
    async def _send_request(
        self, normalized_request: NormalizedRequest
    ) -> RawResponse: ...
    @abstractmethod
    def _parse_response(self, raw: RawResponse) -> NormalizedResponse: ...
    @abstractmethod
    def _get_pricing(self) -> TokenPricing: ...
```

**`gemini_provider.py`** — Gemini adapter (primary, heavy reasoning):
- Uses `google-generativeai` SDK or REST API
- Models: `gemini-2.0-flash` (free tier: 15 RPM, 1M TPM, 1500 RPD)
- Handles: Gemini-specific JSON response format, safety filters, function calling format
- Task types: `REASONING`, `CODE_GENERATION`, `GENERAL`
- Token counting: Uses Gemini's `count_tokens()` API
- Cost estimation: Free tier pricing (input: free, output: free — but tracked for budget engine)

**`groq_provider.py`** — Groq adapter (fast inference, classification):
- Uses OpenAI-compatible SDK (Groq is OpenAI-compatible) with `base_url="https://api.groq.com/openai/v1"`
- Models: `llama-3.1-70b-versatile` (free tier: 30 RPM, 131k TPM)
- Handles: Groq-specific rate limits, model availability
- Task types: `CLASSIFICATION`, `FORMATTING`, `GENERAL`
- Ultra-fast inference latency (~100ms for simple tasks)

**`nvidia_nim_provider.py`** — NVIDIA NIM adapter (free tier):
- Uses OpenAI-compatible SDK with `base_url="https://integrate.api.nvidia.com/v1"`
- Models: `meta/llama-3.1-8b-instruct`, `meta/llama-3.1-70b-instruct` (NIM free tier: 5000 API calls/month)
- Handles: NIM-specific auth (API key in header), model naming conventions (`org/model-name`)
- Task types: `REASONING`, `CODE_GENERATION`, `GENERAL`
- **Configurability**: The NIM adapter accepts any NIM endpoint URL + model name, so users can point to self-hosted NIM instances or different NIM API endpoints

**`openai_compat_provider.py`** — Generic OpenAI-compatible adapter:
- Works with any OpenAI-compatible API (OpenAI, Together, Anyscale, vLLM, etc.)
- Configured entirely via `LLMProviderConfig`: `base_url`, `api_key`, `models`
- This is the **catch-all plugin** — any new OpenAI-compatible provider can be added just by config, no code changes

##### 3.2.4 Request Normalizer
`request_normalizer.py`:
- Converts all provider-specific request/response formats into a **unified internal format**:
  ```python
  class NormalizedRequest(BaseModel):
      messages: list[Message]
      model: str
      temperature: float
      max_tokens: int
      response_format: dict | None  # JSON schema if structured output


  class NormalizedResponse(BaseModel):
      content: str
      model: str
      provider: LLMProviderName
      prompt_tokens: int
      completion_tokens: int
      total_tokens: int
      latency_ms: int
      finish_reason: str
  ```
- This ensures the gateway's core logic (routing, validation, retry, metrics) is completely provider-agnostic

##### 3.2.5 Output Validator
`output_validator.py`:
- Validates LLM JSON output against a JSON Schema or Pydantic model
- Rejects: missing required fields, wrong types, extra fields not in schema, hallucinated tool names
- A malformed output NEVER becomes an Action Intent
- On validation failure, constructs a retry prompt with the validation errors

##### 3.2.6 Circuit Breaker (Per-Provider)
`circuit_breaker.py`:
- **Separate circuit breaker per provider** (Gemini, Groq, NIM each have their own)
- States: `CLOSED` (healthy), `OPEN` (failing — skip this provider), `HALF_OPEN` (testing recovery)
- Trips `OPEN` when error rate > 50% over a 5-minute window (configurable via `LLMGatewayConfig`)
- After 60s in `OPEN`, transitions to `HALF_OPEN` and allows one test request
- Persists state to `provider_health` table for observability
- **Failover chain**: Gemini (primary) → Groq (fallback) → NIM (fallback) → generic OpenAI-compat → `LLMAllProvidersFailedError`

##### 3.2.7 Cost Calculator
`cost_calculator.py`:
- Per-provider pricing tables:
  ```python
  PRICING = {
      LLMProviderName.GEMINI: TokenPricing(
          input_per_1k=0.0, output_per_1k=0.0
      ),  # Free tier
      LLMProviderName.GROQ: TokenPricing(
          input_per_1k=0.0, output_per_1k=0.0
      ),  # Free tier
      LLMProviderName.NVIDIA_NIM: TokenPricing(
          input_per_1k=0.0, output_per_1k=0.0
      ),  # Free tier
  }
  ```
- Even though all are free tier, we track costs as if they were paid — this proves the budget engine works and provides realistic cost estimates

##### 3.2.8 OpenTelemetry GenAI Semantic Conventions
`infrastructure/observability/genai_conventions.py`:
- Implements the [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) for LLM call tracing
- **Span attributes** set on every LLM call:
  ```python
  # Provider identification (separated from model)
  span.set_attribute("gen_ai.system", "gemini")  # or "groq", "nvidia_nim"
  span.set_attribute("gen_ai.request.model", "gemini-2.0-flash")

  # Request parameters
  span.set_attribute("gen_ai.request.temperature", 0.1)
  span.set_attribute("gen_ai.request.max_tokens", 4096)

  # Response metrics
  span.set_attribute("gen_ai.response.model", "gemini-2.0-flash")
  span.set_attribute("gen_ai.response.finish_reasons", ["stop"])
  span.set_attribute("gen_ai.usage.prompt_tokens", 1234)
  span.set_attribute("gen_ai.usage.completion_tokens", 567)

  # Custom AgentGuard attributes
  span.set_attribute("agentguard.task_type", "reasoning")
  span.set_attribute("agentguard.routing_strategy", "task_based")
  span.set_attribute("agentguard.provider_role", "primary")
  span.set_attribute("agentguard.circuit_breaker_state", "closed")
  span.set_attribute("agentguard.estimated_cost_usd", 0.0)
  span.set_attribute("agentguard.run_id", "...")
  ```
- This enables Grafana dashboards to slice LLM metrics by `gen_ai.system` (provider) vs. `gen_ai.request.model` (model) independently — e.g., "show me latency for all Gemini models" or "compare llama-3.1-70b across Groq vs NIM"

##### 3.2.9 Retry Policy
- Uses `tenacity` library
- Exponential backoff (1s, 2s, 4s) for transient errors (429, 500, 502, 503, timeout)
- Max 3 retries per provider before failover
- Rate limit (429) handling: respect `Retry-After` header if provided

#### 3.3 Sandbox Runner (E2B Default + GitHub Actions Fallback)

##### 3.3.1 E2B Runner (Default)
`e2b_runner.py` — Implements `SandboxRunner` protocol using E2B SDK:
- Creates ephemeral sandbox with specified language runtime (Python, Node.js)
- Uploads test files, runs commands, captures stdout/stderr/exit code
- Auto-destroys sandbox after execution (or on timeout)
- **No production secrets** — sandbox receives only: the repo code (or specific files), test commands, ephemeral credentials
- Bounded: max 5 minutes execution, max 512MB memory
- E2B free tier: 100 sandbox hours/month

##### 3.3.2 GitHub Actions Runner (Fallback)
`github_actions_runner.py` — Alternative `SandboxRunner` implementation:
- Triggers a GitHub Actions workflow via API dispatch (`POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches`)
- Polls for workflow completion (or uses webhook callback)
- Retrieves logs and artifacts from the workflow run
- GitHub free tier: 2,000 minutes/month for private repos, unlimited for public

##### 3.3.3 Sandbox Selection
Configured via `SANDBOX_PROVIDER` env var (default: `e2b`). The `container.py` DI root wires the correct implementation:
```python
if config.sandbox_provider == "e2b":
    sandbox_runner = E2BSandboxRunner(config.e2b_api_key)
elif config.sandbox_provider == "github_actions":
    sandbox_runner = GitHubActionsSandboxRunner(github_client)
```

#### 3.4 Agent Workflow — Full Execution Path
With the Tool Gateway, LLM Gateway, and Sandbox Runner in place, complete the agent workflow:
- **Plan node**: Uses `LLMGateway.generate_structured(task_type=TaskType.REASONING)` → routes to Gemini
- **Investigate node**: Uses `LLMGateway.generate(task_type=TaskType.REASONING)` → routes to Gemini
- **Reproduce node**: Emits `COMMAND_EXEC` Action Intent → if allowed, runs failing tests in E2B sandbox → captures output
- **Patch node**: Uses `LLMGateway.generate_structured(task_type=TaskType.CODE_GENERATION)` → routes to Gemini. Emits `FILE_WRITE` Action Intent.
- **Verify node**: Runs tests again in E2B sandbox with the proposed patch applied → captures pass/fail result
- **Report node**: Uses `LLMGateway.generate(task_type=TaskType.FORMATTING)` → routes to Groq (fast). Emits `GITHUB_API` Action Intent to create a commit and post a comment.

#### 3.5 Token & Cost Tracking (Infrastructure)
- Every LLM call records (via `NormalizedResponse`): `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_cost_usd` (calculated by `CostCalculator`)
- `RunRepository.update_token_usage()` atomically increments `total_tokens` and `total_cost_usd` on the run
- `ProviderHealthRepository` records per-provider, per-model metrics per time window
- This data feeds the Budget Engine in Phase 4

#### 3.6 Tests for Phase 3
- **Unit**: `test_llm_gateway.py` (task-based routing, validation, retry, failover chain), `test_gemini_provider.py`, `test_groq_provider.py`, `test_nvidia_nim_provider.py` (each adapter), `test_circuit_breaker.py` (state transitions per provider), `test_tool_gateway.py` (dispatch, capability check, credential scoping), `test_output_validator.py`
- **Integration**: `test_llm_gateway_failover.py` (Gemini fails → circuit breaker opens → Groq takes over → NIM takes over → all fail → error)
- **Integration**: End-to-end test with mocked LLM providers and E2B sandbox

### Phase 3 Deliverable
✅ The agent can execute a complete PR review cycle: read code → reproduce failure in E2B sandbox → generate patch via Gemini → verify fix → post results via Groq (fast formatting). LLM calls route intelligently by task type. Circuit breakers failover across Gemini → Groq → NIM. All LLM calls emit OTel GenAI Semantic Convention spans. All execution goes through the Tool Gateway with capability checks.

---

## Phase 4 — Risk Engine, Budget Engine & Human Approval (Week 7)

### Phase 4 Goal
Complete the Policy Gateway with risk scoring and budget enforcement. Implement the human-in-the-loop approval flow: when a high-risk action is proposed, the run pauses, a human reviews and approves/rejects via the dashboard.

### Phase 4 Architecture

```mermaid
graph TD
    AI[Action Intent] --> PG[Policy Gateway]
    PG --> OPA[OPA Engine<br>Rego Rules]
    PG --> RE[Risk Engine<br>score = Σ weights]
    PG --> BE[Budget Engine<br>tokens/cost/calls check]

    RE -->|score < 30| ALLOW[ALLOW]
    RE -->|30 ≤ score < 70| APPROVAL[REQUIRE_APPROVAL]
    RE -->|score ≥ 70| DENY[DENY]

    BE -->|within budget| OK[Continue]
    BE -->|exceeded| HALT[HALT Run]

    APPROVAL --> AQ[Approval Queue<br>approvals table]
    AQ --> DASH[Dashboard<br>approve / reject UI]
    DASH -->|Approved| RESUME[Resume Run]
    DASH -->|Rejected| STOP[Halt or Adapt]
```

### Phase 4 Features — Exhaustive List

#### 4.1 Risk Engine
`risk_engine.py` — Implements `RiskScorer` protocol:
- **Input**: `ActionIntent` + `PolicyConfig`
- **Scoring logic**: Additive score based on action characteristics:
  ```python
  score = 0
  if action.action == ActionType.FILE_WRITE:
      score += policy.risk_weights.get("filesystem_write", 20)
  if matches_pattern(action.target, "config/prod/**"):
      score += policy.risk_weights.get("production_path", 40)
  if matches_pattern(action.target, ".github/workflows/**"):
      score += policy.risk_weights.get("workflow_modification", 30)
  if action.metadata.get("force_push"):
      score += policy.risk_weights.get("force_push", 50)
  if action.action == ActionType.NETWORK_REQUEST:
      score += policy.risk_weights.get("network_request", 10)
  if involves_secret_access(action):
      score += policy.risk_weights.get("secret_access", 60)
  ```
- **Threshold mapping** (from policy):
  - `score < allow_below` → `ALLOW`
  - `allow_below ≤ score < approval_below` → `REQUIRE_APPROVAL`
  - `score ≥ approval_below` → `DENY`
- All weights and thresholds come from the policy file — zero hardcoded values
- Returns: `RiskAssessment(score: int, factors: list[str], decision: Decision)`

#### 4.2 Budget Engine
`budget_engine.py` — Implements `BudgetTracker` protocol:
- **Per-run tracking**: Reads `total_tokens`, `total_cost_usd`, and count of `LLM_CALL` events from the run
- **Budget check**: Compares against `PolicyConfig.budget`:
  - `max_tokens`: Total tokens used in this run
  - `max_cost_usd`: Total estimated cost in this run
  - `max_llm_calls`: Total number of LLM API calls in this run
- **Enforcement**: If any limit would be exceeded by the current action, returns `BudgetStatus.EXCEEDED` → the Policy Gateway halts the run
- **Preemptive check**: Before an LLM call, estimates token usage (via `LLMProvider.estimate_tokens()`) and checks if it would exceed the budget
- Returns: `BudgetStatus(within_budget: bool, usage: BudgetUsage, limits: BudgetLimits, remaining: BudgetRemaining)`

#### 4.3 Policy Gateway — Complete Integration
Update `policy_gateway.py` to wire in the real Risk Engine and Budget Engine:
- Evaluation order: OPA Policy Engine → Risk Engine → Budget Engine
- **Most restrictive wins**: If OPA says `ALLOW` but Risk says `REQUIRE_APPROVAL`, final decision is `REQUIRE_APPROVAL`
- If Budget is exceeded, decision is `DENY` regardless of other engines
- Full `PolicyDecision` now includes: `decision`, `policy_rule`, `opa_query_id`, `risk_score`, `risk_factors`, `budget_status`, `policy_version`

#### 4.4 Approval Service
`approval_service.py`:
- **Request approval**: Creates an `Approval` record (status `PENDING`) with:
  - The `ActionIntent` that triggered the approval
  - The `DecisionTrace` entry explaining why the agent proposed this action
  - The `PolicyDecision` showing why approval is required (risk score, matched OPA rule)
- **Pause run**: Updates run status to `PAUSED`
- **Process decision**:
  - `approve(approval_id, decided_by)`: Updates approval status to `APPROVED`, resumes the run, executes the action via Tool Gateway
  - `reject(approval_id, decided_by)`: Updates approval status to `REJECTED`, notifies the agent. The agent may:
    - Re-propose a narrower, lower-risk action (e.g., write to `src/` instead of `config/prod/`)
    - Or halt the run if no alternative is possible
- **Timeout**: Approvals pending > 30 minutes auto-expire → run is halted (configurable)

#### 4.5 Approval API Routes
- `GET /api/approvals` — List pending approvals (filterable by status, run_id)
- `GET /api/approvals/{id}` — Get approval detail (includes Action Intent, Decision Trace, diff)
- `POST /api/approvals/{id}/approve` — Approve the action
- `POST /api/approvals/{id}/reject` — Reject the action with optional reason

#### 4.6 Agent Adaptation on Rejection
When an action is rejected:
- The agent receives the rejection reason (including OPA matched rule and risk factors)
- It can analyze why the action was rejected (e.g., "target path `config/prod/**` triggered high risk score")
- It re-plans with a constraint: avoid the rejected action's pattern
- It proposes a narrower alternative (e.g., write to `src/` instead)
- If the alternative is also rejected, the run halts with a clear failure reason

#### 4.7 Tests for Phase 4
- **Unit**: `test_risk_engine.py` (all scoring factors, threshold mapping, edge cases), `test_budget_engine.py` (within budget, exceeded each limit, preemptive check)
- **Integration**: `test_approval_flow.py` (high-risk action → approval created → approve → action executes → run resumes; reject → agent adapts)

### Phase 4 Deliverable
✅ High-risk actions trigger human approval. Runs pause and resume correctly. Budget limits are enforced. Risk scoring is transparent and configurable via the policy file. The complete Policy Gateway (OPA rules + risk + budget) is operational.

---

## Phase 5 — Observability, Decision Trace & Dashboard (Week 8)

### Phase 5 Goal
Build the **observability layer**: OpenTelemetry instrumentation (with GenAI Semantic Conventions fully integrated from Phase 3), Grafana dashboards, and the React dashboard for live run monitoring, decision trace visualization, and approval management.

### Phase 5 Architecture

```mermaid
graph LR
    BE[Backend<br>FastAPI on Fly.io] -->|OTel spans<br>GenAI conventions| OTEL[OpenTelemetry<br>Collector]
    OTEL --> GC[Grafana Cloud<br>Traces + Metrics]

    BE -->|REST API| DASH[React Dashboard<br>Vercel/Netlify]

    subgraph Dashboard Pages
        DP[Dashboard<br>Overview]
        RP[Runs<br>List + Detail]
        AP[Approvals<br>Queue]
        TP[Traces<br>Timeline View]
        PP[Policies<br>Editor + OPA Status]
        LP[LLM Gateway<br>Provider Health]
    end

    DASH --> DP
    DASH --> RP
    DASH --> AP
    DASH --> TP
    DASH --> PP
    DASH --> LP
```

### Phase 5 Features — Exhaustive List

#### 5.1 OpenTelemetry Instrumentation
`infrastructure/observability/tracing.py`:
- **Tracer setup**: Configure `TracerProvider` with `OTLPSpanExporter` pointing to Grafana Cloud
- **Auto-instrumentation**: FastAPI, httpx, asyncpg (via `opentelemetry-instrumentation-*` packages)
- **Custom spans** for every key operation:
  - `webhook.receive` — incoming webhook processing
  - `run.execute` — full run lifecycle
  - `agent.node.{name}` — each LangGraph node (plan, investigate, etc.)
  - `gen_ai.*` — LLM API calls using GenAI Semantic Conventions (already implemented in Phase 3's `genai_conventions.py`):
    - `gen_ai.system` separates provider from model
    - `gen_ai.request.model` identifies the specific model
    - `gen_ai.usage.*` tracks token usage per call
  - `policy.evaluate` — OPA policy gateway evaluation (with risk score, decision, OPA query ID as attributes)
  - `tool.execute` — tool gateway execution (with capability, duration as attributes)
  - `sandbox.run` — sandbox execution (with provider=e2b/github_actions, duration)
  - `approval.wait` — time spent waiting for human approval
- **Custom metrics** (`metrics.py`):
  - `agentguard.runs.total` (counter, by status)
  - `agentguard.runs.duration_seconds` (histogram)
  - `agentguard.llm.tokens_total` (counter, by `gen_ai.system` × `gen_ai.request.model`)
  - `agentguard.llm.cost_usd` (counter, by `gen_ai.system`)
  - `agentguard.llm.latency_seconds` (histogram, by `gen_ai.system` × `gen_ai.request.model`)
  - `agentguard.llm.circuit_breaker_trips` (counter, by provider)
  - `agentguard.llm.failovers` (counter, from_provider × to_provider)
  - `agentguard.policy.decisions_total` (counter, by decision type)
  - `agentguard.policy.risk_score` (histogram)
  - `agentguard.policy.opa_latency_seconds` (histogram)
  - `agentguard.approvals.pending_count` (gauge)
  - `agentguard.sandbox.executions_total` (counter, by provider × status)

#### 5.2 Grafana Cloud Dashboards
Pre-built dashboard JSON configs for import into Grafana Cloud (free tier):
- **Agent Overview**: Runs per day, success rate, average duration, total cost
- **LLM Gateway Performance**: Provider comparison dashboard — latency, error rate, token usage, cost breakdown, sliced by `gen_ai.system` (provider) vs `gen_ai.request.model` (model). Circuit breaker states per provider. Failover frequency.
- **OPA Policy**: Decision distribution (allow/deny/approval), risk score distribution, most-triggered Rego rules, OPA evaluation latency
- **Approval**: Pending count, average approval time, approve/reject ratio
- **Sandbox**: E2B vs GitHub Actions execution stats, success rate, execution time distribution

#### 5.3 Action Ledger API
Enrich the runs API for the dashboard:
- `GET /api/runs/{id}/events` — Full event timeline (Action Intents, OPA policy decisions, tool executions, LLM calls with provider info)
- `GET /api/runs/{id}/trace` — Decision Trace entries for the run
- `GET /api/runs/{id}/cost` — Token usage and cost breakdown per step, per provider
- `GET /api/stats` — Aggregate stats (runs, success rate, total cost, avg duration)
- `GET /api/providers/health` — Current health status of all LLM providers (circuit breaker states, error rates, latencies)

#### 5.4 React Dashboard (Vite + TypeScript)

##### 5.4.1 Dashboard Page (`DashboardPage.tsx`)
- **Cards**: Total runs, success rate, pending approvals, total cost (this week)
- **LLM Provider Status**: Live indicator for each provider (Gemini 🟢, Groq 🟢, NIM 🟡 = half-open, etc.)
- **Chart**: Runs over time (line chart — using Chart.js or Recharts)
- **Recent Runs**: Table with status badge, repo, PR, duration, cost
- **Auto-refresh**: Polls `/api/stats` and `/api/providers/health` every 10 seconds

##### 5.4.2 Runs Page (`RunsPage.tsx`)
- **Run List** (`RunList.tsx`): Filterable table (by repo, status, date range)
- **Run Status Badge** (`RunStatusBadge.tsx`): Color-coded badge (green=completed, yellow=running, orange=paused, red=failed, gray=stale)

##### 5.4.3 Run Detail Page (`RunDetailPage.tsx`)
- **Run header**: Repo, PR number, commit SHA (linked), trigger type, status, duration, cost
- **Decision Trace Timeline** (`TraceTimeline.tsx`): Vertical timeline showing each step:
  - Step name (Plan, Investigate, Reproduce, Patch, Verify, Report)
  - Decision evidence
  - Action Intent (collapsible JSON)
  - OPA Policy Decision with matched Rego rule + risk score visualization (color-coded bar)
  - LLM call details: provider used, model, token count, latency, cost
  - Execution result
  - Duration per step
- **Cost breakdown**: Table showing token usage and cost per LLM call, grouped by provider
- **Live streaming**: If run is in progress, timeline updates in real-time (polling every 3s)

##### 5.4.4 Approvals Page (`ApprovalsPage.tsx`)
- **Approval Queue** (`ApprovalQueue.tsx`): List of pending approvals
- **Approval Card** (`ApprovalCard.tsx`): Shows:
  - The Action Intent (what the agent wants to do)
  - The Decision Trace (why the agent wants to do it)
  - The OPA Policy Decision (why approval is required — matched Rego rule, risk score)
  - Diff viewer (if applicable — for file write actions)
- **Approval Actions** (`ApprovalActions.tsx`): Approve / Reject buttons with optional rejection reason

##### 5.4.5 Policies Page (`PoliciesPage.tsx`)
- **Policy Editor** (`PolicyEditor.tsx`): YAML editor (using CodeMirror or Monaco) for editing policy files
- **Rego Preview**: Read-only view of the compiled Rego rules generated from the YAML
- **OPA Status**: Connection status to OPA sidecar, loaded policies, last evaluation time
- **Policy Viewer** (`PolicyViewer.tsx`): Read-only view of current policy with syntax highlighting
- **Version history**: List of policy versions with diffs
- **Save + validate**: Validates YAML, compiles to Rego, tests against OPA before saving

##### 5.4.6 Common Components
- **`StatusBadge.tsx`**: Generic colored badge component
- **`CostDisplay.tsx`**: Formats cost as "$0.04" with token count tooltip
- **`JsonViewer.tsx`**: Collapsible, syntax-highlighted JSON viewer
- **`LoadingSpinner.tsx`**: Loading state component
- **Layout** (`Layout.tsx`): Sidebar navigation + header + main content area

##### 5.4.7 Dashboard Styling
- Dark theme by default (professional, technical aesthetic)
- CSS custom properties for theming (`variables.css`)
- Responsive layout (sidebar collapses on mobile)
- Use modern typography (Inter or JetBrains Mono for code)

#### 5.5 Policy Versioning in Decision Records
- Every `PolicyDecision` now records the `policy_version` and `opa_query_id` it was evaluated against
- The Run Detail page shows which policy version and Rego bundle was active during the run
- Historical decisions remain explainable even after the policy is updated

#### 5.6 Tests for Phase 5
- **Unit**: API endpoint tests (response schemas, pagination, filtering)
- **Frontend**: Component tests for critical UI flows (approval approve/reject)

### Phase 5 Deliverable
✅ A professional dashboard shows live run status, full decision traces (with OPA rule matches), token costs per provider, LLM provider health (circuit breaker states), and approval management. OpenTelemetry traces with GenAI Semantic Conventions flow to Grafana Cloud — enabling cross-provider performance analysis. Every decision is permanently recorded with its policy version and OPA query ID.

---

## Phase 6 — Polish, Demo & Deployment (Week 9)

### Phase 6 Goal
Production-ready deployment on **Fly.io** with **Neon Postgres**, demo preparation, documentation, and polish. The system should be demoable end-to-end as described in SDD Section 13.

### Phase 6 Features — Exhaustive List

#### 6.1 Rate Limiting
`middleware/rate_limiter.py`:
- Rate limit the webhook endpoint: 100 requests/minute per IP
- Rate limit the API: 60 requests/minute per IP
- Uses in-memory sliding window (no Redis needed at demo scale)
- Returns `429 Too Many Requests` with `Retry-After` header

#### 6.2 Live Policy Editing Demo
- Dashboard Policy Editor saves and activates the new policy version immediately
- YAML → Rego compilation happens on save, pushed to OPA in real-time
- Re-running the same PR with a different policy shows different OPA evaluation results (action allowed vs. blocked by different Rego rule)
- This is the key "change one line and watch the behavior change" demo moment

#### 6.3 Deployment

##### 6.3.1 Backend: Fly.io
- **`Dockerfile`** (multi-stage: build → run):
  ```dockerfile
  FROM python:3.12-slim AS builder
  # Install dependencies
  FROM python:3.12-slim AS runtime
  # Copy built packages, run with uvicorn
  ```
- **`fly.toml`**:
  ```toml
  app = "agentguard"
  primary_region = "iad"

  [http_service]
    internal_port = 8000
    force_https = true

  [[services.http_checks]]
    path = "/health"

  [env]
    OPA_URL = "http://localhost:8181"  # OPA runs as a sidecar process
  ```
- **OPA sidecar**: Run OPA as a process alongside the FastAPI app within the same Fly.io machine (using a process group or `supervisord`), or as a separate Fly.io app on the same private network
- **Secrets**: `fly secrets set DATABASE_URL=... GITHUB_PRIVATE_KEY=... LLM_PROVIDERS_CONFIG=...`
- **Auto-deploy**: GitHub Actions workflow triggers `flyctl deploy` on merge to `main`
- **Known trade-off**: Fly.io free tier machines auto-stop on idle — document this honestly; explain how to fix with a paid always-on machine

##### 6.3.2 Database: Neon Postgres
- Create a Neon project with `main` branch (production) and `dev` branch (development)
- **Pooled connection** string (with `-pooler` suffix) for the app
- **Direct connection** string for Alembic migrations
- `DATABASE_URL` set as Fly.io secret
- Alembic migrations run on deploy via Fly.io release command:
  ```toml
  [deploy]
    release_command = "alembic upgrade head"
  ```
- **Neon branching**: Use Neon's branch feature for development — branch off `main`, test migrations, merge back

##### 6.3.3 Dashboard: Vercel
- Static Vite build deployed to Vercel
- `VITE_API_URL` env var pointing to `https://agentguard.fly.dev`
- Auto-deploy from `main` branch

##### 6.3.4 CI/CD Pipeline
GitHub Actions:
- On PR: `ruff check` → `mypy` → `pytest` → `opa test` (Rego tests)
- On merge to `main`: lint → type-check → test → `flyctl deploy` (backend) → Vercel deploy (dashboard)

#### 6.4 Demo Repository Setup
- Create a small demo repo (e.g., `agentguard-demo-repo`) with:
  - A simple Python project with tests
  - A deliberately broken test (for the CI failure demo)
  - The AgentGuard GitHub App installed
  - A policy file configured
- Create a demo script following SDD Section 13:
  1. Open PR with broken test → run triggers automatically
  2. Show dashboard: live decision trace streaming (OPA rules, risk scores, provider routing)
  3. Agent hits high-risk action → OPA + Risk Engine → `REQUIRE_APPROVAL` → approval UI appears
  4. Reject → agent adapts (proposes narrower action, lower risk score) → approve → run completes
  5. Show Action Ledger: every action, OPA rule matched, risk score, cost per provider
  6. Kill Gemini API key live → show circuit breaker trip in dashboard → automatic failover to Groq → show GenAI convention spans in Grafana showing provider switch mid-run
  7. Duplicate webhook → ignored (show idempotency)
  8. New commit mid-run → run marked stale and restarted
  9. Change policy YAML in dashboard → Rego recompiles → re-run shows different behavior

#### 6.5 Documentation
- **README.md**: Project overview, setup instructions, architecture diagram, demo instructions
- **`docs/architecture.md`**: Detailed architecture document with component diagrams
- **`docs/api.md`**: API documentation (auto-generated from FastAPI OpenAPI schema, plus manual enrichment)
- **`docs/llm-gateway.md`**: LLM Gateway plugin architecture — how to add a new provider, routing strategies, circuit breaker behavior, GenAI conventions
- **`.env.example`**: Complete with descriptions and example values for every env var:
  ```env
  # Database (Neon Postgres)
  DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.us-east-1.aws.neon.tech/agentguard?sslmode=require
  DATABASE_URL_DIRECT=postgresql+asyncpg://user:pass@ep-xxx.us-east-1.aws.neon.tech/agentguard?sslmode=require

  # GitHub App
  GITHUB_APP_ID=123456
  GITHUB_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----...
  GITHUB_WEBHOOK_SECRET=whsec_...

  # LLM Providers (JSON config)
  LLM_PROVIDERS_CONFIG={"providers":{"gemini":{"api_key":"...","models":["gemini-2.0-flash"],"role":"primary","task_types":["reasoning","code_generation"]},"groq":{"api_key":"...","models":["llama-3.1-70b-versatile"],"role":"fallback","task_types":["classification","formatting"]},"nvidia_nim":{"api_key":"...","base_url":"https://integrate.api.nvidia.com/v1","models":["meta/llama-3.1-8b-instruct"],"role":"fallback","task_types":["reasoning"]}},"default_primary":"gemini","default_fallback":"groq"}

  # Sandbox
  SANDBOX_PROVIDER=e2b
  E2B_API_KEY=e2b_...

  # OPA
  OPA_URL=http://localhost:8181

  # Observability
  OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-east-0.grafana.net/otlp
  OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic ...
  ```

#### 6.6 Error Handling Polish
- Ensure all error paths produce meaningful, structured error responses
- Ensure no unhandled exceptions leak stack traces in production
- Add request timeout middleware (30s for API calls, 5min for webhook processing)

#### 6.7 Security Hardening
- Verify CORS is properly configured (only the Vercel dashboard origin)
- Verify no secrets are logged (redact API keys from structured logs — especially LLM provider keys)
- Verify webhook signature verification cannot be bypassed
- Verify OPA sidecar is not exposed to the public internet (only accessible within Fly.io private network)
- Add security headers (X-Content-Type-Options, X-Frame-Options, etc.)

### Phase 6 Deliverable
✅ AgentGuard is publicly deployed on Fly.io + Neon Postgres + Vercel, with a live demo showing the complete workflow from SDD Section 13 — including OPA policy evaluation, multi-provider LLM routing with live failover, and GenAI observability in Grafana. Documentation is complete. The project is portfolio-ready.

---

## Dependency Map Across Phases

```mermaid
graph TD
    P1[Phase 1<br>Foundation<br>Neon Postgres + FastAPI] --> P2[Phase 2<br>OPA Policy Gateway<br>Rego Rules]
    P1 --> P3[Phase 3<br>LLM Gateway + E2B Sandbox<br>Gemini/Groq/NIM Plugins]
    P2 --> P4[Phase 4<br>Risk + Budget + Approvals]
    P3 --> P4
    P4 --> P5[Phase 5<br>OTel GenAI Conventions<br>Grafana + Dashboard]
    P5 --> P6[Phase 6<br>Fly.io Deploy<br>Polish + Demo]

    style P1 fill:#1a1a2e,stroke:#e94560,color:#fff
    style P2 fill:#1a1a2e,stroke:#0f3460,color:#fff
    style P3 fill:#1a1a2e,stroke:#16213e,color:#fff
    style P4 fill:#1a1a2e,stroke:#533483,color:#fff
    style P5 fill:#1a1a2e,stroke:#e94560,color:#fff
    style P6 fill:#1a1a2e,stroke:#0f3460,color:#fff
```

## Technology Summary

| Technology | Purpose | Version |
|---|---|---|
| Python 3.12+ | Backend language | Latest stable |
| FastAPI | HTTP framework | 0.110+ |
| SQLAlchemy 2.0 | ORM | 2.0+ |
| Alembic | Database migrations | Latest |
| Pydantic v2 | Data validation | 2.x |
| LangGraph | Agent orchestration | Latest |
| httpx | Async HTTP client | Latest |
| tenacity | Retry library | Latest |
| structlog | Structured logging | Latest |
| opentelemetry-sdk | Observability | Latest |
| opentelemetry-semantic-conventions | GenAI conventions | Latest |
| ruff | Linting + formatting | Latest |
| mypy | Type checking | Latest |
| pytest + pytest-asyncio | Testing | Latest |
| **Neon Postgres** | **Database (serverless)** | **16** |
| **OPA (Open Policy Agent)** | **Policy engine** | **Latest** |
| **E2B** | **Sandbox execution (default)** | **Latest** |
| **google-generativeai** | **Gemini LLM provider** | **Latest** |
| **groq** | **Groq LLM provider** | **Latest** |
| React 18 + TypeScript | Dashboard frontend | 18+ |
| Vite | Frontend build tool | 5+ |
| **Fly.io** | **Backend hosting** | **—** |
| **Vercel** | **Dashboard hosting** | **—** |
| **Grafana Cloud** | **Observability backend** | **Free tier** |
