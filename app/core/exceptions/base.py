"""Core NetGuard AI Exceptions Hierarchy."""

class NetGuardError(Exception):
    """Base exception for all NetGuard errors."""
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class ConfigurationError(NetGuardError):
    """Raised when configuration validation or loading fails."""
    pass


class PlatformError(NetGuardError):
    """Raised when an operating system-level operation fails."""
    pass


class MonitoringError(NetGuardError):
    """Raised when probe execution or telemetry collection fails."""
    pass


class ProbeTimeoutError(MonitoringError):
    """Raised when a probe exceeds its designated execution deadline."""
    pass


class DiagnosticError(NetGuardError):
    """Raised when diagnostic reasoning encounters an unrecoverable state."""
    pass


class RemediationError(NetGuardError):
    """Raised when an autonomous repair action fails."""
    pass


class PreconditionFailedError(RemediationError):
    """Raised when an action's safety preconditions are not satisfied."""
    pass


class ActionVerificationError(RemediationError):
    """Raised when post-remediation verification metrics fail to meet criteria."""
    pass


class RollbackError(RemediationError):
    """Raised when reverting an action to its prior state fails."""
    pass


class CircuitBreakerOpenError(RemediationError):
    """Raised when an action is rejected because its circuit breaker is tripped."""
    pass
