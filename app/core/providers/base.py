"""Provider-neutral result and error types."""

from dataclasses import dataclass, field

# Long translations (64k-128k output tokens) can take minutes; no retries by design.
PROVIDER_TIMEOUT_SECONDS = 600


@dataclass
class Usage:
    inputTokens: int = 0
    outputTokens: int = 0
    totalTokens: int = 0

    def as_dict(self) -> dict:
