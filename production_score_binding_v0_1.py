
# =============================================================================
# ARUNDA PRODUCTION SCORE BINDING v0.1
#
# PURPOSE
# -------
# Bind the CLOSED production signal engine output to:
#
#     score_producer.py v0.2
#
# ARCHITECTURE
# ------------
#
# PRODUCTION SIGNAL ENGINE v0.2
#          |
#          v
# VALIDATED SIGNALS
#          |
#          v
# SCORE PRODUCER v0.2
#          |
#          v
# REAL SCORE SNAPSHOT
#
# RULES
# -----
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
# FUSION = OFF
# DECISION = OFF
# ORDER_INTENTS = 0
# EXECUTION = OFF
# =============================================================================

from __future__ import annotations

import importlib
import math


# =============================================================================
# MODULES
# =============================================================================

production_binding = importlib.import_module(
    "production_signal_engine_binding_v0_2"
)

score_producer = importlib.import_module(
    "score_producer"
)


# =============================================================================
# CONSTANTS
# =============================================================================

EXPECTED_ASSETS = [
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "DOGE", "SHIB", "LINK", "AVAX", "DOT",
    "LTC", "UNI", "AAVE", "SUI", "NEAR",
]

EXPECTED_ASSET_COUNT = 15


# =============================================================================
# BUILD VALIDATED SIGNALS
# =============================================================================

def build_validated_signals():

    rows = production_binding.load_fabric_rows()

    grouped = production_binding.group_markets(
        rows
    )

    validated_signals = {}

    for asset in EXPECTED_ASSETS:

        candidates = []

        for key, market_rows in grouped.items():

            if key[0] != asset:
                continue

            source_id = str(key[2])

            if not source_id.startswith("KUCOIN"):
                continue

            candidates.append(
                (
                    key,
                    market_rows,
                )
            )

        if not candidates:
            raise RuntimeError(
                f"{asset}: no production KUCOIN market."
            )

        candidates.sort(
            key=lambda item: len(item[1]),
            reverse=True,
        )

        _, selected_rows = candidates[0]

        result = production_binding.process_market(
            asset,
            selected_rows,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                f"{asset}: invalid market binding result."
            )

        signal = result.get("signal")

        if not isinstance(signal, dict):
            raise RuntimeError(
                f"{asset}: missing production signal."
            )

        if result.get("valid") is not True:
            raise RuntimeError(
                f"{asset}: production signal is not valid: "
                f"{result.get('validation')}"
            )

        if signal.get("asset") != asset:
            raise RuntimeError(
                f"{asset}: signal asset mismatch."
            )

        signal_state = signal.get(
            "signal_state"
        )

        direction = signal.get(
            "direction"
        )

        if signal_state not in (
            "ACTIVE",
            "NEUTRAL",
        ):
            raise RuntimeError(
                f"{asset}: invalid signal_state."
            )

        if direction not in (
            "LONG",
            "SHORT",
            "NONE",
        ):
            raise RuntimeError(
                f"{asset}: invalid direction."
            )

        validated_signals[asset] = {
            **signal,
            "asset": asset,
            "valid": True,
        }

    return validated_signals


# =============================================================================
# VALIDATION
# =============================================================================

def validate_binding_input(
    validated_signals,
):

    score_producer.validate_validated_signals(
        validated_signals
    )

    if set(validated_signals.keys()) != set(
        EXPECTED_ASSETS
    ):
        raise RuntimeError(
            "Validated signal asset contract failed."
        )

    if len(validated_signals) != EXPECTED_ASSET_COUNT:
        raise RuntimeError(
            "Validated signal count mismatch."
        )


# =============================================================================
# SCORE RUNTIME
# =============================================================================

def run():

    print("=" * 90)
    print(
        "ARUNDA PRODUCTION SCORE BINDING v0.1"
    )
    print("=" * 90)

    print(
        "SIGNAL SOURCE          : "
        "PRODUCTION_SIGNAL_ENGINE_BINDING_v0.2"
    )

    print(
        "SCORE SOURCE           : SCORE_PRODUCER_v0.2"
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
        "DECISION               : OFF"
    )

    print(
        "ORDER_INTENTS          : 0"
    )

    print(
        "EXECUTION              : OFF"
    )

    print()

    # =========================================================================
    # STEP 1 — PRODUCTION VALIDATED SIGNALS
    # =========================================================================

    print(
        "[1/3] PRODUCTION VALIDATED SIGNALS"
    )

    validated_signals = (
        build_validated_signals()
    )

    validate_binding_input(
        validated_signals
    )

    print(
        "  Validated Signals    : PASS"
    )

    print(
        "  Assets               :",
        len(validated_signals)
    )

    # =========================================================================
    # STEP 2 — SCORE PRODUCER
    # =========================================================================

    print()

    print(
        "[2/3] REAL SCORE GENERATION"
    )

    scores = score_producer.run(
        validated_signals
    )

    if not isinstance(
        scores,
        dict,
    ):
        raise RuntimeError(
            "Score Producer returned invalid object."
        )

    # =========================================================================
    # STEP 3 — FINAL VALIDATION
    # =========================================================================

    print()

    print(
        "[3/3] FINAL SCORE CONTRACT"
    )

    score_producer.validate_score_snapshot(
        scores
    )

    for asset in EXPECTED_ASSETS:

        item = scores[asset]

        score = float(
            item["score"]
        )

        if not math.isfinite(score):
            raise RuntimeError(
                f"{asset}: non-finite score."
            )

    # =========================================================================
    # RESULT
    # =========================================================================

    print()
    print("=" * 90)
    print(
        "PRODUCTION SCORE BINDING RESULT"
    )
    print("=" * 90)

    print(
        "VALIDATED_SIGNALS=",
        len(validated_signals)
    )

    print(
        "SCORES=",
        len(scores)
    )

    print(
        "SCORE_CONTRACT=PASS"
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
        "DECISION=OFF"
    )

    print(
        "ORDER_INTENTS=0"
    )

    print(
        "EXECUTION=OFF"
    )

    print(
        "STATUS=PRODUCTION_SCORE_BINDING_PASS"
    )

    print()

    for asset in EXPECTED_ASSETS:

        item = scores[asset]

        print(
            "{} | {} | {} | SCORE={}".format(
                asset,
                item["signal_state"],
                item["direction"],
                item["score"],
            )
        )

    print()

    return scores


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    run()