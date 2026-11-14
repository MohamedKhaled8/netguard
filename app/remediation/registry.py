"""Remediation Action Registry and Base Contract."""

from __future__ import annotations
import sys
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from app.core.models.metrics import RiskLevel
from app.platform.interfaces import IPlatformAdapter

logger = logging.getLogger("netguard.remediation.registry")


class RemediationAction(ABC):
    """Abstract contract for every policy-governed remediation action."""

    def __init__(
        self,
        action_id: str,
        name: str,
        description: str,
        risk_level: RiskLevel,
        supported_os: Optional[List[str]] = None,
        timeout_sec: float = 10.0,
        cooldown_sec: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self.action_id = action_id
        self.name = name
        self.description = description
        self.risk_level = risk_level
        self.supported_os = supported_os or ["win32", "linux"]
        self.timeout_sec = timeout_sec
        self.cooldown_sec = cooldown_sec
        self.max_retries = max_retries

    def is_os_supported(self) -> bool:
        """Verify action is authorized and supported on current operating system."""
        current_platform = sys.platform
        for supported in self.supported_os:
            if current_platform.startswith(supported):
                return True
        return False

    @abstractmethod
    def check_preconditions(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Check all safety invariants and permissions before executing."""
        pass

    @abstractmethod
    async def execute(self, platform: IPlatformAdapter, context: Dict[str, Any]) -> Any:
        """Execute recovery action. Must return pre-state snapshot for potential rollback."""
        pass

    @abstractmethod
    async def verify(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str, Dict[str, Any]]:
        """Empirically measure post-action network behavior.
        Returns: (success: bool, message: str, post_metrics: dict)
        """
        pass

    @abstractmethod
    async def rollback(self, platform: IPlatformAdapter, context: Dict[str, Any], pre_state: Any) -> Tuple[bool, str]:
        """Restore previous configuration if verification fails or side effects occur."""
        pass


class ActionRegistry:
    """Catalog of registered and auditable remediation actions."""

    def __init__(self) -> None:
        self._actions: Dict[str, RemediationAction] = {}

    def register(self, action: RemediationAction) -> None:
        if action.action_id in self._actions:
            logger.warning("Overwriting existing action: %s", action.action_id)
        self._actions[action.action_id] = action
        logger.info("Registered remediation action: %s (%s)", action.action_id, action.risk_level.value)

    def get(self, action_id: str) -> Optional[RemediationAction]:
        return self._actions.get(action_id)

    def list_actions(self) -> List[RemediationAction]:
        return list(self._actions.values())
