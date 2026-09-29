"""
Unit tests for deterministic RiskEngine scoring, path pattern matching,
destructive command heuristics, and metadata factor evaluations.
"""

from app.domain.models.action_intent import ActionType
from app.domain.models.policy_decision import Decision
from app.services.risk_engine import RiskEngine
from tests.factories import create_test_action_intent, create_test_policy


def test_standard_read_action_allows() -> None:
    engine = RiskEngine()
    policy = create_test_policy()
    intent = create_test_action_intent(
        action=ActionType.FILE_READ,
        target="src/utils.py",
        operation="read",
    )

    assessment = engine.evaluate(intent, policy)
    assert assessment.score == 0
    assert assessment.decision == Decision.ALLOW
    assert "Standard operation" in assessment.reason


def test_production_path_triggers_approval() -> None:
    engine = RiskEngine()
    policy = create_test_policy()
    intent = create_test_action_intent(
        action=ActionType.FILE_WRITE,
        target="config/prod/database.yaml",
        operation="modify",
    )

    # Base write (20) + prod path (40) = 60 >= require_approval (50)
    assessment = engine.evaluate(intent, policy)
    assert assessment.score == 60
    assert assessment.decision == Decision.REQUIRE_APPROVAL
    assert any("Production path target match" in f for f in assessment.factors)


def test_workflow_modification_triggers_approval() -> None:
    engine = RiskEngine()
    policy = create_test_policy()
    intent = create_test_action_intent(
        action=ActionType.FILE_WRITE,
        target=".github/workflows/deploy.yml",
        operation="modify",
    )

    # Base write (20) + workflow mod (30) = 50 >= require_approval (50)
    assessment = engine.evaluate(intent, policy)
    assert assessment.score == 50
    assert assessment.decision == Decision.REQUIRE_APPROVAL
    assert any("CI/CD workflow" in f for f in assessment.factors)


def test_secret_target_inspection_triggers_approval() -> None:
    engine = RiskEngine()
    policy = create_test_policy()
    intent = create_test_action_intent(
        action=ActionType.FILE_READ,
        target="credentials.env",
        operation="read",
    )

    # Base read (0) + secret access (60) = 60 >= require_approval (50)
    assessment = engine.evaluate(intent, policy)
    assert assessment.score == 60
    assert assessment.decision == Decision.REQUIRE_APPROVAL


def test_destructive_command_triggers_deny() -> None:
    engine = RiskEngine()
    policy = create_test_policy()
    intent = create_test_action_intent(
        action=ActionType.COMMAND_EXEC,
        target="rm -rf /var/cache",
        operation="exec",
    )

    # Command (25) + destructive command (60) = 85 >= deny (80)
    assessment = engine.evaluate(intent, policy)
    assert assessment.score == 85
    assert assessment.decision == Decision.DENY
    assert any("Destructive shell command" in f for f in assessment.factors)


def test_metadata_force_push_increases_score() -> None:
    engine = RiskEngine()
    policy = create_test_policy()
    intent = create_test_action_intent(
        action=ActionType.FILE_WRITE,
        target="src/main.py",
        metadata={"force_push": True},
    )

    # Base write (20) + force push (50) = 70 >= require_approval (50)
    assessment = engine.evaluate(intent, policy)
    assert assessment.score == 70
    assert assessment.decision == Decision.REQUIRE_APPROVAL
    assert any("Force-push" in f for f in assessment.factors)


def test_score_clamps_at_100() -> None:
    engine = RiskEngine()
    policy = create_test_policy()
    intent = create_test_action_intent(
        action=ActionType.COMMAND_EXEC,
        target="rm -rf config/prod/database.yaml",
        metadata={"force_push": True, "elevated_privileges": True},
    )

    assessment = engine.evaluate(intent, policy)
    assert assessment.score == 100
    assert assessment.decision == Decision.DENY
