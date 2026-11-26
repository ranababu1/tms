"""Cost math and formatters (spec §4.3, §4.4)."""

USD_TO_INR = 88
CHARS_PER_LAKH = 100_000


def request_cost(usage: dict, pricing: dict) -> float:
    """USD cost for one call: in/1e6*inputPer1M + out/1e6*outputPer1M."""
    return (
        usage.get("inputTokens", 0) / 1e6 * pricing["inputPer1M"]
        + usage.get("outputTokens", 0) / 1e6 * pricing["outputPer1M"]
    )


def cost_per_lakh_chars(pricing: dict) -> float:
