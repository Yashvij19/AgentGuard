"""
LangGraph workflow definition for AgentGuard Phase 2.
Assembles the 6-node state graph:
Plan -> Investigate -> Reproduce -> Patch -> Verify -> Report
All steps flow through PolicyGateway before execution.
"""

from collections.abc import Awaitable, Callable
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from app.agent.nodes.investigate import investigate_node
from app.agent.nodes.patch import patch_node
from app.agent.nodes.plan import plan_node
from app.agent.nodes.report import report_node
from app.agent.nodes.reproduce import reproduce_node
from app.agent.nodes.verify import verify_node
from app.agent.state import AgentState
from app.domain.models.run import Run
from app.domain.models.run_event import EventType, RunEvent
from app.domain.protocols.github_client import GitHubClient
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.services.policy_gateway import PolicyGateway


def create_phase2_graph(
    github_client: GitHubClient,
    policy_gateway: PolicyGateway | None = None,
) -> Any:
    """
    Assemble and compile the Phase 2 6-node governed LangGraph StateGraph.
    """
    graph = StateGraph(cast(Any, AgentState))

    # Node execution wrappers
    async def _plan(state: AgentState) -> dict[str, Any]:
        return await plan_node(state, github_client, policy_gateway)

    async def _investigate(state: AgentState) -> dict[str, Any]:
        return await investigate_node(state, github_client, policy_gateway)

    async def _reproduce(state: AgentState) -> dict[str, Any]:
        return await reproduce_node(state, policy_gateway)

    async def _patch(state: AgentState) -> dict[str, Any]:
        return await patch_node(state, policy_gateway)

    async def _verify(state: AgentState) -> dict[str, Any]:
        return await verify_node(state, policy_gateway)

    async def _report(state: AgentState) -> dict[str, Any]:
        return await report_node(state, github_client, policy_gateway)

    # Register Nodes
    graph.add_node("plan", _plan)
    graph.add_node("investigate", _investigate)
    graph.add_node("reproduce", _reproduce)
    graph.add_node("patch", _patch)
    graph.add_node("verify", _verify)
    graph.add_node("report", _report)

    # Conditional router: if halted by policy denial/pause, skip to report
    def _router(state: AgentState) -> str:
        return "report" if state.get("halted") else "continue"

    # Connect Edges
    graph.add_edge(START, "plan")

    graph.add_conditional_edges(
        "plan",
        _router,
        {"continue": "investigate", "report": "report"},
    )
    graph.add_conditional_edges(
        "investigate",
        _router,
        {"continue": "reproduce", "report": "report"},
    )
    graph.add_conditional_edges(
        "reproduce",
        _router,
        {"continue": "patch", "report": "report"},
    )
    graph.add_conditional_edges(
        "patch",
        _router,
        {"continue": "verify", "report": "report"},
    )
    graph.add_edge("verify", "report")
    graph.add_edge("report", END)

    return graph.compile()


# Maintain backwards compatibility for Phase 1 references
create_phase1_graph = create_phase2_graph


def create_agent_runner(
    github_client: GitHubClient,
    event_repository: EventRepository,
    policy_gateway: PolicyGateway | None = None,
) -> Callable[[Run], Awaitable[None]]:
    """
    Factory creating an agent runner callable suitable for RunCoordinator.
    Executes the governed 6-node LangGraph workflow and records audit traces.
    """
    compiled_app = create_phase2_graph(github_client, policy_gateway)

    async def runner(run: Run) -> None:
        initial_state: AgentState = {
            "run_id": run.id,
            "repo": run.repo,
            "pr_number": run.pr_number,
            "head_sha": run.head_sha,
            "changed_files": [],
            "action_intents": [],
            "policy_decisions": [],
            "decision_traces": [],
            "halted": False,
            "error": None,
        }

        # Log agent startup audit event
        await event_repository.append(
            RunEvent(
                run_id=run.id,
                step_name="agent_workflow",
                event_type=EventType.DECISION,
                content={"message": "Phase 2 Governed LangGraph workflow started"},
            )
        )

        # Execute LangGraph
        result_state = await compiled_app.ainvoke(initial_state)

        # Log completion audit event
        await event_repository.append(
            RunEvent(
                run_id=run.id,
                step_name="report",
                event_type=EventType.TOOL_CALL,
                content={
                    "message": "Governed workflow completed",
                    "comment_id": result_state.get("comment_id"),
                    "halted": result_state.get("halted", False),
                    "intents_evaluated": len(result_state.get("action_intents", [])),
                },
            )
        )

    return runner
