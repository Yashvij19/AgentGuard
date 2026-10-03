"""
Report node: compiles governance audit summary and posts PR comment strictly through ToolGateway.
"""

from typing import Any

from app.agent.prompts.review_prompts import REPORT_PROMPT_TEMPLATE
from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy_decision import Decision
from app.domain.protocols.github_client import GitHubClient
from app.services.policy_gateway import PolicyGateway
from app.services.tool_gateway import ToolGateway


async def report_node(
    state: AgentState,
    github_client: GitHubClient | None = None,
    policy_gateway: PolicyGateway | None = None,
    tool_gateway: ToolGateway | None = None,
) -> dict[str, Any]:
    """
    Format a complete audit summary of all action intents and post to GitHub via ToolGateway.
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
    is_paused = state.get("paused", False)
    pause_reason = state.get("pause_reason", "")
    if is_paused:
        status_str = f"PAUSED (Awaiting Human Approval: {pause_reason})"
    elif is_halted:
        status_str = f"HALTED ({halt_reason})"
    else:
        status_str = "COMPLETED"

    summary_lines = [
        f"Automated PR review and governance audit completed for **{len(changed_files)} changed files**.",
        f"**Run Status**: `{status_str}`",
        f"**Governed Action Intents**: `{len(intents)} total` ({allowed_count} Allowed, {approval_count} Approval Required, {denied_count} Denied)",
        f"**Patch Status**: `{'Proposed' if state.get('patch') else 'None'}` | **Verified**: `{'Yes' if state.get('verified') else 'No'}`",
    ]
    if is_paused:
        summary_lines.append(
            f"⏸️ **Action Paused**: Review required via `/api/approvals/{state.get('pending_approval_id', '')}`"
        )
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
        metadata={
            "pr_number": pr_number,
            "comment_preview": comment_body[:200],
            "body": comment_body,
        },
    )
    intents.append(comment_intent.model_dump(mode="json"))

    # 3. Evaluate Policy Gateway for Commenting
    post_allowed = True
    if policy_gateway:
        verdict = await policy_gateway.evaluate_intent(comment_intent, repo)
        decisions.append(verdict.model_dump(mode="json"))
        post_allowed = verdict.decision == Decision.ALLOW

    # 4. Post comment strictly via ToolGateway (or fallback to github_client)
    comment_id: int | None = None
    if post_allowed:
        if tool_gateway:
            exec_res = await tool_gateway.execute(comment_intent, repo=repo)
            if exec_res.success and isinstance(exec_res.output, dict):
                comment_id = exec_res.output.get("comment_id")
        elif github_client:
            comment_id = await github_client.post_comment(repo, pr_number, comment_body)

    return {
        "summary_report": comment_body,
        "comment_id": comment_id,
        "action_intents": intents,
        "policy_decisions": decisions,
    }
