"""
Cost calculator for multi-provider LLM token accounting.
Maintains pricing tables and calculates estimated USD costs using high-precision Decimal.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.domain.models.llm_config import LLMProviderName, TokenPricing

# Pricing table in USD per 1,000 tokens (Commercial API benchmark rates)
DEFAULT_PRICING_TABLE: dict[LLMProviderName, TokenPricing] = {
    # Google Gemini 2.5 Flash / 1.5 Flash ($0.15 / 1M prompt, $0.60 / 1M completion)
    LLMProviderName.GEMINI: TokenPricing(
        input_per_1k=Decimal("0.00015"),
        output_per_1k=Decimal("0.00060"),
    ),
    # Groq LLaMA 3.3 70B ($0.59 / 1M prompt, $0.79 / 1M completion)
    LLMProviderName.GROQ: TokenPricing(
        input_per_1k=Decimal("0.00059"),
        output_per_1k=Decimal("0.00079"),
    ),
    # NVIDIA NIM Nemotron / DeepSeek ($0.20 / 1M prompt, $0.60 / 1M completion)
    LLMProviderName.NVIDIA_NIM: TokenPricing(
        input_per_1k=Decimal("0.00020"),
        output_per_1k=Decimal("0.00060"),
    ),
    # Generic fallback commercial baseline ($0.15 / $0.60 per 1M tokens)
    LLMProviderName.OPENAI_COMPAT: TokenPricing(
        input_per_1k=Decimal("0.00015"),
        output_per_1k=Decimal("0.00060"),
    ),
}


class CostCalculator:
    """
    Calculates estimated monetary cost for LLM invocations.
    Thread-safe and decoupled from network I/O.
    """

    def __init__(
        self,
        pricing_overrides: dict[LLMProviderName, TokenPricing] | None = None,
    ) -> None:
        self._pricing: dict[LLMProviderName, TokenPricing] = {
            **DEFAULT_PRICING_TABLE,
            **(pricing_overrides or {}),
        }

    def get_pricing(self, provider: LLMProviderName) -> TokenPricing:
        """Retrieve token pricing configuration for a given provider."""
        return self._pricing.get(
            provider,
            TokenPricing(input_per_1k=Decimal("0.0"), output_per_1k=Decimal("0.0")),
        )

    def calculate_cost(
        self,
        provider: LLMProviderName,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Decimal:
        """
        Compute estimated cost in USD based on token counts and provider pricing.
        Rounds to 6 decimal places using ROUND_HALF_UP.
        """
        pricing = self.get_pricing(provider)

        prompt_cost = (Decimal(prompt_tokens) / Decimal(1000)) * pricing.input_per_1k
        completion_cost = (Decimal(completion_tokens) / Decimal(1000)) * pricing.output_per_1k

        total = prompt_cost + completion_cost
        return total.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
