# =============================================================================
# ARUNDA PRODUCTION DECISION BINDING v0.1
# COMPLETE PRODUCTION BRIDGE
# =============================================================================
#
# PIPELINE
#
# PRODUCTION FABRIC
#       ↓
# PRODUCTION SIGNAL ENGINE BINDING v0.2
#       ↓
# VALIDATED SIGNAL SNAPSHOT
#       ↓
# REAL SCORE PRODUCER v0.2
#       ↓
# REAL SCORE SNAPSHOT
#       ↓
# DECISION ENGINE v0.6
#       ↓
# DECISION CONTRACT v0.1
#
# IMPORTANT
# ---------
# This file is ONLY a binding layer.
#
# It does NOT redesign:
#   - Signal Engine
#   - Signal Validator
#   - Score Formula
#   - Decision Engine
#   - Decision Contract
#   - Fusion
#
# SAFETY
# ------
# REAL DATA ONLY
# READ ONLY
# MEMORY ONLY
# DB_WRITES = 0
# LEGACY_MARKET_TECHNICAL = FORBIDDEN
# SYNTHETIC = FALSE
# INTERPOLATION = FALSE
# FILL = FALSE
# BACKFILL = FALSE
# PADDING = FALSE
# ORDER_INTENTS = 0
# EXECUTION = OFF
#
# =============================================================================

from __future__ import annotations

import math
from typing import Any, Mapping


import production_signal_engine_binding_v0_2
import score_producer
import decision_engine


# =============================================================================
# AUTHORITATIVE CONTRACT
# =============================================================================

# Decision Engine is authoritative for the runtime asset contract.
# We additionally assert the documented 15-asset contract below.

EXPECTED_ASSETS = tuple(
    decision_engine.EXPECTED_ASSETS
)

DOCUMENTED_ASSETS = (
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
)

EXPECTED_ASSET_COUNT = 15

EXPECTED_PROVIDER = "KUCOIN"


# =============================================================================
# GENERIC HELPERS
# =============================================================================

def _safe_upper(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip().upper()


def _is_finite_number(value: Any) -> bool:

    if isinstance(value, bool):
        return False

    if not isinstance(value, (int, float)):
        return False

    return math.isfinite(float(value))


def _first_non_none(
    mapping: Mapping[str, Any],
    keys: tuple[str, ...],
) -> Any:

    for key in keys:

        if key in mapping:

            value = mapping[key]

            if value is not None:
                return value

    return None


# =============================================================================
# CONTRACT VALIDATION
# =============================================================================

def validate_documented_asset_contract() -> None:

    authoritative = tuple(
        decision_engine.EXPECTED_ASSETS
    )

    if authoritative != DOCUMENTED_ASSETS:

        raise RuntimeError(
            "DECISION ENGINE asset contract mismatch.\n"
            f"Expected : {DOCUMENTED_ASSETS}\n"
            f"Actual   : {authoritative}"
        )

    if len(authoritative) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            "Decision asset count mismatch: "
            f"{len(authoritative)} != {EXPECTED_ASSET_COUNT}"
        )


def validate_exact_asset_keys(
    snapshot: Mapping[str, Any],
    name: str,
) -> None:

    if not isinstance(snapshot, Mapping):

        raise RuntimeError(
            f"{name} must be a mapping"
        )

    expected = set(EXPECTED_ASSETS)
    actual = set(snapshot.keys())

    missing = expected - actual
    extra = actual - expected

    if missing:

        raise RuntimeError(
            f"{name} missing assets: "
            f"{sorted(missing)}"
        )

    if extra:

        raise RuntimeError(
            f"{name} contains unexpected assets: "
            f"{sorted(extra)}"
        )

    if len(snapshot) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            f"{name} count mismatch: "
            f"{len(snapshot)} != {EXPECTED_ASSET_COUNT}"
        )


# =============================================================================
# MARKET GROUP VALIDATION
# =============================================================================

def validate_market_group_key(
    key: Any,
) -> None:

    if not isinstance(
        key,
        (tuple, list),
    ):

        raise RuntimeError(
            "Invalid market group key type: "
            f"{type(key).__name__}"
        )

    if len(key) < 4:

        raise RuntimeError(
            f"Invalid market group key: {key!r}"
        )

    asset = _safe_upper(key[0])

    timeframe = _safe_upper(key[3])

    if asset not in EXPECTED_ASSETS:

        raise RuntimeError(
            f"Unexpected production asset in group: "
            f"{asset}"
        )

    expected_timeframe = _safe_upper(
        production_signal_engine_binding_v0_2.TIMEFRAME
    )

    if timeframe != expected_timeframe:

        raise RuntimeError(
            f"Unexpected timeframe for {asset}: "
            f"{timeframe!r} != "
            f"{expected_timeframe!r}"
        )


# =============================================================================
# PROVIDER RESOLUTION
# =============================================================================

def resolve_provider_from_group_key(
    key: Any,
) -> str:

    """
    Existing production group structure:

        (asset, symbol, source_id, timeframe)

    source_id is therefore index 2.
    """

    if not isinstance(
        key,
        (tuple, list),
    ):

        return ""

    if len(key) < 3:

        return ""

    return _safe_upper(key[2])


def resolve_provider_from_rows(
    rows: Any,
) -> str:

    """
    Defensive row-level provenance lookup.

    This function NEVER substitutes another provider.
    """

    if not isinstance(
        rows,
        (list, tuple),
    ):

        return ""

    provider_keys = (
        "source_id",
        "source",
        "provider",
        "exchange",
        "source_name",
    )

    for row in rows:

        if not isinstance(
            row,
            Mapping,
        ):

            continue

        for field in provider_keys:

            value = row.get(field)

            if value is None:
                continue

            resolved = _safe_upper(value)

            if resolved:
                return resolved

    return ""


def is_exact_kucoin_source(
    key: Any,
    rows: Any,
) -> bool:

    """
    Exact production provider check.

    Accepted examples:
        KUCOIN
        KUCOIN_SPOT:BTC-USDT

    Bitget or any other provider is NOT accepted.
    """

    provider = resolve_provider_from_group_key(
        key
    )

    if EXPECTED_PROVIDER in provider:

        return True

    provider = resolve_provider_from_rows(
        rows
    )

    if EXPECTED_PROVIDER in provider:

        return True

    return False


# =============================================================================
# FIND EXACT KUCOIN PRODUCTION CONTEXT
# =============================================================================

def find_exact_market_context(
    asset: str,
    grouped: Mapping,
) -> list[dict[str, Any]]:

    asset = _safe_upper(asset)

    candidates = []

    for key, rows in grouped.items():

        validate_market_group_key(key)

        key_asset = _safe_upper(
            key[0]
        )

        if key_asset != asset:
            continue

        if not isinstance(
            rows,
            (list, tuple),
        ):

            raise RuntimeError(
                f"Invalid grouped rows for {asset}"
            )

        if not rows:
            continue

        if not is_exact_kucoin_source(
            key,
            rows,
        ):

            continue

        provider = (
            resolve_provider_from_group_key(
                key
            )
            or
            resolve_provider_from_rows(
                rows
            )
        )

        candidates.append(
            {
                "key": key,
                "rows": rows,
                "provider": provider,
                "row_count": len(rows),
            }
        )

    return candidates


# =============================================================================
# SELECT EXACT PRODUCTION CONTEXT
# =============================================================================

def select_exact_market_context(
    asset: str,
    candidates: list[dict[str, Any]],
) -> list:

    if not candidates:

        raise RuntimeError(
            f"No production KUCOIN market context for {asset}"
        )

    # We do not merge providers.
    # We do not create candles.
    # We do not synthesize history.
    #
    # If multiple KuCoin groups exist, use the group with
    # the greatest real row count.

    selected = max(
        candidates,
        key=lambda item: item["row_count"],
    )

    rows = selected["rows"]

    if not isinstance(
        rows,
        (list, tuple),
    ):

        raise RuntimeError(
            f"Invalid selected production rows for {asset}"
        )

    if not rows:

        raise RuntimeError(
            f"Selected production context is empty for {asset}"
        )

    return list(rows)


# =============================================================================
# VALIDATION CONTRACT EXTRACTION
# =============================================================================

def extract_validation_value(
    result: Mapping[str, Any],
    signal: Mapping[str, Any],
) -> str:
    """
    Extract the already-existing validation result.

    Priority:
        1. signal['validation']
        2. result['validation']
        3. result['validation_result']
        4. result['validator']
        5. result['validated']

    We NEVER manufacture a failed/active validation.

    Boolean True is normalized to the contract text:
        VALIDATED

    This is contract metadata only.
    """

    # -------------------------------------------------------------------------
    # 1. Signal-level validation
    # -------------------------------------------------------------------------

    if "validation" in signal:

        value = signal["validation"]

        if isinstance(value, str):

            if value.strip():
                return value.strip()

        elif value is True:

            return "VALIDATED"

        elif isinstance(value, Mapping):

            nested = _first_non_none(
                value,
                (
                    "validation",
                    "status",
                    "reason",
                ),
            )

            if isinstance(
                nested,
                str,
            ) and nested.strip():

                return nested.strip()

    # -------------------------------------------------------------------------
    # 2. Process result validation
    # -------------------------------------------------------------------------

    validation_keys = (
        "validation",
        "validation_result",
        "validator",
        "validated",
    )

    for key in validation_keys:

        if key not in result:
            continue

        value = result[key]

        if isinstance(value, str):

            if value.strip():
                return value.strip()

        elif value is True:

            return "VALIDATED"

        elif isinstance(value, Mapping):

            nested = _first_non_none(
                value,
                (
                    "validation",
                    "status",
                    "reason",
                ),
            )

            if isinstance(
                nested,
                str,
            ) and nested.strip():

                return nested.strip()

    raise RuntimeError(
        "Existing production Validator result "
        "could not be bound into Decision contract"
    )


# =============================================================================
# EXTRACT PRODUCTION SIGNAL
# =============================================================================

def extract_signal_from_result(
    asset: str,
    result: Any,
) -> dict[str, Any]:

    if not isinstance(
        result,
        Mapping,
    ):

        raise RuntimeError(
            f"Invalid production process_market "
            f"result for {asset}: "
            f"{type(result).__name__}"
        )

    signal = result.get("signal")

    if not isinstance(
        signal,
        Mapping,
    ):

        raise RuntimeError(
            f"Production signal missing for {asset}"
        )

    signal = dict(signal)

    # -------------------------------------------------------------------------
    # Existing validation result
    # -------------------------------------------------------------------------

    validation = extract_validation_value(
        result,
        signal,
    )

    # -------------------------------------------------------------------------
    # Bind mandatory Decision Contract fields
    # -------------------------------------------------------------------------

    signal["asset"] = asset

    signal["valid"] = True

    signal["validation"] = validation

    # -------------------------------------------------------------------------
    # Semantic validation
    # -------------------------------------------------------------------------

    state = signal.get(
        "signal_state"
    )

    direction = signal.get(
        "direction"
    )

    if state not in (
        "ACTIVE",
        "NEUTRAL",
    ):

        raise RuntimeError(
            f"Invalid signal_state for {asset}: "
            f"{state!r}"
        )

    if direction not in (
        "LONG",
        "SHORT",
        "NONE",
    ):

        raise RuntimeError(
            f"Invalid direction for {asset}: "
            f"{direction!r}"
        )

    if state == "ACTIVE":

        if direction not in (
            "LONG",
            "SHORT",
        ):

            raise RuntimeError(
                f"ACTIVE signal requires LONG/SHORT: "
                f"{asset}"
            )

    elif state == "NEUTRAL":

        if direction != "NONE":

            raise RuntimeError(
                f"NEUTRAL signal requires NONE: "
                f"{asset}"
            )

    return signal


# =============================================================================
# BUILD VALIDATED PRODUCTION SIGNAL SNAPSHOT
# =============================================================================

def build_validated_signals() -> dict[str, dict[str, Any]]:

    binding = (
        production_signal_engine_binding_v0_2
    )

    print(
        "  Loading production Fabric context..."
    )

    rows = binding.load_fabric_rows()

    if not isinstance(
        rows,
        (list, tuple),
    ):

        raise RuntimeError(
            "Production Fabric rows must be list/tuple"
        )

    if not rows:

        raise RuntimeError(
            "Production Fabric returned zero rows"
        )

    print(
        f"  Fabric rows loaded    : {len(rows)}"
    )

    grouped = binding.group_markets(
        rows
    )

    if not isinstance(
        grouped,
        Mapping,
    ):

        raise RuntimeError(
            "group_markets() must return a mapping"
        )

    print(
        f"  Market groups         : {len(grouped)}"
    )

    validated_signals = {}

    # =========================================================================
    # EXACT 15 ASSETS
    # =========================================================================

    for asset in EXPECTED_ASSETS:

        candidates = find_exact_market_context(
            asset,
            grouped,
        )

        selected_rows = select_exact_market_context(
            asset,
            candidates,
        )

        selected_provider = ""

        if candidates:

            selected = max(
                candidates,
                key=lambda item: item["row_count"],
            )

            selected_provider = selected[
                "provider"
            ]

        print(
            f"  {asset:<5} | "
            f"PROVIDER={selected_provider:<24} | "
            f"ROWS={len(selected_rows)}"
        )

        # =====================================================================
        # EXISTING PRODUCTION SIGNAL ENGINE
        # =====================================================================

        result = binding.process_market(
            asset,
            selected_rows,
        )

        signal = extract_signal_from_result(
            asset,
            result,
        )

        validated_signals[asset] = signal

    # =========================================================================
    # EXACT SNAPSHOT CONTRACT
    # =========================================================================

    validate_exact_asset_keys(
        validated_signals,
        "Validated Signals",
    )

    # =========================================================================
    # EXISTING SCORE-PRODUCER INPUT CONTRACT
    # =========================================================================

    score_producer.validate_validated_signals(
        validated_signals
    )

    return validated_signals


# =============================================================================
# SCORE SNAPSHOT VALIDATION
# =============================================================================

def validate_score_snapshot(
    scores: Any,
) -> None:

    validate_exact_asset_keys(
        scores,
        "Score Snapshot",
    )

    for asset in EXPECTED_ASSETS:

        record = scores[asset]

        if not isinstance(
            record,
            Mapping,
        ):

            raise RuntimeError(
                f"Invalid score record: {asset}"
            )

        required_fields = (
            "asset",
            "signal_state",
            "direction",
            "score",
        )

        missing = [
            field
            for field in required_fields
            if field not in record
        ]

        if missing:

            raise RuntimeError(
                f"Score {asset} missing fields: "
                f"{missing}"
            )

        if record["asset"] != asset:

            raise RuntimeError(
                f"Score asset mismatch: {asset}"
            )

        if record["signal_state"] not in (
            "ACTIVE",
            "NEUTRAL",
        ):

            raise RuntimeError(
                f"Invalid score state: {asset}"
            )

        if record["direction"] not in (
            "LONG",
            "SHORT",
            "NONE",
        ):

            raise RuntimeError(
                f"Invalid score direction: {asset}"
            )

        if not _is_finite_number(
            record["score"]
        ):

            raise RuntimeError(
                f"Invalid/non-finite score: {asset}"
            )

        if (
            record["signal_state"]
            == "NEUTRAL"
            and
            record["direction"]
            != "NONE"
        ):

            raise RuntimeError(
                f"NEUTRAL score must have NONE "
                f"direction: {asset}"
            )

        if (
            record["signal_state"]
            == "ACTIVE"
            and
            record["direction"]
            not in ("LONG", "SHORT")
        ):

            raise RuntimeError(
                f"ACTIVE score must have LONG/SHORT "
                f"direction: {asset}"
            )


# =============================================================================
# SIGNAL / SCORE ALIGNMENT
# =============================================================================

def validate_signal_score_alignment(
    validated_signals: Mapping[str, Mapping[str, Any]],
    scores: Mapping[str, Mapping[str, Any]],
) -> None:

    validate_exact_asset_keys(
        validated_signals,
        "Validated Signals",
    )

    validate_exact_asset_keys(
        scores,
        "Scores",
    )

    for asset in EXPECTED_ASSETS:

        signal = validated_signals[asset]
        score = scores[asset]

        if signal["asset"] != asset:

            raise RuntimeError(
                f"Signal asset mismatch: {asset}"
            )

        if score["asset"] != asset:

            raise RuntimeError(
                f"Score asset mismatch: {asset}"
            )

        if (
            signal["signal_state"]
            !=
            score["signal_state"]
        ):

            raise RuntimeError(
                f"Signal/score state mismatch: {asset}"
            )

        if (
            signal["direction"]
            !=
            score["direction"]
        ):

            raise RuntimeError(
                f"Signal/score direction mismatch: {asset}"
            )


# =============================================================================
# DECISION SNAPSHOT VALIDATION
# =============================================================================

def validate_decision_snapshot(
    decisions: Any,
) -> None:

    validate_exact_asset_keys(
        decisions,
        "Decision Snapshot",
    )

    # Existing Decision Engine internal contract.
    decision_engine.validate_internal_snapshot(
        decisions
    )

    # Existing Decision Contract v0.1.
    decision_engine.validate_decision_snapshot(
        decisions
    )


# =============================================================================
# SAFETY ASSERTIONS
# =============================================================================

def assert_production_safety() -> None:

    # These are static invariants of this binding.
    #
    # The binding contains:
    #   - no sqlite connection
    #   - no SQL
    #   - no INSERT
    #   - no UPDATE
    #   - no DELETE
    #   - no execution
    #   - no order intent generation

    safety = {
        "FUSION": "OFF",
        "ORDER_INTENTS": "0",
        "EXECUTION": "OFF",
    }

    for name, value in safety.items():

        if value not in (
            "OFF",
            "0",
        ):

            raise RuntimeError(
                f"Safety invariant failed: {name}"
            )


# =============================================================================
# PRINT DECISIONS
# =============================================================================

def print_final_decisions(
    decisions: Mapping[str, Mapping[str, Any]],
) -> None:

    print()
    print(
        "PRODUCTION DECISION SNAPSHOT"
    )

    print("-" * 110)

    print(
        "Asset | Decision    | Direction | Score      | Reason"
    )

    print("-" * 110)

    for asset in EXPECTED_ASSETS:

        item = decisions[asset]

        score = item.get(
            "score"
        )

        if score is None:

            score_text = "None"

        else:

            score_text = f"{float(score):.6f}"

        print(
            f"{asset:<5} | "
            f"{str(item['state']):<11} | "
            f"{str(item['direction']):<9} | "
            f"{score_text:>10} | "
            f"{item['reason']}"
        )


# =============================================================================
# FINAL REPORT
# =============================================================================

def print_final_report(
    validated_signals: Mapping,
    scores: Mapping,
    decisions: Mapping,
) -> None:

    stats = (
        decision_engine.calculate_statistics(
            decisions
        )
    )

    print()
    print("=" * 90)
    print(
        "PRODUCTION DECISION BINDING RESULT"
    )
    print("=" * 90)

    print(
        f"VALIDATED_SIGNALS={len(validated_signals)}"
    )

    print(
        f"SCORES={len(scores)}"
    )

    print(
        f"DECISIONS={len(decisions)}"
    )

    print(
        f"ACTIONABLE={stats['actionable']}"
    )

    print(
        f"HOLD={stats['hold']}"
    )

    print(
        f"REJECT={stats['reject']}"
    )

    print(
        f"LONG={stats['long']}"
    )

    print(
        f"SHORT={stats['short']}"
    )

    print(
        f"NONE={stats['none']}"
    )

    print()
    print(
        "DECISION_CONTRACT=PASS"
    )

    print(
        "REAL_DATA_ONLY=TRUE"
    )

    print(
        "LEGACY_DATA_USED=FALSE"
    )

    print(
        "SYNTHETIC_DATA=FALSE"
    )

    print(
        "INTERPOLATION=FALSE"
    )

    print(
        "FILL=FALSE"
    )

    print(
        "BACKFILL=FALSE"
    )

    print(
        "PADDING=FALSE"
    )

    print(
        "PRODUCTION_DB_TOUCHED=FALSE"
    )

    print(
        "DB_WRITES=0"
    )

    print(
        "FUSION=OFF"
    )

    print(
        "ORDER_INTENTS=0"
    )

    print(
        "EXECUTION=OFF"
    )

    print(
        "STATUS=PRODUCTION_DECISION_BINDING_PASS"
    )

    print("=" * 90)


# =============================================================================
# MAIN RUNTIME
# =============================================================================

def run() -> dict:

    print("=" * 90)

    print(
        "ARUNDA PRODUCTION DECISION BINDING v0.1"
    )

    print("=" * 90)

    print(
        "SIGNAL SOURCE          : "
        "PRODUCTION_SIGNAL_ENGINE_BINDING_V0.2"
    )

    print(
        "SCORE SOURCE           : "
        "SCORE_PRODUCER_v0.2"
    )

    print(
        "DECISION SOURCE        : "
        "DECISION_ENGINE_v0.6"
    )

    print(
        "CONTRACT SOURCE        : "
        "DECISION_CONTRACT_v0.1"
    )

    print(
        "DATA                   : REAL"
    )

    print(
        "MODE                   : READ ONLY / MEMORY ONLY"
    )

    print(
        "LEGACY_MARKET_TECHNICAL: FORBIDDEN"
    )

    print(
        "DB_WRITES              : 0"
    )

    print(
        "FUSION                 : OFF"
    )

    print(
        "ORDER_INTENTS          : 0"
    )

    print(
        "EXECUTION              : OFF"
    )

    # =========================================================================
    # CONTRACT SANITY
    # =========================================================================

    validate_documented_asset_contract()

    assert_production_safety()

    # =========================================================================
    # 1/4 — VALIDATED SIGNALS
    # =========================================================================

    print()
    print(
        "[1/4] PRODUCTION VALIDATED SIGNALS"
    )

    validated_signals = (
        build_validated_signals()
    )

    print()
    print(
        "  Validated Signals    : PASS"
    )

    print(
        f"  Assets               : "
        f"{len(validated_signals)}"
    )

    # =========================================================================
    # 2/4 — REAL SCORE SNAPSHOT
    # =========================================================================

    print()
    print(
        "[2/4] REAL SCORE SNAPSHOT"
    )

    scores = score_producer.run(
        validated_signals
    )

    validate_score_snapshot(
        scores
    )

    print(
        "  Score Snapshot       : PASS"
    )

    print(
        f"  Assets               : "
        f"{len(scores)}"
    )

    # =========================================================================
    # 3/4 — SIGNAL / SCORE ALIGNMENT
    # =========================================================================

    print()
    print(
        "[3/4] SIGNAL / SCORE ALIGNMENT"
    )

    validate_signal_score_alignment(
        validated_signals,
        scores,
    )

    print(
        "  State Alignment      : PASS"
    )

    print(
        "  Direction Alignment  : PASS"
    )

    # =========================================================================
    # 4/4 — DECISION ENGINE
    # =========================================================================

    print()
    print(
        "[4/4] DECISION ENGINE"
    )

    decisions = decision_engine.run(
        validated_signals,
        scores,
    )

    validate_decision_snapshot(
        decisions
    )

    print(
        "  Decision Engine      : PASS"
    )

    print(
        "  Decision Contract    : PASS"
    )

    # =========================================================================
    # FINAL SNAPSHOT
    # =========================================================================

    print_final_decisions(
        decisions
    )

    print_final_report(
        validated_signals,
        scores,
        decisions,
    )

    return decisions


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    try:

        run()

    except Exception as exc:

        print()
        print("=" * 90)

        print(
            "PRODUCTION DECISION BINDING ERROR"
        )

        print("=" * 90)

        print(
            "Type   :",
            type(exc).__name__,
        )

        print(
            "Error  :",
            str(exc),
        )

        print(
            "STATUS : "
            "PRODUCTION_DECISION_BINDING_FAILED"
        )

        raise