<div align="center">

# AgentGuard

### Policy Governance & Execution Control for Autonomous AI Coding Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![OPA](https://img.shields.io/badge/OPA-Rego-7C3AED.svg)](https://www.openpolicyagent.org/)

**Live Demo → [agent-guard-red.vercel.app](https://agent-guard-red.vercel.app)**

</div>

---

## Table of Contents

- [What is AgentGuard?](#what-is-agentguard)
- [Why This Exists](#why-this-exists)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
  - [High-Level System Diagram](#high-level-system-diagram)
  - [Request Flow End-to-End](#request-flow-end-to-end)
  - [Core Components](#core-components)
- [The Action Intent Model](#the-action-intent-model)
- [Policy Gateway](#policy-gateway)
  - [Risk Engine](#risk-engine)
  - [Budget Engine](#budget-engine)
  - [Policy File Reference](#policy-file-reference)
- [Data Model](#data-model)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Local Setup](#local-setup)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [GitHub App Setup](#github-app-setup)
  - [OPA Setup](#opa-setup)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Use Cases and Demo Workflow](#use-cases-and-demo-workflow)
- [Security Model](#security-model)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## What is AgentGuard?

AgentGuard is a **governance and execution-control layer** for autonomous coding agents. It ships with one concrete, end-to-end use case — reviewing and automatically fixing GitHub pull requests and failing CI runs — but the architecture is deliberately generic: nothing in the core system is PR-specific.

> **One-line pitch:** *"A governance and execution-control layer that lets an AI agent safely act on a real codebase — every action goes through policy, risk, and budget checks before it runs, with human approval gates and full observability."*

The agent **never executes anything directly**. Every proposed action — read a file, run a command, write a patch, call an API — is converted into an explicit **Action Intent**, evaluated by a **Policy Gateway** (policy rules + risk scoring + budget limits), and only then dispatched to a tool. High-risk actions pause for human approval. Every decision — allowed, denied, or escalated — is recorded in an **Action Ledger**, alongside token cost, latency, and outcome.

---

## Why This Exists

Autonomous coding agents are increasingly given real permissions — to read code, run commands, call APIs, and push changes. Five critical problems appear the moment you do this for real:

| Problem | Description |
|---|---|
| **Unrestricted blast radius** | An agent with shell/file access can do damage (delete files, leak secrets, push to `main`) if nothing constrains it |
| **No accountability** | When an agent does something wrong, there is no record of *why* it decided to do it, or which rule allowed it |
| **No intervention point** | Most agent demos are fully autonomous; there is no seam where a human can step in before something risky happens |
| **No cost visibility** | Teams running agents in production have no idea what a given task cost in tokens or dollars |
| **No safety net around the LLM** | A hallucinated or malformed "tool call" from the model can become an executed action if nothing validates it first |

**AgentGuard directly solves all five**, demonstrated end-to-end through one concrete workflow: safely automating PR review and CI-failure fixes.

---

## Key Features

- **Zero-Trust Action Boundary** — Every LLM tool invocation is intercepted as an explicit `ActionIntent` before any execution
- **OPA/Rego Policy Engine** — Declarative YAML policies compiled to Rego rules; evaluated sub-15ms via a local OPA sidecar
- **Deterministic Risk Scoring** — Additive risk weights (no ML model); thresholds map directly to `ALLOW` / `REQUIRE_APPROVAL` / `DENY`
- **Budget Engine** — Per-run token count, API cost, and LLM call limits enforced before each reasoning step
- **Dual-Custody Human Approval** — High-risk actions quarantine the agent and surface an interactive diff review UI for human sign-off
- **PostgreSQL Row-Level Locking** — Serializes concurrent approval submissions; prevents duplicate GitHub commits from double-clicks
- **100% Webhook Idempotency** — GitHub delivery IDs stored with unique constraint; duplicate network retries are silently dropped
- **Commit-SHA Binding** — Every run is bound to the exact head commit SHA; stale runs are detected and halted if the PR changes mid-run
- **Plugin-Based LLM Router** — Gemini (primary), Groq (fast inference), NVIDIA NIM (additional); circuit breaker and automatic failover
- **LLM Output Validation** — Every model response is schema-validated before it can become an `ActionIntent`; hallucinated tool calls are rejected
- **E2B Sandboxing** — Test execution happens in ephemeral, isolated micro-sandboxes; never on the host
- **Append-Only Action Ledger** — Full audit trail of every intent, policy decision, and execution result per run
- **Governance Dashboard** — Live run status, decision traces, token cost tracking, LLM provider health, and approve/reject controls
- **OpenTelemetry Instrumented** — Every LLM call, tool call, and policy decision emits OTel spans

---

## Architecture Overview

### High-Level System Diagram

```
                         GitHub
                           |
                     Webhook Event
                     (HMAC + delivery-id)
                           |
                           v
                  +------------------+
                  | Webhook Gateway  |
                  | HMAC verify +    |
                  | delivery-id      |
                  | idempotency      |
                  +--------+---------+
                           |
                           v
                  +------------------+
                  | Run Coordinator  |
                  | per-PR lock/queue|
                  | commit-SHA bind  |
                  +--------+---------+
                           |
                           v
                  +------------------+
                  | Agent Workflow   |
                  |   (LangGraph)    |
                  | Plan->Investigate|
                  | ->Reproduce->Patch
                  | ->Verify->Report |
                  +--------+---------+
                           |
                     Action Intent
                           |
                           v
                  +------------------+
                  |  Policy Gateway  |
                  |  Policy Engine   |  <- OPA / Rego
                  |  Risk Engine     |  <- Deterministic score
                  |  Budget Engine   |  <- Token / cost limits
                  +--------+---------+
                           |
           +---------------+---------------+
           v               v               v
         ALLOW      REQUIRE_APPROVAL      DENY
           |               |
           |               v
           |    +------------------+
           |    |  Approval Queue  |
           |    |  Dashboard UI    |
           |    +--------+---------+
           |             | (human approved)
           +------+------+
                  v
         +------------------+
         |  Tool Gateway    |
         | capability model |
         | scoped tokens    |
         +--------+---------+
                  |
      +-----------+-----------+
      v           v           v
  GitHub API   E2B         LLM Router
  commits,    Sandbox      Gemini/Groq
  comments    tests        failover
      |           |           |
      +-----------+-----------+
                  v
         +------------------+
         |  Action Ledger   |
         |  Decision Trace  |
         |  (Neon Postgres) |
         +--------+---------+
                  |
                  v
         +------------------+
         |  Dashboard (UI)  |
         |  Vercel / React  |
         +------------------+
```

### Request Flow End-to-End

1. **Developer opens a PR** or CI fails. GitHub sends a webhook with an HMAC signature and a unique delivery ID.
2. **Webhook Gateway** verifies the HMAC signature and checks the delivery ID against a unique DB constraint. Duplicate deliveries are dropped without processing.
3. **Run Coordinator** checks for an in-progress run on the same `(repo, PR)` pair. If one exists, the event is queued. Otherwise it creates a new `Run` bound to the current **head commit SHA**.
4. **Agent Workflow** (LangGraph) executes its `Plan → Investigate → Reproduce → Patch → Verify → Report` state machine. At each step requiring an external action, it emits an explicit **Action Intent** along with a structured **Decision Trace** entry.
5. Every `ActionIntent` passes through the **Policy Gateway**: the Policy Engine checks declarative rules, the Risk Engine computes a deterministic score, the Budget Engine checks remaining token/cost budget. Returns `ALLOW`, `DENY`, or `REQUIRE_APPROVAL`.
6. `ALLOW` dispatches to the **Tool Gateway**, which executes via a named capability using least-privilege scoped credentials. `REQUIRE_APPROVAL` pauses the run; a human reviews the proposed intent and diff in the dashboard and approves or rejects. `DENY` informs the agent, which must adapt or halt.
7. If the PR's head SHA changes mid-run, the **Run Coordinator** marks the run stale and restarts/halts it. It never applies a patch computed against outdated code.
8. Every step's Action Intent, policy decision, and execution result is appended to the **Action Ledger** and emitted as an OpenTelemetry span.
9. The **Dashboard** reads run state and the ledger to render the live decision trace and expose approve/reject controls.

### Core Components

| Component | Responsibility | Implementation |
|---|---|---|
| **Webhook Gateway** | HMAC verification + delivery-ID idempotency | FastAPI route + unique DB constraint |
| **Run Coordinator** | Per-PR locking/queueing, commit-SHA binding, staleness detection | Python + Postgres row lock |
| **Agent Workflow** | Multi-step reasoning state machine (pausable/resumable) | LangGraph |
| **Model Router** | Abstract LLM provider, validate output schema, retry/circuit-break, failover | Plugin-based gateway + JSON schema validator |
| **Policy Gateway** | Mandatory authorization boundary: policy rules + risk score + budget check | OPA (Rego) sidecar |
| **Tool Gateway** | Execute only allowed, capability-scoped actions | Python |
| **Sandbox Runner** | Execute code/tests in isolation with minimal ephemeral credentials | E2B SDK |
| **Approval Queue** | Hold paused runs awaiting a human decision | Postgres table + dashboard polling |
| **Action Ledger** | Append-only record of every intent, decision, and execution result | Postgres (asyncpg) |
| **Dashboard** | Visualize runs, traces, costs; expose approve/reject | React + TypeScript (Vercel) |

---

## The Action Intent Model

The **Action Intent** is the single most important security boundary in AgentGuard. It is the *only* thing that crosses from "agent reasoning" into "the system." The agent **proposes**; the Policy Gateway **decides**; the Tool Gateway **executes**.

```json
{
  "action": "file_write",
  "target": "src/payment.py",
  "operation": "modify",
  "capability": "github.create_commit",
  "reason": "Fix failing payment idempotency test by adding retry guard",
  "run_id": "8f82d1a7-7a2c-401c-89d7-aae6adfdbb84"
}
```

Every intent is schema-validated via Pydantic before it reaches the Policy Gateway. A hallucinated or malformed model output is rejected at this boundary and cannot become an executed action.

The agent also records a structured **Decision Trace** entry alongside every intent:

```json
{
  "decision": "modify_payment_service",
  "evidence": ["CI run #184 (FAILED)", "tests/payment_test.py:42", "src/payment.py:L88"],
  "proposed_action": { "type": "file_write", "path": "src/payment.py" },
  "policy_decision": { "result": "ALLOW", "rule": "src/**", "risk_score": 20 },
  "execution": { "status": "success", "commit_sha": "a3f8c12" }
}
```

---

## Policy Gateway

The Policy Gateway is the single mandatory checkpoint every Action Intent passes through before execution. It combines three sub-engines and **fails closed**: if a policy cannot be evaluated, is missing, times out, or the action is malformed, the default is `DENY` — never silent allow.

### Risk Engine

A deterministic, additive scoring model — no ML required:

| Signal | Score |
|---|---|
| `filesystem_write` | +20 |
| `production_path` — matches `config/prod/**`, `*.env` | +40 |
| `workflow_modification` — `.github/workflows/**` | +30 |
| `force_push` | +50 |
| `network_request` | +10 |
| `secret_access` | +60 |

**Decision thresholds:**

- Score `< 30` → `ALLOW`
- Score `30–69` → `REQUIRE_APPROVAL`
- Score >= `70` → `DENY`

All weights and thresholds live in the per-repo YAML policy file and are tunable without a code change.

### Budget Engine

Per-run limits enforced before each reasoning step:

```yaml
budget:
  max_tokens: 50000      # Total LLM tokens across all calls in this run
  max_cost_usd: 0.50     # Maximum dollar spend per run
  max_llm_calls: 20      # Maximum distinct LLM API calls
```

If a run would exceed its budget, the Budget Engine halts it. The policy layer governs not just *what* the agent can do, but *how much* it can consume.

### Policy File Reference

```yaml
# Per-repository policy — edit live to control agent behavior in real time
agent: pr-fixer
version: 3

capabilities:
  allow:
    - github.read_file
    - github.read_pr
    - github.comment_pr
  approval:
    - github.create_commit     # Requires human sign-off
  deny:
    - github.delete_repository
    - github.admin_repository

filesystem:
  read: ["**"]
  write: ["src/**", "tests/**"]

network:
  allow: [github.com, pypi.org, registry.npmjs.org]

commands:
  allow: [pytest, npm, git, node, python]
  deny:  [rm, curl, ssh, wget, sudo]

resources:
  max_execution_time: 10m
  max_files_touched: 15

risk_weights:
  filesystem_write:       20
  production_path:        40
  workflow_modification:  30
  force_push:             50
  network_request:        10
  secret_access:          60

risk_thresholds:
  allow_below:    30
  approval_below: 70

budget:
  max_tokens:    50000
  max_cost_usd:  0.50
  max_llm_calls: 20

sensitive_actions:
  require_approval:
    - path: "config/prod/**"
    - path: "*.env"
    - path: ".github/workflows/**"
    - command: "git push --force"
```

---

## Data Model

```
runs
  id, repo, pr_number, head_sha, trigger_type,
  status (running | paused | stale | completed | failed),
  started_at, completed_at, total_tokens, total_cost_usd

webhook_deliveries
  id, github_delivery_id UNIQUE, received_at, run_id

run_events
  id, run_id, step_name,
  event_type (decision | action_intent | tool_call | policy_decision),
  content (jsonb), tokens_used, latency_ms, created_at

policy_decisions
  id, run_id, event_id, action_requested, rule_matched,
  risk_score, decision (allow | deny | require_approval),
  policy_version, created_at

approvals
  id, run_id, event_id,
  status (pending | approved | rejected),
  requested_at, decided_at, decided_by, rejection_reason

policies
  id, repo, yaml_content, version, updated_at

provider_health
  id, provider, window_start, request_count, error_count,
  timeout_count, avg_latency_ms
```

The `webhook_deliveries` table's `UNIQUE` constraint on `github_delivery_id` is the entire idempotency implementation — no extra logic needed. The `provider_health` table drives circuit-breaker decisions in the LLM router.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, asyncpg |
| **Agent Workflow** | LangGraph (stateful, pausable LLM state machine) |
| **Policy Engine** | Open Policy Agent (OPA) + Rego, running as a local sidecar |
| **LLM Providers** | Gemini (primary), Groq (fast inference), NVIDIA NIM (fallback) |
| **Database** | Neon Postgres (serverless, free tier) |
| **Sandbox Execution** | E2B (default), GitHub Actions (fallback) |
| **Frontend** | React 18, TypeScript, Vite, Vercel |
| **Containerization** | Docker, Docker Compose |
| **Deployment** | AWS EC2 (backend), Vercel (frontend) |
| **Observability** | OpenTelemetry, structlog (structured JSON logging) |
| **Testing** | pytest, pytest-asyncio, unittest.mock |

---

## Project Structure

```
AgentGuard/
├── .github/
│   └── workflows/
│       └── ci.yml                   # Lint -> type-check -> test -> build
│
├── backend/                         # FastAPI backend (Python)
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory, lifespan, middleware
│   │   ├── container.py             # DI composition root
│   │   ├── config.py                # pydantic-settings: all env vars, validated
│   │   │
│   │   ├── api/                     # HTTP layer — routes only, no business logic
│   │   │   ├── webhooks/router.py   # POST /webhooks/github
│   │   │   ├── runs/router.py       # GET /runs, GET /runs/{id}
│   │   │   ├── approvals/router.py  # POST /approvals/{id}/approve|reject
│   │   │   └── health/router.py     # GET /health
│   │   │
│   │   ├── domain/                  # Domain models — pure Python, no framework deps
│   │   │   ├── models/              # Run, ActionIntent, Approval, PolicyDecision ...
│   │   │   ├── protocols/           # Abstract interfaces (PolicyEvaluator, LLMProvider ...)
│   │   │   └── exceptions.py        # Domain exception hierarchy
│   │   │
│   │   ├── services/                # Business logic — orchestration layer
│   │   │   ├── webhook_service.py
│   │   │   ├── run_coordinator.py
│   │   │   ├── policy_gateway.py
│   │   │   ├── risk_engine.py
│   │   │   ├── budget_engine.py
│   │   │   ├── tool_gateway.py
│   │   │   ├── llm_gateway.py
│   │   │   └── approval_service.py
│   │   │
│   │   ├── agent/                   # LangGraph agent workflow
│   │   │   ├── workflow.py          # State machine definition
│   │   │   └── nodes/               # plan.py, investigate.py, patch.py, verify.py ...
│   │   │
│   │   └── infrastructure/          # Concrete implementations
│   │       ├── database/            # SQLAlchemy ORM + repositories
│   │       ├── github/              # GitHub API client + HMAC validator
│   │       ├── llm/                 # Provider adapters (Gemini, Groq, NVIDIA NIM)
│   │       │   ├── circuit_breaker.py
│   │       │   └── providers/
│   │       ├── policy/              # OPA client + Rego files
│   │       │   └── rego/            # main.rego, capabilities.rego, filesystem.rego ...
│   │       └── sandbox/             # E2B runner + GitHub Actions runner
│   │
│   └── tests/
│       ├── unit/                    # Service-level unit tests (mocked dependencies)
│       └── integration/             # Webhook -> policy -> tool flow tests
│
├── frontend/                        # React dashboard (Vite + TypeScript)
│   ├── src/
│   │   ├── pages/                   # OverviewPage, RunsPage, ApprovalsPage ...
│   │   ├── components/              # MetricCard, StatusBadge, DiffViewer, Modal ...
│   │   ├── services/api.ts          # Typed API client
│   │   └── types/                   # Shared TypeScript types
│   └── vercel.json                  # API reverse-proxy rewrite rules
│
├── policies/                        # Default YAML policy files per repo
│   └── default.yaml
│
└── docker-compose.yml               # Local dev: backend + OPA sidecar
```

---

## Local Setup

### Prerequisites

- Python 3.12+
- Node.js 18+ and npm
- Docker and Docker Compose
- A GitHub account (to create a GitHub App)
- A [Neon Postgres](https://neon.tech) account (free tier)
- An API key for at least one LLM provider: [Gemini](https://aistudio.google.com/app/apikey), [Groq](https://console.groq.com), or [NVIDIA NIM](https://build.nvidia.com)
- An [E2B](https://e2b.dev) API key (free tier, for sandboxed test execution)

### Backend Setup

```bash
# 1. Clone the repository
git clone https://github.com/Yashvij19/AgentGuard.git
cd AgentGuard

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

# 3. Install backend dependencies
cd backend
pip install -e ".[dev]"

# 4. Copy the environment template and fill in your secrets
cp .env.example .env

# 5. Run database migrations
alembic upgrade head

# 6. Start OPA sidecar (separate terminal)
docker run --rm -p 8181:8181 \
  -v $(pwd)/app/infrastructure/policy/rego:/policies:ro \
  openpolicyagent/opa:latest run \
  --server --addr localhost:8181 /policies

# 7. Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Or, using Docker Compose (recommended):**

```bash
docker compose up --build
```

- Backend: `http://localhost:8000`
- OPA sidecar: `http://localhost:8181`
- API docs: `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
# Dashboard: http://localhost:5173
```

Create a `.env.local` file in `frontend/` to point at your local backend:

```env
VITE_API_BASE_URL=http://localhost:8000
```

### GitHub App Setup

1. Go to **GitHub → Settings → Developer Settings → GitHub Apps → New GitHub App**.
2. Set **Webhook URL** to `https://<your-backend-host>/api/webhooks/github`.
3. Set a **Webhook Secret** (save it for `.env`).
4. Grant these **Repository Permissions**:
   - Contents: Read & Write
   - Pull Requests: Read & Write
   - Checks: Read
   - Metadata: Read
5. Subscribe to events: `pull_request`, `check_suite`.
6. Generate and download the **Private Key** (`.pem` file). Save it as `github_key.pem` in the repo root.
7. Note your **App ID** and **Installation ID** and add them to `.env`.

### OPA Setup

```bash
# Verify OPA is running
curl http://localhost:8181/health
# -> {"status":"ok"}

# Test a policy decision
curl -X POST http://localhost:8181/v1/data/agentguard/allow \
  -H "Content-Type: application/json" \
  -d '{"input": {"action": "file_write", "target": "src/main.py", "risk_score": 20}}'
```

---

## Environment Variables

Create a `.env` file in the `backend/` directory. **Never commit this file.**

```env
# Application
APP_ENV=development
LOG_LEVEL=info

# Database (Neon Postgres)
DATABASE_URL=postgresql+asyncpg://user:password@host/agentguard

# GitHub App
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=/app/github_key.pem
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here
GITHUB_INSTALLATION_ID=12345678

# LLM Providers
GEMINI_API_KEY=your-gemini-api-key
GROQ_API_KEY=your-groq-api-key
NVIDIA_NIM_API_KEY=your-nvidia-nim-api-key
PRIMARY_LLM_PROVIDER=gemini
FALLBACK_LLM_PROVIDER=groq

# E2B Sandbox
E2B_API_KEY=your-e2b-api-key
SANDBOX_PROVIDER=e2b

# OPA Sidecar
OPA_URL=http://localhost:8181

# Optional: OpenTelemetry (Grafana Cloud)
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-eu-west-0.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <base64-token>
```

---

## API Reference

Full interactive docs at `/docs` (Swagger UI) and `/redoc`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/webhooks/github` | Receive GitHub webhook events (HMAC-verified) |
| `GET` | `/api/runs` | List all runs (paginated) |
| `GET` | `/api/runs/{run_id}` | Get full run details + decision trace |
| `GET` | `/api/runs/{run_id}/events` | Audit log for a run |
| `GET` | `/api/approvals` | List all pending approval requests |
| `POST` | `/api/approvals/{id}/approve` | Approve a quarantined action |
| `POST` | `/api/approvals/{id}/reject` | Reject a quarantined action |
| `GET` | `/api/stats` | Dashboard metrics (totals, trends, costs) |
| `GET` | `/api/providers/health` | LLM provider health and circuit breaker status |
| `GET` | `/api/analytics/hourly` | Hourly run analytics |
| `GET` | `/api/runs/export.csv` | Export audit ledger as CSV |
| `GET` | `/health` | Container health check |

**Example: Approve an Action**

```bash
curl -X POST https://<backend>/api/approvals/<id>/approve \
  -H "Content-Type: application/json" \
  -d '{"decided_by": "engineer", "comment": "Reviewed patch — idempotency guards confirmed."}'
```

---

## Deployment

### AWS EC2 Backend

```bash
ssh -i github_key.pem ubuntu@<your-ec2-ip>

git clone https://github.com/Yashvij19/AgentGuard.git
cd AgentGuard
cp .env.example .env
# Fill in production secrets

sudo docker build -t agentguard .
sudo docker run -d \
  --restart unless-stopped \
  --name agentguard-backend \
  --env-file .env \
  -e APP_ENV=production \
  -v $(pwd)/github_key.pem:/app/github_key.pem:ro \
  -p 8000:8000 \
  agentguard

sudo docker logs -f agentguard-backend
```

**To update after a code change:**

```bash
sudo docker stop agentguard-backend && sudo docker rm agentguard-backend
git pull origin main
sudo docker build -t agentguard .
sudo docker run -d --restart unless-stopped --name agentguard-backend \
  --env-file .env -e APP_ENV=production \
  -v $(pwd)/github_key.pem:/app/github_key.pem:ro \
  -p 8000:8000 agentguard
```

### Vercel Frontend

```bash
cd frontend
npx vercel --prod
```

Set the environment variable `VITE_API_BASE_URL` to your EC2 backend URL in the Vercel project settings. The `frontend/vercel.json` already contains reverse-proxy rewrite rules routing `/api/*` to the backend, enabling HTTPS termination at Vercel's edge.

---

## Use Cases and Demo Workflow

### Primary Use Case: Automated PR Review and CI Fix

1. Developer opens a PR with a failing test.
2. AgentGuard receives the webhook, verifies it, and starts a governed run.
3. The LangGraph agent investigates the CI failure, reads relevant files, and proposes a code patch.
4. The agent's `file_write` Intent targeting `config/prod/settings.py` scores **risk 60 → REQUIRE_APPROVAL**.
5. The dashboard shows the quarantined action with the proposed diff, risk score, and decision trace.
6. The human **rejects** it with feedback. The agent adapts and re-proposes a narrower patch to `src/` (risk 20 → ALLOW).
7. The patch is executed, tests pass in the E2B sandbox, and the fix is committed to the PR branch.
8. The Action Ledger records the full run: `$0.09 cost`, `38 seconds`, `3 policy decisions`, `1 human intervention`.

### Interview Demo Script

1. Open a PR with a deliberately broken test on the connected demo repo.
2. Show the dashboard: a new run appears with a live decision trace streaming in.
3. The agent's Intent proposes writing to `config/prod/settings.py`. Policy Gateway returns `REQUIRE_APPROVAL`. The run pauses and the approval UI shows the intent plus diff.
4. Reject it. Watch the agent adapt and re-propose a narrower action scoped to `src/`.
5. Approve. Watch it verify in the sandbox and push a comment with the working patch.
6. Pull up the Action Ledger: "Here's every action this run took, the rule behind each decision, and what it cost — $0.09, 45 seconds."
7. Kill the primary LLM provider's API key live. Show the circuit breaker trip and automatic failover mid-run.
8. Trigger a duplicate webhook delivery manually. Show it's silently dropped by the delivery-ID idempotency check.

---

## Security Model

| Control | Implementation |
|---|---|
| **HMAC Webhook Verification** | Every incoming event is signature-verified before processing |
| **Delivery-ID Idempotency** | Duplicate deliveries dropped via unique DB constraint |
| **Action Intent Boundary** | The agent never holds credentials or calls external APIs directly |
| **Policy Fails Closed** | Unavailable policy, malformed action, timeout → `DENY` — never silent allow |
| **LLM Output Validation** | Every model response schema-validated; hallucinated tool calls rejected |
| **Least-Privilege Capabilities** | GitHub App permissions (coarse-grained) and internal capability model (fine-grained) are separate layers |
| **Commit-SHA Binding** | Runs bound to a specific commit SHA; PR head changes mid-run → stale, halted |
| **Sandboxed Execution** | Code execution in ephemeral E2B sandboxes; no access to production secrets or host filesystem |
| **Concurrent Approval Guard** | PostgreSQL row-level locking on approval state transitions; prevents duplicate commits |
| **Audit Trail** | Every approval records who decided and when; Action Ledger is append-only |
| **Rate Limiting** | Webhook endpoint rate-limited to prevent abuse |

---

## Roadmap

### v1.0 — Complete

- [x] GitHub App webhook integration (HMAC + idempotency)
- [x] LangGraph agent workflow (Plan → Investigate → Reproduce → Patch → Verify → Report)
- [x] Action Intent model + Policy Gateway (OPA Rego + Risk Engine + Budget Engine)
- [x] Tool Gateway with named capability model
- [x] E2B sandboxed test execution
- [x] Human-in-the-loop dual-custody approval queue
- [x] Action Ledger + Decision Trace persistence (Neon Postgres)
- [x] Plugin-based LLM router (Gemini, Groq, NVIDIA NIM) with circuit breaker + failover
- [x] Governance Dashboard (React + Vercel)
- [x] Production deployment (AWS EC2 + Docker)

### v2.0 — Planned

- [ ] **Policy Simulation** — replay historical Action Ledger entries against a proposed new policy version and report the delta impact before activating
- [ ] **Policy Replay** — reconstruct a completed run's event/action sequence from the ledger for debugging
- [ ] **What-If Policy Testing** — "What happens if I allow the agent to modify `.github/workflows/**`?" shown as a before/after impact report
- [ ] **Controlled Fault Injection** — trigger LLM timeouts, 429s, and sandbox failures in a demo environment to validate the retry/circuit-breaker recovery path live

### Future

- Multi-repo, multi-agent governance (multi-tenant policies)
- Prometheus metrics endpoint + Grafana dashboard templates
- Slack / Discord / webhook notification integrations

---

## Contributing

Contributions are welcome. This project follows a clean architecture and strict coding standards — please read before submitting PRs.

### Engineering Standards

| Area | Rule |
|---|---|
| **Architecture** | Dependency Injection through constructor injection. No instantiating collaborators inside classes. |
| **Interfaces** | Define an ABC/Protocol first, then implement. Example: `PolicyEvaluator` → `OPAPolicyEvaluator`. |
| **Fail Closed** | All authorization checks default to `DENY` on error, missing config, or unknown input. |
| **Type Hints** | Every function signature and variable must have type hints. `mypy --strict` must pass. |
| **Pydantic Models** | All external data (webhook payloads, LLM outputs, Action Intents) must be validated via Pydantic. |
| **Structured Logging** | Use `structlog` with JSON output. Every log line includes `run_id`, `step`, `action`. No `print()`. |
| **Test Coverage** | Unit tests for all services; integration tests for the webhook → policy → tool flow. |
| **Commits** | Follow Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`. |

```bash
# Fork and clone
git clone https://github.com/<your-username>/AgentGuard.git

# Create a feature branch
git checkout -b feature/your-feature-name

# Run tests
cd backend
pytest tests/unit/ -v
pytest tests/integration/ -v

# Lint and type-check
ruff check .
mypy app/ --strict

# Submit a PR against main
```

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built by [Yash Vijay](https://github.com/Yashvij19) &nbsp;·&nbsp; [Live Demo](https://agent-guard-red.vercel.app) &nbsp;·&nbsp; [GitHub](https://github.com/Yashvij19/AgentGuard)

</div>
