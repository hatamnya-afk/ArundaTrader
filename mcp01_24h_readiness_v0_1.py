"""MCP-01.8 24/7 readiness verification.

Readiness-only contract. This module verifies that the compact evidence,
projection, reconciliation, aggregation, and email layers are structurally
present. It never starts a scheduler, sends email, changes Trader logic, or
activates 24/7 operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


SCHEMA = "arunda.24h_readiness"
SCHEMA_VERSION = "1.0"

REQUIRED_COMPONENTS = (
    "evidence_contract",
    "runtime_projection",
    "case_projection",
    "trade_projection",
    "outcome_reconciliation",
    "24h_aggregator",
    "24h_email",
)


@dataclass(frozen=True)
class ReadinessResult:
    schema: str
    schema_version: str
    components_present: tuple[str, ...]
    components_missing: tuple[str, ...]
    structural_checks_passed: tuple[str, ...]
    structural_checks_failed: tuple[str, ...]
    ready_for_24h_activation: bool
    activation_enabled: bool
    management_authorization_required: bool

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "components_present": list(self.components_present),
            "components_missing": list(self.components_missing),
            "structural_checks_passed": list(self.structural_checks_passed),
            "structural_checks_failed": list(self.structural_checks_failed),
            "ready_for_24h_activation": self.ready_for_24h_activation,
            "activation_enabled": self.activation_enabled,
            "management_authorization_required": self.management_authorization_required,
        }


def verify_24h_readiness(
    *,
    available_components: Iterable[str],
    email_delivery_enabled: bool = False,
    management_authorized: bool = False,
    scheduler_active: bool = False,
) -> dict:
    available = {
        value.strip()
        for value in available_components
        if isinstance(value, str) and value.strip()
    }

    present = tuple(name for name in REQUIRED_COMPONENTS if name in available)
    missing = tuple(name for name in REQUIRED_COMPONENTS if name not in available)

    passed: list[str] = []
    failed: list[str] = []

    if not missing:
        passed.append("all_mcp01_components_present")
    else:
        failed.append("missing_mcp01_components")

    if email_delivery_enabled:
        passed.append("email_delivery_enabled")
    else:
        passed.append("email_delivery_intentionally_disabled")

    if scheduler_active:
        failed.append("24h_scheduler_active_before_management_gate")
    else:
        passed.append("24h_scheduler_not_active")

    if management_authorized:
        passed.append("management_authorization_present")
    else:
        passed.append("management_authorization_required")

    ready = not missing and not scheduler_active

    return ReadinessResult(
        schema=SCHEMA,
        schema_version=SCHEMA_VERSION,
        components_present=present,
        components_missing=missing,
        structural_checks_passed=tuple(passed),
        structural_checks_failed=tuple(failed),
        ready_for_24h_activation=ready,
        activation_enabled=bool(email_delivery_enabled and management_authorized),
        management_authorization_required=not management_authorized,
    ).to_dict()
