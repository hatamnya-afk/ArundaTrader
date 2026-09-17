import sqlite3
import math
from datetime import datetime, timezone


# =============================================================================
# ARUNDA TECHNICAL ENGINE v0.5
# LEGACY CONTRACT VALIDATION
# =============================================================================

DB_PATH = "arunda.db"

ENGINE_VERSION = "0.5.0"


# =============================================================================
# LEGACY CONTRACT
# =============================================================================

MIN_RETURN_5_POINTS = 6
MIN_VOLATILITY_20_POINTS = 21
MIN_STRUCTURE_20_POINTS = 20


VALIDATION_COLUMNS = {
    "technical_validation_score": "REAL",
    "technical_validation_status": "TEXT",
    "technical_validation_flags": "TEXT",
    "technical_validation_version": "TEXT",
    "technical_validated_at": "TEXT",
}


# =============================================================================
# TIME
# =============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# SAFE CONVERSION
# =============================================================================

def safe_float(value):
    if value is None:
        return None

    try:
        x = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(x):
        return None

    return x


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


# =============================================================================
# VALIDITY
# =============================================================================

def is_valid_positive(value):
    x = safe_float(value)
    return x is not None and x > 0


def is_valid_non_negative(value):
    x = safe_float(value)
    return x is not None and x >= 0


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name="market_technical"):
    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]


def add_validation_columns(conn):
    existing = set(
        get_columns(conn, "market_technical")
    )

    added = []

    for column, data_type in VALIDATION_COLUMNS.items():

        if column not in existing:

            conn.execute(
                f"""
                ALTER TABLE market_technical
                ADD COLUMN {column} {data_type}
                """
            )

            added.append(column)

    conn.commit()

    return added


# =============================================================================
# LEGACY INPUT CONTRACT
# =============================================================================

def validate_legacy_input_contract(data, flags):
    """
    Validate the fields that represent the Legacy Technical Engine input/output
    contract.

    This function DOES NOT calculate technical indicators.

    It only validates whether an existing technical record is compatible with
    the recovered Legacy contract.
    """

    history_points = safe_int(
        data.get("history_points"),
        0,
    )

    # -------------------------------------------------------------------------
    # HISTORY
    # -------------------------------------------------------------------------

    if history_points <= 0:
        flags.append("HISTORY_COUNT_UNKNOWN")

    elif history_points < MIN_RETURN_5_POINTS:
        flags.append("LEGACY_INSUFFICIENT_RETURN_HISTORY")

    elif history_points < MIN_VOLATILITY_20_POINTS:
        flags.append("LEGACY_PARTIAL_VOLATILITY_HISTORY")

    # -------------------------------------------------------------------------
    # DATA QUALITY
    # -------------------------------------------------------------------------

    data_quality = data.get("data_quality")

    if data_quality is not None:

        allowed_quality = {
            "INVALID",
            "INSUFFICIENT",
            "PARTIAL",
            "READY",
        }

        if str(data_quality) not in allowed_quality:
            flags.append("DATA_QUALITY_INVALID")


# =============================================================================
# PRICE CONTRACT
# =============================================================================

def validate_price_contract(data, flags):
    """
    Legacy calculation uses market_history.price.

    'close' is NOT a replacement source for Legacy price.

    market_technical may contain price/close depending on schema, but this
    validator does not silently promote close into canonical price.
    """

    price = safe_float(
        data.get("price")
    )

    close = safe_float(
        data.get("close")
    )

    canonical_price = price

    if canonical_price is None:
        flags.append("MISSING_PRICE")

    elif canonical_price <= 0:
        flags.append("INVALID_PRICE")

    # close is informational only.
    if close is not None:

        if close <= 0:
            flags.append("INVALID_CLOSE")

        elif price is not None:

            relative_difference = (
                abs(price - close)
                / max(abs(price), 1e-12)
            )

            if relative_difference > 0.25:
                flags.append(
                    "PRICE_CLOSE_MISMATCH"
                )

    return canonical_price


# =============================================================================
# CORE NUMERIC CONTRACT
# =============================================================================

def validate_numeric_fields(data, flags):

    non_negative_fields = [
        "volatility",
        "atr14",
        "atr_14",
        "volatility_5",
        "volatility_10",
        "volatility_20",
        "bb_width",
        "cloud_thickness",
    ]

    for field in non_negative_fields:

        if field not in data:
            continue

        raw = data.get(field)

        if raw is None:
            continue

        value = safe_float(raw)

        if value is None:

            flags.append(
                f"INVALID_{field.upper()}"
            )

        elif value < 0:

            flags.append(
                f"NEGATIVE_{field.upper()}"
            )


# =============================================================================
# RSI CONTRACT
# =============================================================================

def validate_rsi_contract(data, flags):

    for field in (
        "rsi14",
        "rsi_14",
    ):

        if field not in data:
            continue

        raw = data.get(field)

        if raw is None:
            continue

        value = safe_float(raw)

        if value is None:

            flags.append(
                f"INVALID_{field.upper()}"
            )

        elif not 0.0 <= value <= 100.0:

            flags.append(
                "RSI_OUT_OF_RANGE"
            )


# =============================================================================
# LEGACY STRUCTURE CONTRACT
# =============================================================================

def validate_structure_contract(data, flags):

    fields = [
        "high_20",
        "low_20",
        "price_position_20",
        "distance_from_high_20",
        "distance_from_low_20",
    ]

    present = {}

    for field in fields:

        if field not in data:
            continue

        raw = data.get(field)

        if raw is None:
            continue

        value = safe_float(raw)

        if value is None:

            flags.append(
                f"INVALID_{field.upper()}"
            )

        else:

            present[field] = value

    high = present.get("high_20")
    low = present.get("low_20")
    position = present.get("price_position_20")

    if high is not None and high <= 0:
        flags.append("INVALID_HIGH_20")

    if low is not None and low <= 0:
        flags.append("INVALID_LOW_20")

    if (
        high is not None
        and low is not None
        and high < low
    ):
        flags.append(
            "STRUCTURE_HIGH_LOW_INVALID"
        )

    if position is not None:

        if not 0.0 <= position <= 1.0:

            flags.append(
                "PRICE_POSITION_20_OUT_OF_RANGE"
            )


# =============================================================================
# LEGACY STATE CONTRACT
# =============================================================================

def validate_state_contract(data, flags):

    allowed_trend_direction = {
        "UNKNOWN",
        "UP",
        "DOWN",
        "SIDEWAYS",
    }

    allowed_trend_alignment = {
        "UNKNOWN",
        "BULLISH_ALIGNMENT",
        "BEARISH_ALIGNMENT",
        "MIXED_ALIGNMENT",
    }

    allowed_momentum = {
        "UNKNOWN",
        "POSITIVE",
        "NEGATIVE",
        "NEUTRAL",
    }

    allowed_volatility = {
        "UNKNOWN",
        "LOW",
        "NORMAL",
        "HIGH",
        "EXTREME",
    }

    allowed_volume = {
        "UNKNOWN",
        "LOW",
        "NORMAL",
        "ELEVATED",
        "EXTREME",
    }

    allowed_structure = {
        "UNKNOWN",
        "BULLISH_STRUCTURE",
        "BEARISH_STRUCTURE",
        "RANGE_STRUCTURE",
    }

    allowed_regime = {
        "UNKNOWN",
        "HIGH_VOLATILITY",
        "TRENDING_UP",
        "TRENDING_DOWN",
        "RANGING",
        "LOW_VOLATILITY",
        "TRANSITION",
    }

    contracts = {
        "trend_direction": allowed_trend_direction,
        "direction": allowed_trend_direction,
        "trend_alignment": allowed_trend_alignment,
        "alignment": allowed_trend_alignment,
        "momentum_state": allowed_momentum,
        "momentum": allowed_momentum,
        "volatility_state": allowed_volatility,
        "volatility": allowed_volatility,
        "volume_state": allowed_volume,
        "volume": allowed_volume,
        "structure_state": allowed_structure,
        "structure": allowed_structure,
        "regime_state": allowed_regime,
        "regime": allowed_regime,
    }

    for field, allowed in contracts.items():

        if field not in data:
            continue

        value = data.get(field)

        if value is None:
            continue

        value = str(value)

        if value not in allowed:

            flags.append(
                f"INVALID_{field.upper()}"
            )


# =============================================================================
# TREND NUMERIC CONTRACT
# =============================================================================

def validate_trend_contract(data, flags):

    trend_fields = [
        "sma_20",
        "ema_20",
        "sma_50",
        "ema_50",
        "trend_strength",
    ]

    for field in trend_fields:

        if field not in data:
            continue

        raw = data.get(field)

        if raw is None:
            continue

        value = safe_float(raw)

        if value is None:

            flags.append(
                f"INVALID_{field.upper()}"
            )

        elif field != "trend_strength" and value <= 0:

            flags.append(
                f"INVALID_{field.upper()}"
            )

    if (
        "trend_strength" in data
        and data.get("trend_strength") is not None
    ):

        strength = safe_float(
            data.get("trend_strength")
        )

        if strength is None:

            flags.append(
                "INVALID_TREND_STRENGTH"
            )

        elif strength < 0:

            flags.append(
                "NEGATIVE_TREND_STRENGTH"
            )


# =============================================================================
# MOMENTUM NUMERIC CONTRACT
# =============================================================================

def validate_momentum_contract(data, flags):

    return_fields = [
        "return_5",
        "return_10",
        "return_20",
    ]

    for field in return_fields:

        if field not in data:
            continue

        raw = data.get(field)

        if raw is None:
            continue

        value = safe_float(raw)

        if value is None:

            flags.append(
                f"INVALID_{field.upper()}"
            )


# =============================================================================
# VOLUME CONTRACT
# =============================================================================

def validate_volume_contract(data, flags):

    fields = [
        "volume_sma_20",
        "volume_ratio_20",
        "volume_ratio",
    ]

    for field in fields:

        if field not in data:
            continue

        raw = data.get(field)

        if raw is None:
            continue

        value = safe_float(raw)

        if value is None:

            flags.append(
                f"INVALID_{field.upper()}"
            )

        elif value < 0:

            flags.append(
                f"NEGATIVE_{field.upper()}"
            )

    for field in (
        "volume_ratio_20",
        "volume_ratio",
    ):

        if field not in data:
            continue

        raw = data.get(field)

        if raw is None:
            continue

        value = safe_float(raw)

        if value is not None and value < 0:

            flags.append(
                f"NEGATIVE_{field.upper()}"
            )


# =============================================================================
# VOLATILITY CONTRACT
# =============================================================================

def validate_volatility_contract(data, flags):

    volatility = None

    for field in (
        "volatility_20",
        "volatility",
    ):

        if field in data and data.get(field) is not None:

            volatility = safe_float(
                data.get(field)
            )

            if volatility is None:

                flags.append(
                    f"INVALID_{field.upper()}"
                )

            elif volatility < 0:

                flags.append(
                    f"NEGATIVE_{field.upper()}"
                )

            break


# =============================================================================
# FIBONACCI CONTRACT
# =============================================================================

def validate_fibonacci_contract(data, flags):

    fib_available = safe_int(
        data.get("fib_available"),
        0,
    )

    if fib_available not in (0, 1):

        flags.append(
            "FIB_AVAILABILITY_INVALID"
        )

        return

    if fib_available != 1:
        return

    fields = [
        "fib_236",
        "fib_382",
        "fib_500",
        "fib_618",
        "fib_786",
    ]

    values = []

    for field in fields:

        value = safe_float(
            data.get(field)
        )

        if value is None:

            flags.append(
                f"FIB_MISSING_{field.upper()}"
            )

        else:

            values.append(value)

    if len(values) >= 2:

        ordered = all(
            values[index]
            <= values[index + 1]
            for index in range(
                len(values) - 1
            )
        )

        if not ordered:

            flags.append(
                "FIB_LEVEL_ORDER_INVALID"
            )


# =============================================================================
# ICHIMOKU CONTRACT
# =============================================================================

def validate_ichimoku_contract(data, flags):

    ichimoku_available = safe_int(
        data.get("ichimoku_available"),
        0,
    )

    if ichimoku_available not in (0, 1):

        flags.append(
            "ICHIMOKU_AVAILABILITY_INVALID"
        )

        return

    if ichimoku_available != 1:
        return

    fields = [
        "tenkan",
        "kijun",
        "senkou_a",
        "senkou_b",
    ]

    for field in fields:

        value = safe_float(
            data.get(field)
        )

        if value is None:

            flags.append(
                f"ICHIMOKU_MISSING_{field.upper()}"
            )

        elif value <= 0:

            flags.append(
                f"ICHIMOKU_INVALID_{field.upper()}"
            )


# =============================================================================
# SCORE CONTRACT
# =============================================================================

def validate_score_contract(data, flags):

    fields = [
        "trend_score",
        "momentum_score",
        "volatility_score",
        "volume_score",
        "range_score",
        "breakout_score",
    ]

    for field in fields:

        if field not in data:
            continue

        raw = data.get(field)

        if raw is None:
            continue

        value = safe_float(raw)

        if value is None:

            flags.append(
                f"INVALID_{field.upper()}"
            )

        # IMPORTANT:
        #
        # Legacy contract does NOT establish a 0..1 range
        # for these scores.
        #
        # Therefore we only require finite numeric values.


# =============================================================================
# COMPLETENESS CONTRACT
# =============================================================================

def validate_completeness_contract(data, flags):

    value = None

    for field in (
        "technical_completeness",
        "completeness",
    ):

        if field in data and data.get(field) is not None:

            value = safe_float(
                data.get(field)
            )

            if value is None:

                flags.append(
                    f"INVALID_{field.upper()}"
                )

            break

    if value is not None:

        if not 0.0 <= value <= 1.0:

            flags.append(
                "COMPLETENESS_OUT_OF_RANGE"
            )

    return value


# =============================================================================
# AVAILABILITY CONTRACT
# =============================================================================

def validate_availability_contract(data, flags):

    for field in (
        "available",
        "technical_available",
    ):

        if field not in data:
            continue

        raw = data.get(field)

        if raw is None:
            continue

        value = safe_int(
            raw,
            -1,
        )

        if value not in (0, 1):

            flags.append(
                f"{field.upper()}_INVALID"
            )


# =============================================================================
# HARD INVALID FLAGS
# =============================================================================

HARD_INVALID_FLAGS = {
    "MISSING_PRICE",
    "INVALID_PRICE",
    "INVALID_CLOSE",
    "PRICE_CLOSE_MISMATCH",

    "RSI_OUT_OF_RANGE",

    "BREAKOUT_INVALID",

    "AVAILABILITY_INVALID",
    "TECHNICAL_AVAILABILITY_INVALID",

    "FIB_LEVEL_ORDER_INVALID",
    "FIB_AVAILABILITY_INVALID",

    "ICHIMOKU_AVAILABILITY_INVALID",

    "COMPLETENESS_OUT_OF_RANGE",

    "STRUCTURE_HIGH_LOW_INVALID",
    "PRICE_POSITION_20_OUT_OF_RANGE",

    "INVALID_TREND_DIRECTION",
    "INVALID_DIRECTION",
    "INVALID_TREND_ALIGNMENT",
    "INVALID_ALIGNMENT",
    "INVALID_MOMENTUM_STATE",
    "INVALID_MOMENTUM",
    "INVALID_VOLATILITY_STATE",
    "INVALID_VOLATILITY",
    "INVALID_VOLUME_STATE",
    "INVALID_VOLUME",
    "INVALID_STRUCTURE_STATE",
    "INVALID_STRUCTURE",
    "INVALID_REGIME_STATE",
    "INVALID_REGIME",
}


# =============================================================================
# VALIDATION
# =============================================================================

def validate_row(row, columns):

    data = dict(
        zip(columns, row)
    )

    flags = []

    # -------------------------------------------------------------------------
    # PRIMARY CONTRACTS
    # -------------------------------------------------------------------------

    canonical_price = validate_price_contract(
        data,
        flags,
    )

    validate_legacy_input_contract(
        data,
        flags,
    )

    validate_numeric_fields(
        data,
        flags,
    )

    validate_rsi_contract(
        data,
        flags,
    )

    validate_structure_contract(
        data,
        flags,
    )

    validate_state_contract(
        data,
        flags,
    )

    validate_trend_contract(
        data,
        flags,
    )

    validate_momentum_contract(
        data,
        flags,
    )

    validate_volume_contract(
        data,
        flags,
    )

    validate_volatility_contract(
        data,
        flags,
    )

    validate_fibonacci_contract(
        data,
        flags,
    )

    validate_ichimoku_contract(
        data,
        flags,
    )

    validate_score_contract(
        data,
        flags,
    )

    validate_availability_contract(
        data,
        flags,
    )

    completeness_value = (
        validate_completeness_contract(
            data,
            flags,
        )
    )

    # -------------------------------------------------------------------------
    # HISTORY
    # -------------------------------------------------------------------------

    history_points = safe_int(
        data.get("history_points"),
        0,
    )

    # -------------------------------------------------------------------------
    # HARD INVALID
    # -------------------------------------------------------------------------

    has_hard_invalid = any(
        flag in HARD_INVALID_FLAGS
        for flag in flags
    )

    # Any malformed numeric value is hard-invalid.
    if any(
        flag.startswith("INVALID_")
        or flag.startswith("NEGATIVE_")
        for flag in flags
    ):

        has_hard_invalid = True

    # -------------------------------------------------------------------------
    # STATUS
    # -------------------------------------------------------------------------

    if has_hard_invalid:

        status = "INVALID"

    elif (
        completeness_value is not None
        and completeness_value >= 0.75
    ):

        status = "VALID"

    elif (
        completeness_value is not None
        and completeness_value > 0
    ):

        status = "PARTIAL"

    elif (
        canonical_price is not None
        and history_points >= MIN_RETURN_5_POINTS
    ):

        status = "PARTIAL"

    elif (
        canonical_price is not None
        and history_points > 0
    ):

        status = "PARTIAL"

    else:

        status = "UNAVAILABLE"

    # -------------------------------------------------------------------------
    # SCORE
    # -------------------------------------------------------------------------

    score = 1.0

    if canonical_price is None:
        score -= 0.50

    if history_points <= 0:

        score -= 0.15

    elif history_points < MIN_RETURN_5_POINTS:

        score -= 0.10

    elif history_points < MIN_VOLATILITY_20_POINTS:

        score -= 0.05

    # -------------------------------------------------------------------------
    # OPTIONAL FEATURE AVAILABILITY
    # -------------------------------------------------------------------------

    optional_fields = [
        "rsi14",
        "rsi_14",
        "atr14",
        "atr_14",
        "ema20",
        "ema_20",
        "sma_20",
        "volatility_20",
        "volume_ratio",
        "volume_ratio_20",
        "trend",
        "trend_direction",
        "trend_alignment",
        "momentum_state",
        "volatility_state",
        "volume_state",
        "structure_state",
        "regime_state",
    ]

    optional_present = 0
    optional_total = 0

    for field in optional_fields:

        if field not in data:
            continue

        optional_total += 1

        if data.get(field) is not None:
            optional_present += 1

    if optional_total > 0:

        feature_ratio = (
            optional_present
            / optional_total
        )

        score *= (
            0.60
            + 0.40 * feature_ratio
        )

    # -------------------------------------------------------------------------
    # INVALID PENALTY
    # -------------------------------------------------------------------------

    if has_hard_invalid:
        score *= 0.50

    score = clamp(score)

    # -------------------------------------------------------------------------
    # FLAGS
    # -------------------------------------------------------------------------

    if not flags:

        flag_text = "NONE"

    else:

        flag_text = ",".join(
            sorted(
                set(flags)
            )
        )

    return (
        score,
        status,
        flag_text,
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA TECHNICAL ENGINE v0.5.0"
    )
    print(
        "LEGACY CONTRACT VALIDATION"
    )
    print("=" * 100)

    print(
        f"Database        : {DB_PATH}"
    )

    print(
        f"Engine Version  : {ENGINE_VERSION}"
    )

    print(
        "Mode            : VALIDATION"
    )

    print(
        "Calculation     : NOT PERFORMED"
    )

    print(
        "Synthetic Data  : FORBIDDEN"
    )

    print(
        "Interpolation   : FORBIDDEN"
    )

    print(
        "DB Source       : market_technical"
    )

    print("=" * 100)

    print()
    print(
        "LEGACY CONTRACT"
    )

    print("-" * 100)

    print(
        f"MIN_RETURN_5_POINTS      : "
        f"{MIN_RETURN_5_POINTS}"
    )

    print(
        f"MIN_VOLATILITY_20_POINTS : "
        f"{MIN_VOLATILITY_20_POINTS}"
    )

    print(
        f"MIN_STRUCTURE_20_POINTS  : "
        f"{MIN_STRUCTURE_20_POINTS}"
    )

    print("=" * 100)

    conn = None

    try:

        conn = sqlite3.connect(
            DB_PATH
        )

        conn.execute(
            "PRAGMA foreign_keys = ON"
        )

        print()
        print(
            "Database        : CONNECTED"
        )

        if not table_exists(
            conn,
            "market_technical",
        ):

            raise RuntimeError(
                "market_technical table does not exist"
            )

        print(
            "Technical Table : market_technical"
        )

        # ---------------------------------------------------------------------
        # SCHEMA
        # ---------------------------------------------------------------------

        added = add_validation_columns(
            conn
        )

        print(
            f"Validation Columns Added : "
            f"{len(added)}"
        )

        if added:

            print(
                "Added Columns             : "
                + ", ".join(added)
            )

        else:

            print(
                "Added Columns             : NONE"
            )

        # ---------------------------------------------------------------------
        # READ
        # ---------------------------------------------------------------------

        columns = get_columns(
            conn,
            "market_technical",
        )

        rows = conn.execute(
            "SELECT * FROM market_technical"
        ).fetchall()

        total = len(rows)

        print(
            f"Technical Records         : "
            f"{total}"
        )

        # ---------------------------------------------------------------------
        # VALIDATION
        # ---------------------------------------------------------------------

        print()
        print(
            "Running Legacy Contract "
            "Validation..."
        )

        valid_count = 0
        partial_count = 0
        invalid_count = 0
        unavailable_count = 0
        errors = 0

        validation_results = []

        update_sql = """
            UPDATE market_technical
            SET
                technical_validation_score = ?,
                technical_validation_status = ?,
                technical_validation_flags = ?,
                technical_validation_version = ?,
                technical_validated_at = ?
            WHERE id = ?
        """

        for row in rows:

            try:

                record_id = row[0]

                score, status, flags = (
                    validate_row(
                        row,
                        columns,
                    )
                )

                validation_results.append(
                    (
                        score,
                        status,
                        flags,
                        ENGINE_VERSION,
                        utc_now(),
                        record_id,
                    )
                )

                if status == "VALID":

                    valid_count += 1

                elif status == "PARTIAL":

                    partial_count += 1

                elif status == "INVALID":

                    invalid_count += 1

                elif status == "UNAVAILABLE":

                    unavailable_count += 1

            except Exception as exc:

                errors += 1

                validation_results.append(
                    (
                        0.0,
                        "INVALID",
                        "VALIDATION_ERROR:"
                        + str(exc)[:200],
                        ENGINE_VERSION,
                        utc_now(),
                        row[0],
                    )
                )

                invalid_count += 1

        # ---------------------------------------------------------------------
        # WRITE VALIDATION RESULTS
        # ---------------------------------------------------------------------

        conn.executemany(
            update_sql,
            validation_results,
        )

        conn.commit()

        # ---------------------------------------------------------------------
        # SUMMARY
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print(
            "TECHNICAL VALIDATION SUMMARY"
        )
        print("=" * 100)

        print(
            f"Technical Records       : "
            f"{total}"
        )

        print(
            f"Valid                   : "
            f"{valid_count}"
        )

        print(
            f"Partial                 : "
            f"{partial_count}"
        )

        print(
            f"Invalid                 : "
            f"{invalid_count}"
        )

        print(
            f"Unavailable             : "
            f"{unavailable_count}"
        )

        print(
            f"Errors                  : "
            f"{errors}"
        )

        # ---------------------------------------------------------------------
        # RECENT
        # ---------------------------------------------------------------------

        print()
        print(
            "RECENT TECHNICAL VALIDATION"
        )

        print("-" * 100)

        print(
            f"{'SYMBOL':<18}"
            f"{'SCORE':<10}"
            f"{'STATUS':<14}"
            f"{'HISTORY':<10}"
            f"FLAGS"
        )

        print("-" * 100)

        recent = conn.execute(
            """
            SELECT
                symbol,
                technical_validation_score,
                technical_validation_status,
                history_points,
                technical_validation_flags
            FROM market_technical
            ORDER BY id DESC
            LIMIT 30
            """
        ).fetchall()

        for item in recent:

            symbol = (
                str(item[0])
                if item[0] is not None
                else "UNKNOWN"
            )

            score = safe_float(
                item[1]
            )

            score_text = (
                f"{score:.3f}"
                if score is not None
                else "NA"
            )

            status = (
                str(item[2])
                if item[2] is not None
                else "NA"
            )

            history = (
                str(item[3])
                if item[3] is not None
                else "NA"
            )

            flags = (
                str(item[4])
                if item[4] is not None
                else "NONE"
            )

            print(
                f"{symbol:<18}"
                f"{score_text:<10}"
                f"{status:<14}"
                f"{history:<10}"
                f"{flags}"
            )

        # ---------------------------------------------------------------------
        # CONTRACT STATUS
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print(
            "ARUNDA TECHNICAL ENGINE v0.5.0 COMPLETE"
        )
        print("=" * 100)

        print(
            "ROLE              : LEGACY CONTRACT VALIDATOR"
        )

        print(
            "CALCULATION       : NOT PERFORMED"
        )

        print(
            "PRICE              : PRICE PRIMARY"
        )

        print(
            "CLOSE              : OPTIONAL / NON-CANONICAL"
        )

        print(
            "RETURN WARMUP      : 6 POINTS"
        )

        print(
            "VOLATILITY WARMUP  : 21 POINTS"
        )

        print(
            "STRUCTURE WARMUP   : 20 POINTS"
        )

        print(
            "RSI RANGE          : 0..100"
        )

        print(
            "SCORE RANGE        : NOT ASSUMED"
        )

        print(
            "SYNTHETIC DATA     : FORBIDDEN"
        )

        print(
            "INTERPOLATION      : FORBIDDEN"
        )

        print(
            "SIGNAL             : NOT USED"
        )

        print(
            "PREDICTION         : NOT USED"
        )

        print(
            "OPPORTUNITY        : NOT USED"
        )

        print(
            "RISK               : NOT USED"
        )

        print(
            "EXECUTION          : NOT USED"
        )

        print("=" * 100)

    except Exception as exc:

        if conn is not None:
            conn.rollback()

        print()
        print("=" * 100)
        print(
            "ARUNDA TECHNICAL ENGINE ERROR"
        )
        print("=" * 100)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print("=" * 100)

        raise

    finally:

        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()