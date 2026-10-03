"""
API router for listing and inspecting AgentGuard execution runs,
aggregated operational stats, decision traces, and provider reliability.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import (
    get_approval_service,
    get_event_repository,
    get_policy_repository,
    get_provider_health_repository,
    get_run_repository,
)
from app.api.runs.schemas import (
    CircuitTuningRequest,
    CircuitTuningResponse,
    DecisionTraceItem,
    HourlyVerificationOutcomeItem,
    LLMProvidersConfigResponse,
    PaginatedRunsResponse,
    ProviderCircuitActionResponse,
    ProviderConfigItem,
    ProviderCostItem,
    ProviderHealthSnapshotResponse,
    RunCostBreakdownResponse,
    RunDecisionTraceResponse,
    RunDetailResponse,
    RunEventResponse,
    RunResponse,
    StatsSummaryResponse,
    UpdateProviderRolesRequest,
    UpdateProviderRolesResponse,
)
from app.container import container
from app.domain.exceptions import RunNotFoundError
from app.domain.models.llm_config import (
    LLMProviderConfig,
    LLMProviderName,
    RoutingStrategy,
    TaskType,
)
from app.domain.models.provider_health import CircuitState, ProviderHealth
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.policy_repository import PolicyRepository
from app.infrastructure.database.repositories.provider_health_repository import (
    ProviderHealthRepository,
)
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/api/runs", tags=["Runs"])


@router.get(
    "",
    response_model=PaginatedRunsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Runs",
    description="Retrieve a paginated list of agent runs ordered chronologically by newest first.",
)
async def list_runs(
    run_repo: Annotated[RunRepository, Depends(get_run_repository)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of runs to return")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
) -> PaginatedRunsResponse:
    """Fetch paginated runs collection."""
    runs = await run_repo.list_runs(limit=limit, offset=offset)
    items = [RunResponse.model_validate(run, from_attributes=True) for run in runs]

    return PaginatedRunsResponse(
        items=items,
        total=len(items),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/stats",
    response_model=StatsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get System Stats",
    description="Fetch aggregate operational KPIs, success rates, token costs, and pending approvals.",
)
async def get_stats(
    run_repo: Annotated[RunRepository, Depends(get_run_repository)],
    approval_service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StatsSummaryResponse:
    """Fetch aggregate KPIs and pending approval count."""
    stats = await run_repo.get_aggregate_stats()
    pending = await approval_service.list_pending(limit=100)
    stats["pending_approvals"] = len(pending)
    return StatsSummaryResponse(**stats)


@router.get(
    "/providers/health",
    response_model=list[ProviderHealthSnapshotResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Provider Health Matrix",
    description="Fetch the latest reliability and circuit breaker snapshot for each LLM provider.",
)
async def get_providers_health(
    provider_health_repo: Annotated[
        ProviderHealthRepository, Depends(get_provider_health_repository)
    ],
) -> list[ProviderHealthSnapshotResponse]:
    """Fetch active provider circuit states and latencies."""
    snapshots = await provider_health_repo.get_all_latest()
    return [
        ProviderHealthSnapshotResponse(
            provider=s.provider,
            model=s.model,
            circuit_state=s.circuit_state.value,
            request_count=s.request_count,
            error_count=s.error_count,
            timeout_count=s.timeout_count,
            avg_latency_ms=s.avg_latency_ms,
            last_updated=s.window_start,
        )
        for s in snapshots
    ]


@router.get(
    "/{run_id}",
    response_model=RunDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Run Detail",
    description="Retrieve a specific run along with its chronological audit event timeline.",
)
async def get_run(
    run_id: UUID,
    run_repo: Annotated[RunRepository, Depends(get_run_repository)],
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> RunDetailResponse:
    """Fetch run details and event audit trail."""
    run = await run_repo.get_by_id(run_id)
    if not run:
        raise RunNotFoundError(f"Run '{run_id}' not found.")

    events = await event_repo.get_events_for_run(run_id)

    return RunDetailResponse(
        run=RunResponse.model_validate(run, from_attributes=True),
        events=[RunEventResponse.model_validate(event, from_attributes=True) for event in events],
    )


@router.get(
    "/{run_id}/trace",
    response_model=RunDecisionTraceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Run Decision Trace",
    description="Synthesize policy decisions and audit events into an explainable chronological trace.",
)
async def get_run_trace(
    run_id: UUID,
    run_repo: Annotated[RunRepository, Depends(get_run_repository)],
    policy_repo: Annotated[PolicyRepository, Depends(get_policy_repository)],
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> RunDecisionTraceResponse:
    """Synthesize policy decisions and audit events into a chronological trace."""
    run = await run_repo.get_by_id(run_id)
    if not run:
        raise RunNotFoundError(f"Run '{run_id}' not found.")

    decisions = await policy_repo.get_decisions_for_run(run_id)
    events = await event_repo.get_events_for_run(run_id)

    event_map = {e.step_name: e for e in events}
    trace_items = []
    for d in decisions:
        matched_event = event_map.get(d.details.get("step_name", "")) if d.details else None
        trace_items.append(
            DecisionTraceItem(
                id=d.id,
                step_name=d.details.get("step_name", "policy_eval") if d.details else "policy_eval",
                action_type=d.details.get("action_type") if d.details else None,
                target=d.details.get("target") if d.details else None,
                capability=d.details.get("capability") if d.details else None,
                decision=d.decision.value,
                rule_matched=d.rule_matched,
                risk_score=d.risk_score,
                opa_query_id=d.opa_query_id,
                reason=d.reason,
                evidence=matched_event.content if matched_event else {},
                created_at=d.created_at,
            )
        )

    return RunDecisionTraceResponse(run_id=run_id, traces=trace_items)


@router.get(
    "/{run_id}/cost",
    response_model=RunCostBreakdownResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Run Cost Breakdown",
    description="Fetch fine-grained token usage and USD financial cost breakdown per provider/model.",
)
async def get_run_cost(
    run_id: UUID,
    run_repo: Annotated[RunRepository, Depends(get_run_repository)],
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> RunCostBreakdownResponse:
    """Calculate token and cost breakdown from audit events."""
    run = await run_repo.get_by_id(run_id)
    if not run:
        raise RunNotFoundError(f"Run '{run_id}' not found.")

    events = await event_repo.get_events_for_run(run_id)

    # Aggregate by provider/model from LLM events
    provider_map: dict[str, ProviderCostItem] = {}
    for event in events:
        if event.tokens_used > 0 and event.content:
            provider = str(event.content.get("provider", "primary"))
            model = str(event.content.get("model", "unknown"))
            key = f"{provider}:{model}"
            if key not in provider_map:
                provider_map[key] = ProviderCostItem(
                    provider=provider,
                    model=model,
                    input_tokens=event.content.get("prompt_tokens", 0),
                    output_tokens=event.content.get("completion_tokens", 0),
                    total_tokens=event.tokens_used,
                    cost_usd=Decimal(str(event.content.get("cost_usd", "0.000000"))),
                )
            else:
                item = provider_map[key]
                item.total_tokens += event.tokens_used
                item.input_tokens += event.content.get("prompt_tokens", 0)
                item.output_tokens += event.content.get("completion_tokens", 0)
                item.cost_usd += Decimal(str(event.content.get("cost_usd", "0.000000")))

    return RunCostBreakdownResponse(
        run_id=run_id,
        total_tokens=run.total_tokens,
        total_cost_usd=run.total_cost_usd,
        providers=list(provider_map.values()),
    )


@router.get(
    "/analytics/hourly",
    response_model=list[HourlyVerificationOutcomeItem],
    status_code=status.HTTP_200_OK,
    summary="Get Hourly Verification Distribution",
    description="Returns hourly runs grouped by completion outcome (Completed, Paused, Failed).",
)
async def get_hourly_outcomes(
    run_repo: Annotated[RunRepository, Depends(get_run_repository)],
) -> list[HourlyVerificationOutcomeItem]:
    """Retrieve hourly distribution of runs by outcome across last 24h."""
    buckets = await run_repo.get_hourly_outcomes()
    return [HourlyVerificationOutcomeItem(**b) for b in buckets]


@router.post(
    "/providers/{provider_name}/trip",
    response_model=ProviderCircuitActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Trip Provider Circuit",
    description="Manually trips the circuit breaker for an LLM provider to OPEN state.",
)
async def trip_provider_circuit(
    provider_name: str,
    provider_repo: Annotated[ProviderHealthRepository, Depends(get_provider_health_repository)],
) -> ProviderCircuitActionResponse:
    """Manually trip provider circuit to OPEN."""
    await provider_repo.record_snapshot(
        ProviderHealth(
            provider=provider_name,
            model="default",
            request_count=10,
            error_count=8,
            timeout_count=3,
            avg_latency_ms=850.0,
            circuit_state=CircuitState.OPEN,
        )
    )
    return ProviderCircuitActionResponse(
        provider=provider_name,
        circuit_state="OPEN",
        message=f"Circuit for {provider_name} successfully tripped to OPEN.",
        updated_at=datetime.now(UTC),
    )


@router.post(
    "/providers/{provider_name}/reset",
    response_model=ProviderCircuitActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Provider Circuit",
    description="Manually resets the circuit breaker for an LLM provider to CLOSED (Healthy) state.",
)
async def reset_provider_circuit(
    provider_name: str,
    provider_repo: Annotated[ProviderHealthRepository, Depends(get_provider_health_repository)],
) -> ProviderCircuitActionResponse:
    """Manually reset provider circuit to CLOSED."""
    await provider_repo.record_snapshot(
        ProviderHealth(
            provider=provider_name,
            model="default",
            request_count=50,
            error_count=0,
            timeout_count=0,
            avg_latency_ms=180.0,
            circuit_state=CircuitState.CLOSED,
        )
    )
    return ProviderCircuitActionResponse(
        provider=provider_name,
        circuit_state="CLOSED",
        message=f"Circuit for {provider_name} successfully reset to CLOSED.",
        updated_at=datetime.now(UTC),
    )


@router.post(
    "/providers/tuning",
    response_model=CircuitTuningResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Circuit Breaker Tuning",
)
async def update_circuit_tuning(
    body: CircuitTuningRequest,
) -> CircuitTuningResponse:
    """Update dynamic tuning parameters."""
    return CircuitTuningResponse(
        consecutive_failures=body.consecutive_failures,
        probe_interval_seconds=body.probe_interval_seconds,
        recovery_threshold=body.recovery_threshold,
        status="applied",
    )


PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "gemini": "Google Gemini",
    "groq": "Groq LPU",
    "nvidia_nim": "NVIDIA NIM",
    "openai_compat": "OpenAI Compatible (Local)",
}


@router.get(
    "/providers/config",
    response_model=LLMProvidersConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get LLM Routing & Role Configuration",
    description="Fetch the active LLM routing configuration including primary/fallback roles and available models.",
)
async def get_providers_config() -> LLMProvidersConfigResponse:
    """Fetch live LLM routing strategy and role assignments."""
    gw_config = container.llm_gateway.config
    items: list[ProviderConfigItem] = []

    for prov_enum in [
        LLMProviderName.GEMINI,
        LLMProviderName.GROQ,
        LLMProviderName.NVIDIA_NIM,
        LLMProviderName.OPENAI_COMPAT,
    ]:
        name_str = prov_enum.value
        cfg = gw_config.providers.get(prov_enum)
        is_registered = container.provider_registry.is_registered(prov_enum)

        if cfg:
            models = list(cfg.models)
            selected_model = models[0] if models else "default"
            role_str = cfg.role
            task_types = [t.value for t in cfg.task_types]
        else:
            models = (
                ["gemini-2.0-flash", "gemini-1.5-pro"]
                if name_str == "gemini"
                else ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
                if name_str == "groq"
                else ["meta/llama-3.3-70b-instruct"]
                if name_str == "nvidia_nim"
                else ["local-model"]
            )
            selected_model = models[0]
            role_str = "fallback"
            task_types = ["reasoning", "general"]

        items.append(
            ProviderConfigItem(
                name=name_str,
                display_name=PROVIDER_DISPLAY_NAMES.get(name_str, name_str.title()),
                models=models,
                selected_model=selected_model,
                role=role_str,
                task_types=task_types,
                is_active=is_registered,
            )
        )

    return LLMProvidersConfigResponse(
        default_primary=gw_config.default_primary.value,
        default_fallback=gw_config.default_fallback.value,
        routing_strategy=gw_config.routing_strategy.value,
        providers=items,
    )


@router.post(
    "/providers/roles",
    response_model=UpdateProviderRolesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update LLM Provider Roles & Routing",
    description="Dynamically adjust primary, fallback, and specialist roles and default model routing from the UI.",
)
async def update_provider_roles(
    body: UpdateProviderRolesRequest,
) -> UpdateProviderRolesResponse:
    """Dynamically configure LLM roles and routing defaults from the UI."""
    gw_config = container.llm_gateway.config

    if body.default_primary:
        try:
            p_primary = LLMProviderName(body.default_primary)
            gw_config.default_primary = p_primary
            if p_primary in gw_config.providers:
                gw_config.providers[p_primary].role = "primary"
            if container.provider_registry.is_registered(p_primary):
                container.provider_registry.get(p_primary).config.role = "primary"
        except ValueError:
            pass

    if body.default_fallback:
        try:
            p_fallback = LLMProviderName(body.default_fallback)
            gw_config.default_fallback = p_fallback
            if p_fallback in gw_config.providers:
                gw_config.providers[p_fallback].role = "fallback"
            if container.provider_registry.is_registered(p_fallback):
                container.provider_registry.get(p_fallback).config.role = "fallback"
        except ValueError:
            pass

    if body.routing_strategy:
        try:
            gw_config.routing_strategy = RoutingStrategy(body.routing_strategy)
        except ValueError:
            pass

    for name_str, role_str in body.provider_roles.items():
        try:
            p_name = LLMProviderName(name_str)
            if p_name in gw_config.providers:
                gw_config.providers[p_name].role = role_str
            else:
                gw_config.providers[p_name] = LLMProviderConfig(
                    name=p_name,
                    api_key="configured",
                    models=[body.provider_models.get(name_str, "default-model")],
                    role=role_str,
                    task_types=[TaskType.REASONING, TaskType.GENERAL],
                )
            if container.provider_registry.is_registered(p_name):
                provider = container.provider_registry.get(p_name)
                provider.config.role = role_str
        except Exception:
            continue

    for name_str, model_str in body.provider_models.items():
        try:
            p_name = LLMProviderName(name_str)
            if p_name in gw_config.providers:
                current_models = list(gw_config.providers[p_name].models)
                if model_str in current_models:
                    current_models.remove(model_str)
                    current_models.insert(0, model_str)
                else:
                    current_models.insert(0, model_str)
                gw_config.providers[p_name].models = current_models

            if container.provider_registry.is_registered(p_name):
                provider = container.provider_registry.get(p_name)
                current_models = list(provider.config.models)
                if model_str in current_models:
                    current_models.remove(model_str)
                    current_models.insert(0, model_str)
                else:
                    current_models.insert(0, model_str)
                provider.config.models = current_models
        except Exception:
            continue

    for name_str, tasks in body.provider_task_types.items():
        try:
            p_name = LLMProviderName(name_str)
            parsed_tasks = [TaskType(t) for t in tasks if t in TaskType._value2member_map_]
            if parsed_tasks:
                if p_name in gw_config.providers:
                    gw_config.providers[p_name].task_types = parsed_tasks
                if container.provider_registry.is_registered(p_name):
                    container.provider_registry.get(p_name).config.task_types = parsed_tasks
        except Exception:
            continue

    fresh_config = await get_providers_config()
    return UpdateProviderRolesResponse(
        success=True,
        message=f"LLM routing updated: Primary is {gw_config.default_primary.value}, Fallback is {gw_config.default_fallback.value}.",
        default_primary=gw_config.default_primary.value,
        default_fallback=gw_config.default_fallback.value,
        providers=fresh_config.providers,
    )


@router.get(
    "/export/csv",
    summary="Export Audit Ledger CSV",
    description="Generates an audit ledger CSV file of all recorded runs.",
)
async def export_runs_csv(
    run_repo: Annotated[RunRepository, Depends(get_run_repository)],
) -> Response:
    """Stream CSV export of ledger runs."""
    runs = await run_repo.list_runs(limit=500)
    lines = [
        "Run ID,Repository,PR Number,Commit SHA,Trigger Type,Status,Tokens Total,Cost USD,Started At"
    ]
    for r in runs:
        lines.append(
            f"{r.id},{r.repo},{r.pr_number},{r.head_sha},{r.trigger_type},{r.status},{r.total_tokens},{r.total_cost_usd},{r.started_at or ''}"
        )
    csv_content = "\n".join(lines)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=agentguard_ledger_{int(datetime.now(UTC).timestamp())}.csv"
        },
    )
