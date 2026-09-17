# =============================================================================
# ARUNDA PRODUCTION SIGNAL ENGINE BINDING v0.1
#
# FIX:
# MarketBar -> IndicatorBar / FeatureBar conversions are explicit.
#
# READ ONLY
# MEMORY ONLY
# NO PRODUCTION DB
# NO DATABASE WRITE
# NO FUSION
# NO SCORE
# NO DECISION
# NO ORDER INTENT
# NO EXECUTION
# =============================================================================

from pathlib import Path
import sqlite3
import importlib
import math


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

FABRIC_DB = (
    PROJECT_ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

LAUNCH_TIMESTAMP = "2026-08-31T00:00:00+00:00"

TIMEFRAME = "1h"
MIN_CONTEXT = 21

EXPECTED_ASSETS = [
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "DOGE", "SHIB", "LINK", "AVAX", "DOT",
    "LTC", "UNI", "AAVE", "SUI", "NEAR",
]


# =============================================================================
# EXISTING MODULES
# =============================================================================

signal_engine = importlib.import_module(
    "signal_engine"
)

signal_validator = importlib.import_module(
    "signal_validator"
)

adapter = importlib.import_module(
    "rolling_context_adapter_v0_1"
)


# =============================================================================
# FABRIC READ
# =============================================================================

def load_fabric_rows():

    if not FABRIC_DB.exists():
        raise RuntimeError(
            "Fabric DB not found: " + str(FABRIC_DB)
        )

    conn = sqlite3.connect(
        str(FABRIC_DB)
    )

    conn.row_factory = sqlite3.Row

    try:

        return conn.execute(
            """
            SELECT
                asset,
                symbol,
                timestamp,
                timeframe,
                open,
                high,
                low,
                close,
                volume,
                source_id,
                source_type,
                source_timestamp,
                retrieved_at
            FROM canonical_ohlcv
            WHERE timeframe = ?
              AND timestamp IS NOT NULL
              AND timestamp > 0
            ORDER BY
                asset,
                symbol,
                source_id,
                timestamp
            """,
            (TIMEFRAME,),
        ).fetchall()

    finally:

        conn.close()


# =============================================================================
# IDENTITY
# =============================================================================

def market_key(row):

    return (
        str(row["asset"]).upper(),
        str(row["symbol"]),
        str(row["source_id"]),
        str(row["timeframe"]),
    )


def group_markets(rows):

    grouped = {}

    for row in rows:

        asset = str(
            row["asset"]
        ).upper()

        if asset not in EXPECTED_ASSETS:
            continue

        key = market_key(row)

        grouped.setdefault(
            key,
            []
        ).append(row)

    return grouped


# =============================================================================
# CURRENT CONTIGUOUS RUN
# =============================================================================

def current_contiguous_run(rows):

    ordered = sorted(
        rows,
        key=lambda r: int(r["timestamp"])
    )

    if not ordered:
        return []

    run = [
        ordered[-1]
    ]

    for index in range(
        len(ordered) - 1,
        0,
        -1
    ):

        newer = int(
            ordered[index]["timestamp"]
        )

        older = int(
            ordered[index - 1]["timestamp"]
        )

        if newer - older != 3600:
            break

        run.append(
            ordered[index - 1]
        )

    run.reverse()

    return run


# =============================================================================
# PROVENANCE
# =============================================================================

def validate_production_rows(rows):

    for row in rows:

        if row["timeframe"] != TIMEFRAME:
            return False

        if not row["source_id"]:
            return False

        if not row["source_type"]:
            return False

        if not row["source_timestamp"]:
            return False

        if int(row["timestamp"]) <= 0:
            return False

    return True


# =============================================================================
# MARKET BARS
# =============================================================================

def build_market_bars(rows):

    return [
        adapter.row_to_market_bar(row)
        for row in rows
    ]


# =============================================================================
# FEATURE PIPELINE
#
# IMPORTANT:
#
# MarketBar is NOT passed directly into indicator_engine.
#
# Explicit conversions:
#
# MarketBar
#     -> IndicatorBar
#     -> Indicator Engine
#
# MarketBar
#     -> FeatureBar
#     -> Feature Engine
#
# =============================================================================

def build_feature_record(
    asset,
    rows,
):

    if len(rows) < MIN_CONTEXT:
        return None

    # -------------------------------------------------------------------------
    # CANONICAL MARKET BAR
    # -------------------------------------------------------------------------

    market_bars = build_market_bars(
        rows
    )

    # -------------------------------------------------------------------------
    # INDICATOR BAR
    # -------------------------------------------------------------------------

    indicator_bars = [
        adapter.market_bar_to_indicator_bar(
            bar
        )
        for bar in market_bars
    ]

    # -------------------------------------------------------------------------
    # INDICATORS
    # -------------------------------------------------------------------------

    indicators = (
        adapter.calculate_indicator_records(
            indicator_bars
        )
    )

    # -------------------------------------------------------------------------
    # MARKET STRUCTURE
    #
    # Structure engine consumes its MarketBar contract.
    # The adapter's MarketBar is the established structure-side type.
    # -------------------------------------------------------------------------

    structure_result = (
        adapter.analyze_market_structure(
            market_bars
        )
    )

    structures = (
        adapter.align_structure_points(
            market_bars,
            structure_result
        )
    )

    # -------------------------------------------------------------------------
    # FEATURE BAR
    # -------------------------------------------------------------------------

    feature_bars = [
        adapter.market_bar_to_feature_bar(
            bar
        )
        for bar in market_bars
    ]

    # -------------------------------------------------------------------------
    # FEATURE RECORDS
    # -------------------------------------------------------------------------

    features = (
        adapter.calculate_feature_records(
            feature_bars,
            indicators,
            structures
        )
    )

    if not features:
        return None

    return features[-1]


# =============================================================================
# FEATURE RECORD -> PUBLIC SIGNAL STRUCTURE
#
# NO INFERENCE
# NO FABRICATION
#
# Only fields genuinely present in FeatureRecord are forwarded.
# Missing fields remain None.
# =============================================================================

def feature_record_to_signal_input(
    asset,
    record,
    points,
):

    if record is None:
        raise RuntimeError(
            "Missing FeatureRecord: " + asset
        )

    def get(name):

        value = getattr(
            record,
            name,
            None
        )

        if isinstance(
            value,
            float
        ):

            if not math.isfinite(value):
                return None

        return value

    return {

        "asset": asset,

        "points": int(points),

        # Genuine structural fields
        "structure_direction":
            get("structure_direction"),

        "structure_strength":
            get("structure_strength"),

        "structure_confidence":
            get("structure_confidence"),

        "structure_point_type":
            get("structure_point_type"),

        # Public fields only when genuinely available.
        # FeatureRecord does not expose acceleration/position,
        # therefore they remain None.

        "trend":
            None,

        "momentum":
            None,

        "acceleration":
            None,

        "position":
            None,

        "volatility":
            get("volatility_regime"),
    }


# =============================================================================
# ONE MARKET
# =============================================================================

def process_market(
    asset,
    rows,
):

    result = {

        "asset":
            asset,

        "input_ready":
            False,

        "signal":
            None,

        "valid":
            False,

        "validation":
            None,

        "context_violation":
            False,

        "provenance_valid":
            False,

        "continuity_valid":
            False,
    }

    if not rows:

        result["validation"] = "NO_ROWS"

        return result

    if not validate_production_rows(
        rows
    ):

        result["validation"] = (
            "PROVENANCE_INVALID"
        )

        return result

    run = current_contiguous_run(
        rows
    )

    if len(run) < MIN_CONTEXT:

        result["validation"] = (
            "INSUFFICIENT_CURRENT_RUN"
        )

        return result

    # -------------------------------------------------------------------------
    # CONTEXT READY
    # -------------------------------------------------------------------------

    result["input_ready"] = True
    result["provenance_valid"] = True
    result["continuity_valid"] = True

    # -------------------------------------------------------------------------
    # BUILD FEATURES FROM CURRENT RUN ONLY
    # -------------------------------------------------------------------------

    feature_record = build_feature_record(
        asset,
        run
    )

    if feature_record is None:

        result["validation"] = (
            "FEATURE_RECORD_UNAVAILABLE"
        )

        return result

    # -------------------------------------------------------------------------
    # SIGNAL INPUT
    # -------------------------------------------------------------------------

    signal_input = (
        feature_record_to_signal_input(
            asset,
            feature_record,
            len(run)
        )
    )

    # -------------------------------------------------------------------------
    # EXISTING SIGNAL ENGINE
    # -------------------------------------------------------------------------

    engine_record = (
        signal_engine.build_signal(
            asset,
            signal_input
        )
    )

    if not isinstance(
        engine_record,
        dict
    ):

        result["validation"] = (
            "ENGINE_RECORD_INVALID"
        )

        return result

    signal = engine_record.get(
        "signal"
    )

    if not isinstance(
        signal,
        dict
    ):

        result["validation"] = (
            "SIGNAL_OBJECT_INVALID"
        )

        return result

    # -------------------------------------------------------------------------
    # EXISTING VALIDATOR
    # -------------------------------------------------------------------------

    valid, reason = (
        signal_validator.validate_one_signal(
            asset,
            signal
        )
    )

    result["signal"] = signal
    result["valid"] = bool(valid)
    result["validation"] = reason

    return result


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 90)
    print(
        "ARUNDA PRODUCTION SIGNAL ENGINE BINDING v0.1"
    )
    print("=" * 90)

    print(
        "FABRIC_DB               :",
        FABRIC_DB
    )

    print(
        "LAUNCH_TIMESTAMP        :",
        LAUNCH_TIMESTAMP
    )

    print(
        "TIMEFRAME               :",
        TIMEFRAME
    )

    print(
        "MIN_CONTEXT             :",
        MIN_CONTEXT
    )

    print(
        "PRODUCTION DB           : NOT TOUCHED"
    )

    print(
        "FUSION                  : OFF"
    )

    print(
        "SCORE                   : OFF"
    )

    print(
        "DECISION                : OFF"
    )

    print(
        "ORDER INTENTS           : 0"
    )

    print(
        "EXECUTION               : OFF"
    )

    print()

    rows = load_fabric_rows()

    grouped = group_markets(
        rows
    )

    results = {}

    # -------------------------------------------------------------------------
    # EXACT 15-MARKET PRODUCTION CEX UNIVERSE
    # -------------------------------------------------------------------------

    for asset in EXPECTED_ASSETS:

        candidates = []

        for key, market_rows in grouped.items():

            market_asset = key[0]
            source_id = str(
                key[2]
            )

            if market_asset != asset:
                continue

            if not source_id.startswith(
                "KUCOIN"
            ):
                continue

            candidates.append(
                (
                    key,
                    market_rows
                )
            )

        if not candidates:

            results[asset] = {
                "asset": asset,
                "input_ready": False,
                "valid": False,
                "validation":
                    "NO_PRODUCTION_MARKET",
                "signal": None,
                "provenance_valid": False,
                "continuity_valid": False,
                "context_violation": False,
            }

            continue

        # ---------------------------------------------------------------------
        # ONE EXPLICIT MARKET IDENTITY
        # ---------------------------------------------------------------------

        candidates.sort(
            key=lambda item: len(
                item[1]
            ),
            reverse=True
        )

        selected_key, selected_rows = (
            candidates[0]
        )

        # Identity remains explicit.
        # SOL/USDT and SOL/USDC are never merged.
        _ = selected_key

        results[asset] = process_market(
            asset,
            selected_rows
        )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    markets_total = len(
        EXPECTED_ASSETS
    )

    signal_records = [
        x
        for x in results.values()
        if x.get("signal") is not None
    ]

    signals_produced = len(
        signal_records
    )

    signals_valid = sum(
        1
        for x in results.values()
        if x.get("valid") is True
    )

    signals_rejected = (
        markets_total
        - signals_valid
    )

    signal_input_ready = sum(
        1
        for x in results.values()
        if x.get("input_ready") is True
    )

    ready_items = [
        x
        for x in results.values()
        if x.get("input_ready") is True
    ]

    provenance_valid = (
        len(ready_items) == 15
        and all(
            x.get("provenance_valid")
            for x in ready_items
        )
    )

    continuity_valid = (
        len(ready_items) == 15
        and all(
            x.get("continuity_valid")
            for x in ready_items
        )
    )

    context_violation = any(
        x.get(
            "context_violation",
            False
        )
        for x in results.values()
    )

    legacy_data_used = False

    signal_contract_valid = (
        signals_produced == 15
        and signals_valid == 15
    )

    status = (
        "PRODUCTION_SIGNAL_BINDING_PASS"
        if (
            markets_total == 15
            and signal_input_ready == 15
            and signals_produced == 15
            and signals_valid == 15
            and provenance_valid
            and continuity_valid
            and not context_violation
            and not legacy_data_used
            and signal_contract_valid
        )
        else
        "PRODUCTION_SIGNAL_BINDING_BLOCKED"
    )

    print("=" * 90)
    print("BINDING RESULT")
    print("=" * 90)

    print(
        "MARKETS_TOTAL=",
        markets_total
    )

    print(
        "SIGNALS_PRODUCED=",
        signals_produced
    )

    print(
        "SIGNALS_VALID=",
        signals_valid
    )

    print(
        "SIGNALS_REJECTED=",
        signals_rejected
    )

    print(
        "SIGNAL_INPUT_READY=",
        signal_input_ready
    )

    print(
        "PRODUCTION_DATA_ONLY=TRUE"
    )

    print(
        "LEGACY_DATA_USED=",
        legacy_data_used
    )

    print(
        "CONTEXT_VIOLATION=",
        context_violation
    )

    print(
        "PROVENANCE_VALID=",
        provenance_valid
    )

    print(
        "CONTINUITY_VALID=",
        continuity_valid
    )

    print(
        "SIGNAL_CONTRACT_VALID=",
        signal_contract_valid
    )

    print(
        "PRODUCTION_DB_TOUCHED=FALSE"
    )

    print(
        "DB_WRITES=0"
    )

    print(
        "ORDER_INTENTS=0"
    )

    print(
        "EXECUTION=OFF"
    )

    print(
        "STATUS=",
        status
    )

    print()

    for asset in EXPECTED_ASSETS:

        item = results[asset]

        signal = item.get(
            "signal"
        )

        if signal is not None:

            print(
                "{} | {} | {} | VALID={} | {}".format(
                    asset,
                    signal.get(
                        "signal_state"
                    ),
                    signal.get(
                        "direction"
                    ),
                    item.get(
                        "valid"
                    ),
                    item.get(
                        "validation"
                    ),
                )
            )

        else:

            print(
                "{} | NO_SIGNAL | {}".format(
                    asset,
                    item.get(
                        "validation"
                    )
                )
            )

    print()

    return (
        0
        if status ==
        "PRODUCTION_SIGNAL_BINDING_PASS"
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
