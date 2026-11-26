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
        return {
            "inputTokens": self.inputTokens,
            "outputTokens": self.outputTokens,
            "totalTokens": self.totalTokens,
        }


@dataclass
class Completion:
    text: str
    usage: Usage = field(default_factory=Usage)
    # Normalised stop reason: "safety", "max_tokens", "stop" or the raw provider value.
    finish_reason: str | None = None


class ProviderError(Exception):
    """A provider call failed. `status` is the provider HTTP status when known."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
