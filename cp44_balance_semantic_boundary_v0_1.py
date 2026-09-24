
from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Optional


SEMANTIC_CONTRACT_VERSION = "CP44_BALANCE_SEMANTIC_v0.1"
PORTFOLIO_DENOMINATION = "USDT"


@dataclass(frozen=True)
class BalanceSemanticObservation:
    capital_state: str
    portfolio_capital: Optional[float]
    usable_capital: Optional[float]
    denomination: str
    validation: str
    source: Optional[str]
    observed_at: Optional[str]
    provenance: Mapping[str, Any]
    reason: str

    synthetic: bool = False
    interpolated: bool = False
    filled: bool = False
    backfilled: bool = False
    padded: bool = False
    blended: bool = False
    db_writes: int = 0
    execution: bool = False

    def as_mapping(self) -> dict[str, Any]:
        return {
            "capital_state": self.capital_state,
            "portfolio_capital": self.portfolio_capital,
            "usable_capital": self.usable_capital,
            "denomination": self.denomination,
            "validation": self.validation,
            "source": self.source,
            "observed_at": self.observed_at,
            "provenance": dict(self.provenance),
            "synthetic": self.synthetic,
            "interpolated": self.interpolated,
            "filled": self.filled,
            "backfilled": self.backfilled,
            "padded": self.padded,
            "blended": self.blended,
            "db_writes": self.db_writes,
            "execution": self.execution,
        }


def _blocked(
    reason: str,
    *,
    source: Optional[str] = None,
    observed_at: Optional[str] = None,
    provenance: Optional[Mapping[str, Any]] = None,
) -> BalanceSemanticObservation:
    return BalanceSemanticObservation(
        capital_state="UNAVAILABLE",
        portfolio_capital=None,
        usable_capital=None,
        denomination=PORTFOLIO_DENOMINATION,
        validation="BLOCKED",
        source=source,
        observed_at=observed_at,
        provenance=dict(provenance or {}),
        reason=reason,
    )


def build_cp44_balance_semantics(
    balance: Any,
    *,
    denomination: str = PORTFOLIO_DENOMINATION,
) -> BalanceSemanticObservation:
    if balance is None:
        return _blocked("BALANCE_UNAVAILABLE")

    if str(denomination).upper() != PORTFOLIO_DENOMINATION:
        return _blocked("AMBIGUOUS_PORTFOLIO_DENOMINATION")

    asset = str(getattr(balance, "asset", "")).upper()
    if asset != PORTFOLIO_DENOMINATION:
        return _blocked("PORTFOLIO_DENOMINATION_NOT_OBSERVED")

    source = getattr(balance, "source_id", None)
    observed_at = getattr(balance, "source_timestamp", None)

    if not source:
        return _blocked(
            "BALANCE_SOURCE_UNAVAILABLE",
            source=source,
            observed_at=observed_at,
        )

    if not observed_at:
        return _blocked(
            "BALANCE_SOURCE_TIMESTAMP_UNAVAILABLE",
            source=source,
            observed_at=observed_at,
        )

    provenance = {
        "source": source,
        "source_type": getattr(balance, "source_type", None),
        "source_timestamp": observed_at,
        "semantic_contract": SEMANTIC_CONTRACT_VERSION,
        "denomination": PORTFOLIO_DENOMINATION,
    }

    try:
        portfolio_capital = float(balance.total)
        usable_capital = float(balance.free)
    except (TypeError, ValueError):
        return _blocked(
            "BALANCE_TOTAL_OR_FREE_INVALID",
            source=source,
            observed_at=observed_at,
            provenance=provenance,
        )

    if not isfinite(portfolio_capital) or not isfinite(usable_capital):
        return _blocked(
            "BALANCE_TOTAL_OR_FREE_NON_FINITE",
            source=source,
            observed_at=observed_at,
            provenance=provenance,
        )

    if portfolio_capital <= 0:
        return _blocked(
            "PORTFOLIO_CAPITAL_NON_POSITIVE",
            source=source,
            observed_at=observed_at,
            provenance=provenance,
        )

    if usable_capital < 0 or usable_capital > portfolio_capital:
        return _blocked(
            "USABLE_CAPITAL_INVALID",
            source=source,
            observed_at=observed_at,
            provenance=provenance,
        )

    return BalanceSemanticObservation(
        capital_state="REAL_CAPITAL",
        portfolio_capital=portfolio_capital,
        usable_capital=usable_capital,
        denomination=PORTFOLIO_DENOMINATION,
        validation="VALID",
        source=source,
        observed_at=observed_at,
        provenance=provenance,
        reason="REAL_USDT_BALANCE_SEMANTICALLY_MAPPED",
    )
