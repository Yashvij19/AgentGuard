"""
Output validation and repair engine for LLM responses.
Extracts JSON from free-form or markdown text, verifies against Pydantic models,
and generates structured correction prompts on schema violations.
"""

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.domain.exceptions import LLMOutputValidationError

T = TypeVar("T", bound=BaseModel)

# Regex to detect markdown JSON code fences e.g. ```json { ... } ```
JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class OutputValidator:
    """
    Validates model completions against target schemas.
    Guarantees malformed or hallucinated responses are intercepted before execution.
    """

    @staticmethod
    def extract_json_string(raw_text: str) -> str:
        """
        Extract clean JSON substring from raw text, stripping markdown wrappers or preamble.
        """
        text = raw_text.strip()

        # Check for markdown code blocks first
        match = JSON_BLOCK_PATTERN.search(text)
        if match:
            return match.group(1).strip()

        # If text starts with '{' or '[', find the balanced matching closing bracket
        first_brace = text.find("{")
        first_bracket = text.find("[")

        if first_brace == -1 and first_bracket == -1:
            return text  # Return as-is, json.loads will raise appropriate error

        start_idx = first_brace if (first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket)) else first_bracket
        is_brace = text[start_idx] == "{"
        target_char = "}" if is_brace else "]"

        last_idx = text.rfind(target_char)
        if last_idx != -1 and last_idx > start_idx:
            return text[start_idx : last_idx + 1]

        return text

    def parse_and_validate(
        self,
        raw_text: str,
        response_model: type[T],
    ) -> T:
        """
        Extract and validate JSON string against a target Pydantic model.
        Raises LLMOutputValidationError on syntax or schema errors.
        """
        extracted = self.extract_json_string(raw_text)

        try:
            parsed_dict = json.loads(extracted)
        except json.JSONDecodeError as err:
            raise LLMOutputValidationError(
                f"Failed to decode JSON from model output: {err}. Raw output was: {raw_text[:200]}"
            ) from err

        try:
            return response_model.model_validate(parsed_dict)
        except ValidationError as err:
            raise LLMOutputValidationError(
                f"Schema validation failed for model {response_model.__name__}: {err}"
            ) from err

    @staticmethod
    def build_repair_prompt(
        original_output: str,
        error_message: str,
        response_model: type[BaseModel],
    ) -> str:
        """
        Generate a targeted error correction prompt for retry attempts.
        """
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        return (
            "Your previous response failed validation with the following error:\n"
            f"ERROR: {error_message}\n\n"
            "Here is the exact JSON Schema you must conform to:\n"
            f"{schema_json}\n\n"
            "Here was your previous invalid output:\n"
            f"{original_output}\n\n"
            "Please fix the error and output ONLY the valid, corrected JSON object. "
            "Do not include any explanation or markdown commentary."
        )
