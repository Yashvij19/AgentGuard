"""
Run Coordinator service: manages per-PR concurrency locks, commit-SHA binding,
and execution lifecycle transitions.
"""

import hashlib
import struct
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import ConcurrentRunError, RunNotFoundError, StaleRunError
from app.domain.models.run import Run, RunStatus, TriggerType
from app.domain.models.run_event import EventType, RunEvent
from app.domain.protocols.github_client import GitHubClient
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.run_repository import RunRepository


class RunCoordinator:
    """
    Coordinates run execution by serializing per-PR operations using PostgreSQL
    advisory locks and preventing execution against stale commits.
    """

    def __init__(
        self,
        session: AsyncSession,
        run_repository: RunRepository,
        event_repository: EventRepository,
        github_client: GitHubClient,
        agent_runner: Callable[[Run], Awaitable[None]] | None = None,
    ) -> None:
        self._session = session
        self._run_repo = run_repository
        self._event_repo = event_repository
        self._github_client = github_client
        self._agent_runner = agent_runner

    @staticmethod
    def generate_lock_key(repo: str, pr_number: int) -> int:
        """
        Generate a deterministic signed 64-bit integer from repo and PR number.
        Do NOT use Python's builtin hash() as it is randomly salted per process.
        """
        raw_key = f"{repo.strip().lower()}#{pr_number}".encode()
        digest = hashlib.sha256(raw_key).digest()[:8]
        # Unpack as signed 64-bit integer (-2^63 to 2^63 - 1) for Postgres bigint
        return int(struct.unpack(">q", digest)[0])

    async def acquire_pr_lock(self, repo: str, pr_number: int) -> bool:
        """
        Attempt to acquire a PostgreSQL transaction-scoped advisory lock for this PR.
        Automatically released when the session transaction commits or aborts.
        """
        lock_id = self.generate_lock_key(repo, pr_number)
        stmt = text("SELECT pg_try_advisory_xact_lock(:lock_id)")
        result = await self._session.execute(stmt, {"lock_id": lock_id})
        acquired = result.scalar()
        return bool(acquired)

    async def create_run(
        self,
        repo: str,
        pr_number: int,
        head_sha: str,
        trigger_type: TriggerType = TriggerType.PULL_REQUEST,
    ) -> Run:
        """
        Initialize and persist a new Run in QUEUED status.
        Logs an initial decision event in the audit trail.
        """
        run = Run(
            repo=repo,
            pr_number=pr_number,
            head_sha=head_sha,
            trigger_type=trigger_type,
            status=RunStatus.QUEUED,
        )
        created_run = await self._run_repo.create(run)

        # Log initial event in append-only audit trail
        event = RunEvent(
            run_id=created_run.id,
            step_name="coordinator",
            event_type=EventType.DECISION,
            content={
                "message": "Run queued by coordinator",
                "repo": repo,
                "pr_number": pr_number,
                "head_sha": head_sha,
            },
        )
        await self._event_repo.append(event)
        return created_run

    async def execute_run(self, run_id: UUID) -> Run:
        """
        Execute a run with strict concurrency locking and staleness verification.
        """
        run = await self._run_repo.get_by_id(run_id)
        if not run:
            raise RunNotFoundError(f"Run '{run_id}' does not exist.")

        # 1. Enforce Per-PR Concurrency Lock
        has_lock = await self.acquire_pr_lock(run.repo, run.pr_number)
        if not has_lock:
            raise ConcurrentRunError(
                f"PR {run.repo}#{run.pr_number} is currently locked by another active run."
            )

        # 2. Enforce Commit-SHA Staleness Check
        latest_sha = await self._github_client.get_latest_pr_sha(run.repo, run.pr_number)
        if latest_sha != run.head_sha:
            await self._run_repo.mark_stale(run.id)
            await self._event_repo.append(
                RunEvent(
                    run_id=run.id,
                    step_name="coordinator",
                    event_type=EventType.DECISION,
                    content={
                        "message": "Run marked stale. New commit detected on PR.",
                        "expected_sha": run.head_sha,
                        "current_sha": latest_sha,
                    },
                )
            )
            raise StaleRunError(
                f"Run commit {run.head_sha} is stale. PR head is currently at {latest_sha}."
            )

        # 3. Transition to RUNNING
        run = await self._run_repo.update_status(
            run_id=run.id,
            status=RunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

        # 4. Invoke Agent Workflow (if configured)
        if self._agent_runner:
            try:
                await self._agent_runner(run)
                run = await self._run_repo.update_status(
                    run_id=run.id,
                    status=RunStatus.COMPLETED,
                    completed_at=datetime.now(UTC),
                )
            except Exception as err:
                await self._run_repo.update_status(
                    run_id=run.id,
                    status=RunStatus.FAILED,
                    completed_at=datetime.now(UTC),
                )
                await self._event_repo.append(
                    RunEvent(
                        run_id=run.id,
                        step_name="coordinator",
                        event_type=EventType.DECISION,
                        content={"error": str(err)},
                    )
                )
                raise

        return run
