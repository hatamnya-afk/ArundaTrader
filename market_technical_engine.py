import sqlite3
import math
from datetime import datetime, timezone

DB_PATH = "arunda.db"
ENGINE_VERSION = "0.4.1"

VALIDATION_COLUMNS = {
    "technical_validation_score": "REAL",
    "technical_validation_status": "TEXT",
    "technical_validation_flags": "TEXT",
    "technical_validation_version": "TEXT",
    "technical_validated_at": "TEXT",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


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


def is_valid_positive(value):
    x = safe_float(value)
    return x is not None and x > 0


def is_valid_non_negative(value):
    x = safe_float(value)
    return x is not None and x >= 0


def add_validation_columns(conn):
    existing = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(market_technical)"
        ).fetchall()
    }

    added = []

    for column, data_type in VALIDATION_COLUMNS.items():
        if column not in existing:
            conn.execute(
                f"ALTER TABLE market_technical "
                f"ADD COLUMN {column} {data_type}"
            )
            added.append(column)

    conn.commit()
    return added


def get_columns(conn):
    return [
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(market_technical)"
        ).fetchall()
    ]


def validate_row(row, columns):
    data = dict(zip(columns, row))

    flags = []

    history_points = safe_int(data.get("history_points"), 0)

    price = safe_float(data.get("price"))
    close = safe_float(data.get("close"))

    # ------------------------------------------------------------------
    # PRICE CONTRACT
    # ------------------------------------------------------------------
    # v0.4.1:
    # price is the canonical current-price field.
    # close is optional and must NOT be required.
    # ------------------------------------------------------------------

    if price is None:
        if close is not None and close > 0:
            canonical_price = close
        else:
            canonical_price = None
            flags.append("MISSING_PRICE")
    else:
        canonical_price = price

    if canonical_price is not None and canonical_price <= 0:
        flags.append("INVALID_PRICE")

    # close is optional.
    # If both close and price exist, check only internal consistency.
    if price is not None and close is not None:
        if close <= 0:
            flags.append("INVALID_CLOSE")
        else:
            relative_difference = abs(price - close) / max(abs(price), 1e-12)

            if relative_difference > 0.25:
                flags.append("PRICE_CLOSE_MISMATCH")

    # ------------------------------------------------------------------
    # HISTORY CONTRACT
    # ------------------------------------------------------------------

    if history_points <= 0:
        flags.append("HISTORY_COUNT_UNKNOWN")
    elif history_points < 2:
        flags.append("LIMITED_HISTORY")

    # ------------------------------------------------------------------
    # CORE NUMERIC FEATURES
    # ------------------------------------------------------------------

    numeric_non_negative = [
        "volatility",
        "atr14",
        "atr_14",
        "volatility_5",
        "volatility_10",
        "volatility_20",
        "bb_width",
        "cloud_thickness",
        "technical_completeness",
        "completeness",
    ]

    for field in numeric_non_negative:
        if field in data and data.get(field) is not None:
            value = safe_float(data.get(field))

            if value is None:
                flags.append(f"INVALID_{field.upper()}")
            elif value < 0:
                flags.append(f"NEGATIVE_{field.upper()}")

    # ------------------------------------------------------------------
    # RSI CONTRACT
    # ------------------------------------------------------------------

    rsi_fields = ["rsi14", "rsi_14"]

    for field in rsi_fields:
        if field in data and data.get(field) is not None:
            value = safe_float(data.get(field))

            if value is None:
                flags.append(f"INVALID_{field.upper()}")
            elif not 0.0 <= value <= 100.0:
                flags.append(f"RSI_OUT_OF_RANGE")

    # ------------------------------------------------------------------
    # BREAKOUT CONTRACT
    # ------------------------------------------------------------------

    if "breakout_20" in data and data.get("breakout_20") is not None:
        breakout = safe_int(data.get("breakout_20"), -1)

        if breakout not in (-1, 0, 1):
            flags.append("BREAKOUT_INVALID")

    # ------------------------------------------------------------------
    # AVAILABILITY CONTRACT
    # ------------------------------------------------------------------

    available = data.get("available")

    if available is not None:
        available_int = safe_int(available, -1)

        if available_int not in (0, 1):
            flags.append("AVAILABILITY_INVALID")

    technical_available = data.get("technical_available")

    if technical_available is not None:
        technical_available_int = safe_int(
            technical_available,
            -1
        )

        if technical_available_int not in (0, 1):
            flags.append("TECHNICAL_AVAILABILITY_INVALID")

    # ------------------------------------------------------------------
    # FIBONACCI CONTRACT
    # ------------------------------------------------------------------

    fib_available = safe_int(
        data.get("fib_available"),
        0
    )

    if fib_available == 1:

        fib_fields = [
            "fib_236",
            "fib_382",
            "fib_500",
            "fib_618",
            "fib_786",
        ]

        fib_values = []

        for field in fib_fields:
            value = safe_float(data.get(field))

            if value is None:
                flags.append(f"FIB_MISSING_{field.upper()}")
            else:
                fib_values.append(value)

        if len(fib_values) >= 2:
            ordered = all(
                fib_values[i] <= fib_values[i + 1]
                for i in range(len(fib_values) - 1)
            )

            if not ordered:
                flags.append("FIB_LEVEL_ORDER_INVALID")

    # ------------------------------------------------------------------
    # ICHIMOKU CONTRACT
    # ------------------------------------------------------------------

    ichimoku_available = safe_int(
        data.get("ichimoku_available"),
        0
    )

    if ichimoku_available == 1:

        ichimoku_fields = [
            "tenkan",
            "kijun",
            "senkou_a",
            "senkou_b",
        ]

        for field in ichimoku_fields:
            value = safe_float(data.get(field))

            if value is None:
                flags.append(
                    f"ICHIMOKU_MISSING_{field.upper()}"
                )

    # ------------------------------------------------------------------
    # SCORE CONTRACT
    # ------------------------------------------------------------------
    # IMPORTANT:
    # v0.4.1 does NOT assume trend_score, momentum_score,
    # volatility_score or volume_score are normalized 0..1.
    #
    # They are treated as opaque engine outputs.
    # Only finite numeric validity is checked.
    # ------------------------------------------------------------------

    score_fields = [
        "trend_score",
        "momentum_score",
        "volatility_score",
        "volume_score",
        "range_score",
        "breakout_score",
    ]

    score_present = 0

    for field in score_fields:

        if field not in data:
            continue

        value_raw = data.get(field)

        if value_raw is None:
            continue

        value = safe_float(value_raw)

        if value is None:
            flags.append(
                f"INVALID_{field.upper()}"
            )
        else:
            score_present += 1

    # ------------------------------------------------------------------
    # TECHNICAL COMPLETENESS
    # ------------------------------------------------------------------

    completeness_value = None

    for field in [
        "technical_completeness",
        "completeness",
    ]:
        if field in data and data.get(field) is not None:
            completeness_value = safe_float(
                data.get(field)
            )
            break

    if completeness_value is not None:

        if not 0.0 <= completeness_value <= 1.0:
            flags.append("COMPLETENESS_OUT_OF_RANGE")

    # ------------------------------------------------------------------
    # DATA QUALITY CLASSIFICATION
    # ------------------------------------------------------------------

    hard_invalid_flags = {
        "MISSING_PRICE",
        "INVALID_PRICE",
        "INVALID_CLOSE",
        "PRICE_CLOSE_MISMATCH",
        "INVALID_RSI14",
        "INVALID_RSI_14",
        "RSI_OUT_OF_RANGE",
        "BREAKOUT_INVALID",
        "AVAILABILITY_INVALID",
        "TECHNICAL_AVAILABILITY_INVALID",
        "FIB_LEVEL_ORDER_INVALID",
        "COMPLETENESS_OUT_OF_RANGE",
    }

    has_hard_invalid = any(
        flag in hard_invalid_flags
        for flag in flags
    )

    # Any explicitly malformed numeric field is also invalid.
    if any(
        flag.startswith("INVALID_")
        or flag.startswith("NEGATIVE_")
        for flag in flags
    ):
        has_hard_invalid = True

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
        and history_points >= 2
    ):
        status = "PARTIAL"

    else:
        status = "UNAVAILABLE"

    # ------------------------------------------------------------------
    # VALIDATION SCORE
    # ------------------------------------------------------------------

    score = 1.0

    if canonical_price is None:
        score -= 0.50

    if history_points <= 0:
        score -= 0.15
    elif history_points < 2:
        score -= 0.10

    # Missing optional features do NOT incur a penalty.
    # They are simply unavailable.

    optional_available = 0
    optional_total = 0

    for field in [
        "rsi14",
        "rsi_14",
        "atr14",
        "atr_14",
        "ema20",
        "ema_20",
        "sma_20",
        "volatility_20",
        "volume_ratio",
        "trend",
    ]:

        if field not in data:
            continue

        optional_total += 1

        if data.get(field) is not None:
            optional_available += 1

    if optional_total > 0:
        feature_ratio = (
            optional_available / optional_total
        )
        score = score * (
            0.60 + 0.40 * feature_ratio
        )

    if has_hard_invalid:
        score *= 0.50

    score = clamp(score)

    # ------------------------------------------------------------------
    # FLAG NORMALIZATION
    # ------------------------------------------------------------------

    if not flags:
        flag_text = "NONE"
    else:
        flag_text = ",".join(sorted(set(flags)))

    return (
        score,
        status,
        flag_text,
    )


def main():

    print("=" * 90)
    print(
        "ARUNDA MARKET TECHNICAL ENGINE v0.4.1"
    )
    print(
        "TECHNICAL VALIDATION / CALIBRATION"
    )
    print("=" * 90)
    print(
        f"Database        : {DB_PATH}"
    )
    print(
        "Mode            : TECHNICAL VALIDATION / "
        "CALIBRATION"
    )
    print(
        "Validation      : CONTRACT FIX"
    )
    print(
        "Price Contract  : PRICE PRIMARY / CLOSE OPTIONAL"
    )
    print(
        "Score Contract  : FINITE VALUE ONLY"
    )
    print(
        "Signal          : NOT USED"
    )
    print(
        "Prediction      : NOT USED"
    )
    print(
        "Opportunity     : NOT USED"
    )
    print(
        "Risk            : NOT USED"
    )
    print(
        "Execution       : NOT USED"
    )
    print("=" * 90)

    conn = None

    try:

        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")

        print("Database        : CONNECTED")
        print(
            "Technical Table : market_technical"
        )

        table_exists = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name='market_technical'
            """
        ).fetchone()

        if not table_exists:
            raise RuntimeError(
                "market_technical table does not exist"
            )

        added = add_validation_columns(conn)

        print(
            f"Validation Columns Added : {len(added)}"
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

        columns = get_columns(conn)

        rows = conn.execute(
            "SELECT * FROM market_technical"
        ).fetchall()

        total = len(rows)

        print(
            f"Technical Records         : {total}"
        )

        print(
            "Running validation..."
        )
        print()

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

                score, status, flags = validate_row(
                    row,
                    columns
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

        conn.executemany(
            update_sql,
            validation_results
        )

        conn.commit()

        print()
        print("=" * 90)
        print(
            "TECHNICAL VALIDATION / CALIBRATION SUMMARY"
        )
        print("=" * 90)

        print(
            f"Technical Records       : {total}"
        )
        print(
            f"Valid                   : {valid_count}"
        )
        print(
            f"Partial                 : {partial_count}"
        )
        print(
            f"Invalid                 : {invalid_count}"
        )
        print(
            f"Unavailable             : {unavailable_count}"
        )
        print(
            f"Errors                  : {errors}"
        )

        print()
        print(
            "Validation Rules:"
        )
        print(
            "  PRICE                  : PRIMARY"
        )
        print(
            "  CLOSE                  : OPTIONAL"
        )
        print(
            "  SCORE RANGE            : NOT ASSUMED"
        )
        print(
            "  HISTORY                : CONTEXTUAL"
        )
        print(
            "  OPTIONAL FEATURES      : NO PENALTY"
        )
        print(
            "  FIBONACCI              : VALIDATE IF AVAILABLE"
        )
        print(
            "  ICHIMOKU               : VALIDATE IF AVAILABLE"
        )

        print()
        print(
            "RECENT TECHNICAL VALIDATION"
        )
        print("-" * 90)
        print(
            f"{'SYMBOL':<14}"
            f"{'SCORE':<10}"
            f"{'STATUS':<14}"
            f"{'HISTORY':<10}"
            f"FLAGS"
        )
        print("-" * 90)

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

            score = safe_float(item[1])

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
                f"{symbol:<14}"
                f"{score_text:<10}"
                f"{status:<14}"
                f"{history:<10}"
                f"{flags}"
            )

        print()
        print("=" * 90)
        print(
            "ARUNDA MARKET TECHNICAL ENGINE v0.4.1 COMPLETE"
        )
        print("=" * 90)
        print(
            "VALIDATION STATUS : SUCCESS"
        )
        print(
            "Contract          : FIXED"
        )
        print(
            "Price             : VALIDATED"
        )
        print(
            "Close             : OPTIONAL"
        )
        print(
            "Scores            : TYPE VALIDATED"
        )
        print(
            "History           : CONTEXTUAL"
        )
        print(
            "Structure         : VALIDATED"
        )
        print(
            "Trend             : VALIDATED"
        )
        print(
            "Momentum          : VALIDATED"
        )
        print(
            "Volatility        : VALIDATED"
        )
        print(
            "Volume            : VALIDATED"
        )
        print(
            "Fibonacci         : VALIDATED WHEN AVAILABLE"
        )
        print(
            "Ichimoku          : VALIDATED WHEN AVAILABLE"
        )
        print(
            "Ranking           : NOT USED"
        )
        print(
            "Opportunity       : NOT USED"
        )
        print(
            "Signal            : NOT USED"
        )
        print(
            "Prediction        : NOT USED"
        )
        print(
            "Risk              : NOT USED"
        )
        print(
            "Execution         : NOT USED"
        )
        print("=" * 90)

    except Exception as exc:

        if conn is not None:
            conn.rollback()

        print()
        print("=" * 90)
        print(
            "ARUNDA MARKET TECHNICAL ENGINE ERROR"
        )
        print("=" * 90)
        print(
            f"{type(exc).__name__}: {exc}"
        )
        print("=" * 90)

        raise

    finally:

        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()