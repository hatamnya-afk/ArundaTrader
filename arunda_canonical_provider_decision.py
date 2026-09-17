"""
ARUNDA CANONICAL PROVIDER DECISION v0.3
CPD-03 — Explicit Architectural Decision

CANONICAL_ACTIVE here means:
    The architectural provider decision is explicitly active.

It does NOT mean:
    Production market-data consumption is enabled.

NO:
- network
- KUCOIN access
- OHLCV fetch
- CCXT
- database
- persistence
- production mutation
- execution
- order intents
- failover activation
- provider blending
"""

from __future__ import annotations

from dataclasses import dataclass


# ============================================================
# CONTRACT
# ============================================================

ENGINE = "CANONICAL_PROVIDER_DECISION"
VERSION = "v0.3"

DECISION_TYPE = "CANONICAL_PROVIDER_DECISION"

PROVIDER = "KUCOIN"
ROLE = "CANONICAL_ACTIVE"
STATUS = "CANONICAL_ACTIVE"

QUALIFICATION_VERSION = "v0.3"
SELECTION_PROBE_VERSION = "v0.1"
DECISION_VERSION = "v0.3"

EFFECTIVE_FROM = "2026-08-31T00:00:00+00:00"
TIMEFRAME = "1h"

FAILOVER_POLICY = "NOT_YET_ACTIVATED"
BLENDING_POLICY = "FORBIDDEN"

EVIDENCE_BOUND = True

NETWORK = False
DB_WRITES = 0
PRODUCTION_DB_TOUCHED = False
PRODUCTION_MUTATION = False

PRODUCTION_CONSUMPTION_ENABLED = False
EXECUTION = "DISABLED"
ORDER_INTENTS_CREATED = 0


# ============================================================
# VERIFIED EVIDENCE LINEAGE
# ============================================================

QUALIFICATION_EVIDENCE = (
    "qualification_evidence_v0.3"
)

SELECTION_EVIDENCE = (
    "selection_evidence_v0.1"
)


# ============================================================
# IMMUTABLE DECISION CONTRACT
# ============================================================

@dataclass(frozen=True)
class CanonicalProviderDecision:
    decision_type: str
    provider: str
    role: str
    status: str
    qualification_version: str
    selection_probe_version: str
    decision_version: str
    effective_from: str
    timeframe: str
    failover_policy: str
    blending_policy: str
    evidence_bound: bool
    network: bool
    db_writes: int
    production_db_touched: bool
    production_mutation: bool
    production_consumption_enabled: bool
    execution: str
    order_intents_created: int


# ============================================================
# CONSTRUCTION
# ============================================================

def build_decision() -> CanonicalProviderDecision:
    """
    Construct the explicit architectural decision.

    No external access is performed.
    """

    return CanonicalProviderDecision(
        decision_type=DECISION_TYPE,
        provider=PROVIDER,
        role=ROLE,
        status=STATUS,
        qualification_version=QUALIFICATION_VERSION,
        selection_probe_version=SELECTION_PROBE_VERSION,
        decision_version=DECISION_VERSION,
        effective_from=EFFECTIVE_FROM,
        timeframe=TIMEFRAME,
        failover_policy=FAILOVER_POLICY,
        blending_policy=BLENDING_POLICY,
        evidence_bound=EVIDENCE_BOUND,
        network=NETWORK,
        db_writes=DB_WRITES,
        production_db_touched=PRODUCTION_DB_TOUCHED,
        production_mutation=PRODUCTION_MUTATION,
        production_consumption_enabled=(
            PRODUCTION_CONSUMPTION_ENABLED
        ),
        execution=EXECUTION,
        order_intents_created=ORDER_INTENTS_CREATED,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_decision(
    decision: CanonicalProviderDecision,
) -> None:

    if decision.decision_type != (
        "CANONICAL_PROVIDER_DECISION"
    ):
        raise ValueError("DECISION_TYPE_INVALID")

    if decision.provider != "KUCOIN":
        raise ValueError("PROVIDER_INVALID")

    if decision.role != "CANONICAL_ACTIVE":
        raise ValueError("ROLE_INVALID")

    if decision.status != "CANONICAL_ACTIVE":
        raise ValueError("STATUS_INVALID")

    if decision.qualification_version != "v0.3":
        raise ValueError("QUALIFICATION_VERSION_INVALID")

    if decision.selection_probe_version != "v0.1":
        raise ValueError("SELECTION_PROBE_VERSION_INVALID")

    if decision.decision_version != "v0.3":
        raise ValueError("DECISION_VERSION_INVALID")

    if decision.effective_from != (
        "2026-08-31T00:00:00+00:00"
    ):
        raise ValueError("EFFECTIVE_BOUNDARY_INVALID")

    if decision.timeframe != "1h":
        raise ValueError("TIMEFRAME_INVALID")

    if decision.failover_policy != (
        "NOT_YET_ACTIVATED"
    ):
        raise ValueError("FAILOVER_POLICY_INVALID")

    if decision.blending_policy != "FORBIDDEN":
        raise ValueError("BLENDING_POLICY_INVALID")

    if decision.evidence_bound is not True:
        raise ValueError("EVIDENCE_BINDING_INVALID")

    if decision.network is not False:
        raise ValueError("NETWORK_DEPENDENCY_DETECTED")

    if decision.db_writes != 0:
        raise ValueError("DB_WRITES_DETECTED")

    if decision.production_db_touched is not False:
        raise ValueError("PRODUCTION_DB_TOUCHED")

    if decision.production_mutation is not False:
        raise ValueError("PRODUCTION_MUTATION_DETECTED")

    if decision.production_consumption_enabled is not False:
        raise ValueError(
            "PRODUCTION_CONSUMPTION_MUST_REMAIN_DISABLED"
        )

    if decision.execution != "DISABLED":
        raise ValueError("EXECUTION_MUST_REMAIN_DISABLED")

    if decision.order_intents_created != 0:
        raise ValueError("ORDER_INTENTS_CREATED")


# ============================================================
# SINGLE SELF-CHECK
# ============================================================

def self_check() -> CanonicalProviderDecision:

    decision = build_decision()

    validate_decision(decision)

    return decision


# ============================================================
# RUNTIME
# ============================================================

def main() -> int:

    try:
        decision = self_check()

    except Exception:
        print("ENGINE=CANONICAL_PROVIDER_DECISION")
        print("VERSION=v0.3")
        print("DECISION_TYPE=CANONICAL_PROVIDER_DECISION")
        print("PROVIDER=KUCOIN")
        print("ROLE=CANONICAL_ACTIVE")
        print("STATUS=CANONICAL_ACTIVE")
        print("QUALIFICATION_VERSION=v0.3")
        print("SELECTION_PROBE_VERSION=v0.1")
        print("DECISION_VERSION=v0.3")
        print(
            "EFFECTIVE_FROM="
            "2026-08-31T00:00:00+00:00"
        )
        print("TIMEFRAME=1h")
        print(
            "FAILOVER_POLICY="
            "NOT_YET_ACTIVATED"
        )
        print("BLENDING_POLICY=FORBIDDEN")
        print("EVIDENCE_BOUND=False")
        print("NETWORK=False")
        print("DB_WRITES=0")
        print("PRODUCTION_DB_TOUCHED=False")
        print("PRODUCTION_MUTATION=False")
        print(
            "PRODUCTION_CONSUMPTION_ENABLED=False"
        )
        print("EXECUTION=DISABLED")
        print("ORDER_INTENTS_CREATED=0")
        print("VALIDATION=FAIL")
        return 1

    print("ENGINE=CANONICAL_PROVIDER_DECISION")
    print("VERSION=v0.3")
    print(
        f"DECISION_TYPE={decision.decision_type}"
    )
    print(f"PROVIDER={decision.provider}")
    print(f"ROLE={decision.role}")
    print(f"STATUS={decision.status}")
    print(
        f"QUALIFICATION_VERSION="
        f"{decision.qualification_version}"
    )
    print(
        f"SELECTION_PROBE_VERSION="
        f"{decision.selection_probe_version}"
    )
    print(
        f"DECISION_VERSION="
        f"{decision.decision_version}"
    )
    print(
        f"EFFECTIVE_FROM="
        f"{decision.effective_from}"
    )
    print(f"TIMEFRAME={decision.timeframe}")
    print(
        f"FAILOVER_POLICY="
        f"{decision.failover_policy}"
    )
    print(
        f"BLENDING_POLICY="
        f"{decision.blending_policy}"
    )
    print(
        f"EVIDENCE_BOUND="
        f"{decision.evidence_bound}"
    )
    print(f"NETWORK={decision.network}")
    print(f"DB_WRITES={decision.db_writes}")
    print(
        f"PRODUCTION_DB_TOUCHED="
        f"{decision.production_db_touched}"
    )
    print(
        f"PRODUCTION_MUTATION="
        f"{decision.production_mutation}"
    )
    print(
        f"PRODUCTION_CONSUMPTION_ENABLED="
        f"{decision.production_consumption_enabled}"
    )
    print(f"EXECUTION={decision.execution}")
    print(
        f"ORDER_INTENTS_CREATED="
        f"{decision.order_intents_created}"
    )
    print("VALIDATION=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())