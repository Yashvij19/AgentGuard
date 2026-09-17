"""
Unit tests for RegoCompiler.
"""

from app.domain.models.policy import (
    CapabilityConfig,
    CommandConfig,
    FilesystemConfig,
    NetworkConfig,
    PolicyConfig,
    SensitiveActionRule,
    SensitiveActionTrigger,
)
from app.infrastructure.policy.rego_compiler import RegoCompiler


def test_rego_compiler_transforms_policy_config() -> None:
    """Compiler must map all PolicyConfig fields into OPA data document."""
    config = PolicyConfig(
        version=2,
        capabilities=CapabilityConfig(
            allow=["github.read_file"],
            approval=["github.create_commit"],
            deny=["github.admin"],
        ),
        filesystem=FilesystemConfig(
            read=["src/**/*"],
            write=["src/app/**/*"],
        ),
        commands=CommandConfig(
            allow=["^pytest.*"],
            deny=[".*rm -rf.*"],
        ),
        network=NetworkConfig(
            allowed_domains=["api.github.com"],
        ),
        sensitive_actions=[
            SensitiveActionRule(
                name="ci_tampering",
                trigger=SensitiveActionTrigger.FILE_PATTERN,
                pattern=".github/workflows/**",
                description="CI change protection",
            )
        ],
    )

    doc = RegoCompiler.compile_data_document(config)

    assert doc["version"] == 2
    assert "github.read_file" in doc["capabilities"]["allow"]
    assert "github.create_commit" in doc["capabilities"]["approval"]
    assert "github.admin" in doc["capabilities"]["deny"]
    assert doc["filesystem"]["read"] == ["src/**/*"]
    assert doc["filesystem"]["write"] == ["src/app/**/*"]
    assert doc["commands"]["allow"] == ["^pytest.*"]
    assert doc["commands"]["deny"] == [".*rm -rf.*"]
    assert "api.github.com" in doc["network"]["allowed_domains"]
    assert len(doc["sensitive_actions"]) == 1
    assert doc["sensitive_actions"][0]["trigger"] == "file_pattern"
