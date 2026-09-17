"""
Policy Management API router.
Provides CRUD and validation endpoints for repository security policies.
"""

import urllib.parse
from typing import Annotated, Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.api.dependencies import get_policy_repository
from app.api.policies.schemas import (
    PolicyResponse,
    PolicyUpdateRequest,
    PolicyValidateRequest,
    PolicyValidateResponse,
    RegoBundleResponse,
)
from app.domain.models.policy import PolicyConfig
from app.infrastructure.database.repositories.policy_repository import PolicyRepository
from app.infrastructure.policy.rego_compiler import RegoCompiler

router = APIRouter()
PolicyRepoDep = Annotated[PolicyRepository, Depends(get_policy_repository)]


@router.get(
    "/{repo:path}/rego",
    response_model=RegoBundleResponse,
    summary="Get compiled Rego data document for a repo",
)
async def get_compiled_rego(
    repo: str,
    policy_repo: PolicyRepoDep,
) -> RegoBundleResponse:
    """Return the OPA data.policy document compiled from the active YAML policy."""
    clean_repo = urllib.parse.unquote(repo).strip()
    policy = await policy_repo.get_by_repo(clean_repo)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy not found for repository '{clean_repo}'",
        )

    rego_data = RegoCompiler.compile_data_document(policy.parsed_content)
    return RegoBundleResponse(
        repo=clean_repo,
        version=policy.version,
        rego_data=rego_data,
    )


@router.get(
    "/{repo:path}",
    response_model=PolicyResponse,
    summary="Get active policy for a repository",
)
async def get_policy(
    repo: str,
    policy_repo: PolicyRepoDep,
) -> PolicyResponse:
    """Fetch the current governance policy and version for a given repository."""
    clean_repo = urllib.parse.unquote(repo).strip()
    policy = await policy_repo.get_by_repo(clean_repo)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No policy registered for repository '{clean_repo}'",
        )

    return PolicyResponse(
        id=policy.id,
        repo=policy.repo,
        yaml_content=policy.yaml_content,
        version=policy.version,
        parsed_content=policy.parsed_content,
        rego_bundle=policy.rego_bundle,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.put(
    "/{repo:path}",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update or create a repository policy",
)
async def update_policy(
    repo: str,
    payload: PolicyUpdateRequest,
    policy_repo: PolicyRepoDep,
) -> PolicyResponse:
    """
    Validate, compile, and persist a new policy YAML for a repository.
    Automatically increments the policy version counter.
    """
    clean_repo = urllib.parse.unquote(repo).strip()

    # 1. Parse YAML safely
    try:
        raw_dict = yaml.safe_load(payload.yaml_content)
        if not isinstance(raw_dict, dict):
            raise ValueError("YAML root must be a dictionary/mapping")
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid YAML syntax: {err}",
        ) from err

    # 2. Validate against PolicyConfig domain model
    try:
        parsed_config = PolicyConfig.model_validate(raw_dict)
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Policy schema validation failed: {err.errors()}",
        ) from err

    # 3. Test compilation to OPA data document
    try:
        RegoCompiler.compile_data_document(parsed_config)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to compile policy into Rego data format: {err}",
        ) from err

    # 4. Save and increment version
    saved_policy = await policy_repo.save_policy(
        repo=clean_repo,
        yaml_content=payload.yaml_content,
        parsed_config=parsed_config,
    )

    return PolicyResponse(
        id=saved_policy.id,
        repo=saved_policy.repo,
        yaml_content=saved_policy.yaml_content,
        version=saved_policy.version,
        parsed_content=saved_policy.parsed_content,
        rego_bundle=saved_policy.rego_bundle,
        created_at=saved_policy.created_at,
        updated_at=saved_policy.updated_at,
    )


@router.post(
    "/validate",
    response_model=PolicyValidateResponse,
    summary="Dry-run validate a policy YAML without persisting",
)
async def validate_policy(
    payload: PolicyValidateRequest,
) -> PolicyValidateResponse:
    """
    Validate YAML syntax, verify schema conformance, and test OPA compilation.
    """
    errors: list[str] = []
    raw_dict: Any = None

    # Step 1: YAML syntax check
    try:
        raw_dict = yaml.safe_load(payload.yaml_content)
        if not isinstance(raw_dict, dict):
            errors.append("Root YAML structure must be a key-value mapping.")
    except Exception as err:
        return PolicyValidateResponse(valid=False, errors=[f"YAML parsing error: {err}"])

    if errors or not isinstance(raw_dict, dict):
        return PolicyValidateResponse(valid=False, errors=errors)

    # Step 2: Schema validation check
    try:
        parsed_config = PolicyConfig.model_validate(raw_dict)
    except ValidationError as err:
        for err_detail in err.errors():
            loc = " -> ".join(str(item) for item in err_detail.get("loc", []))
            errors.append(f"Field '{loc}': {err_detail.get('msg')}")
        return PolicyValidateResponse(valid=False, errors=errors)

    # Step 3: OPA Rego compilation check
    rego_preview: dict[str, Any] | None = None
    try:
        rego_preview = RegoCompiler.compile_data_document(parsed_config)
    except Exception as err:
        return PolicyValidateResponse(
            valid=False,
            version=parsed_config.version,
            errors=[f"Rego compilation failure: {err}"],
        )

    return PolicyValidateResponse(
        valid=True,
        version=parsed_config.version,
        errors=[],
        rego_data_preview=rego_preview,
    )
