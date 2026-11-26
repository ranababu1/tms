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
    """1 lakh chars ≈ 25k tokens each way (4 chars/token), doubled for draft+critique+final."""
    tokens = CHARS_PER_LAKH / 4
    return 2 * (tokens / 1e6 * pricing["inputPer1M"] + tokens / 1e6 * pricing["outputPer1M"])


def format_usd(value: float) -> str:
    return f"${value:.4f}" if value < 0.01 else f"${value:.2f}"


def format_inr(value: float) -> str:
    return f"₹{value:.3f}" if value < 1 else f"₹{value:.2f}"


def pricing_summary(pricing: dict) -> dict:
    """Pre-computed figures the model-info modal shows."""
    lakh = cost_per_lakh_chars(pricing)
    return {
        "inputPer1M": pricing["inputPer1M"],
        "outputPer1M": pricing["outputPer1M"],
        "inputPer1MInr": pricing["inputPer1M"] * USD_TO_INR,
        "outputPer1MInr": pricing["outputPer1M"] * USD_TO_INR,
        "perLakhUsd": lakh,
        "perLakhInr": lakh * USD_TO_INR,
        "perLakhUsdText": format_usd(lakh),
        "perLakhInrText": format_inr(lakh * USD_TO_INR),
    }
