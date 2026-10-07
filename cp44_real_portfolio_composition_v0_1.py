"""CP44 Real Portfolio / Capital Composition Boundary v0.1.

Purpose:
    Compose already-observed real account, balance and portfolio state into
    the explicit input contract required by CP44 Smart Risk.

Rules:
    - Read-only.
    - No DB writes.
    - No exchange calls.
    - No synthetic/fill/backfill/interpolation/padding/blending.
    - No capital_config.
    - No risk_budget_engine.
    - No risk-budget -> allocated-risk conversion.
    - allocated_risk must come from an explicit real portfolio
      risk/allocation observation.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Sequence


REAL_CAPITAL = "REAL_CAPITAL"
COMPOSITION_VERSION = "CP44_REAL_PORTFOLIO_COMPOSITION_v0.1"


@dataclass(frozen=True)
class RealPortfolioComposition:
    capital_state: str
    portfolio_capital: float | None
    usable_capital: float | None
    allocated_risk: float | None
    concurrent_positions: int | None
    source: str
    observed_at: str
    provenance: Mapping[str, str]
    validation: str
    state: str
    gaps: tuple[str, ...]

    def as_mapping(self) -> dict[str, Any]:
        return {
            "capital_state": self.capital_state,
            "portfolio_capital": self.portfolio_capital,
            "usable_capital": self.usable_capital,
            "allocated_risk": self.allocated_risk,
            "concurrent_positions": self.concurrent_positions,
            "source": self.source,
            "observed_at": self.observed_at,
            "provenance": dict(self.provenance),
            "validation": self.validation,
            "state": self.state,
            "gaps": list(self.gaps),
            "composition_version": COMPOSITION_VERSION,
            "synthetic": False,
            "interpolation": False,
            "fill": False,
            "backfill": False,
            "padding": False,
            "blending": False,
            "db_writes": 0,
            "execution": False,
        }


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not isfinite(result):
        return None

    return result


def _positive_number(value: Any) -> float | None:
    result = _number(value)
    if result is None or result < 0:
        return None
    return result


def _non_negative_number(value: Any) -> float | None:
    result = _number(value)
    if result is None or result < 0:
        return None
    return result


def _position_count(portfolio_observation: Mapping[str, Any]) -> int | None:
    positions = portfolio_observation.get("positions")

    if positions is None:
        return None

    if not isinstance(positions, Sequence) or isinstance(
        positions,
        (str, bytes, bytearray),
    ):
        return None

    count = 0

    for position in positions:
        if not isinstance(position, Mapping):
            continue

        quantity = _positive_number(position.get("quantity"))

        if quantity is None:
            continue

        count += 1

    return count


def _extract_capital(
    account_balance_observation: Mapping[str, Any],
) -> tuple[float | None, float | None]:
    """Extract only explicitly named capital fields.

    We deliberately do NOT reinterpret:
        balance.total -> portfolio_capital
        balance.free  -> usable_capital

    unless the producer has already exposed those semantic fields.
    """

    portfolio_capital = _positive_number(
        account_balance_observation.get("portfolio_capital")
    )

    usable_capital = _positive_number(
        account_balance_observation.get("usable_capital")
    )

    return portfolio_capital, usable_capital


def _extract_provenance(
    *observations: Mapping[str, Any],
) -> dict[str, str]:
    provenance: dict[str, str] = {}

    for observation in observations:
        value = observation.get("provenance")

        if isinstance(value, Mapping):
            for key, item in value.items():
                if (
                    isinstance(key, str)
                    and key
                    and isinstance(item, str)
                    and item
                ):
                    provenance[key] = item

    return provenance


def compose_real_portfolio_capital(
    account_balance_observation: Mapping[str, Any],
    portfolio_observation: Mapping[str, Any],
    real_risk_allocation_observation: Mapping[str, Any] | None = None,
) -> RealPortfolioComposition:
    """Compose explicit real observations for CP44 Smart Risk.

    allocated_risk is never calculated from notional, balance, PnL,
    locked funds, risk budget or position sizing.

    Special zero-position invariant:
        If the real portfolio contains zero valid open positions,
        allocated_risk is exactly 0.0 because there is no open position
        to which risk can be allocated.

    If real positions exist, an explicit real risk-allocation source
    remains mandatory.
    """

    if not isinstance(account_balance_observation, Mapping):
        raise TypeError(
            "account_balance_observation must be a Mapping"
        )

    if not isinstance(portfolio_observation, Mapping):
        raise TypeError(
            "portfolio_observation must be a Mapping"
        )

    if (
        real_risk_allocation_observation is not None
        and not isinstance(
            real_risk_allocation_observation,
            Mapping,
        )
    ):
        raise TypeError(
            "real_risk_allocation_observation must be a Mapping or None"
        )

    gaps: list[str] = []

    portfolio_capital, usable_capital = _extract_capital(
        account_balance_observation
    )

    if portfolio_capital is None:
        gaps.append("PORTFOLIO_CAPITAL_UNAVAILABLE")

    if usable_capital is None:
        gaps.append("USABLE_CAPITAL_UNAVAILABLE")

    if (
        portfolio_capital is not None
        and usable_capital is not None
        and usable_capital > portfolio_capital
    ):
        gaps.append("USABLE_CAPITAL_EXCEEDS_PORTFOLIO_CAPITAL")

    concurrent_positions = _position_count(
        portfolio_observation
    )

    if concurrent_positions is None:
        gaps.append("CONCURRENT_POSITIONS_UNAVAILABLE")

    allocated_risk: float | None = None

    # ---------------------------------------------------------
    # REAL ZERO-POSITION INVARIANT
    # ---------------------------------------------------------
    #
    # If the real position observation explicitly contains zero
    # valid open positions, there is no currently allocated
    # position risk. Therefore allocated_risk = 0.0 is a direct
    # consequence of the observed empty position set.
    #
    # This is NOT:
    #   risk_budget
    #   capital_config
    #   position sizing
    #   notional conversion
    #   locked-balance conversion
    #
    if concurrent_positions == 0:
        allocated_risk = 0.0

    # ---------------------------------------------------------
    # REAL NON-ZERO POSITION CASE
    # ---------------------------------------------------------
    #
    # When real positions exist, allocated_risk must come from
    # an explicit real risk/allocation observation.
    #
    elif real_risk_allocation_observation is None:
        gaps.append("ALLOCATED_RISK_UNAVAILABLE")

    else:
        source = real_risk_allocation_observation.get("source")
        provenance = real_risk_allocation_observation.get(
            "provenance"
        )
        validation = real_risk_allocation_observation.get(
            "validation"
        )
        risk_state = real_risk_allocation_observation.get(
            "allocation_state"
        )

        if not isinstance(source, str) or not source:
            gaps.append("RISK_ALLOCATION_SOURCE_INVALID")

        if not isinstance(provenance, Mapping) or not provenance:
            gaps.append("RISK_ALLOCATION_PROVENANCE_INVALID")

        if validation != "VALID":
            gaps.append("RISK_ALLOCATION_NOT_VALIDATED")

        if risk_state not in ("AVAILABLE", "REAL"):
            gaps.append("RISK_ALLOCATION_NOT_AVAILABLE")

        allocated_risk = _non_negative_number(
            real_risk_allocation_observation.get(
                "allocated_risk"
            )
        )

        if allocated_risk is None:
            gaps.append("ALLOCATED_RISK_INVALID")

    provenance = _extract_provenance(
        account_balance_observation,
        portfolio_observation,
        real_risk_allocation_observation or {},
    )

    observed_at_values = [
        observation.get("observed_at")
        for observation in (
            account_balance_observation,
            portfolio_observation,
            real_risk_allocation_observation or {},
        )
        if isinstance(observation.get("observed_at"), str)
        and observation.get("observed_at")
    ]

    observed_at = (
        observed_at_values[-1]
        if observed_at_values
        else ""
    )

    if not observed_at:
        gaps.append("OBSERVED_AT_UNAVAILABLE")

    if not provenance:
        gaps.append("PROVENANCE_UNAVAILABLE")

    if gaps:
        return RealPortfolioComposition(
            capital_state="UNAVAILABLE",
            portfolio_capital=portfolio_capital,
            usable_capital=usable_capital,
            allocated_risk=allocated_risk,
            concurrent_positions=concurrent_positions,
            source=COMPOSITION_VERSION,
            observed_at=observed_at,
            provenance=provenance,
            validation="INVALID",
            state="BLOCKED",
            gaps=tuple(dict.fromkeys(gaps)),
        )

    return RealPortfolioComposition(
        capital_state=REAL_CAPITAL,
        portfolio_capital=portfolio_capital,
        usable_capital=usable_capital,
        allocated_risk=allocated_risk,
        concurrent_positions=concurrent_positions,
        source=COMPOSITION_VERSION,
        observed_at=observed_at,
        provenance=provenance,
        validation="VALID",
        state="AVAILABLE",
        gaps=(),
    )

    return RealPortfolioComposition(
        capital_state=REAL_CAPITAL,
        portfolio_capital=portfolio_capital,
        usable_capital=usable_capital,
        allocated_risk=allocated_risk,
        concurrent_positions=concurrent_positions,
        source=COMPOSITION_VERSION,
        observed_at=observed_at,
        provenance=provenance,
        validation="VALID",
        state="AVAILABLE",
        gaps=(),
    )
