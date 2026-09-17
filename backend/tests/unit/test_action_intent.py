"""
Unit tests for ActionIntent domain models and ActionIntentBuilder.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.models.action_intent import ActionIntent, ActionIntentBuilder, ActionType
from tests.factories import create_test_action_intent


def test_action_intent_creation_valid() -> None:
    """Valid ActionIntent must initialize with expected fields."""
    run_id = uuid4()
    intent = create_test_action_intent(
        run_id=run_id,
        action=ActionType.FILE_READ,
        target="src/auth.py",
        operation="read",
        capability="github.read_file",
    )
    assert intent.run_id == run_id
    assert intent.action == ActionType.FILE_READ
    assert intent.target == "src/auth.py"
    assert intent.operation == "read"
    assert intent.capability == "github.read_file"


def test_action_intent_is_immutable() -> None:
    """ActionIntent is frozen and must reject in-place attribute mutations."""
    intent = create_test_action_intent()
    with pytest.raises(ValidationError):
        # Type checker knows it's frozen; runtime raises ValidationError
        intent.target = "malicious_path"  # type: ignore[misc]



def test_action_intent_validation_empty_strings() -> None:
    """ActionIntent must reject empty target, operation, or capability strings."""
    run_id = uuid4()
    with pytest.raises(ValidationError):
        ActionIntent(
            run_id=run_id,
            action=ActionType.FILE_READ,
            target="",  # Invalid: min_length=1
            operation="read",
            capability="github.read_file",
            reason="valid reason",
        )


def test_action_intent_builder_file_read() -> None:
    """ActionIntentBuilder.file_read must produce a valid FILE_READ intent."""
    run_id = uuid4()
    builder = ActionIntentBuilder(run_id)
    intent = builder.file_read("src/payment.py", "Inspect payment logic")

    assert intent.run_id == run_id
    assert intent.action == ActionType.FILE_READ
    assert intent.target == "src/payment.py"
    assert intent.operation == "read"
    assert intent.capability == "github.read_file"


def test_action_intent_builder_file_write_with_diff() -> None:
    """ActionIntentBuilder.file_write must include diff in metadata."""
    run_id = uuid4()
    builder = ActionIntentBuilder(run_id)
    diff_content = "+ def new_func(): pass"
    intent = builder.file_write("src/utils.py", "modify", "Add helper", diff=diff_content)

    assert intent.action == ActionType.FILE_WRITE
    assert intent.capability == "github.create_commit"
    assert intent.metadata.get("diff") == diff_content


def test_action_intent_builder_github_comment() -> None:
    """ActionIntentBuilder.github_comment must target the PR comments API."""
    run_id = uuid4()
    builder = ActionIntentBuilder(run_id)
    intent = builder.github_comment(42, "Post review", "Looks good!")

    assert intent.action == ActionType.GITHUB_API
    assert intent.target == "pull_requests/42/comments"
    assert intent.capability == "github.comment_pr"
    assert intent.metadata.get("comment_preview") == "Looks good!"
