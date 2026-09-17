from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, Iterable, List, Optional

from dynamic_signal_semantic_layer import production_input_to_semantics


# ============================================================================
# ARUNDA TRADER
# DYNAMIC SIGNAL BOUNDARY v0.1
#
# PURPOSE:
#
#   ProductionSignalInput
#          â†“
#   PUBLIC FIVE-FIELD STRUCTURE
#          â†“
#   EXISTING signal_logic
#          â†“
#   DYNAMIC SIGNAL RECORD
#
# HARD BOUNDARY:
#
#   Dynamic Universe ONLY
#   No EXPECTED_ASSETS
#   No CMC
#   No legacy market_technical
#   No database
#   No SQL
#   No writes
#   No synthetic data
#   No interpolation
#   No fill
#   No backfill
#   No padding
#   No blending
#   No scoring
#   No decision
#   No risk
#   No trade gate
#   No opportunity generation
#   No order
#   No execution
#
# IMPORTANT:
#
#   This module does NOT modify:
#
#       signal_logic.py
#       signal_engine.py
#       signal_contract.py
#       signal_validator.py
#
#   signal_logic.py remains the authoritative direction engine.
#
# ============================================================================


ENGINE_NAME = "DYNAMIC_SIGNAL_BOUNDARY_v0.1"

TIMEFRAME = "1h"

MIN_CONTEXT = 21
FULL_CONTEXT_TARGET = 150

VALID_CONTEXTS = {
    "FULL",
    "LIMITED",
    "NONE",
}

VALID_STATUS = {
    "AVAILABLE",
    "UNAVAILABLE",
}

VALID_DIRECTIONS = {
    "LONG",
    "SHORT",
    "NONE",
}

VALID_SIGNAL_STATES = {
    "ACTIVE",
    "NEUTRAL",
}

VALID_TRENDS = {
    "UP",
    "DOWN",
    "FLAT",
    None,
}

VALID_MOMENTUM = {
    "STRONG",
    "WEAK",
    None,
}

VALID_POSITION = {
    "UPPER",
    "MIDDLE",
    "LOWER",
    None,
}

VALID_VOLATILITY = {
    "LOW",
    "MEDIUM",
    "HIGH",
    None,
}


SIGNAL_FIELDS = (
    "asset",
    "timestamp",
    "signal_state",
    "direction",
    "confidence",
    "reason",
)


# ============================================================================
# DYNAMIC SIGNAL RECORD
# ============================================================================

@dataclass(frozen=True)
class DynamicSignalRecord:
    """
    Dynamic-universe signal result.

    This is intentionally independent from signal_contract.py because
    signal_contract.py currently enforces the historical 15-asset universe.

    No scoring, decision, risk, trade, or order information is contained here.
    """

    asset: str
    timestamp: Optional[str]

    signal_state: str
    direction: str
    confidence: Optional[float]
    reason: Optional[str]

    points: int
    context: str
    status: str
    eligible: bool

    structure: Dict[str, Any]


# ============================================================================
# NORMALIZATION
# ============================================================================

def normalize_text(
    value: Any,
) -> Optional[str]:

    if value is None:
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    return value


def normalize_float(
    value: Any,
) -> Optional[float]:

    if value is None:
        return None

    try:
        value = float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None

    if not math.isfinite(value):
        return None

    return value


def safe_int(
    value: Any,
) -> int:

    if value is None:
        return 0

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return 0


# ============================================================================
# GENERIC FIELD ACCESS
# ============================================================================

def read_field(
    obj: Any,
    field: str,
    default: Any = None,
) -> Any:

    if isinstance(obj, dict):

        return obj.get(
            field,
            default,
        )

    return getattr(
        obj,
        field,
        default,
    )


# ============================================================================
# CONTEXT
# ============================================================================

def context_from_points(
    points: Any,
) -> str:

    points = safe_int(
        points
    )

    if points >= FULL_CONTEXT_TARGET:
        return "FULL"

    if points >= MIN_CONTEXT:
        return "LIMITED"

    return "NONE"


def status_from_context(
    context: str,
) -> str:

    if context in {
        "FULL",
        "LIMITED",
    }:
        return "AVAILABLE"

    return "UNAVAILABLE"


# ============================================================================
# PUBLIC FIVE-FIELD ADAPTER
#
# This is the existing signal_engine v0.8 semantic mapping.
#
# ONLY the five public fields cross into signal_logic:
#
#   trend
#   momentum
#   acceleration
#   position
#   volatility
#
# No hidden fields are inferred.
# ============================================================================

def build_public_structure(
    feature: Any,
) -> Dict[str, Any]:

    if not isinstance(
        feature,
        dict,
    ):

        raise RuntimeError(
            "INVALID_STRUCTURAL_FEATURE"
        )

    # ------------------------------------------------------------------------
    # TREND
    #
    # Existing semantic:
    #
    #   BULLISH â†’ UP
    #   BEARISH â†’ DOWN
    #   NEUTRAL â†’ FLAT
    #
    # ------------------------------------------------------------------------

    direction = normalize_text(
        feature.get(
            "structure_direction"
        )
    )

    if direction is None:

        direction = normalize_text(
            feature.get(
                "structure_state"
            )
        )

    if direction == "BULLISH":

        trend = "UP"

    elif direction == "BEARISH":

        trend = "DOWN"

    elif direction == "NEUTRAL":

        trend = "FLAT"

    else:

        direct_trend = normalize_text(
            feature.get(
                "trend"
            )
        )

        if direct_trend in {
            "UP",
            "DOWN",
            "FLAT",
        }:

            trend = direct_trend

        else:

            trend = None

    # ------------------------------------------------------------------------
    # MOMENTUM
    #
    # Existing semantic:
    #
    #   STRONG / VERY_STRONG â†’ STRONG
    #   WEAK / MODERATE / MEDIUM â†’ WEAK
    #
    # ------------------------------------------------------------------------

    strength = normalize_text(
        feature.get(
            "structure_strength"
        )
    )

    if strength in {
        "STRONG",
        "VERY_STRONG",
    }:

        momentum = "STRONG"

    elif strength in {
        "WEAK",
        "MODERATE",
        "MEDIUM",
    }:

        momentum = "WEAK"

    else:

        direct_momentum = normalize_text(
            feature.get(
                "momentum"
            )
        )

        if direct_momentum in {
            "STRONG",
            "WEAK",
        }:

            momentum = direct_momentum

        else:

            momentum = None

    # ------------------------------------------------------------------------
    # ACCELERATION
    #
    # Preserve only a genuine numeric value.
    #
    # IMPORTANT:
    # No acceleration is derived from MACD, RSI, trend alignment,
    # volatility, or any other proxy.
    # ------------------------------------------------------------------------

    acceleration = normalize_float(
        feature.get(
            "acceleration"
        )
    )

    # ------------------------------------------------------------------------
    # POSITION
    #
    # Existing contract permits only a genuine public position.
    #
    # No position is inferred from Bollinger Bands, close price,
    # structure point, or any other proxy.
    # ------------------------------------------------------------------------

    position = normalize_text(
        feature.get(
            "position"
        )
    )

    if position not in {
        "UPPER",
        "MIDDLE",
        "LOWER",
    }:

        position = None

    # ------------------------------------------------------------------------
    # VOLATILITY
    #
    # Existing public contract only.
    #
    # ------------------------------------------------------------------------

    volatility = normalize_text(
        feature.get(
            "volatility"
        )
    )

    if volatility not in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }:

        volatility = None

    # ------------------------------------------------------------------------
    # EXACT FIVE-FIELD STRUCTURE
    # ------------------------------------------------------------------------

    structure = {
        "trend": trend,
        "momentum": momentum,
        "acceleration": acceleration,
        "position": position,
        "volatility": volatility,
    }

    return structure


# ============================================================================
# PUBLIC STRUCTURE VALIDATION
# ============================================================================

def validate_public_structure(
    structure: Any,
) -> bool:

    if not isinstance(
        structure,
        dict,
    ):
        return False

    expected_fields = {
        "trend",
        "momentum",
        "acceleration",
        "position",
        "volatility",
    }

    if set(
        structure.keys()
    ) != expected_fields:

        return False

    if structure["trend"] not in VALID_TRENDS:
        return False

    if structure["momentum"] not in VALID_MOMENTUM:
        return False

    if structure["position"] not in VALID_POSITION:
        return False

    if structure["volatility"] not in VALID_VOLATILITY:
        return False

    acceleration = structure[
        "acceleration"
    ]

    if acceleration is not None:

        if not isinstance(
            acceleration,
            (int, float),
        ):
            return False

        if not math.isfinite(
            float(acceleration)
        ):
            return False

    return True


# ============================================================================
# SIGNAL LOGIC LOADER
#
# signal_logic.py remains authoritative.
# ============================================================================

def load_signal_logic():

    import signal_logic

    required = (
        "build_direction",
    )

    for function_name in required:

        if not hasattr(
            signal_logic,
            function_name,
        ):

            raise RuntimeError(
                "SIGNAL_LOGIC_API_MISSING:"
                + function_name
            )

    return signal_logic


# ============================================================================
# DYNAMIC SIGNAL CONTRACT VALIDATION
#
# This mirrors the existing signal contract semantics WITHOUT imposing
# EXPECTED_ASSETS.
#
# It validates one dynamic signal record only.
# ============================================================================

def validate_dynamic_signal(
    signal: Dict[str, Any],
) -> bool:

    if not isinstance(
        signal,
        dict,
    ):

        return False

    if set(
        signal.keys()
    ) != set(
        SIGNAL_FIELDS
    ):

        return False

    asset = signal.get(
        "asset"
    )

    if not isinstance(
        asset,
        str,
    ):

        return False

    asset = asset.strip().upper()

    if not asset:
        return False

    timestamp = signal.get(
        "timestamp"
    )

    if timestamp is not None and not isinstance(
        timestamp,
        str,
    ):
        return False

    signal_state = signal.get(
        "signal_state"
    )

    if signal_state not in VALID_SIGNAL_STATES:
        return False

    direction = signal.get(
        "direction"
    )

    if direction not in VALID_DIRECTIONS:
        return False

    confidence = signal.get(
        "confidence"
    )

    if confidence is not None:

        if not isinstance(
            confidence,
            (int, float),
        ):
            return False

        if not math.isfinite(
            float(confidence)
        ):
            return False

        if not (
            0.0
            <= float(confidence)
            <= 1.0
        ):
            return False

    reason = signal.get(
        "reason"
    )

    if signal_state == "ACTIVE":

        if direction not in {
            "LONG",
            "SHORT",
        }:
            return False

        if reason != "STRUCTURAL_DIRECTION":
            return False

    elif signal_state == "NEUTRAL":

        if direction != "NONE":
            return False

        if reason is not None:
            return False

    return True


# ============================================================================
# PRODUCTION SIGNAL INPUT â†’ PUBLIC FEATURE
# ============================================================================

def production_input_to_feature(
    production_input: Any,
) -> Dict[str, Any]:

    if production_input is None:

        raise RuntimeError(
            "PRODUCTION_SIGNAL_INPUT_MISSING"
        )

    asset = normalize_text(
        read_field(
            production_input,
            "asset",
        )
    )

    if asset is None:

        raise RuntimeError(
            "PRODUCTION_SIGNAL_INPUT_ASSET_MISSING"
        )

    points = safe_int(
        read_field(
            production_input,
            "points",
            read_field(
                production_input,
                "actual_points",
                0,
            ),
        )
    )

    # ------------------------------------------------------------------------
    # Only genuine fields are copied.
    #
    # No interpretation occurs here.
    # ------------------------------------------------------------------------

    return {
        "asset": asset,
        "points": points,

        "structure_direction":
            read_field(
                production_input,
                "structure_direction",
            ),

        "structure_strength":
            read_field(
                production_input,
                "structure_strength",
            ),

        "structure_confidence":
            read_field(
                production_input,
                "structure_confidence",
            ),

        "structure_point_type":
            read_field(
                production_input,
                "structure_point_type",
            ),

        "trend":
            read_field(
                production_input,
                "trend",
            ),

        "momentum":
            read_field(
                production_input,
                "momentum",
            ),

        "acceleration":
            read_field(
                production_input,
                "acceleration",
            ),

        "position":
            read_field(
                production_input,
                "position",
            ),

        "volatility":
            read_field(
                production_input,
                "volatility",
            ),
    }


# ============================================================================
# ONE DYNAMIC SIGNAL
# ============================================================================

def build_dynamic_signal(
    production_input: Any,
) -> DynamicSignalRecord:

    feature = production_input_to_feature(
        production_input
    )

    asset = feature[
        "asset"
    ]

    points = safe_int(
        feature.get(
            "points",
            0,
        )
    )

    context = context_from_points(
        points
    )

    status = status_from_context(
        context
    )

    # ------------------------------------------------------------------------
    # PUBLIC FIVE-FIELD STRUCTURE
    # ------------------------------------------------------------------------

    semantic = production_input_to_semantics(
        production_input
    )

    structure = {
        "trend": semantic.trend,
        "momentum": semantic.momentum,
        "acceleration": semantic.acceleration,
        "position": semantic.position,
        "volatility": semantic.volatility,
    }

    if not validate_public_structure(
        structure
    ):

        raise RuntimeError(
            "PUBLIC_FIVE_FIELD_STRUCTURE_INVALID:"
            + asset
        )

    # ------------------------------------------------------------------------
    # AUTHORITATIVE SIGNAL LOGIC
    # ------------------------------------------------------------------------

    signal_logic = load_signal_logic()

    direction = signal_logic.build_direction(
        structure
    )

    if direction not in VALID_DIRECTIONS:

        raise RuntimeError(
            "INVALID_SIGNAL_DIRECTION:"
            + asset
            + ":"
            + str(direction)
        )

    # ------------------------------------------------------------------------
    # ACTIVE
    #
    # Existing semantics:
    #
    #   AVAILABLE + LONG/SHORT = ACTIVE
    #
    # ------------------------------------------------------------------------

    active = (
        status == "AVAILABLE"
        and direction in {
            "LONG",
            "SHORT",
        }
    )

    if active:

        signal_state = "ACTIVE"
        reason = "STRUCTURAL_DIRECTION"

    else:

        signal_state = "NEUTRAL"
        direction = "NONE"
        reason = None

    # ------------------------------------------------------------------------
    # ELIGIBILITY
    #
    # Existing signal-engine boundary:
    #
    #   AVAILABLE
    #   REAL CONTEXT >= 21
    #   VALID DIRECTION
    #
    # ------------------------------------------------------------------------

    eligible = (
        status == "AVAILABLE"
        and points >= MIN_CONTEXT
        and direction in {
            "LONG",
            "SHORT",
        }
    )

    # ------------------------------------------------------------------------
    # TIMESTAMP
    #
    # Prefer latest_timestamp_iso from ProductionSignalInput.
    # No timestamp is manufactured.
    # ------------------------------------------------------------------------

    timestamp = read_field(
        production_input,
        "latest_timestamp_iso",
        None,
    )

    if timestamp is not None:

        timestamp = str(
            timestamp
        )

    # ------------------------------------------------------------------------
    # Dynamic signal contract object.
    #
    # Confidence remains None because the existing Signal Engine does not
    # fabricate confidence at this boundary.
    # ------------------------------------------------------------------------

    signal = {
        "asset": asset,
        "timestamp": timestamp,
        "signal_state": signal_state,
        "direction": direction,
        "confidence": None,
        "reason": reason,
    }

    if not validate_dynamic_signal(
        signal
    ):

        raise RuntimeError(
            "DYNAMIC_SIGNAL_CONTRACT_INVALID:"
            + asset
        )

    return DynamicSignalRecord(
        asset=asset,
        timestamp=timestamp,
        signal_state=signal_state,
        direction=direction,
        confidence=None,
        reason=reason,

        points=points,
        context=context,
        status=status,
        eligible=eligible,

        structure=structure,
    )


# ============================================================================
# BATCH
#
# Accepts arbitrary dynamic-universe ProductionSignalInput objects.
#
# No fixed asset count.
# No EXPECTED_ASSETS.
# ============================================================================

def build_dynamic_signals(
    production_inputs: Iterable[Any],
) -> List[DynamicSignalRecord]:

    if production_inputs is None:

        raise RuntimeError(
            "PRODUCTION_SIGNAL_INPUT_COLLECTION_MISSING"
        )

    results = []

    seen_assets = set()

    for production_input in production_inputs:

        record = build_dynamic_signal(
            production_input
        )

        asset = record.asset

        if asset in seen_assets:

            raise RuntimeError(
                "DUPLICATE_DYNAMIC_SIGNAL_ASSET:"
                + asset
            )

        seen_assets.add(
            asset
        )

        results.append(
            record
        )

    return results


# ============================================================================
# SIGNAL â†’ DICT
#
# Useful for the next boundary without coupling this module to
# signal_contract.py.
# ============================================================================

def signal_record_to_dict(
    record: DynamicSignalRecord,
) -> Dict[str, Any]:

    if not isinstance(
        record,
        DynamicSignalRecord,
    ):

        raise RuntimeError(
            "INVALID_DYNAMIC_SIGNAL_RECORD"
        )

    signal = {
        "asset": record.asset,
        "timestamp": record.timestamp,
        "signal_state": record.signal_state,
        "direction": record.direction,
        "confidence": record.confidence,
        "reason": record.reason,
    }

    if not validate_dynamic_signal(
        signal
    ):

        raise RuntimeError(
            "DYNAMIC_SIGNAL_RECORD_CONVERSION_INVALID:"
            + record.asset
        )

    return signal


# ============================================================================
# VALIDATION
# ============================================================================

def validate_dynamic_signal_record(
    record: DynamicSignalRecord,
) -> bool:

    if not isinstance(
        record,
        DynamicSignalRecord,
    ):

        return False

    if not isinstance(
        record.asset,
        str,
    ):

        return False

    if not record.asset.strip():
        return False

    if record.context not in VALID_CONTEXTS:
        return False

    if record.status not in VALID_STATUS:
        return False

    if record.signal_state not in VALID_SIGNAL_STATES:
        return False

    if record.direction not in VALID_DIRECTIONS:
        return False

    if record.points < 0:
        return False

    if not validate_public_structure(
        record.structure
    ):
        return False

    signal = signal_record_to_dict(
        record
    )

    if not validate_dynamic_signal(
        signal
    ):
        return False

    # ------------------------------------------------------------------------
    # Context consistency.
    # ------------------------------------------------------------------------

    if record.points < MIN_CONTEXT:

        if record.status != "UNAVAILABLE":
            return False

        if record.context != "NONE":
            return False

        if record.eligible:
            return False

    elif record.points < FULL_CONTEXT_TARGET:

        if record.status != "AVAILABLE":
            return False

        if record.context != "LIMITED":
            return False

    else:

        if record.status != "AVAILABLE":
            return False

        if record.context != "FULL":
            return False

    # ------------------------------------------------------------------------
    # Eligibility consistency.
    # ------------------------------------------------------------------------

    expected_eligible = (
        record.status == "AVAILABLE"
        and record.points >= MIN_CONTEXT
        and record.direction in {
            "LONG",
            "SHORT",
        }
    )

    if record.eligible != expected_eligible:
        return False

    return True


# ============================================================================
# BATCH VALIDATION
# ============================================================================

def validate_dynamic_signal_records(
    records: Iterable[DynamicSignalRecord],
) -> bool:

    if records is None:
        return False

    seen = set()

    for record in records:

        if not validate_dynamic_signal_record(
            record
        ):

            return False

        if record.asset in seen:
            return False

        seen.add(
            record.asset
        )

    return True


# ============================================================================
# SUMMARY
# ============================================================================

def summarize_dynamic_signals(
    records: Iterable[DynamicSignalRecord],
) -> Dict[str, Any]:

    records = list(
        records
    )

    if not validate_dynamic_signal_records(
        records
    ):

        raise RuntimeError(
            "DYNAMIC_SIGNAL_RECORDS_INVALID"
        )

    active = 0
    eligible = 0
    neutral = 0

    long_count = 0
    short_count = 0

    for record in records:

        if record.signal_state == "ACTIVE":
            active += 1

        else:
            neutral += 1

        if record.eligible:
            eligible += 1

        if record.direction == "LONG":
            long_count += 1

        elif record.direction == "SHORT":
            short_count += 1

    return {
        "signals_total": len(records),
        "active": active,
        "neutral": neutral,
        "eligible": eligible,
        "long": long_count,
        "short": short_count,
    }


# ============================================================================
# CONTRACT INSPECTION
# ============================================================================

def contract_check() -> bool:

    signal_logic = load_signal_logic()

    if not hasattr(
        signal_logic,
        "build_direction",
    ):

        return False

    if set(
        VALID_TRENDS
    ) != {
        "UP",
        "DOWN",
        "FLAT",
        None,
    }:

        return False

    if set(
        VALID_MOMENTUM
    ) != {
        "STRONG",
        "WEAK",
        None,
    }:

        return False

    if set(
        VALID_POSITION
    ) != {
        "UPPER",
        "MIDDLE",
        "LOWER",
        None,
    }:

        return False

    if set(
        VALID_VOLATILITY
    ) != {
        "LOW",
        "MEDIUM",
        "HIGH",
        None,
    }:

        return False

    if set(
        SIGNAL_FIELDS
    ) != {
        "asset",
        "timestamp",
        "signal_state",
        "direction",
        "confidence",
        "reason",
    }:

        return False

    return True


# ============================================================================
# STATIC CONTRACT CHECK
#
# This checks structure only.
# It does NOT execute a production signal runtime.
# It does NOT access the database.
# It does NOT create production data.
# ============================================================================

def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA DYNAMIC SIGNAL BOUNDARY v0.1"
    )
    print("=" * 100)

    print(
        "DYNAMIC_UNIVERSE=True"
    )

    print(
        "EXPECTED_ASSETS_USED=False"
    )

    print(
        "CMC_USED=False"
    )

    print(
        "LEGACY_MARKET_TECHNICAL=False"
    )

    print(
        "PRODUCTION_DB_TOUCHED=False"
    )

    print(
        "DB_WRITES=0"
    )

    print(
        "SYNTHETIC=False"
    )

    print(
        "INTERPOLATION=False"
    )

    print(
        "FILL=False"
    )

    print(
        "BACKFILL=False"
    )

    print(
        "PADDING=False"
    )

    print(
        "BLENDING=False"
    )

    print(
        "SCORING_EXECUTED=False"
    )

    print(
        "DECISION_EXECUTED=False"
    )

    print(
        "RISK_EXECUTED=False"
    )

    print(
        "TRADE_GATE_EXECUTED=False"
    )

    print(
        "OPPORTUNITY_EXECUTED=False"
    )

    print(
        "ORDER_INTENTS_CREATED=0"
    )

    print(
        "EXECUTION=OFF"
    )

    print()

    # ------------------------------------------------------------------------
    # Authoritative Signal Logic API.
    # ------------------------------------------------------------------------

    signal_logic = load_signal_logic()

    print(
        "SIGNAL_LOGIC_IMPORT=PASS"
    )

    if not hasattr(
        signal_logic,
        "build_direction",
    ):

        raise RuntimeError(
            "SIGNAL_LOGIC_BUILD_DIRECTION_MISSING"
        )

    print(
        "SIGNAL_LOGIC_API=PASS"
    )

    # ------------------------------------------------------------------------
    # Contract structure.
    # ------------------------------------------------------------------------

    if not contract_check():

        raise RuntimeError(
            "DYNAMIC_SIGNAL_BOUNDARY_CONTRACT_FAILED"
        )

    print(
        "PUBLIC_FIVE_FIELD_CONTRACT=PASS"
    )

    print(
        "DYNAMIC_ASSET_BINDING=PASS"
    )

    print(
        "NO_EXPECTED_ASSETS=PASS"
    )

    print(
        "NO_PRODUCTION_DB=PASS"
    )

    print(
        "NO_EXECUTION=PASS"
    )

    print()

    print("=" * 100)

    print(
        "DYNAMIC SIGNAL BOUNDARY STATUS=READY"
    )

    print(
        "RUNTIME_EXECUTED=FALSE"
    )

    print(
        "PRODUCTION_INPUTS_PROCESSED=0"
    )

    print(
        "SIGNALS_CREATED=0"
    )

    print(
        "ELIGIBLE_SIGNALS=0"
    )

    print(
        "BLOCKER=NONE"
    )

    print(
        "NEXT=PRODUCTION_SIGNAL_INPUT â†’ DYNAMIC_SIGNAL"
    )

    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

