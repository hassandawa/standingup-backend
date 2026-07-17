class AIServiceError(Exception):
    """Raised when the configured AI provider fails."""


class AIRateLimitError(AIServiceError):
    """Raised when the configured AI provider is rate limited."""
