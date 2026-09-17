"""
Report node: compiles governance audit summary and proposes GITHUB_API / comment_pr intent.
"""

from typing import Any

from app.agent.prompts.review_prompts import REPORT_PROMPT_TEMPLATE
from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy_decision import Decision
from app.domain.protocols.github_client import GitHubClient
from app.services.policy_gateway import PolicyGateway


async def report_node(
    state: AgentState,
    github_client: GitHubClient,
    policy_gateway: PolicyGateway | None = None,
) -> dict[str, Any]:
    """
    Format a complete audit summary of all action intents and post to GitHub if permitted.
    """
    repo = state["repo"]
    pr_number = state["pr_number"]
    head_sha = state["head_sha"]
    run_id = state["run_id"]
    changed_files = state.get("changed_files", [])

    intents = list(state.get("action_intents", []))
    decisions = list(state.get("policy_decisions", []))
    is_halted = state.get("halted", False)
    halt_reason = state.get("halt_reason", "")

    # 1. Compile Executive Summary with Governance Audit
    allowed_count = sum(1 for d in decisions if d.get("decision") == "ALLOW")
    approval_count = sum(1 for d in decisions if d.get("decision") == "REQUIRE_APPROVAL")
    denied_count = sum(1 for d in decisions if d.get("decision") == "DENY")

    status_str = f"HALTED ({halt_reason})" if is_halted else "COMPLETED"

    summary_lines = [
        f"Automated PR review and governance audit completed for **{len(changed_files)} changed files**.",
        f"**Run Status**: `{status_str}`",
        f"**Governed Action Intents**: `{len(intents)} total` ({allowed_count} Allowed, {approval_count} Approval Required, {denied_count} Denied)",
        f"**Patch Status**: `{'Proposed' if state.get('patch') else 'None'}` | **Verified**: `{'Yes' if state.get('verified') else 'No'}`",
    ]
    summary = "\n".join(summary_lines)
    findings = state.get("investigation", "No findings available.")

    comment_body = REPORT_PROMPT_TEMPLATE.format(
        repo=repo,
        pr_number=pr_number,
        head_sha=head_sha[:8],
        summary=summary,
        findings=findings[:800],
    )

    # 2. Propose GITHUB_API intent to post comment
    comment_intent = ActionIntent(
        run_id=run_id,
        action=ActionType.GITHUB_API,
        target=f"pull_requests/{pr_number}/comments",
        operation="comment",
        capability="github.comment_pr",
        reason="Post governance audit summary and review findings on PR",
        metadata={"comment_preview": comment_body[:200]},
    )
    intents.append(comment_intent.model_dump(mode="json"))

    # 3. Evaluate Policy Gateway for Commenting
    post_allowed = True
    if policy_gateway:
        verdict = await policy_gateway.evaluate_intent(comment_intent, repo)
        decisions.append(verdict.model_dump(mode="json"))
        post_allowed = verdict.decision == Decision.ALLOW

    # 4. Post comment only if explicitly allowed by policy
    comment_id: int | None = None
    if post_allowed:
        comment_id = await github_client.post_comment(repo, pr_number, comment_body)

    return {
        "summary_report": comment_body,
        "comment_id": comment_id,
        "action_intents": intents,
        "policy_decisions": decisions,
    }
