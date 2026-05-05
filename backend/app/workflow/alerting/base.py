"""
workflow/alerting/base.py + strategies
───────────────────────────────────────
Strategy Pattern for alerting.

Different component types get different alert severity:
  RDBMS / API  → P0 Critical (page on-call immediately)
  CACHE / QUEUE → P2 Warning (Slack channel notification)
  MCP_HOST     → P1 High (email + Slack)
"""
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


# ─── Abstract Base ────────────────────────────────────────────────────────────
class AlertStrategy(ABC):
    priority: str = "P2"

    @abstractmethod
    async def send(self, work_item: dict) -> None:
        """Send an alert for the given Work Item."""
        ...

    def get_priority(self) -> str:
        return self.priority


# ─── Concrete Strategies ──────────────────────────────────────────────────────
class P0CriticalAlert(AlertStrategy):
    """P0 – Database/core API down. Page on-call engineer immediately."""
    priority = "P0"

    async def send(self, work_item: dict) -> None:
        msg = (
            f"🔴 [P0 CRITICAL] Component DOWN: {work_item.get('component_id')}\n"
            f"   Type: {work_item.get('component_type')}\n"
            f"   Work Item: {work_item.get('id')}\n"
            f"   → Paging on-call via PagerDuty"
        )
        logger.critical(msg)
        print(msg, flush=True)
        # Production: await pagerduty_client.trigger(work_item)


class P1HighAlert(AlertStrategy):
    """P1 – MCP Host / critical dependency degraded."""
    priority = "P1"

    async def send(self, work_item: dict) -> None:
        msg = (
            f"🟠 [P1 HIGH] Component DEGRADED: {work_item.get('component_id')}\n"
            f"   Type: {work_item.get('component_type')}\n"
            f"   → Notifying via Email + Slack #incidents"
        )
        logger.error(msg)
        print(msg, flush=True)
        # Production: await slack_client.post("#incidents", msg)


class P2WarningAlert(AlertStrategy):
    """P2 – Cache miss / queue slowdown. Post to Slack."""
    priority = "P2"

    async def send(self, work_item: dict) -> None:
        msg = (
            f"🟡 [P2 WARNING] Component SLOW: {work_item.get('component_id')}\n"
            f"   Type: {work_item.get('component_type')}\n"
            f"   → Slack #monitoring"
        )
        logger.warning(msg)
        print(msg, flush=True)
        # Production: await slack_client.post("#monitoring", msg)


# ─── Strategy Registry ────────────────────────────────────────────────────────
COMPONENT_STRATEGY_MAP: dict[str, AlertStrategy] = {
    "RDBMS":    P0CriticalAlert(),
    "API":      P0CriticalAlert(),
    "MCP_HOST": P1HighAlert(),
    "QUEUE":    P2WarningAlert(),
    "CACHE":    P2WarningAlert(),
    "NOSQL":    P1HighAlert(),
}

DEFAULT_STRATEGY = P2WarningAlert()


def get_alert_strategy(component_type: str) -> AlertStrategy:
    """Returns the correct alert strategy for a component type."""
    return COMPONENT_STRATEGY_MAP.get(component_type.upper(), DEFAULT_STRATEGY)
