import math
import sqlite3

import market_structure_engine


# =============================================================================
# ARUNDA MARKET REGIME ENGINE v0.6
#
# MARKET_DATA
#     ->
# BOUNDED ROLLING CONTEXT
#     ->
# MARKET_STRUCTURE_ENGINE
#     ->
# STRUCTURAL STATE
#     ->
# ACCELERATION
#     ->
# MARKET REGIME
#
# ARCHITECTURAL CONTRACT
#
# FULL_CONTEXT_TARGET = 150
# MIN_CONTEXT         = 21
#
# 150 is NOT a minimum requirement.
# 150 is NOT a signal limit.
# 150 is NOT a history limit.
#
# 150 is the maximum amount of market context consumed by one calculation.
#
# A real context smaller than 150 is accepted when it satisfies the actual
# computational dependency of the engine.
#
# No synthetic data.
# No interpolation.
# No forward fill.
# No backward fill.
# No padding.
# No fake bars.
#
# READ ONLY
# SQL READ ONLY
# MEMORY ONLY
# NO INSERT
# NO UPDATE
# NO DELETE
# NO SIGNAL
# NO SCORING
# NO DECISION
# =============================================================================


DB_PATH = "arunda.db"


# =============================================================================
# CONTEXT CONTRACT
# =============================================================================

FULL_CONTEXT_TARGET = 150

LEFT_BARS = 2
RIGHT_BARS = 2

ACCELERATION_PERIOD = 10

# The acceleration calculation requires:
#
#     2 * ACCELERATION_PERIOD + 1
#
# real bars.
#
# Therefore:
#
#     2 * 10 + 1 = 21
#
# This is the actual minimum computational context.
MIN_CONTEXT = (
    ACCELERATION_PERIOD * 2
) + 1


WINDOW_SIZE = FULL_CONTEXT_TARGET


EXPECTED_ASSETS = [
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
]


# =============================================================================
# NORMALIZATION
# =============================================================================


def _normalize_text(value):

    if value is None:
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    return value


def _safe_float(value):

    if value is None:
        return None

    try:
        value = float(value)

    except (TypeError, ValueError):

        return None

    if not math.isfinite(value):

        return None

    return value


# =============================================================================
# CONTEXT STATUS
# =============================================================================


def _context_status(points):

    if points < MIN_CONTEXT:

        return "INSUFFICIENT"

    if points < FULL_CONTEXT_TARGET:

        return "LIMITED"

    return "FULL"


# =============================================================================
# ACCELERATION
# =============================================================================


def _calculate_acceleration(
    bars,
):

    period = ACCELERATION_PERIOD

    required = (
        period * 2
    ) + 1

    if len(bars) < required:

        return None

    closes = []

    for bar in bars:

        if not isinstance(
            bar,
            dict,
        ):

            continue

        close = _safe_float(
            bar.get("close")
        )

        if close is None:

            continue

        if close <= 0:

            continue

        closes.append(
            close
        )

    if len(closes) < required:

        return None

    recent_start = (
        len(closes)
        - 1
        - period
    )

    previous_start = (
        len(closes)
        - 1
        - (period * 2)
    )

    latest_close = closes[-1]

    recent_base = closes[
        recent_start
    ]

    previous_base = closes[
        previous_start
    ]

    if (
        latest_close <= 0
        or recent_base <= 0
        or previous_base <= 0
    ):

        return None

    recent_return = (
        latest_close
        / recent_base
    ) - 1.0

    previous_return = (
        recent_base
        / previous_base
    ) - 1.0

    acceleration = (
        recent_return
        - previous_return
    )

    if not math.isfinite(
        acceleration
    ):

        return None

    return acceleration


def _normalize_acceleration(
    value,
):

    return _safe_float(
        value
    )


# =============================================================================
# DATABASE HELPERS
# =============================================================================


def _get_columns(
    conn,
    table_name,
):

    rows = conn.execute(
        'PRAGMA table_info("{}")'.format(
            table_name
        )
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


def _find_column(
    columns,
    candidates,
):

    normalized = {
        str(column).lower(): column
        for column in columns
    }

    for candidate in candidates:

        key = str(
            candidate
        ).lower()

        if key in normalized:

            return normalized[
                key
            ]

    return None


# =============================================================================
# MARKET BAR
# =============================================================================


def _build_market_bar(
    symbol,
    timestamp,
    open_price,
    high,
    low,
    close,
    volume,
):

    return {
        "symbol": symbol,
        "timestamp": timestamp,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


# =============================================================================
# LOAD MARKET DATA
# =============================================================================


def load_market_data_by_symbol():

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    try:

        columns = _get_columns(
            conn,
            "market_data",
        )

        if not columns:

            raise RuntimeError(
                "market_data table does not exist or has no columns."
            )

        symbol_col = _find_column(
            columns,
            ["symbol"],
        )

        timestamp_col = _find_column(
            columns,
            [
                "timestamp",
                "source_timestamp",
            ],
        )

        open_col = _find_column(
            columns,
            [
                "open",
                "open_price",
                "openPrice",
            ],
        )

        high_col = _find_column(
            columns,
            [
                "high",
                "high_price",
                "highPrice",
            ],
        )

        low_col = _find_column(
            columns,
            [
                "low",
                "low_price",
                "lowPrice",
            ],
        )

        close_col = _find_column(
            columns,
            [
                "close",
                "close_price",
                "closePrice",
            ],
        )

        volume_col = _find_column(
            columns,
            ["volume"],
        )

        required = {
            "symbol": symbol_col,
            "timestamp": timestamp_col,
            "open": open_col,
            "high": high_col,
            "low": low_col,
            "close": close_col,
            "volume": volume_col,
        }

        for name, column in required.items():

            if column is None:

                raise RuntimeError(
                    "market_data has no "
                    + name
                    + " column."
                )

        query = """
            SELECT
                "{symbol}" AS symbol,
                "{timestamp}" AS timestamp,
                "{open}" AS open,
                "{high}" AS high,
                "{low}" AS low,
                "{close}" AS close,
                "{volume}" AS volume
            FROM market_data
            ORDER BY
                "{symbol}" ASC,
                "{timestamp}" ASC
        """.format(
            symbol=symbol_col,
            timestamp=timestamp_col,
            open=open_col,
            high=high_col,
            low=low_col,
            close=close_col,
            volume=volume_col,
        )

        rows = conn.execute(
            query
        ).fetchall()

        result = {
            asset: []
            for asset in EXPECTED_ASSETS
        }

        for row in rows:

            symbol = _normalize_text(
                row["symbol"]
            )

            if symbol not in result:

                continue

            open_price = _safe_float(
                row["open"]
            )

            high = _safe_float(
                row["high"]
            )

            low = _safe_float(
                row["low"]
            )

            close = _safe_float(
                row["close"]
            )

            volume = _safe_float(
                row["volume"]
            )

            if (
                open_price is None
                or high is None
                or low is None
                or close is None
            ):

                continue

            if high < low:

                raise RuntimeError(
                    "Invalid OHLC data for "
                    + symbol
                    + ": high < low."
                )

            result[
                symbol
            ].append(
                _build_market_bar(
                    symbol=symbol,
                    timestamp=row["timestamp"],
                    open_price=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=(
                        volume
                        if volume is not None
                        else 0.0
                    ),
                )
            )

        return result

    finally:

        conn.close()


# =============================================================================
# UNAVAILABLE STRUCTURAL STATE
# =============================================================================


def _build_insufficient_state(
    asset,
    points,
):

    return {
        "status": "UNAVAILABLE",
        "asset": asset,
        "points": points,
        "context_status": "INSUFFICIENT",
        "context_target": FULL_CONTEXT_TARGET,
        "context_minimum": MIN_CONTEXT,
        "structure_direction": "UNKNOWN",
        "structure_strength": "UNKNOWN",
        "structure_confidence": "UNKNOWN",
        "structure_point_type": None,
        "bos_recent": False,
        "choch_recent": False,
        "swing_count": 0,
        "structure_point_count": 0,
        "event_count": 0,
        "acceleration": None,
    }


# =============================================================================
# STRUCTURE CALCULATION
# =============================================================================


def calculate_structure(
    asset,
    bars,
):

    real_points = len(
        bars
    )

    context_status = _context_status(
        real_points
    )

    # -------------------------------------------------------------------------
    # ACTUAL MINIMUM
    # -------------------------------------------------------------------------

    if real_points < MIN_CONTEXT:

        return _build_insufficient_state(
            asset,
            real_points,
        )

    # -------------------------------------------------------------------------
    # BOUNDED ROLLING CONTEXT
    #
    # IMPORTANT:
    #
    # Even if millions of historical bars exist, this calculation consumes
    # at most FULL_CONTEXT_TARGET bars.
    # -------------------------------------------------------------------------

    window = bars[
        -FULL_CONTEXT_TARGET:
    ]

    context_points = len(
        window
    )

    # -------------------------------------------------------------------------
    # MARKET STRUCTURE ENGINE
    # -------------------------------------------------------------------------

    try:

        analysis = (
            market_structure_engine
            .analyze_market_structure(
                window,
                left_bars=LEFT_BARS,
                right_bars=RIGHT_BARS,
            )
        )

    except Exception as error:

        raise RuntimeError(
            "Structure analysis failed for "
            + asset
            + ": "
            + str(error)
        ) from error

    if not isinstance(
        analysis,
        dict,
    ):

        raise RuntimeError(
            "Invalid structure analysis for "
            + asset
        )

    swings = analysis.get(
        "swings",
        [],
    )

    structure_points = analysis.get(
        "structure_points",
        [],
    )

    events = analysis.get(
        "events",
        [],
    )

    if swings is None:
        swings = []

    if structure_points is None:
        structure_points = []

    if events is None:
        events = []

    # -------------------------------------------------------------------------
    # REAL PRICE ACCELERATION
    # -------------------------------------------------------------------------

    acceleration = (
        _normalize_acceleration(
            _calculate_acceleration(
                window
            )
        )
    )

    # -------------------------------------------------------------------------
    # NO STRUCTURE POINTS
    # -------------------------------------------------------------------------

    if not structure_points:

        return {
            "status": "AVAILABLE",
            "asset": asset,
            "points": context_points,
            "context_status": context_status,
            "context_target": FULL_CONTEXT_TARGET,
            "context_minimum": MIN_CONTEXT,
            "structure_direction": "UNKNOWN",
            "structure_strength": "UNKNOWN",
            "structure_confidence": "UNKNOWN",
            "structure_point_type": None,
            "bos_recent": False,
            "choch_recent": False,
            "swing_count": len(
                swings
            ),
            "structure_point_count": 0,
            "event_count": len(
                events
            ),
            "acceleration": acceleration,
        }

    # -------------------------------------------------------------------------
    # STRUCTURE DIRECTION
    # -------------------------------------------------------------------------

    direction = (
        market_structure_engine
        .classify_structure_direction(
            structure_points
        )
    )

    # -------------------------------------------------------------------------
    # STRUCTURE STRENGTH
    # -------------------------------------------------------------------------

    strength = (
        market_structure_engine
        .calculate_structure_strength(
            structure_points
        )
    )

    # -------------------------------------------------------------------------
    # STRUCTURE CONFIDENCE
    # -------------------------------------------------------------------------

    confidence = (
        market_structure_engine
        .calculate_structure_confidence(
            structure_points,
            events,
        )
    )

    # -------------------------------------------------------------------------
    # LATEST STRUCTURE POINT
    # -------------------------------------------------------------------------

    point_type = None

    latest_point = (
        structure_points[-1]
    )

    if hasattr(
        latest_point,
        "point_type",
    ):

        point_type = (
            latest_point.point_type
        )

    elif hasattr(
        latest_point,
        "type",
    ):

        point_type = (
            latest_point.type
        )

    elif isinstance(
        latest_point,
        dict,
    ):

        point_type = (
            latest_point.get(
                "point_type"
            )
        )

        if point_type is None:

            point_type = (
                latest_point.get(
                    "type"
                )
            )

    # -------------------------------------------------------------------------
    # EVENTS
    # -------------------------------------------------------------------------

    bos_recent = False
    choch_recent = False

    for event in events:

        event_type = None

        if hasattr(
            event,
            "event_type",
        ):

            event_type = (
                event.event_type
            )

        elif hasattr(
            event,
            "type",
        ):

            event_type = (
                event.type
            )

        elif isinstance(
            event,
            dict,
        ):

            event_type = (
                event.get(
                    "event_type"
                )
            )

            if event_type is None:

                event_type = (
                    event.get(
                        "type"
                    )
                )

        event_type = _normalize_text(
            event_type
        )

        if event_type == "BOS":

            bos_recent = True

        elif event_type == "CHOCH":

            choch_recent = True

    # -------------------------------------------------------------------------
    # AVAILABLE STRUCTURAL STATE
    # -------------------------------------------------------------------------

    return {
        "status": "AVAILABLE",
        "asset": asset,
        "points": context_points,
        "context_status": context_status,
        "context_target": FULL_CONTEXT_TARGET,
        "context_minimum": MIN_CONTEXT,
        "structure_direction": (
            _normalize_text(
                direction
            )
            or "UNKNOWN"
        ),
        "structure_strength": (
            _normalize_text(
                strength
            )
            or "UNKNOWN"
        ),
        "structure_confidence": (
            _normalize_text(
                confidence
            )
            or "UNKNOWN"
        ),
        "structure_point_type": (
            _normalize_text(
                point_type
            )
            if point_type is not None
            else None
        ),
        "bos_recent": bos_recent,
        "choch_recent": choch_recent,
        "swing_count": len(
            swings
        ),
        "structure_point_count": len(
            structure_points
        ),
        "event_count": len(
            events
        ),
        "acceleration": acceleration,
    }


# =============================================================================
# BUILD STRUCTURAL STATE
# =============================================================================


def build_structural_state():

    history = (
        load_market_data_by_symbol()
    )

    result = {}

    for asset in EXPECTED_ASSETS:

        bars = history.get(
            asset,
            [],
        )

        result[
            asset
        ] = calculate_structure(
            asset,
            bars,
        )

    return result


# =============================================================================
# REGIME CLASSIFICATION
# =============================================================================


def classify_regime(
    structure,
):

    if not isinstance(
        structure,
        dict,
    ):

        return "UNDEFINED"

    if structure.get(
        "status"
    ) != "AVAILABLE":

        return "UNDEFINED"

    direction = _normalize_text(
        structure.get(
            "structure_direction"
        )
    )

    strength = _normalize_text(
        structure.get(
            "structure_strength"
        )
    )

    confidence = _normalize_text(
        structure.get(
            "structure_confidence"
        )
    )

    bos_recent = bool(
        structure.get(
            "bos_recent",
            False,
        )
    )

    choch_recent = bool(
        structure.get(
            "choch_recent",
            False,
        )
    )

    if direction in {
        "BULLISH",
        "BEARISH",
    }:

        if strength in {
            "STRONG",
            "VERY_STRONG",
        }:

            return "TRENDING"

        if bos_recent:

            return "TRENDING"

        if confidence in {
            "HIGH",
            "VERY_HIGH",
        }:

            return "TRENDING"

    if choch_recent:

        return "TRANSITION"

    if direction == "NEUTRAL":

        return "RANGING"

    return "UNDEFINED"


# =============================================================================
# BUILD MARKET REGIME
# =============================================================================


def build_market_regime():

    structural_state = (
        build_structural_state()
    )

    if len(
        structural_state
    ) != len(
        EXPECTED_ASSETS
    ):

        raise RuntimeError(
            "Invalid structural asset count: "
            + str(
                len(
                    structural_state
                )
            )
        )

    market_regime = {}

    for asset in EXPECTED_ASSETS:

        if asset not in structural_state:

            raise RuntimeError(
                "Missing structural asset: "
                + asset
            )

        structure = (
            structural_state[
                asset
            ]
        )

        # ---------------------------------------------------------------------
        # SIGNAL BOUNDARY
        #
        # Only the five-field structural contract crosses this boundary.
        # ---------------------------------------------------------------------

        public_structure = {
            "trend": None,
            "volatility": None,
            "momentum": None,
            "position": None,
            "acceleration":
                structure.get(
                    "acceleration"
                ),
        }

        market_regime[
            asset
        ] = {

            "asset":
                asset,

            "status":
                structure.get(
                    "status",
                    "UNAVAILABLE",
                ),

            "points":
                structure.get(
                    "points",
                    0,
                ),

            "context_status":
                structure.get(
                    "context_status",
                    "INSUFFICIENT",
                ),

            "context_target":
                FULL_CONTEXT_TARGET,

            "context_minimum":
                MIN_CONTEXT,

            "regime":
                classify_regime(
                    structure
                ),

            "structure":
                public_structure,
        }

    return market_regime


# =============================================================================
# PUBLIC API
# =============================================================================


def load_market_regime():

    return build_market_regime()


def load_structural_state():

    return build_structural_state()


# =============================================================================
# VALIDATION
# =============================================================================


def validate_market_regime(
    market_regime,
):

    if not isinstance(
        market_regime,
        dict,
    ):

        return False

    if len(
        market_regime
    ) != len(
        EXPECTED_ASSETS
    ):

        return False

    allowed_status = {
        "AVAILABLE",
        "UNAVAILABLE",
    }

    allowed_context = {
        "FULL",
        "LIMITED",
        "INSUFFICIENT",
    }

    allowed_regimes = {
        "TRENDING",
        "RANGING",
        "HIGH_VOLATILITY",
        "LOW_VOLATILITY",
        "TRANSITION",
        "UNDEFINED",
    }

    for asset in EXPECTED_ASSETS:

        if asset not in market_regime:
            return False

        data = market_regime[
            asset
        ]

        if not isinstance(
            data,
            dict,
        ):
            return False

        if data.get(
            "asset"
        ) != asset:
            return False

        status = data.get(
            "status"
        )

        if status not in allowed_status:
            return False

        points = data.get(
            "points"
        )

        if not isinstance(
            points,
            int,
        ):
            return False

        context_status = data.get(
            "context_status"
        )

        if context_status not in allowed_context:
            return False

        if data.get(
            "context_target"
        ) != FULL_CONTEXT_TARGET:
            return False

        if data.get(
            "context_minimum"
        ) != MIN_CONTEXT:
            return False

        if data.get(
            "regime"
        ) not in allowed_regimes:
            return False

        structure = data.get(
            "structure"
        )

        if not isinstance(
            structure,
            dict,
        ):
            return False

        expected_fields = {
            "trend",
            "volatility",
            "momentum",
            "position",
            "acceleration",
        }

        if set(
            structure.keys()
        ) != expected_fields:

            return False

        acceleration = structure.get(
            "acceleration"
        )

        if acceleration is not None:

            if not isinstance(
                acceleration,
                (int, float),
            ):
                return False

            if not math.isfinite(
                float(
                    acceleration
                )
            ):
                return False

        # ---------------------------------------------------------------------
        # CONTEXT CONSISTENCY
        # ---------------------------------------------------------------------

        if points < MIN_CONTEXT:

            if status != "UNAVAILABLE":
                return False

            if context_status != "INSUFFICIENT":
                return False

        elif points < FULL_CONTEXT_TARGET:

            if status != "AVAILABLE":
                return False

            if context_status != "LIMITED":
                return False

        else:

            if status != "AVAILABLE":
                return False

            if context_status != "FULL":
                return False

    return True


# =============================================================================
# PRINT HEADER
# =============================================================================


def print_header():

    print("=" * 86)

    print(
        "ARUNDA MARKET REGIME ENGINE v0.6"
    )

    print("=" * 86)

    print(
        "Source              : market_data"
    )

    print(
        "Engine              : market_structure_engine"
    )

    print(
        "Storage             : MEMORY ONLY"
    )

    print(
        "Writes              : NONE"
    )

    print(
        "SQL                 : READ ONLY"
    )

    print(
        "Synthetic            : NO"
    )

    print(
        "Interpolation        : NO"
    )

    print(
        "Padding              : NO"
    )

    print(
        "Full Context Target  :",
        FULL_CONTEXT_TARGET
    )

    print(
        "Minimum Context      :",
        MIN_CONTEXT
    )

    print(
        "Context Model        :",
        "BOUNDED ROLLING"
    )

    print(
        "Unlimited Signals    :",
        "SUPPORTED"
    )

    print(
        "RAM Context          :",
        "BOUNDED"
    )

    print(
        "Signal Engine        :",
        "NOT USED"
    )

    print(
        "Scoring              :",
        "NOT USED"
    )

    print(
        "Decision             :",
        "NOT USED"
    )

    print("=" * 86)

    print()


# =============================================================================
# PRINT REGIME
# =============================================================================


def print_regime(
    market_regime,
):

    print(
        "MARKET REGIME"
    )

    print("-" * 100)

    print(
        "Asset  | Status      | Context     | Points | Regime"
    )

    print("-" * 100)

    for asset in EXPECTED_ASSETS:

        data = market_regime[
            asset
        ]

        print(
            "{:<6} | {:<11} | {:<11} | {:>6} | {}".format(
                asset,
                data.get(
                    "status",
                    "UNKNOWN",
                ),
                data.get(
                    "context_status",
                    "UNKNOWN",
                ),
                data.get(
                    "points",
                    0,
                ),
                data.get(
                    "regime",
                    "UNDEFINED",
                ),
            )
        )

    print()


# =============================================================================
# PRINT STRUCTURE DETAILS
# =============================================================================


def print_structure_details(
    market_regime,
):

    print(
        "STRUCTURAL STATE"
    )

    print("-" * 145)

    print(
        "Asset  | Direction | Strength | Confidence | BOS | CHOCH | Context | Points | Acceleration | Regime"
    )

    print("-" * 145)

    for asset in EXPECTED_ASSETS:

        data = market_regime[
            asset
        ]

        structure = data.get(
            "structure",
            {},
        )

        acceleration = structure.get(
            "acceleration"
        )

        if acceleration is None:

            acceleration_text = "NONE"

        else:

            acceleration_text = "{:.8f}".format(
                float(
                    acceleration
                )
            )

        print(
            "{:<6} | {:<9} | {:<8} | {:<10} | {:<3} | {:<5} | {:<7} | {:>6} | {:>12} | {}".format(
                asset,
                structure.get(
                    "structure_direction",
                    "UNKNOWN",
                ),
                structure.get(
                    "structure_strength",
                    "UNKNOWN",
                ),
                structure.get(
                    "structure_confidence",
                    "UNKNOWN",
                ),
                "Y"
                if structure.get(
                    "bos_recent",
                    False,
                )
                else "N",
                "Y"
                if structure.get(
                    "choch_recent",
                    False,
                )
                else "N",
                data.get(
                    "context_status",
                    "UNKNOWN",
                ),
                data.get(
                    "points",
                    0,
                ),
                acceleration_text,
                data.get(
                    "regime",
                    "UNDEFINED",
                ),
            )
        )

    print()


# =============================================================================
# CONTRACT
# =============================================================================


def print_contract(
    market_regime,
):

    valid = validate_market_regime(
        market_regime
    )

    available_assets = 0
    limited_assets = 0
    full_assets = 0
    insufficient_assets = 0
    acceleration_assets = 0

    for asset in EXPECTED_ASSETS:

        data = market_regime[
            asset
        ]

        if data.get(
            "status"
        ) == "AVAILABLE":

            available_assets += 1

        context_status = data.get(
            "context_status"
        )

        if context_status == "LIMITED":
            limited_assets += 1

        elif context_status == "FULL":
            full_assets += 1

        elif context_status == "INSUFFICIENT":
            insufficient_assets += 1

        if data.get(
            "structure",
            {}
        ).get(
            "acceleration"
        ) is not None:

            acceleration_assets += 1

    print("=" * 86)

    print(
        "MARKET REGIME CONTRACT"
    )

    print("=" * 86)

    print(
        "Expected Assets       :",
        len(EXPECTED_ASSETS)
    )

    print(
        "Available Assets      :",
        available_assets
    )

    print(
        "Full Context          :",
        full_assets
    )

    print(
        "Limited Context       :",
        limited_assets
    )

    print(
        "Insufficient Context  :",
        insufficient_assets
    )

    print(
        "Acceleration Data     :",
        acceleration_assets
    )

    print(
        "Full Context Target   :",
        FULL_CONTEXT_TARGET
    )

    print(
        "Minimum Context       :",
        MIN_CONTEXT
    )

    print(
        "Context Model         :",
        "BOUNDED ROLLING"
    )

    print(
        "Signal Capacity       :",
        "UNBOUNDED"
    )

    print(
        "RAM Context           :",
        "BOUNDED"
    )

    print(
        "Synthetic Data        :",
        "NONE"
    )

    print(
        "Storage               :",
        "MEMORY ONLY"
    )

    print(
        "Database writes       :",
        "NONE"
    )

    print(
        "SQL                   :",
        "READ ONLY"
    )

    print(
        "Signal Engine         :",
        "NOT USED"
    )

    print(
        "Scoring               :",
        "NOT USED"
    )

    print(
        "Decision              :",
        "NOT USED"
    )

    print(
        "Contract Status       :",
        "VALID"
        if valid
        else "INVALID",
    )

    print()

    return valid


# =============================================================================
# MAIN
# =============================================================================


def main():

    print_header()

    try:

        market_regime = (
            load_market_regime()
        )

        print_regime(
            market_regime
        )

        print_structure_details(
            market_regime
        )

        contract_valid = (
            print_contract(
                market_regime
            )
        )

        if contract_valid:

            print(
                "MARKET REGIME ENGINE STATUS : READY"
            )

            return 0

        print(
            "MARKET REGIME ENGINE STATUS : FAILED"
        )

        return 1

    except Exception as error:

        print("=" * 86)

        print(
            "MARKET REGIME ENGINE ERROR"
        )

        print("=" * 86)

        print(
            "Type  :",
            type(error).__name__
        )

        print(
            "Error :",
            str(error)
        )

        print()

        print(
            "MARKET REGIME ENGINE STATUS : FAILED"
        )

        return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================


if __name__ == "__main__":

    raise SystemExit(
        main()
    )