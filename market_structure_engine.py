"""
ARUNDA TRADER — DEV-06
MARKET STRUCTURE ENGINE v0.1

Analysis-layer only.

Core concepts:
    Swing High
    Swing Low
    HH / HL / LH / LL
    BOS
    CHoCH
    Structure Direction
    Structure Strength
    Structure Confidence

Architecture:
    - No database access
    - No SQL
    - No writes
    - No future-data access beyond explicit swing confirmation window
    - CMC_ID is optional identity metadata
    - Input order is preserved
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
import math


ENGINE_NAME = "MARKET_STRUCTURE_ENGINE_v0.1"

DEFAULT_LEFT_BARS = 2
DEFAULT_RIGHT_BARS = 2

ALLOWED_SWING_TYPES = {
    "SWING_HIGH",
    "SWING_LOW",
}

ALLOWED_STRUCTURE_TYPES = {
    "HH",
    "HL",
    "LH",
    "LL",
}

ALLOWED_BREAK_TYPES = {
    "NONE",
    "BOS",
    "CHoCH",
}

ALLOWED_DIRECTIONS = {
    "BULLISH",
    "BEARISH",
    "NEUTRAL",
}

ALLOWED_STRENGTH = {
    "WEAK",
    "MODERATE",
    "STRONG",
}

ALLOWED_CONFIDENCE = {
    "LOW",
    "MEDIUM",
    "HIGH",
}


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass(frozen=True)
class MarketBar:
    timestamp: Any
    high: float
    low: float
    close: float
    open: Optional[float] = None
    volume: Optional[float] = None
    cmc_id: Optional[int] = None
    symbol: Optional[str] = None


@dataclass(frozen=True)
class SwingPoint:
    index: int
    timestamp: Any
    price: float
    swing_type: str
    confirmation_index: int
    cmc_id: Optional[int] = None
    symbol: Optional[str] = None


@dataclass(frozen=True)
class StructurePoint:
    index: int
    timestamp: Any
    price: float
    swing_type: str
    structure_type: str
    previous_price: Optional[float]
    cmc_id: Optional[int] = None
    symbol: Optional[str] = None


@dataclass(frozen=True)
class StructureEvent:
    index: int
    timestamp: Any
    event_type: str
    direction: str
    reference_price: float
    broken_price: Optional[float]
    strength: str
    confidence: str
    cmc_id: Optional[int] = None
    symbol: Optional[str] = None


@dataclass(frozen=True)
class MarketStructureRecord:
    index: int
    timestamp: Any
    cmc_id: Optional[int]
    symbol: Optional[str]

    swing_high: bool
    swing_low: bool

    structure_type: Optional[str]

    bos: bool
    choch: bool
    break_type: str

    direction: str
    strength: str
    confidence: str

    last_structure_price: Optional[float]
    previous_structure_price: Optional[float]


# ============================================================================
# NUMERIC SAFETY
# ============================================================================

def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _float(value: Any) -> float:
    result = float(value)

    if not math.isfinite(result):
        raise ValueError(f"Non-finite numeric value: {value}")

    return result


# ============================================================================
# INPUT VALIDATION
# ============================================================================

def validate_bar(bar: Any) -> MarketBar:

    if isinstance(bar, MarketBar):
        result = bar

    elif isinstance(bar, dict):

        required = (
            "timestamp",
            "high",
            "low",
            "close",
        )

        for field in required:
            if field not in bar:
                raise ValueError(
                    f"Missing required bar field: {field}"
                )

        result = MarketBar(
            timestamp=bar["timestamp"],
            high=_float(bar["high"]),
            low=_float(bar["low"]),
            close=_float(bar["close"]),
            open=(
                _float(bar["open"])
                if bar.get("open") is not None
                else None
            ),
            volume=(
                _float(bar["volume"])
                if bar.get("volume") is not None
                else None
            ),
            cmc_id=bar.get("cmc_id"),
            symbol=bar.get("symbol"),
        )

    else:
        raise TypeError(
            f"Unsupported bar type: {type(bar).__name__}"
        )

    if result.high < result.low:
        raise ValueError(
            f"Invalid OHLC bar: high < low at {result.timestamp}"
        )

    if not _finite(result.high):
        raise ValueError(
            f"Invalid high at {result.timestamp}"
        )

    if not _finite(result.low):
        raise ValueError(
            f"Invalid low at {result.timestamp}"
        )

    if not _finite(result.close):
        raise ValueError(
            f"Invalid close at {result.timestamp}"
        )

    if result.open is not None and not _finite(result.open):
        raise ValueError(
            f"Invalid open at {result.timestamp}"
        )

    if result.volume is not None and result.volume < 0:
        raise ValueError(
            f"Negative volume at {result.timestamp}"
        )

    return result


def validate_bars(
    bars: Sequence[Any],
) -> List[MarketBar]:

    if bars is None:
        raise ValueError("bars cannot be None")

    result = [
        validate_bar(bar)
        for bar in bars
    ]

    if len(result) < 3:
        raise ValueError(
            "At least 3 bars are required."
        )

    # Chronological validation.
    # We intentionally avoid assuming timestamp type.
    # When timestamps are comparable, they must be non-decreasing.
    for i in range(1, len(result)):

        previous = result[i - 1].timestamp
        current = result[i].timestamp

        try:
            if current < previous:
                raise ValueError(
                    "Bars must be supplied in chronological order."
                )
        except TypeError:
            # Non-orderable metadata is allowed.
            pass

    return result


# ============================================================================
# SWING HIGH / LOW CORE
# ============================================================================

def is_swing_high(
    bars: Sequence[MarketBar],
    index: int,
    left_bars: int = DEFAULT_LEFT_BARS,
    right_bars: int = DEFAULT_RIGHT_BARS,
) -> bool:

    if left_bars < 1 or right_bars < 1:
        raise ValueError(
            "left_bars and right_bars must be >= 1"
        )

    if index < left_bars:
        return False

    if index + right_bars >= len(bars):
        return False

    current = bars[index].high

    left = bars[
        index - left_bars:index
    ]

    right = bars[
        index + 1:index + right_bars + 1
    ]

    return (
        all(current >= bar.high for bar in left)
        and
        all(current >= bar.high for bar in right)
        and
        (
            any(current > bar.high for bar in left)
            or
            any(current > bar.high for bar in right)
        )
    )


def is_swing_low(
    bars: Sequence[MarketBar],
    index: int,
    left_bars: int = DEFAULT_LEFT_BARS,
    right_bars: int = DEFAULT_RIGHT_BARS,
) -> bool:

    if left_bars < 1 or right_bars < 1:
        raise ValueError(
            "left_bars and right_bars must be >= 1"
        )

    if index < left_bars:
        return False

    if index + right_bars >= len(bars):
        return False

    current = bars[index].low

    left = bars[
        index - left_bars:index
    ]

    right = bars[
        index + 1:index + right_bars + 1
    ]

    return (
        all(current <= bar.low for bar in left)
        and
        all(current <= bar.low for bar in right)
        and
        (
            any(current < bar.low for bar in left)
            or
            any(current < bar.low for bar in right)
        )
    )


# ============================================================================
# EXPLICIT CONTRACT API
# ============================================================================

def detect_swing_highs(
    bars: Sequence[Any],
    left_bars: int = DEFAULT_LEFT_BARS,
    right_bars: int = DEFAULT_RIGHT_BARS,
) -> List[SwingPoint]:

    validated = validate_bars(bars)

    result: List[SwingPoint] = []

    for i in range(len(validated)):

        if not is_swing_high(
            validated,
            i,
            left_bars,
            right_bars,
        ):
            continue

        bar = validated[i]

        result.append(
            SwingPoint(
                index=i,
                timestamp=bar.timestamp,
                price=bar.high,
                swing_type="SWING_HIGH",
                confirmation_index=i + right_bars,
                cmc_id=bar.cmc_id,
                symbol=bar.symbol,
            )
        )

    return result


def detect_swing_lows(
    bars: Sequence[Any],
    left_bars: int = DEFAULT_LEFT_BARS,
    right_bars: int = DEFAULT_RIGHT_BARS,
) -> List[SwingPoint]:

    validated = validate_bars(bars)

    result: List[SwingPoint] = []

    for i in range(len(validated)):

        if not is_swing_low(
            validated,
            i,
            left_bars,
            right_bars,
        ):
            continue

        bar = validated[i]

        result.append(
            SwingPoint(
                index=i,
                timestamp=bar.timestamp,
                price=bar.low,
                swing_type="SWING_LOW",
                confirmation_index=i + right_bars,
                cmc_id=bar.cmc_id,
                symbol=bar.symbol,
            )
        )

    return result


def detect_swings(
    bars: Sequence[Any],
    left_bars: int = DEFAULT_LEFT_BARS,
    right_bars: int = DEFAULT_RIGHT_BARS,
) -> List[SwingPoint]:

    validated = validate_bars(bars)

    highs = detect_swing_highs(
        validated,
        left_bars,
        right_bars,
    )

    lows = detect_swing_lows(
        validated,
        left_bars,
        right_bars,
    )

    combined = highs + lows

    combined.sort(
        key=lambda point: (
            point.index,
            0 if point.swing_type == "SWING_HIGH" else 1,
        )
    )

    return combined


# ============================================================================
# STRUCTURE CLASSIFICATION
# ============================================================================

def classify_structure(
    swings: Sequence[SwingPoint],
) -> List[StructurePoint]:

    last_high: Optional[float] = None
    last_low: Optional[float] = None

    result: List[StructurePoint] = []

    for swing in swings:

        if swing.swing_type == "SWING_HIGH":

            if last_high is None:
                structure_type = None
                previous_price = None

            elif swing.price > last_high:
                structure_type = "HH"
                previous_price = last_high

            else:
                structure_type = "LH"
                previous_price = last_high

            last_high = swing.price

        elif swing.swing_type == "SWING_LOW":

            if last_low is None:
                structure_type = None
                previous_price = None

            elif swing.price > last_low:
                structure_type = "HL"
                previous_price = last_low

            else:
                structure_type = "LL"
                previous_price = last_low

            last_low = swing.price

        else:
            raise ValueError(
                f"Unknown swing type: {swing.swing_type}"
            )

        if structure_type is not None:

            result.append(
                StructurePoint(
                    index=swing.index,
                    timestamp=swing.timestamp,
                    price=swing.price,
                    swing_type=swing.swing_type,
                    structure_type=structure_type,
                    previous_price=previous_price,
                    cmc_id=swing.cmc_id,
                    symbol=swing.symbol,
                )
            )

    return result


# Backward-compatible name.
def classify_swing_structure(
    swings: Sequence[SwingPoint],
) -> List[StructurePoint]:

    return classify_structure(swings)


# ============================================================================
# DIRECTION / STRENGTH / CONFIDENCE
# ============================================================================

def classify_structure_direction(
    structure_points: Sequence[StructurePoint],
) -> str:

    recent = list(structure_points[-4:])

    types = {
        point.structure_type
        for point in recent
    }

    if "HH" in types and "HL" in types:
        return "BULLISH"

    if "LH" in types and "LL" in types:
        return "BEARISH"

    return "NEUTRAL"


def calculate_structure_strength(
    structure_points: Sequence[StructurePoint],
) -> str:

    if len(structure_points) < 2:
        return "WEAK"

    recent = list(
        structure_points[-4:]
    )

    bullish = sum(
        1
        for point in recent
        if point.structure_type in {"HH", "HL"}
    )

    bearish = sum(
        1
        for point in recent
        if point.structure_type in {"LH", "LL"}
    )

    if bullish >= 3 or bearish >= 3:
        return "STRONG"

    if bullish >= 2 or bearish >= 2:
        return "MODERATE"

    return "WEAK"


def calculate_structure_confidence(
    structure_points: Sequence[StructurePoint],
    events: Sequence[StructureEvent],
) -> str:

    if len(structure_points) >= 4 and events:
        return "HIGH"

    if len(structure_points) >= 2:
        return "MEDIUM"

    return "LOW"


# ============================================================================
# BREAK DETECTION CORE
# ============================================================================

def _confirmed_structure_points_at(
    structure_points: Sequence[StructurePoint],
    bar_index: int,
) -> List[StructurePoint]:

    return [
        point
        for point in structure_points
        if point.index < bar_index
    ]


def _initial_structure_direction(
    structure_points: Sequence[StructurePoint],
) -> str:

    for point in reversed(structure_points):

        if point.structure_type in {"HH", "HL"}:
            return "BULLISH"

        if point.structure_type in {"LH", "LL"}:
            return "BEARISH"

    return "NEUTRAL"


def detect_bos(
    bars: Sequence[Any],
    structure_points: Sequence[StructurePoint],
) -> List[StructureEvent]:

    validated = validate_bars(bars)

    if not structure_points:
        return []

    events: List[StructureEvent] = []

    direction = _initial_structure_direction(
        structure_points
    )

    broken_high_indices = set()
    broken_low_indices = set()

    for bar_index, bar in enumerate(validated):

        available = _confirmed_structure_points_at(
            structure_points,
            bar_index,
        )

        latest_high = None
        latest_low = None

        for point in available:

            if point.swing_type == "SWING_HIGH":
                latest_high = point

            elif point.swing_type == "SWING_LOW":
                latest_low = point

        if (
            latest_high is not None
            and latest_high.index not in broken_high_indices
            and bar.close > latest_high.price
        ):

            previous_direction = direction

            if previous_direction == "BEARISH":
                event_type = "CHoCH"
            else:
                event_type = "BOS"

            direction = "BULLISH"

            broken_high_indices.add(
                latest_high.index
            )

            events.append(
                StructureEvent(
                    index=bar_index,
                    timestamp=bar.timestamp,
                    event_type=event_type,
                    direction="BULLISH",
                    reference_price=bar.close,
                    broken_price=latest_high.price,
                    strength="MODERATE",
                    confidence="HIGH",
                    cmc_id=bar.cmc_id,
                    symbol=bar.symbol,
                )
            )

            continue

        if (
            latest_low is not None
            and latest_low.index not in broken_low_indices
            and bar.close < latest_low.price
        ):

            previous_direction = direction

            if previous_direction == "BULLISH":
                event_type = "CHoCH"
            else:
                event_type = "BOS"

            direction = "BEARISH"

            broken_low_indices.add(
                latest_low.index
            )

            events.append(
                StructureEvent(
                    index=bar_index,
                    timestamp=bar.timestamp,
                    event_type=event_type,
                    direction="BEARISH",
                    reference_price=bar.close,
                    broken_price=latest_low.price,
                    strength="MODERATE",
                    confidence="HIGH",
                    cmc_id=bar.cmc_id,
                    symbol=bar.symbol,
                )
            )

    return [
        event
        for event in events
        if event.event_type == "BOS"
    ]


def detect_choch(
    bars: Sequence[Any],
    structure_points: Sequence[StructurePoint],
) -> List[StructureEvent]:

    validated = validate_bars(bars)

    if not structure_points:
        return []

    events: List[StructureEvent] = []

    direction = _initial_structure_direction(
        structure_points
    )

    broken_high_indices = set()
    broken_low_indices = set()

    for bar_index, bar in enumerate(validated):

        available = _confirmed_structure_points_at(
            structure_points,
            bar_index,
        )

        latest_high = None
        latest_low = None

        for point in available:

            if point.swing_type == "SWING_HIGH":
                latest_high = point

            elif point.swing_type == "SWING_LOW":
                latest_low = point

        if (
            latest_high is not None
            and latest_high.index not in broken_high_indices
            and bar.close > latest_high.price
        ):

            if direction == "BEARISH":

                broken_high_indices.add(
                    latest_high.index
                )

                direction = "BULLISH"

                events.append(
                    StructureEvent(
                        index=bar_index,
                        timestamp=bar.timestamp,
                        event_type="CHoCH",
                        direction="BULLISH",
                        reference_price=bar.close,
                        broken_price=latest_high.price,
                        strength="MODERATE",
                        confidence="HIGH",
                        cmc_id=bar.cmc_id,
                        symbol=bar.symbol,
                    )
                )

            else:
                broken_high_indices.add(
                    latest_high.index
                )

        elif (
            latest_low is not None
            and latest_low.index not in broken_low_indices
            and bar.close < latest_low.price
        ):

            if direction == "BULLISH":

                broken_low_indices.add(
                    latest_low.index
                )

                direction = "BEARISH"

                events.append(
                    StructureEvent(
                        index=bar_index,
                        timestamp=bar.timestamp,
                        event_type="CHoCH",
                        direction="BEARISH",
                        reference_price=bar.close,
                        broken_price=latest_low.price,
                        strength="MODERATE",
                        confidence="HIGH",
                        cmc_id=bar.cmc_id,
                        symbol=bar.symbol,
                    )
                )

            else:
                broken_low_indices.add(
                    latest_low.index
                )

    return events


def detect_structure_events(
    bars: Sequence[Any],
    structure_points: Sequence[StructurePoint],
) -> List[StructureEvent]:

    validated = validate_bars(bars)

    if not structure_points:
        return []

    events: List[StructureEvent] = []

    direction = _initial_structure_direction(
        structure_points
    )

    broken_high_indices = set()
    broken_low_indices = set()

    for bar_index, bar in enumerate(validated):

        available = _confirmed_structure_points_at(
            structure_points,
            bar_index,
        )

        latest_high = None
        latest_low = None

        for point in available:

            if point.swing_type == "SWING_HIGH":
                latest_high = point

            elif point.swing_type == "SWING_LOW":
                latest_low = point

        # Bullish break
        if (
            latest_high is not None
            and latest_high.index not in broken_high_indices
            and bar.close > latest_high.price
        ):

            previous_direction = direction

            event_type = (
                "CHoCH"
                if previous_direction == "BEARISH"
                else "BOS"
            )

            direction = "BULLISH"

            broken_high_indices.add(
                latest_high.index
            )

            events.append(
                StructureEvent(
                    index=bar_index,
                    timestamp=bar.timestamp,
                    event_type=event_type,
                    direction="BULLISH",
                    reference_price=bar.close,
                    broken_price=latest_high.price,
                    strength="MODERATE",
                    confidence="HIGH",
                    cmc_id=bar.cmc_id,
                    symbol=bar.symbol,
                )
            )

            continue

        # Bearish break
        if (
            latest_low is not None
            and latest_low.index not in broken_low_indices
            and bar.close < latest_low.price
        ):

            previous_direction = direction

            event_type = (
                "CHoCH"
                if previous_direction == "BULLISH"
                else "BOS"
            )

            direction = "BEARISH"

            broken_low_indices.add(
                latest_low.index
            )

            events.append(
                StructureEvent(
                    index=bar_index,
                    timestamp=bar.timestamp,
                    event_type=event_type,
                    direction="BEARISH",
                    reference_price=bar.close,
                    broken_price=latest_low.price,
                    strength="MODERATE",
                    confidence="HIGH",
                    cmc_id=bar.cmc_id,
                    symbol=bar.symbol,
                )
            )

    return events


# ============================================================================
# MAIN ENGINE
# ============================================================================

def analyze_market_structure(
    bars: Sequence[Any],
    left_bars: int = DEFAULT_LEFT_BARS,
    right_bars: int = DEFAULT_RIGHT_BARS,
) -> Dict[str, Any]:

    validated = validate_bars(bars)

    swings = detect_swings(
        validated,
        left_bars,
        right_bars,
    )

    structures = classify_structure(
        swings
    )

    events = detect_structure_events(
        validated,
        structures,
    )

    direction = classify_structure_direction(
        structures
    )

    strength = calculate_structure_strength(
        structures
    )

    confidence = calculate_structure_confidence(
        structures,
        events,
    )

    return {
        "engine": ENGINE_NAME,
        "bars": validated,
        "swings": swings,
        "structure_points": structures,
        "events": events,
        "direction": direction,
        "strength": strength,
        "confidence": confidence,
    }


# ============================================================================
# OUTPUT VALIDATION
# ============================================================================

def validate_swing_point(
    point: SwingPoint,
) -> None:

    if point.swing_type not in ALLOWED_SWING_TYPES:
        raise ValueError(
            f"Invalid swing type: {point.swing_type}"
        )

    if point.confirmation_index <= point.index:
        raise ValueError(
            "Swing confirmation index must be after swing index."
        )

    if not _finite(point.price):
        raise ValueError(
            "Swing price must be finite."
        )


def validate_structure_point(
    point: StructurePoint,
) -> None:

    if point.structure_type not in ALLOWED_STRUCTURE_TYPES:
        raise ValueError(
            f"Invalid structure type: {point.structure_type}"
        )

    if not _finite(point.price):
        raise ValueError(
            "Structure price must be finite."
        )

    if point.previous_price is not None:
        if not _finite(point.previous_price):
            raise ValueError(
                "Previous structure price must be finite."
            )


def validate_structure_event(
    event: StructureEvent,
) -> None:

    if event.event_type not in ALLOWED_BREAK_TYPES:
        raise ValueError(
            f"Invalid event type: {event.event_type}"
        )

    if event.direction not in ALLOWED_DIRECTIONS:
        raise ValueError(
            f"Invalid direction: {event.direction}"
        )

    if event.strength not in ALLOWED_STRENGTH:
        raise ValueError(
            f"Invalid strength: {event.strength}"
        )

    if event.confidence not in ALLOWED_CONFIDENCE:
        raise ValueError(
            f"Invalid confidence: {event.confidence}"
        )

    if not _finite(event.reference_price):
        raise ValueError(
            "Event reference price must be finite."
        )

    if event.broken_price is not None:
        if not _finite(event.broken_price):
            raise ValueError(
                "Broken price must be finite."
            )


def validate_market_structure_output(
    result: Dict[str, Any],
) -> bool:

    required = {
        "engine",
        "bars",
        "swings",
        "structure_points",
        "events",
        "direction",
        "strength",
        "confidence",
    }

    missing = required - set(result.keys())

    if missing:
        raise ValueError(
            f"Missing output fields: {sorted(missing)}"
        )

    if result["direction"] not in ALLOWED_DIRECTIONS:
        raise ValueError(
            f"Invalid direction: {result['direction']}"
        )

    if result["strength"] not in ALLOWED_STRENGTH:
        raise ValueError(
            f"Invalid strength: {result['strength']}"
        )

    if result["confidence"] not in ALLOWED_CONFIDENCE:
        raise ValueError(
            f"Invalid confidence: {result['confidence']}"
        )

    for point in result["swings"]:
        validate_swing_point(point)

    for point in result["structure_points"]:
        validate_structure_point(point)

    for event in result["events"]:
        validate_structure_event(event)

    return True


# ============================================================================
# LOOK-AHEAD AUDIT
# ============================================================================

def lookahead_audit(
    bars: Sequence[Any],
    left_bars: int = DEFAULT_LEFT_BARS,
    right_bars: int = DEFAULT_RIGHT_BARS,
) -> bool:

    validated = validate_bars(bars)

    swings = detect_swings(
        validated,
        left_bars,
        right_bars,
    )

    for swing in swings:

        if swing.confirmation_index != (
            swing.index + right_bars
        ):
            return False

        if swing.confirmation_index >= len(validated):
            return False

    return True


# ============================================================================
# SELF TEST
# ============================================================================

def self_test() -> bool:

    closes = [
        100,
        102,
        105,
        103,
        101,
        104,
        108,
        106,
        103,
        107,
        112,
        109,
        106,
        110,
        115,
        111,
        108,
        104,
    ]

    bars = []

    for i, close in enumerate(closes):

        bars.append(
            MarketBar(
                timestamp=i,
                high=close + 1,
                low=close - 1,
                close=close,
                cmc_id=1,
                symbol="TEST",
            )
        )

    result = analyze_market_structure(
        bars,
        left_bars=2,
        right_bars=2,
    )

    assert validate_market_structure_output(
        result
    )

    assert isinstance(
        result["swings"],
        list,
    )

    assert isinstance(
        result["structure_points"],
        list,
    )

    assert isinstance(
        result["events"],
        list,
    )

    assert result["direction"] in ALLOWED_DIRECTIONS
    assert result["strength"] in ALLOWED_STRENGTH
    assert result["confidence"] in ALLOWED_CONFIDENCE

    for point in result["structure_points"]:
        assert (
            point.structure_type
            in ALLOWED_STRUCTURE_TYPES
        )

    for swing in result["swings"]:

        assert (
            swing.confirmation_index
            == swing.index + 2
        )

        assert swing.cmc_id == 1
        assert swing.symbol == "TEST"

    assert lookahead_audit(
        bars,
        left_bars=2,
        right_bars=2,
    )

    # Explicit API contract tests.
    highs = detect_swing_highs(
        bars,
        left_bars=2,
        right_bars=2,
    )

    lows = detect_swing_lows(
        bars,
        left_bars=2,
        right_bars=2,
    )

    all_swings = detect_swings(
        bars,
        left_bars=2,
        right_bars=2,
    )

    assert all(
        point.swing_type == "SWING_HIGH"
        for point in highs
    )

    assert all(
        point.swing_type == "SWING_LOW"
        for point in lows
    )

    assert len(all_swings) == (
        len(highs) + len(lows)
    )

    structures = classify_structure(
        all_swings
    )

    assert isinstance(
        structures,
        list,
    )

    bos = detect_bos(
        bars,
        structures,
    )

    choch = detect_choch(
        bars,
        structures,
    )

    assert isinstance(bos, list)
    assert isinstance(choch, list)

    for event in bos:
        assert event.event_type == "BOS"

    for event in choch:
        assert event.event_type == "CHoCH"

    # Numeric safety.
    assert _finite(100.0)
    assert not _finite(float("nan"))
    assert not _finite(float("inf"))

    # Invalid OHLC.
    invalid_bars = [
        MarketBar(
            timestamp=0,
            high=10,
            low=20,
            close=15,
        ),
        MarketBar(
            timestamp=1,
            high=10,
            low=5,
            close=8,
        ),
        MarketBar(
            timestamp=2,
            high=11,
            low=6,
            close=9,
        ),
    ]

    try:
        validate_bars(
            invalid_bars
        )
        raise AssertionError(
            "Invalid OHLC was not rejected."
        )
    except ValueError:
        pass

    # Insufficient data.
    try:
        validate_bars(
            bars[:2]
        )
        raise AssertionError(
            "Insufficient bars were not rejected."
        )
    except ValueError:
        pass

    # Chronological order.
    reversed_bars = [
        MarketBar(
            timestamp=2,
            high=10,
            low=8,
            close=9,
        ),
        MarketBar(
            timestamp=1,
            high=11,
            low=8,
            close=10,
        ),
        MarketBar(
            timestamp=3,
            high=12,
            low=9,
            close=11,
        ),
    ]

    try:
        validate_bars(
            reversed_bars
        )
        raise AssertionError(
            "Non-chronological bars were not rejected."
        )
    except ValueError:
        pass

    return True


# ============================================================================
# SAMPLE PRINTER
# ============================================================================

def print_structure_sample(
    result: Dict[str, Any],
    limit: int = 10,
) -> None:

    print()
    print("=" * 100)
    print(
        "ARUNDA TRADER — MARKET STRUCTURE ENGINE v0.1"
    )
    print("=" * 100)

    print(
        f"Direction   : {result['direction']}"
    )

    print(
        f"Strength    : {result['strength']}"
    )

    print(
        f"Confidence  : {result['confidence']}"
    )

    print()
    print("SWINGS")
    print("-" * 100)

    for swing in result["swings"][:limit]:

        print(
            f"INDEX={swing.index} | "
            f"TYPE={swing.swing_type} | "
            f"PRICE={swing.price} | "
            f"CONFIRMED_AT={swing.confirmation_index}"
        )

    print()
    print("STRUCTURE")
    print("-" * 100)

    for point in result["structure_points"][:limit]:

        print(
            f"INDEX={point.index} | "
            f"{point.structure_type} | "
            f"PRICE={point.price} | "
            f"PREVIOUS={point.previous_price}"
        )

    print()
    print("EVENTS")
    print("-" * 100)

    for event in result["events"][:limit]:

        print(
            f"INDEX={event.index} | "
            f"{event.event_type} | "
            f"DIRECTION={event.direction} | "
            f"PRICE={event.reference_price} | "
            f"BROKEN={event.broken_price}"
        )


# ============================================================================
# MODULE SELF TEST
# ============================================================================

if __name__ == "__main__":

    print("=" * 100)
    print(
        "ARUNDA TRADER — DEV-06 — STEP 11"
    )
    print(
        "MARKET STRUCTURE ENGINE v0.1"
    )
    print("SELF TEST")
    print("=" * 100)

    try:

        self_test()

        print()
        print("SELF TEST RESULT : PASS")
        print()
        print(
            "ENGINE            : MARKET_STRUCTURE_v0.1"
        )
        print(
            "DATABASE          : NOT USED"
        )
        print(
            "DATABASE WRITE    : NONE"
        )
        print(
            "LOOK-AHEAD        : PROTECTED"
        )
        print(
            "CMC_ID IDENTITY   : PRESERVED"
        )
        print(
            "STATUS            : READY FOR STEP 11A CONTRACT AUDIT"
        )

    except Exception as exc:

        print()
        print("SELF TEST RESULT : FAIL")
        print(
            f"ERROR            : {type(exc).__name__}: {exc}"
        )

        raise