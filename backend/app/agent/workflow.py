"""
LangGraph workflow definition for AgentGuard Phase 1.
Assembles the 3-node graph: Plan -> Investigate -> Report.
"""

from collections.abc import Awaitable, Callable
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from app.agent.nodes.investigate import investigate_node
from app.agent.nodes.plan import plan_node
from app.agent.nodes.report import report_node
from app.agent.state import AgentState
from app.domain.models.run import Run
from app.domain.models.run_event import EventType, RunEvent
from app.domain.protocols.github_client import GitHubClient
from app.infrastructure.database.repositories.event_repository import EventRepository


def create_phase1_graph(github_client: GitHubClient) -> Any:
    """
    Assemble and compile the Phase 1 LangGraph StateGraph.
    """
    graph = StateGraph(cast(Any, AgentState))

    # Wrap nodes with injected dependencies
    async def _plan(state: AgentState) -> dict[str, Any]:
        return await plan_node(state, github_client)

    async def _investigate(state: AgentState) -> dict[str, Any]:
        return await investigate_node(state, github_client)

    async def _report(state: AgentState) -> dict[str, Any]:
        return await report_node(state, github_client)

    # Add Nodes
    graph.add_node("plan", _plan)
    graph.add_node("investigate", _investigate)
    graph.add_node("report", _report)

    # Add Edges (Linear pipeline for Phase 1)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "investigate")
    graph.add_edge("investigate", "report")
    graph.add_edge("report", END)

    return graph.compile()


def create_agent_runner(
    github_client: GitHubClient,
    event_repository: EventRepository,
) -> Callable[[Run], Awaitable[None]]:
    """
    Factory creating an agent runner callable suitable for RunCoordinator.
    Executes the compiled LangGraph workflow and records audit events for each step.
    """
    compiled_app = create_phase1_graph(github_client)

    async def runner(run: Run) -> None:
        initial_state: AgentState = {
            "run_id": run.id,
            "repo": run.repo,
            "pr_number": run.pr_number,
            "head_sha": run.head_sha,
            "changed_files": [],
            "error": None,
        }

        # Log agent startup event
        await event_repository.append(
            RunEvent(
                run_id=run.id,
                step_name="agent_workflow",
                event_type=EventType.DECISION,
                content={"message": "LangGraph workflow execution started"},
            )
        )

        # Execute LangGraph
        result_state = await compiled_app.ainvoke(initial_state)

        # Log completion event
        await event_repository.append(
            RunEvent(
                run_id=run.id,
                step_name="report",
                event_type=EventType.TOOL_CALL,
                content={
                    "message": "Analysis comment posted to GitHub",
                    "comment_id": result_state.get("comment_id"),
                },
            )
        )

    return runner
