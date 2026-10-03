# AgentGuard
## Governance & Execution Control for Autonomous Coding Agents
### Software Development Document — v2.0

*(v2.0 changelog: repositioned around a governance/control layer; added Action Intent, Policy Gateway, Risk Engine, Tool Gateway, Action Ledger, policy versioning, webhook idempotency, concurrency locking, commit-SHA binding, and model-output validation. See Section 14 for the full change rationale.)*

---

## 1. Project Overview

**AgentGuard** is a governance and execution-control layer for autonomous coding agents. It ships with one concrete, end-to-end use case — reviewing and fixing GitHub pull requests / failing CI runs — but the architecture is deliberately generic: nothing in the core system is PR-specific.

The agent never executes anything directly. Every proposed action — read a file, run a command, write a patch, call an API — is converted into an explicit **Action Intent**, evaluated by a **Policy Gateway** (policy rules + risk scoring + budget limits), and only then dispatched to a tool. High-risk actions pause for human approval. Every decision — allowed, denied, or escalated — is recorded in an **Action Ledger**, alongside token cost, latency, and outcome.

**One-line pitch:** *"A governance and execution-control layer that lets an AI agent safely act on a real codebase — every action goes through policy, risk, and budget checks before it runs, with human approval gates and full observability, built entirely on free-tier infrastructure."*

### 1.1 Why this project

| Requirement | How AgentGuard satisfies it |
|---|---|
| Single developer, limited time | One well-scoped use case (PR review/fix) on top of a reusable control layer, not a platform |
| No local heavy compute (no Ollama) | All inference via hosted LLM APIs |
| No budget for server infra | Every component maps to a real free tier (Section 9) |
| Must be actually deployed | Live public URL, not "runs on my laptop" |
| Must show senior-level thinking | Explicit authorization boundary, risk-based governance, audit trails, human-in-the-loop, observability, resilient model routing |

### 1.2 The story in one paragraph

> "I built AgentGuard, a governance and execution-control layer for autonomous coding agents. The agent investigates CI failures and proposes patches, but it never directly controls the environment — every proposed action becomes an explicit Action Intent, evaluated by a Policy Gateway that combines declarative rules, a risk score, and a cost budget before anything executes. High-risk actions require human approval, every decision is recorded in an auditable Action Ledger, and the whole system is instrumented with OpenTelemetry — all running on free-tier infrastructure."

---

## 2. Problem Statement

Autonomous coding agents are increasingly given real permissions — to read code, run commands, call APIs, and push changes. Five problems come up the moment you do this for real:

1. **Unrestricted blast radius** — an agent with shell/file access can do damage (delete files, leak secrets, push to `main`) if nothing constrains it.
2. **No accountability** — when an agent does something wrong, there's often no record of *why* it decided to do it, or which rule allowed it.
3. **No intervention point** — most agent demos are fully autonomous; there's no seam where a human can step in before something risky happens.
4. **No cost/performance visibility** — teams running agents in production have no idea what a given task cost in tokens/$, or how often the agent actually succeeds.
5. **No safety net around the LLM itself** — a hallucinated or malformed "tool call" from the model can become an executed action if nothing validates it first.

AgentGuard directly solves all five, demonstrated end-to-end through one concrete workflow: **safely automating PR review and CI-failure fixes.**

---

## 3. Goals & Non-Goals

### Goals (v1)
- Agent analyzes a failing CI run or open PR and proposes a fix
- Every proposed action is an explicit **Action Intent**, evaluated by the **Policy Gateway** before anything executes
- Risky actions pause for human approval via a simple UI
- Full **Decision Trace** of agent reasoning, actions, and policy/risk decisions, viewable per run
- Token usage and cost tracked per run, with budget limits enforced
- Runs on 100% free-tier infrastructure, publicly deployed
- Model-agnostic: swappable LLM backend with validated output and automatic failover
- Webhooks are idempotent; runs are bound to a specific commit and safely serialized per PR

### Non-Goals (explicitly out of scope for v1)
- Multi-tenant / multi-org support
- Kubernetes, service mesh, custom container runtimes
- Self-hosted sandboxing infrastructure (kernel-level isolation, gVisor, custom microVMs)
- Building a custom sandbox at all — use existing managed/ephemeral execution primitives
- Supporting arbitrary repos at scale (v1 targets a small number of connected repos)
- A full agent marketplace / plugin ecosystem
- Multiple specialized agents (planner/coder/reviewer/etc.) — one workflow, one state machine
- A vector database / RAG — the agent's context is the PR diff, CI logs, and repo files it reads directly, which is sufficient for this use case
- Policy Simulation, Replay, "what-if" analysis, fault injection — real, valuable features, but deliberately deferred to Phase 2 (Section 12) so v1 stays finishable solo
- Agent "Digital Twin" simulation — noted only as a long-term, speculative idea (Section 12.3), not designed or scheduled

These non-goals matter: they're what keeps this buildable solo, and they're honest things to say in an interview ("here's what I deliberately didn't build yet, and why").

---

## 4. Core Features

### 4.1 GitHub Integration
- Webhook listener for `pull_request` and `check_suite` (CI failure) events
- Every webhook carries a GitHub **delivery ID**; duplicate deliveries are detected and ignored (idempotency — see 4.8)
- Reads PR diff, CI logs, repo file tree via GitHub API
- Posts results back as a PR comment + status check

### 4.2 Agent Workflow
- LangGraph-based state machine: `Plan → Investigate → Reproduce → Patch → Verify → Report`
- Each node proposes **Action Intents** (see 4.3) rather than calling tools directly
- Each node also emits a **Decision Trace** entry — decision, supporting evidence, proposed action, policy outcome, execution result (see 4.4)
- Model-agnostic LLM client with validated output, configurable primary/fallback provider (see 4.7)

### 4.3 Action Intent (core architectural concept)
The agent never calls a tool directly. Instead it emits a structured intent:

```json
{
  "action": "file_write",
  "target": "src/payment.py",
  "operation": "modify",
  "reason": "Fix failing payment test"
}
```

This intent is the **only** thing that crosses from "agent reasoning" into "the system." It is the seam where authorization happens — the agent proposes, the Policy Gateway decides, the Tool Gateway executes. This separation ("what the AI wants to do" vs. "what the system permits it to do") is the single most important security boundary in the system.

### 4.4 Decision Trace
Rather than persisting the model's raw chain-of-thought, AgentGuard records structured **decision evidence** for every step:

```json
{
  "decision": "modify_payment_service",
  "evidence": ["CI run #184", "tests/payment_test.py:42", "src/payment.py"],
  "proposed_action": { "type": "file_write", "path": "src/payment.py" },
  "policy_decision": { "result": "ALLOW", "rule": "src/**" },
  "execution": { "status": "success" }
}
```

This is more useful for debugging and auditing than free-form reasoning text, and it avoids depending on / exposing a model's private chain-of-thought.

### 4.5 Policy Gateway (the core differentiator)
The single mandatory checkpoint every Action Intent passes through before execution. It combines three sub-engines:

- **Policy Engine** — declarative YAML rules per repo (filesystem, network, commands, capabilities — see Section 8)
- **Risk Engine** — a deterministic score per action (see 4.5.1)
- **Budget Engine** — enforces per-run token/cost/call limits (see 4.5.2)

Every evaluation returns one of: `ALLOW`, `DENY`, `REQUIRE_APPROVAL` — and **fails closed**: if a policy can't be evaluated, is missing, times out, or the action is malformed or unrecognized, the default is `DENY` (or `REQUIRE_APPROVAL` for ambiguous-but-plausible cases), never silent allow.

#### 4.5.1 Risk Engine
A simple, deterministic additive score — no ML model needed:

```
filesystem write         +20
production path          +40
workflow file modified   +30
force push                +50
network request            +10
secret access              +60
```

Thresholds map to a decision, e.g. `< 30 → ALLOW`, `30–69 → REQUIRE_APPROVAL`, `≥ 70 → DENY`. The scoring weights live in the same policy file as everything else, so they're tunable without a code change.

#### 4.5.2 Budget Engine
Enforced per repo/run via the policy file:

```yaml
budget:
  max_tokens: 50000
  max_cost_usd: 0.50
  max_llm_calls: 20
```

If a run would exceed its budget, the Budget Engine halts it — the policy layer governs not just *what* the agent can do, but *how much* it can consume.

### 4.6 Tool Gateway & Capability Model
The agent (and even the Policy Gateway's `ALLOW` decisions) never hold a raw GitHub token or shell. Every allowed action is dispatched through a **Tool Gateway** that exposes named **capabilities**, not raw APIs:

```yaml
capabilities:
  allow:
    - github.read_file
    - github.read_pr
    - github.comment_pr
  approval:
    - github.create_commit
  deny:
    - github.delete_repository
```

This keeps GitHub App permissions (external, coarse-grained) and Agent permissions (internal, fine-grained) as two separate layers — least-privilege at both.

### 4.7 Model Router (LLM abstraction, validation, and resilience)
- `ModelRouter` abstracts the LLM provider behind a single interface (primary + fallback, e.g. Gemini free tier → a different provider's free tier)
- **Output validation**: every LLM response is schema-validated before it's allowed to become an Action Intent — a malformed or hallucinated "tool call" is rejected here, before it ever reaches the Policy Gateway
- **Retry with backoff + circuit breaker**: transient failures (timeouts, 429s) are retried with backoff; a sustained failure rate trips a circuit breaker and routes to the fallback provider, tracked per-provider (latency, error rate, timeout count)

### 4.8 Webhook Idempotency & Concurrency Control
- Every incoming webhook's GitHub delivery ID is checked against a unique DB constraint; duplicates are ignored, not reprocessed
- Runs are serialized per (repo, PR): if a new commit lands on a PR while a run is in progress, the new event is queued rather than started concurrently, avoiding two runs patching against different versions of the same PR
- Every run is explicitly bound to the **head commit SHA** at the time it started; if the PR's head SHA changes mid-run, the run is marked stale and either restarted or halted — it never applies a patch computed against outdated code

### 4.9 Human-in-the-Loop Approval
- When the Policy Gateway returns `REQUIRE_APPROVAL`, the run pauses
- Reviewer sees the proposed Action Intent, the decision trace entry behind it, and a diff (if applicable)
- Approve → action executes via the Tool Gateway and the run resumes; Reject → run halts, and the agent may adapt and re-propose a narrower action

### 4.10 Isolated Execution
- Verification steps (running tests, executing generated code) happen in a short-lived, disposable sandbox — never on the host running your backend
- v1: ephemeral GitHub Actions runner triggered by the backend, or a free-tier code-execution sandbox (e.g. E2B free tier)
- The sandbox receives **only the minimum, scoped, ephemeral credentials** needed for that specific operation — never production secrets, never the host filesystem, and is bounded by CPU/memory/time/process limits

### 4.11 Action Ledger & Observability
- Every Action Intent, policy decision, and execution result is written to an append-only **Action Ledger** (Postgres) — answering, for any run: *"what exactly did this agent do, and why was each action allowed?"*
- Every LLM call, tool call, and policy decision is also emitted as an OpenTelemetry span
- Dashboard shows: live run status, the full decision trace (timeline view), token usage & estimated cost per run, and success/failure rate over time
- Each run records the **policy version** it was evaluated against, so a decision made months ago remains explainable even after the policy changes

---

## 5. System Architecture

### 5.1 High-Level Diagram

```
                         GitHub
                           │
                     Webhook Event
                           │
                           ▼
                  ┌──────────────────┐
                  │ Webhook Gateway  │
                  │ HMAC signature + │
                  │ delivery-id      │
                  │ idempotency check│
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Run Coordinator  │
                  │ per-PR lock/queue│
                  │ commit-SHA bind  │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Agent Workflow   │
                  │   (LangGraph)    │
                  │ Plan→Investigate │
                  │ →Reproduce→Patch │
                  │ →Verify→Report   │
                  └────────┬─────────┘
                           │
                     Action Intent
                           │
                           ▼
                  ┌──────────────────┐
                  │  Policy Gateway  │
                  │  Policy Engine   │
                  │  Risk Engine     │
                  │  Budget Engine   │
                  └────────┬─────────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
           ALLOW      REQUIRE_APPROVAL   DENY
             │             │             │
             │             ▼             │
             │      Human Approval UI    │
             │             │             │
             └──────┬──────┘             │
                    ▼                    │
           ┌──────────────────┐         │
           │  Tool Gateway    │         │
           │ (capability model)│        │
           └────────┬─────────┘         │
                     │                   │
        ┌────────────┼────────────┐     │
        ▼            ▼            ▼     │
      GitHub      Sandbox     Model    │
      capability   Runner     Router   │
      calls        (E2B/      (LLM API │
                    GH Actions) + failover)│
        │            │            │     │
        └────────────┼────────────┘     │
                      ▼                  │
              ┌──────────────────┐       │
              │  Action Ledger   │◀──────┘
              │  + Decision Trace│
              │  (Postgres)      │
              └────────┬─────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Observability   │
              │  OTel → Grafana  │
              │  Cloud (free)    │
              └──────────────────┘

              ┌──────────────────┐
              │  Dashboard (UI)  │
              │  Vercel/Netlify  │
              │  – live traces,  │
              │  approve/reject  │
              └──────────────────┘
              (reads Action Ledger + run state via backend API)
```

### 5.2 Request Flow (a single run, end to end)

1. Developer opens a PR, or CI fails → GitHub sends a webhook.
2. **Webhook Gateway** verifies the HMAC signature and checks the delivery ID against the idempotency table; duplicates are dropped.
3. **Run Coordinator** checks for an in-progress run on the same (repo, PR); if one exists, the event is queued. Otherwise it creates a `Run` bound to the current head commit SHA.
4. **Agent Workflow** (LangGraph) executes its state machine. At each step needing an action, it emits an **Action Intent** plus a **Decision Trace** entry (reasoning evidence, not raw chain-of-thought).
5. Every Action Intent goes to the **Policy Gateway**: Policy Engine checks rules, Risk Engine scores it, Budget Engine checks remaining budget → returns `ALLOW` / `DENY` / `REQUIRE_APPROVAL`.
6. `ALLOW` → dispatched to the **Tool Gateway**, which executes via the named capability (GitHub API, Sandbox Runner, etc.) with least-privilege, scoped credentials.
   `REQUIRE_APPROVAL` → run pauses; a human sees the intent + decision trace in the dashboard and approves/rejects.
   `DENY` → the agent is informed and must adapt (propose a narrower action) or the run halts.
7. If the PR's head SHA changes mid-run, the **Run Coordinator** marks the run stale and restarts/halts it rather than continuing against outdated code.
8. Every step's Action Intent, policy decision, and execution result is appended to the **Action Ledger**, and emitted as an OpenTelemetry span.
9. **Dashboard** reads run state and the ledger to render the live trace and expose approve/reject controls.

### 5.3 Component Responsibilities

| Component | Responsibility | Tech |
|---|---|---|
| Webhook Gateway | Verify signature, enforce idempotency | FastAPI route + unique DB constraint |
| Run Coordinator | Per-PR locking/queueing, commit-SHA binding, staleness detection | Python + Postgres row lock |
| Agent Workflow | Own the multi-step reasoning workflow, hold state, allow pause/resume | LangGraph |
| Model Router | Abstract LLM provider, validate output schema, retry/circuit-break, failover | Thin Python wrapper (LiteLLM or hand-rolled) + a JSON-schema validator |
| Policy Gateway | Mandatory authorization boundary: policy rules + risk score + budget check | OPA (Rego) or a small custom rules evaluator |
| Tool Gateway | Execute only allowed, capability-scoped actions | Python |
| Sandbox Runner | Execute code/tests in isolation, minimal ephemeral credentials | E2B SDK, or dispatch to a GitHub Actions workflow |
| Approval Queue | Hold paused runs awaiting a human decision | Postgres table + dashboard polling |
| Action Ledger | Append-only record of every intent, decision, and result | Postgres |
| Dashboard | Visualize runs, decision traces, cost; expose approve/reject | React (Vite) |
| Observability | Collect traces/metrics for every run | OpenTelemetry SDK → Grafana Cloud |

---

## 6. Data Model (core tables)

```
runs
  id, repo, pr_number, head_sha, trigger_type, status (running/paused/stale/completed/failed),
  started_at, completed_at, total_tokens, total_cost_usd

webhook_deliveries
  id, github_delivery_id UNIQUE, received_at, run_id

run_events
  id, run_id, step_name, event_type (decision/action_intent/tool_call/policy_decision),
  content (jsonb), tokens_used, latency_ms, created_at

policy_decisions
  id, run_id, event_id, action_requested, rule_matched, risk_score,
  decision (allow/deny/require_approval), policy_version, created_at

approvals
  id, run_id, event_id, status (pending/approved/rejected),
  requested_at, decided_at, decided_by

policies
  id, repo, yaml_content, version, updated_at

provider_health
  id, provider, window_start, request_count, error_count, timeout_count, avg_latency_ms
```

`webhook_deliveries` and `provider_health` are new versus v1.0 — they exist specifically to support idempotency (4.8) and circuit-breaker decisions (4.7).

---

## 7. Policy File — Concrete Example

```yaml
# policy for repo: myorg/myrepo
agent: pr-fixer
version: 3

capabilities:
  allow:
    - github.read_file
    - github.read_pr
    - github.comment_pr
  approval:
    - github.create_commit
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
  deny: [rm, curl, ssh, wget, sudo]

resources:
  max_execution_time: 10m
  max_files_touched: 15

risk_weights:
  filesystem_write: 20
  production_path: 40
  workflow_modification: 30
  force_push: 50
  network_request: 10
  secret_access: 60

risk_thresholds:
  allow_below: 30
  approval_below: 70   # 30–69 → REQUIRE_APPROVAL, 70+ → DENY

budget:
  max_tokens: 50000
  max_cost_usd: 0.50
  max_llm_calls: 20

sensitive_actions:
  require_approval:
    - path: "config/prod/**"
    - path: "*.env"
    - path: ".github/workflows/**"
    - command: "git push --force"
```

This file is intentionally editable live in a demo — changing one line (e.g. a risk weight or an allow-list entry) and re-running shows the agent get blocked or gated in real time, which is a strong interview moment.

---

## 8. The $0 Technology Stack

| Layer | Component | Free Tier Used |
|---|---|---|
| LLM Inference | Gemini API / Claude / OpenAI | Provider free tiers (rotate as needed) |
| Orchestration | LangGraph | Open-source, self-hosted in your backend |
| Policy Gateway | OPA (Rego) or custom evaluator + risk/budget logic | Open-source, runs in-process |
| Backend hosting | FastAPI app | Render / Fly.io / Railway free tier |
| Database | PostgreSQL | Supabase or Neon free tier |
| Sandbox execution | E2B (agent code sandboxes) | Free tier, or GitHub Actions (2,000 free min/mo) |
| Frontend/dashboard | React app | Vercel / Netlify free tier |
| Observability | OpenTelemetry → Grafana Cloud | Grafana Cloud free tier (metrics/logs/traces) |
| CI trigger source | GitHub | Free for public/small private repos |
| Secrets | Provider's built-in env var storage | Free (Render/Fly.io secrets) |
| Retry/circuit-breaker | `tenacity` or hand-rolled | Open-source library, zero infra cost |

**Total infra cost: $0/month** at demo scale. The only variable cost is LLM API usage if you exceed a provider's free tier — mitigated by the Model Router's failover across multiple providers' free tiers, and bounded by the Budget Engine per run.

---

## 9. Deployment Architecture

```
GitHub Repo ──(webhook)──▶ Render/Fly.io (FastAPI backend)
                                   │
                                   ├──▶ Supabase/Neon Postgres (managed, free)
                                   ├──▶ LLM Provider APIs (Gemini/Claude/OpenAI)
                                   ├──▶ E2B sandbox API / GitHub Actions dispatch
                                   └──▶ Grafana Cloud (OTel export)

Vercel/Netlify (React dashboard) ──(reads via API)──▶ Render/Fly.io backend
```

- **Backend**: containerized FastAPI app, deployed via Render's or Fly.io's free web-service tier (auto-sleep on idle is fine for a portfolio project — mention this honestly as a known trade-off, and how you'd fix it with a paid always-on tier).
- **Database**: managed Postgres, free tier — no self-hosting, no backups to manage yourself.
- **Frontend**: static React build on Vercel/Netlify, calling the backend's API.
- **Secrets** (GitHub App private key, LLM API keys): stored as encrypted environment variables in the hosting platform, never committed.
- **CI/CD for AgentGuard itself**: GitHub Actions running tests + auto-deploy to Render/Fly.io on push to `main`.

---

## 10. Security Considerations

- GitHub webhook signature verification (HMAC) **and** delivery-ID idempotency on every incoming event
- Least-privilege GitHub App permissions (only repo contents + PR write, not full org access) — separate from the finer-grained internal capability model (4.6)
- The Policy Gateway **fails closed** everywhere: unavailable policy, malformed action, unknown command, timeout, or unrecognized file path all resolve to `DENY` or `REQUIRE_APPROVAL`, never silent allow
- LLM output is schema-validated before it can become an Action Intent — a hallucinated or malformed tool call is rejected before reaching the Policy Gateway, not after
- Sandbox execution has no access to production secrets, no host filesystem access, and is bounded by CPU/memory/time/process limits — only a scoped, ephemeral token per operation
- Runs are bound to a specific commit SHA to avoid acting on stale code (TOCTOU-style issue)
- All approval actions are logged with who approved/rejected and when (audit trail)
- Rate limiting on the webhook endpoint to prevent abuse
- Because the agent reads arbitrary repository content (including PR-submitted code), treat file/log contents as **untrusted input** — the Action Intent + Policy Gateway boundary exists precisely so that content the agent reads can never itself become an executable action without passing authorization

---

## 11. Build Roadmap

| Phase | Weeks | Deliverable |
|---|---|---|
| 1 | 1–2 | Webhook Gateway (signature + idempotency) + Run Coordinator (commit-SHA binding, per-PR lock) + a LangGraph agent that reads a PR diff and posts a comment (no execution yet) |
| 2 | 3–4 | Action Intent model + Policy Gateway v1 (policy rules + fail-closed default) wired into every tool call |
| 3 | 5–6 | Tool Gateway with capability model; Sandbox execution (test running) + Verify step; Model Router with output validation, retry/circuit-breaker, and failover |
| 4 | 7 | Risk Engine + Budget Engine added to the Policy Gateway; Human approval flow (pause/resume, approval queue, dashboard approve/reject UI) |
| 5 | 8 | Action Ledger + Decision Trace persistence; Observability (OpenTelemetry instrumentation, Grafana dashboards, cost tracking); policy versioning recorded per decision |
| 6 | 9 | Polish: live policy-editing demo, README, architecture diagram, deployed public demo |

Each phase ends with something demoable — you're never more than two weeks from having a working story to show. Notice the ordering matches the review's advice: get the core loop (webhook → agent → Policy Gateway → tool → ledger) working end-to-end *before* adding risk scoring, budgets, or approval UI polish.

---

## 12. Phase 2 and Beyond (deliberately deferred)

These are good ideas, all implementable for free — they're deferred purely to keep v1 finishable solo. Build them only once the core loop (Section 11, Phases 1–5) is stable and demoable.

### 12.1 Phase 2 — Differentiators
- **Policy Simulation**: before activating a new policy version, replay it against historical Action Ledger entries and report the impact ("72 additional actions would now require approval") — turns the Policy Gateway from a static rule-checker into a governance tool
- **Replay**: reconstruct a completed run's event/action sequence from the ledger for debugging; full deterministic replay isn't possible (LLMs aren't deterministic), but the recorded sequence is still reproducible and inspectable, optionally re-running from a checkpoint
- **"What-if" policy testing**: extension of Policy Simulation — "what happens if I allow the agent to modify `.github/workflows/*`?" — shown as a before/after impact report

### 12.2 Phase 3 — Advanced / demo polish
- **Controlled fault injection**: deliberately trigger LLM timeouts, 429s, sandbox timeouts, or GitHub API failures in a demo environment to show the retry/circuit-breaker/fallback path recovering live — a stronger resilience demo than just showing a happy path
- A Kubernetes-based execution backend — **only if** the project outgrows free-tier ephemeral sandboxes, which is not expected for a portfolio-scale demo

### 12.3 Explicitly not designed (long-term idea only)
- **Agent "Digital Twin"** — simulating an agent's actions against a shadow/staging environment before allowing production execution. Flagged here only as a direction worth mentioning if asked "where would this go next," not something to spend design or build time on now.

---

## 13. Interview Demo Script

1. Open a PR on a demo repo with a deliberately broken test.
2. Show the dashboard: a new run appears, live decision trace streaming in — "Investigate → Reproduce → Patch."
3. The agent's Action Intent proposes writing to `config/prod/settings.py` — the Policy Gateway scores it as high-risk and returns `REQUIRE_APPROVAL`; the run pauses and the approval UI shows the intent + decision trace.
4. Reject it. Show the agent adapt and re-propose a narrower, lower-risk action scoped to `src/`.
5. Approve. Watch it verify in the sandbox (via the Tool Gateway, with scoped credentials) and push a comment with the working patch.
6. Pull up the Action Ledger: "Here's every action this run took, the rule or risk score behind each decision, and what it cost — $0.09, 45 seconds."
7. Kill the primary LLM provider's API key live → show the circuit breaker trip and automatic failover to the secondary provider mid-run, with output validation confirming the fallback's response before it's trusted.
8. (If time allows) Trigger a duplicate webhook delivery manually → show it's ignored, and push a second commit mid-run → show the run marked stale and safely restarted against the new head SHA.

That's a compelling few-minute demo that shows reasoning, governance, risk-based authorization, human oversight, resilience, cost awareness, and production-grade correctness handling (idempotency, concurrency, staleness) — exactly what a senior/staff interview is probing for.

---

## 14. Change Rationale (v1.0 → v2.0)

This revision incorporates an architectural review, filtered against the project's real constraints (solo developer, free-tier infra, must actually be deployed). The filter used:

- **Kept everything that's a software/architecture change with zero infra cost** — Action Intent, Policy Gateway, Decision Trace, fail-closed, webhook idempotency, concurrency locking, commit-SHA binding, Tool Gateway/capabilities, Risk Engine, Action Ledger, policy versioning, budgets, output validation, and circuit breaker. None of these require new servers, paid services, or heavier compute — they're better-organized code and data models.
- **Deferred (not dropped) the good-but-time-expensive features** — Policy Simulation, Replay, What-if analysis, and fault injection are free to build but add real solo-developer time; they're sequenced into Phase 2/3 rather than v1, per the review's own recommendation not to implement everything at once.
- **Reduced to a one-line future note** — Agent Digital Twin, since it's speculative and not concretely specified enough to design against yet.
- **Confirmed exclusions, unchanged** — Kubernetes, a custom sandbox, a multi-agent swarm, and a vector database all remain out of scope; nothing in the review argued for reversing these, and reversing any of them would break the free-tier / solo-developer constraints this project is built around.

---

## 15. What This Demonstrates (for your resume bullet)

> Built and deployed a governance and execution-control layer for autonomous coding agents, featuring an explicit action-authorization boundary (Action Intent → Policy Gateway), risk-based and budget-aware authorization, human-in-the-loop approval gates, an auditable action ledger, and resilient multi-provider LLM routing with output validation — architected entirely on free-tier cloud infrastructure.

That sentence covers: security/authZ architecture, risk-based governance, distributed-systems correctness (idempotency, concurrency, staleness handling), observability, and pragmatic infra judgment — the exact "senior engineer who can also do AI" signal you're after.
