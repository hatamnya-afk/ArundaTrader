# FUSION_RUNTIME_MARKET_CONTRIBUTION_TO_PERSISTED_SIGNAL_FORENSIC_v0.1.py

import os
import sys
import sqlite3
import importlib.util
import traceback
from datetime import datetime, timezone


DB_PATH = os.path.abspath("arunda.db")
FUSION_ENGINE_PATH = os.path.abspath("fusion_engine.py")

EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]


# =============================================================================
# HEADER
# =============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


print("=" * 90)
print(
    "ARUNDA FUSION RUNTIME MARKET CONTRIBUTION "
    "TO PERSISTED SIGNAL FORENSIC v0.1"
)
print("=" * 90)
print(f"Started UTC : {utc_now()}")
print(f"Database    : {DB_PATH}")
print("Mode        : READ ONLY FORENSIC")
print("Writes      : NONE FROM HARNESS")
print("=" * 90)


# =============================================================================
# TRACE STATE
# =============================================================================

TRACE = {
    asset: {
        "row_id": None,
        "technical_score": None,
        "market_norm": None,
        "market_weight": None,
        "market_contribution": None,
        "calculate_fused_score_output": None,
    }
    for asset in EXPECTED_ASSETS
}

CURRENT_ASSET = {
    "value": None
}


# =============================================================================
# LOAD PRODUCTION
# =============================================================================

if not os.path.exists(FUSION_ENGINE_PATH):
    raise RuntimeError(
        f"Production module not found: {FUSION_ENGINE_PATH}"
    )

if not os.path.exists(DB_PATH):
    raise RuntimeError(
        f"Database not found: {DB_PATH}"
    )


spec = importlib.util.spec_from_file_location(
    "fusion_engine_production",
    FUSION_ENGINE_PATH,
)

if spec is None or spec.loader is None:
    raise RuntimeError(
        "Unable to create production module spec."
    )


production = importlib.util.module_from_spec(spec)

sys.modules[
    "fusion_engine_production"
] = production

spec.loader.exec_module(production)


print()
print("Production module : LOADED")
print(
    f"ENGINE_VERSION    : "
    f"{production.ENGINE_VERSION}"
)


# =============================================================================
# CONTROL CONNECTION
#
# This connection belongs exclusively to the forensic harness.
# It is NEVER passed into production main().
# =============================================================================

control_conn = sqlite3.connect(DB_PATH)
control_conn.row_factory = sqlite3.Row

print()
print("CONTROL DATABASE CONNECTION : OK")


# =============================================================================
# BASELINE
# =============================================================================

before_rows = control_conn.execute(
    """
    SELECT
        id
    FROM fusion_signals
    ORDER BY id
    """
).fetchall()

before_ids = {
    int(row["id"])
    for row in before_rows
}

before_count = len(before_ids)

print(
    f"fusion_signals baseline rows : {before_count}"
)


# =============================================================================
# INSTRUMENTATION
# =============================================================================

print()
print("-" * 78)
print("INSTALLING RUNTIME INSTRUMENTATION")
print("-" * 78)


# -----------------------------------------------------------------------------
# 1. get_latest_market()
# -----------------------------------------------------------------------------

_original_get_latest_market = (
    production.get_latest_market
)


def traced_get_latest_market(
    conn,
    asset,
):

    CURRENT_ASSET["value"] = asset

    row = _original_get_latest_market(
        conn,
        asset,
    )

    if asset not in TRACE:
        TRACE[asset] = {
            "row_id": None,
            "technical_score": None,
            "market_norm": None,
            "market_weight": None,
            "market_contribution": None,
            "calculate_fused_score_output": None,
        }

    if row is None:

        print(
            f"[TRACE MARKET ROW] "
            f"{asset:<8} -> NOT FOUND"
        )

        return row

    TRACE[asset][
        "row_id"
    ] = row["id"]

    TRACE[asset][
        "technical_score"
    ] = row["technical_score"]

    print()
    print(
        f"[TRACE MARKET ROW] "
        f"{asset:<8} -> FOUND"
    )

    print(
        f"    row.id          = {row['id']}"
    )

    print(
        f"    technical_score = "
        f"{row['technical_score']}"
    )

    return row


production.get_latest_market = (
    traced_get_latest_market
)


# -----------------------------------------------------------------------------
# 2. normalize_market()
# -----------------------------------------------------------------------------

_original_normalize_market = (
    production.normalize_market
)


def traced_normalize_market(
    score,
):

    result = _original_normalize_market(
        score
    )

    asset = CURRENT_ASSET["value"]

    if asset in TRACE:

        TRACE[asset][
            "market_norm"
        ] = result

        print()
        print(
            f"[TRACE MARKET NORMALIZATION] "
            f"{asset:<8}"
        )

        print(
            f"    input technical_score = "
            f"{score}"
        )

        print(
            f"    market_norm           = "
            f"{result}"
        )

    return result


production.normalize_market = (
    traced_normalize_market
)


# -----------------------------------------------------------------------------
# 3. calculate_fused_score()
# -----------------------------------------------------------------------------

_original_calculate_fused_score = (
    production.calculate_fused_score
)


def traced_calculate_fused_score(
    market_norm,
    positioning_norm,
    news_norm,
    weights,
    missing_penalty,
):

    asset = CURRENT_ASSET["value"]

    market_weight = (
        weights.get("market")
        if weights is not None
        else None
    )

    market_contribution = None

    if (
        market_norm is not None
        and market_weight is not None
    ):

        market_contribution = (
            market_norm
            * market_weight
        )

    if asset in TRACE:

        TRACE[asset][
            "market_weight"
        ] = market_weight

        TRACE[asset][
            "market_contribution"
        ] = market_contribution

    print()
    print(
        f"[TRACE MARKET CONTRIBUTION] "
        f"{asset:<8}"
    )

    print(
        f"    market_norm        = "
        f"{market_norm}"
    )

    print(
        f"    market_weight      = "
        f"{market_weight}"
    )

    print(
        f"    market_contribution = "
        f"{market_contribution}"
    )

    # -------------------------------------------------------------------------
    # REAL production calculation
    # -------------------------------------------------------------------------

    result = _original_calculate_fused_score(
        market_norm,
        positioning_norm,
        news_norm,
        weights,
        missing_penalty,
    )

    if asset in TRACE:

        TRACE[asset][
            "calculate_fused_score_output"
        ] = result

    print(
        f"    fused_score RETURN = "
        f"{result}"
    )

    return result


production.calculate_fused_score = (
    traced_calculate_fused_score
)


print(
    "Instrumentation : READY"
)


# =============================================================================
# REAL PRODUCTION MAIN()
# =============================================================================

print()
print("-" * 78)
print("STARTING REAL fusion_engine.main()")
print("-" * 78)


runtime_exception = None
main_return = None


try:

    main_return = production.main()

    print()
    print(
        "REAL fusion_engine.main() : RETURNED"
    )

    print(
        f"main() return value : "
        f"{main_return}"
    )

except Exception as exc:

    runtime_exception = exc

    print()
    print(
        "REAL fusion_engine.main() : EXCEPTION"
    )

    print(
        f"{type(exc).__name__}: {exc}"
    )

    traceback.print_exc()


# =============================================================================
# IMPORTANT
# =============================================================================
#
# We do NOT touch the production connection.
#
# fusion_engine.main() owns its connection.
#
# The harness uses only control_conn.
# =============================================================================


print()
print("-" * 78)
print("READING PERSISTED fusion_signals")
print("-" * 78)


after_rows = control_conn.execute(
    """
    SELECT
        id,
        asset,
        market_score,
        positioning_score,
        news_score,
        market_weight,
        positioning_weight,
        news_weight,
        fused_score,
        confidence,
        regime,
        data_quality,
        market_available,
        positioning_available,
        news_available,
        engine_version,
        snapshot_id,
        missing_arm_penalty,
        news_confidence,
        signal_strength,
        entry_price,
        direction,
        market_score_norm,
        positioning_score_norm,
        news_score_norm,
        agreement_score,
        available_weight
    FROM fusion_signals
    ORDER BY id
    """
).fetchall()


# =============================================================================
# FIND RUNTIME-NEW ROWS
# =============================================================================

runtime_rows = [
    row
    for row in after_rows
    if int(row["id"]) not in before_ids
]


persisted_by_asset = {}

for row in runtime_rows:

    asset = row["asset"]

    persisted_by_asset[
        asset
    ] = row


# =============================================================================
# FINAL TRACE TABLE
# =============================================================================

print()
print("=" * 90)
print(
    "FINAL MARKET CONTRIBUTION PROPAGATION TRACE"
)
print("=" * 90)

print()

print(
    f"{'ASSET':<8}"
    f"{'ROW.ID':>10}"
    f"{'TECH':>12}"
    f"{'NORM':>12}"
    f"{'M.WEIGHT':>13}"
    f"{'CONTRIBUTION':>18}"
    f"{'CALC.FUSED':>18}"
    f"{'PERSISTED':>12}"
)

print("-" * 103)


for asset in EXPECTED_ASSETS:

    trace = TRACE[asset]

    persisted = (
        persisted_by_asset.get(
            asset
        )
    )

    print(
        f"{asset:<8}"
        f"{str(trace['row_id']):>10}"
        f"{str(trace['technical_score']):>12}"
        f"{str(trace['market_norm']):>12}"
        f"{str(trace['market_weight']):>13}"
        f"{str(trace['market_contribution']):>18}"
        f"{str(trace['calculate_fused_score_output']):>18}"
        f"{'YES' if persisted else 'NO':>12}"
    )


# =============================================================================
# DETAILED PERSISTENCE IDENTITY
# =============================================================================

print()
print("=" * 90)
print(
    "PERSISTED SIGNAL IDENTITY VERIFICATION"
)
print("=" * 90)


all_verified = (
    runtime_exception is None
    and main_return is None
)


for asset in EXPECTED_ASSETS:

    trace = TRACE[asset]

    persisted = (
        persisted_by_asset.get(
            asset
        )
    )

    print()
    print(
        f"{asset}"
    )

    checks = []


    # -------------------------------------------------------------------------
    # Runtime trace exists
    # -------------------------------------------------------------------------

    checks.append(
        (
            "runtime market row",
            trace["row_id"] is not None
        )
    )


    checks.append(
        (
            "technical_score captured",
            trace["technical_score"] is not None
        )
    )


    checks.append(
        (
            "market_norm captured",
            trace["market_norm"] is not None
        )
    )


    checks.append(
        (
            "market_weight captured",
            trace["market_weight"] is not None
        )
    )


    checks.append(
        (
            "market contribution captured",
            trace["market_contribution"] is not None
        )
    )


    checks.append(
        (
            "calculate_fused_score output captured",
            trace[
                "calculate_fused_score_output"
            ] is not None
        )
    )


    # -------------------------------------------------------------------------
    # Persistence exists
    # -------------------------------------------------------------------------

    checks.append(
        (
            "fusion_signals row persisted",
            persisted is not None
        )
    )


    if persisted is not None:

        # -------------------------------------------------------------
        # Asset identity
        # -------------------------------------------------------------

        checks.append(
            (
                "asset identity",
                persisted["asset"] == asset
            )
        )


        # -------------------------------------------------------------
        # Technical score identity
        # -------------------------------------------------------------

        checks.append(
            (
                "market_score identity",
                persisted[
                    "market_score"
                ]
                ==
                trace[
                    "technical_score"
                ]
            )
        )


        # -------------------------------------------------------------
        # Normalized market identity
        # -------------------------------------------------------------

        checks.append(
            (
                "market_score_norm identity",
                persisted[
                    "market_score_norm"
                ]
                ==
                trace[
                    "market_norm"
                ]
            )
        )


        # -------------------------------------------------------------
        # Market weight identity
        # -------------------------------------------------------------

        checks.append(
            (
                "market_weight identity",
                persisted[
                    "market_weight"
                ]
                ==
                trace[
                    "market_weight"
                ]
            )
        )


        # -------------------------------------------------------------
        # Fused score identity
        # -------------------------------------------------------------

        checks.append(
            (
                "fused_score identity",
                persisted[
                    "fused_score"
                ]
                ==
                trace[
                    "calculate_fused_score_output"
                ]
            )
        )


        # -------------------------------------------------------------
        # Engine identity
        # -------------------------------------------------------------

        checks.append(
            (
                "engine_version",
                persisted[
                    "engine_version"
                ]
                ==
                production.ENGINE_VERSION
            )
        )


    asset_verified = all(
        result
        for _, result in checks
    )


    if not asset_verified:

        all_verified = False


    for label, result in checks:

        print(
            f"    {label:<45}"
            f"{'OK' if result else 'FAILED'}"
        )


# =============================================================================
# RUNTIME ROW COUNT
# =============================================================================

print()
print("-" * 90)
print(
    "RUNTIME PERSISTENCE COUNT"
)
print("-" * 90)

print(
    f"Before rows : {before_count}"
)

print(
    f"After rows  : {len(after_rows)}"
)

print(
    f"Runtime new : {len(runtime_rows)}"
)

print(
    f"Expected    : {len(EXPECTED_ASSETS)}"
)


if len(runtime_rows) != len(
    EXPECTED_ASSETS
):

    all_verified = False


# =============================================================================
# FINAL VERDICT
# =============================================================================

print()
print("=" * 90)

if all_verified:

    print(
        "PROPAGATION = VERIFIED"
    )

    print()
    print(
        "Verified chain:"
    )

    print(
        "market_norm"
        " -> market contribution"
        " -> calculate_fused_score()"
        " -> fused_score"
        " -> fusion_signals"
    )

else:

    print(
        "PROPAGATION = FAILED"
    )

print("=" * 90)


# =============================================================================
# HARNESS CLEANUP
# =============================================================================

print()
print(
    "HARNESS CONNECTION CLEANUP"
)

try:

    control_conn.close()

    print(
        "Control connection : CLOSED"
    )

except Exception as exc:

    print(
        "Control connection cleanup error:"
        f" {type(exc).__name__}: {exc}"
    )


print()
print(
    "Production connection ownership : "
    "fusion_engine.main()"
)

print(
    "Harness production-connection action : NONE"
)

print()
print("=" * 90)

if all_verified:

    print(
        "VERDICT : MARKET CONTRIBUTION "
        "TO PERSISTED SIGNAL = VERIFIED"
    )

else:

    print(
        "VERDICT : MARKET CONTRIBUTION "
        "TO PERSISTED SIGNAL = FAILED"
    )

print("=" * 90)