"""
Prompt templates for Phase 1 agent review steps.
"""

PLAN_PROMPT_TEMPLATE = """
You are an expert autonomous code security and QA reviewer.
Analyze the following Pull Request details and generate a structured review plan.

Repository: {repo}
PR Number: #{pr_number}
Changed Files ({file_count} total):
{file_list}

Diff Preview:
{diff_preview}

Formulate a concise review plan covering:
1. Primary objective of this PR.
2. High-risk areas (database schema, authentication, concurrency, external APIs).
3. Specific verification points to investigate.
"""

INVESTIGATE_PROMPT_TEMPLATE = """
Based on the following PR Diff and Review Plan, perform a deep technical investigation.

Review Plan:
{plan}

Full PR Diff:
{pr_diff}

Analyze:
- Potential regressions or breaking changes.
- Unhandled edge cases or missing null checks.
- Code quality, type safety, and test coverage implications.
"""

REPORT_PROMPT_TEMPLATE = """
### 🛡️ AgentGuard Governance Review

**Target**: `{repo}#{pr_number}` | **Commit**: `{head_sha}`
**Status**: `ANALYSIS_COMPLETE` (Phase 1 Baseline)

---

#### 📋 Executive Summary
{summary}

#### 🔍 Investigation Findings
{findings}

#### 📌 Verification Checklist
- [x] Webhook cryptographically verified & delivery recorded
- [x] Per-PR concurrency lock acquired
- [x] Commit-SHA staleness validated
- [x] Automated static review generated

> *AgentGuard Phase 1 — Autonomous Governance & Execution Layer*
"""
