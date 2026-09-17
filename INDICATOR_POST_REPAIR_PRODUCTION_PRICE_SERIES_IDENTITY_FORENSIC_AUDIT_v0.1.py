import ast
import math
import os
import sqlite3
import sys
from collections import Counter


# ============================================================
# ARUNDA
# INDICATOR POST REPAIR PRODUCTION SERIES WINDOW COMPOSITION
# AND RECONSTRUCTION FORENSIC AUDIT v0.1
# ============================================================

MODE = "READ ONLY"
DATABASE_WRITE = "NONE"
ENGINE_WRITE = "NONE"
FORMULA_WRITE = "NONE"
PRODUCTION_RECALCULATION = "NONE"

BASE_DIR = "C:/Users/ASUS/ArundaTrader"
ENGINE_PATH = os.path.join(BASE_DIR, "market_data_engine.py")
DB_PATH = os.path.join(BASE_DIR, "arunda.db")

TARGET_SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

SNAPSHOT_SOURCE = "COINMARKETCAP"
EXPECTED_ENGINE_VERSION = "MARKET_SNAPSHOT_CMC_v0.4"

LOOKBACK = 120

EMA20_PERIOD = 20
EMA50_PERIOD = 50
RSI14_PERIOD = 14

EPSILON = 1e-10


# ============================================================
# PRINT HELPERS
# ============================================================

def line(char="=", width=100):
    print(char * width)


def print_header(title):
    line("=")
    print(title)
    line("=")


def section(title):
    print()
    line("=")
    print(title)
    line("=")


def subsection(title):
    print()
    print(title)
    line("-")


def fmt(value):
    if value is None:
        return "None"

    if isinstance(value, float):
        return f"{value:.15f}"

    return str(value)


# ============================================================
# SAFE NUMERIC HELPERS
# ============================================================

def to_float(value):
    if value is None:
        return None

    try:
        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except Exception:
        return None


def almost_equal(a, b, rel_tol=1e-10, abs_tol=1e-10):
    if a is None or b is None:
        return False

    return math.isclose(
        float(a),
        float(b),
        rel_tol=rel_tol,
        abs_tol=abs_tol,
    )


def relative_error(current, reference):
    if current is None or reference is None:
        return None

    denominator = max(abs(reference), EPSILON)

    return abs(current - reference) / denominator


# ============================================================
# ENGINE SOURCE FORENSICS
# ============================================================

def load_engine_source():
    if not os.path.exists(ENGINE_PATH):
        return None

    with open(
        ENGINE_PATH,
        "r",
        encoding="utf-8",
        errors="replace",
    ) as f:
        return f.read()


def parse_engine(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def function_inventory(tree):
    inventory = {}

    if tree is None:
        return inventory

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            inventory[node.name] = (
                node.lineno,
                getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
            )

    return inventory


# ============================================================
# PRODUCTION FUNCTIONS
# ============================================================

def independent_ema(values, period):
    """
    Independent standard EMA reconstruction.

    Seed:
        SMA of first 'period' values

    Recursive:
        EMA = price * alpha + previous EMA * (1-alpha)

    alpha = 2 / (period + 1)
    """

    clean = [
        to_float(value)
        for value in values
        if to_float(value) is not None
    ]

    if len(clean) < period:
        return None

    alpha = 2.0 / (period + 1.0)

    ema_value = sum(
        clean[:period]
    ) / period

    for price in clean[period:]:
        ema_value = (
            price * alpha
            + ema_value * (1.0 - alpha)
        )

    return ema_value


def independent_rsi(values, period=14):
    """
    Independent Wilder RSI reconstruction.

    Uses:
        initial average gain/loss over first period
        Wilder smoothing afterwards
    """

    clean = [
        to_float(value)
        for value in values
        if to_float(value) is not None
    ]

    if len(clean) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(clean)):
        delta = clean[i] - clean[i - 1]

        if delta > 0:
            gains.append(delta)
            losses.append(0.0)

        else:
            gains.append(0.0)
            losses.append(abs(delta))

    if len(gains) < period:
        return None

    avg_gain = (
        sum(gains[:period])
        / period
    )

    avg_loss = (
        sum(losses[:period])
        / period
    )

    for i in range(period, len(gains)):

        avg_gain = (
            (avg_gain * (period - 1))
            + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1))
            + losses[i]
        ) / period

    if avg_loss == 0:

        if avg_gain == 0:
            return 50.0

        return 100.0

    rs = avg_gain / avg_loss

    return 100.0 - (
        100.0 / (1.0 + rs)
    )


# ============================================================
# DATABASE SCHEMA
# ============================================================

def get_columns(conn, table):
    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


# ============================================================
# ACTUAL PRODUCTION WINDOW
# ============================================================

def get_actual_production_rows(conn, symbol):
    """
    Reproduces the actual production query path discovered
    in the previous producer-chain forensic audit.

    IMPORTANT:
    This intentionally uses the actual production source
    condition:

        source = COINMARKETCAP
        timeframe = SNAPSHOT
        close IS NOT NULL
        ORDER BY id ASC
        LIMIT 120

    No filtering by engine_version is applied here.

    That is deliberate.

    We must inspect whether mixed engine generations exist
    inside the actual production window.
    """

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            symbol,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            ema20,
            ema50,
            rsi14,
            macd,
            macd_signal,
            macd_hist,
            atr14,
            adx14,
            bb_middle,
            bb_upper,
            bb_lower,
            bb_width,
            volume_sma20,
            volume_ratio,
            volatility,
            technical_score,
            source,
            source_timestamp,
            price_change_1h,
            price_change_24h,
            market_cap,
            volume_24h,
            source_latency_ms,
            engine_version
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = 'SNAPSHOT'
            AND close IS NOT NULL
        ORDER BY id ASC
        LIMIT ?
        """,
        (
            symbol,
            SNAPSHOT_SOURCE,
            LOOKBACK,
        ),
    ).fetchall()

    return rows


# ============================================================
# WINDOW COMPOSITION
# ============================================================

def print_window_identity(rows):

    subsection(
        "PRODUCTION WINDOW IDENTITY"
    )

    if not rows:
        print(
            "[NONE] No production rows found"
        )
        return

    first = rows[0]
    last = rows[-1]

    print(
        f"ROW COUNT             : {len(rows)}"
    )

    print(
        f"FIRST ID              : {first[0]}"
    )

    print(
        f"LAST ID               : {last[0]}"
    )

    print(
        f"FIRST TIMESTAMP       : {first[1]}"
    )

    print(
        f"LAST TIMESTAMP        : {last[1]}"
    )

    print(
        f"FIRST SOURCE TIME     : {first[26]}"
    )

    print(
        f"LAST SOURCE TIME      : {last[26]}"
    )

    print(
        f"FIRST CLOSE           : {first[7]}"
    )

    print(
        f"LAST CLOSE            : {last[7]}"
    )


def print_engine_distribution(rows):

    subsection(
        "ENGINE VERSION DISTRIBUTION"
    )

    counter = Counter(
        row[33]
        for row in rows
    )

    for engine, count in counter.items():
        print(
            f"ENGINE={engine} | ROWS={count}"
        )


def print_source_distribution(rows):

    subsection(
        "SOURCE DISTRIBUTION"
    )

    counter = Counter(
        row[25]
        for row in rows
    )

    for source, count in counter.items():
        print(
            f"SOURCE={source} | ROWS={count}"
        )


def print_timeframe_distribution(rows):

    subsection(
        "TIMEFRAME DISTRIBUTION"
    )

    counter = Counter(
        row[3]
        for row in rows
    )

    for timeframe, count in counter.items():
        print(
            f"TIMEFRAME={timeframe} | ROWS={count}"
        )


# ============================================================
# ID CONTINUITY
# ============================================================

def inspect_id_continuity(rows):

    subsection(
        "ID CONTINUITY"
    )

    ids = [
        row[0]
        for row in rows
    ]

    if len(ids) < 2:
        print(
            "STATUS                : INSUFFICIENT"
        )
        return

    gaps = []

    for previous, current in zip(
        ids,
        ids[1:],
    ):

        delta = current - previous

        if delta != 1:
            gaps.append(
                (
                    previous,
                    current,
                    delta,
                )
            )

    print(
        f"FIRST ID              : {ids[0]}"
    )

    print(
        f"LAST ID               : {ids[-1]}"
    )

    print(
        f"EXPECTED ID STEPS     : {len(ids) - 1}"
    )

    print(
        f"NON-CONTIGUOUS STEPS  : {len(gaps)}"
    )

    if gaps:

        print()

        for previous, current, delta in gaps[:20]:
            print(
                f"GAP: {previous} -> {current} "
                f"| DELTA={delta}"
            )

        if len(gaps) > 20:
            print(
                f"... {len(gaps) - 20} additional gaps"
            )

        print(
            "STATUS                : GAPS_DETECTED"
        )

    else:

        print(
            "STATUS                : CONTIGUOUS"
        )


# ============================================================
# TIMESTAMP ANALYSIS
# ============================================================

def inspect_timestamps(rows):

    subsection(
        "TIMESTAMP COMPOSITION"
    )

    timestamps = [
        row[1]
        for row in rows
    ]

    if len(timestamps) < 2:
        print(
            "STATUS                : INSUFFICIENT"
        )
        return

    duplicate_count = (
        len(timestamps)
        - len(set(timestamps))
    )

    print(
        f"TOTAL TIMESTAMPS      : {len(timestamps)}"
    )

    print(
        f"DUPLICATE TIMESTAMPS  : {duplicate_count}"
    )

    deltas = []

    for previous, current in zip(
        timestamps,
        timestamps[1:],
    ):

        try:
            from datetime import datetime

            p = datetime.fromisoformat(
                previous.replace(
                    "Z",
                    "+00:00",
                )
            )

            c = datetime.fromisoformat(
                current.replace(
                    "Z",
                    "+00:00",
                )
            )

            deltas.append(
                (
                    c - p
                ).total_seconds()
            )

        except Exception:
            pass

    if deltas:

        print(
            f"MIN DELTA SEC         : {min(deltas)}"
        )

        print(
            f"MAX DELTA SEC         : {max(deltas)}"
        )

        print(
            f"AVG DELTA SEC         : "
            f"{sum(deltas) / len(deltas)}"
        )

        unusual = [
            d
            for d in deltas
            if d <= 0
            or d > 3600
        ]

        print(
            f"UNUSUAL DELTAS        : "
            f"{len(unusual)}"
        )

        if unusual:
            print(
                "STATUS                : "
                "TIMESTAMP_ANOMALIES_DETECTED"
            )
        else:
            print(
                "STATUS                : "
                "TIMESTAMP_SEQUENCE_VALID"
            )


# ============================================================
# ENGINE TRANSITIONS
# ============================================================

def inspect_engine_transitions(rows):

    subsection(
        "ENGINE VERSION TRANSITIONS"
    )

    if not rows:
        return

    previous_engine = rows[0][33]

    transition_count = 0

    print(
        f"START ENGINE          : "
        f"{previous_engine}"
    )

    for index in range(1, len(rows)):

        current_engine = rows[index][33]

        if current_engine != previous_engine:

            transition_count += 1

            print(
                f"TRANSITION #{transition_count}"
            )

            print(
                f"  POSITION            : "
                f"{index}"
            )

            print(
                f"  ID                  : "
                f"{rows[index][0]}"
            )

            print(
                f"  TIMESTAMP           : "
                f"{rows[index][1]}"
            )

            print(
                f"  FROM                : "
                f"{previous_engine}"
            )

            print(
                f"  TO                  : "
                f"{current_engine}"
            )

            previous_engine = current_engine

    print(
        f"TOTAL TRANSITIONS     : "
        f"{transition_count}"
    )

    if transition_count:
        print(
            "STATUS                : "
            "MIXED_ENGINE_WINDOW"
        )
    else:
        print(
            "STATUS                : "
            "SINGLE_ENGINE_WINDOW"
        )


# ============================================================
# CLOSE SERIES
# ============================================================

def extract_close_series(rows):

    closes = []

    invalid = []

    for index, row in enumerate(rows):

        value = to_float(
            row[7]
        )

        if value is None or value <= 0:

            invalid.append(
                (
                    index,
                    row[0],
                    value,
                )
            )

        else:
            closes.append(value)

    return closes, invalid


def print_close_validation(rows):

    subsection(
        "PRODUCTION CLOSE SERIES VALIDATION"
    )

    closes, invalid = extract_close_series(
        rows
    )

    print(
        f"ROWS                  : {len(rows)}"
    )

    print(
        f"VALID CLOSES          : {len(closes)}"
    )

    print(
        f"INVALID CLOSES        : {len(invalid)}"
    )

    if invalid:

        for item in invalid[:20]:
            print(
                f"INVALID INDEX={item[0]} "
                f"| ID={item[1]} "
                f"| CLOSE={item[2]}"
            )

        print(
            "STATUS                : INVALID_CLOSES"
        )

    else:

        print(
            "STATUS                : ALL_CLOSES_VALID"
        )

    return closes


# ============================================================
# INDEPENDENT RECONSTRUCTION
# ============================================================

def reconstruct_indicators(closes):

    return {
        "ema20": independent_ema(
            closes,
            EMA20_PERIOD,
        ),
        "ema50": independent_ema(
            closes,
            EMA50_PERIOD,
        ),
        "rsi14": independent_rsi(
            closes,
            RSI14_PERIOD,
        ),
    }


def print_reconstruction(
    rows,
    closes,
    reconstruction,
):

    subsection(
        "INDEPENDENT STANDARD RECONSTRUCTION"
    )

    print(
        f"VALID CLOSES          : "
        f"{len(closes)}"
    )

    print(
        f"STANDARD EMA20        : "
        f"{fmt(reconstruction['ema20'])}"
    )

    print(
        f"STANDARD EMA50        : "
        f"{fmt(reconstruction['ema50'])}"
    )

    print(
        f"STANDARD RSI14        : "
        f"{fmt(reconstruction['rsi14'])}"
    )


# ============================================================
# PRODUCTION TARGET INDICATORS
# ============================================================

def get_target_record(
    conn,
    symbol,
):

    return conn.execute(
        """
        SELECT
            id,
            timestamp,
            source_timestamp,
            close,
            ema20,
            ema50,
            rsi14,
            source,
            timeframe,
            engine_version
        FROM market_data
        WHERE
            symbol = ?
            AND engine_version = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            symbol,
            EXPECTED_ENGINE_VERSION,
        ),
    ).fetchone()


# ============================================================
# INDICATOR COMPARISON
# ============================================================

def compare_indicator(
    name,
    current,
    standard,
):

    abs_error = None
    rel_error = None

    if current is not None and standard is not None:

        abs_error = abs(
            current - standard
        )

        rel_error = relative_error(
            current,
            standard,
        )

    match = almost_equal(
        current,
        standard,
    )

    print()
    print(
        f"INDICATOR : {name}"
    )

    print(
        f"CURRENT   : {fmt(current)}"
    )

    print(
        f"STANDARD  : {fmt(standard)}"
    )

    print(
        f"ABS ERR   : {fmt(abs_error)}"
    )

    print(
        f"REL ERR   : {fmt(rel_error)}"
    )

    print(
        f"STATUS    : "
        f"{'MATCH' if match else 'MISMATCH'}"
    )

    return match


# ============================================================
# EXACT PRODUCTION ROW TRACE
# ============================================================

def print_row_trace(rows):

    subsection(
        "ACTUAL PRODUCTION ROW TRACE"
    )

    print(
        "INDEX | ID | TIMESTAMP | CLOSE | SOURCE | ENGINE"
    )

    for index, row in enumerate(rows):

        print(
            f"{index:03d} | "
            f"{row[0]} | "
            f"{row[1]} | "
            f"{row[7]} | "
            f"{row[25]} | "
            f"{row[33]}"
        )


# ============================================================
# SYMBOL FORENSIC
# ============================================================

def verify_symbol(
    conn,
    symbol,
):

    section(
        f"SYMBOL : {symbol}"
    )

    target = get_target_record(
        conn,
        symbol,
    )

    if target is None:

        print(
            "[UNRESOLVED] Production target "
            "not found"
        )

        return "UNRESOLVED"

    print()
    print(
        "PRODUCTION TARGET RECORD"
    )
    line("-")

    print(
        f"ID                    : {target[0]}"
    )

    print(
        f"TIMESTAMP             : {target[1]}"
    )

    print(
        f"SOURCE_TIMESTAMP      : {target[2]}"
    )

    print(
        f"CLOSE                 : {target[3]}"
    )

    print(
        f"EMA20                 : {target[4]}"
    )

    print(
        f"EMA50                 : {target[5]}"
    )

    print(
        f"RSI14                 : {target[6]}"
    )

    print(
        f"SOURCE                : {target[7]}"
    )

    print(
        f"TIMEFRAME             : {target[8]}"
    )

    print(
        f"ENGINE_VERSION        : {target[9]}"
    )

    # --------------------------------------------------------
    # Actual production window
    # --------------------------------------------------------

    rows = get_actual_production_rows(
        conn,
        symbol,
    )

    print_window_identity(
        rows
    )

    print_engine_distribution(
        rows
    )

    print_source_distribution(
        rows
    )

    print_timeframe_distribution(
        rows
    )

    inspect_id_continuity(
        rows
    )

    inspect_timestamps(
        rows
    )

    inspect_engine_transitions(
        rows
    )

    closes = print_close_validation(
        rows
    )

    # --------------------------------------------------------
    # Ensure the actual production target is inside window
    # --------------------------------------------------------

    subsection(
        "TARGET ROW MEMBERSHIP"
    )

    target_id = target[0]

    ids = [
        row[0]
        for row in rows
    ]

    if target_id in ids:

        target_position = ids.index(
            target_id
        )

        print(
            f"TARGET ID             : "
            f"{target_id}"
        )

        print(
            f"TARGET POSITION       : "
            f"{target_position}"
        )

        print(
            "TARGET IN PRODUCTION "
            "WINDOW               : YES"
        )

    else:

        target_position = None

        print(
            f"TARGET ID             : "
            f"{target_id}"
        )

        print(
            "TARGET IN PRODUCTION "
            "WINDOW               : NO"
        )

    # --------------------------------------------------------
    # Independent reconstruction
    # --------------------------------------------------------

    subsection(
        "INDEPENDENT RECONSTRUCTION"
    )

    reconstruction = reconstruct_indicators(
        closes
    )

    print_reconstruction(
        rows,
        closes,
        reconstruction,
    )

    # --------------------------------------------------------
    # Compare actual stored production indicators
    # --------------------------------------------------------

    subsection(
        "PRODUCTION INDICATOR VS SAME-WINDOW RECONSTRUCTION"
    )

    matches = 0
    mismatches = 0

    if compare_indicator(
        "EMA20",
        target[4],
        reconstruction["ema20"],
    ):
        matches += 1
    else:
        mismatches += 1

    if compare_indicator(
        "EMA50",
        target[5],
        reconstruction["ema50"],
    ):
        matches += 1
    else:
        mismatches += 1

    if compare_indicator(
        "RSI14",
        target[6],
        reconstruction["rsi14"],
    ):
        matches += 1
    else:
        mismatches += 1

    # --------------------------------------------------------
    # Window composition verdict
    # --------------------------------------------------------

    subsection(
        "WINDOW COMPOSITION VERDICT"
    )

    engine_counter = Counter(
        row[33]
        for row in rows
    )

    source_counter = Counter(
        row[25]
        for row in rows
    )

    timeframe_counter = Counter(
        row[3]
        for row in rows
    )

    mixed_engine = (
        len(engine_counter) > 1
    )

    mixed_source = (
        len(source_counter) > 1
    )

    mixed_timeframe = (
        len(timeframe_counter) > 1
    )

    print(
        f"MIXED ENGINE          : "
        f"{mixed_engine}"
    )

    print(
        f"MIXED SOURCE          : "
        f"{mixed_source}"
    )

    print(
        f"MIXED TIMEFRAME       : "
        f"{mixed_timeframe}"
    )

    # --------------------------------------------------------
    # Final symbol verdict
    # --------------------------------------------------------

    subsection(
        "SYMBOL FORENSIC VERDICT"
    )

    if (
        len(closes) == LOOKBACK
        and matches == 3
    ):

        status = "RECONSTRUCTION_MATCH"

        reason = (
            "PRODUCTION INDICATORS MATCH "
            "INDEPENDENT RECONSTRUCTION OF "
            "THE ACTUAL PRODUCTION WINDOW"
        )

    elif (
        len(closes) == LOOKBACK
        and mismatches > 0
    ):

        status = "INDICATOR_MISMATCH"

        reason = (
            "PRODUCTION INDICATORS DIFFER "
            "FROM INDEPENDENT RECONSTRUCTION "
            "OF THE ACTUAL PRODUCTION WINDOW"
        )

    elif len(closes) < LOOKBACK:

        status = "WINDOW_INCOMPLETE"

        reason = (
            "ACTUAL PRODUCTION WINDOW CONTAINS "
            "FEWER THAN EXPECTED ROWS"
        )

    else:

        status = "DIFFERENCE_DETECTED"

        reason = (
            "PRODUCTION WINDOW COMPOSITION "
            "REQUIRES FURTHER FORENSICS"
        )

    print(
        f"STATUS                : {status}"
    )

    print(
        f"REASON                : {reason}"
    )

    # --------------------------------------------------------
    # Row trace only when useful
    # --------------------------------------------------------

    if status == "INDICATOR_MISMATCH":

        print_row_trace(
            rows
        )

    return status


# ============================================================
# MAIN
# ============================================================

def main():

    print_header(
        "ARUNDA INDICATOR POST REPAIR PRODUCTION SERIES "
        "WINDOW COMPOSITION AND RECONSTRUCTION "
        "FORENSIC AUDIT v0.1"
    )

    print(
        f"MODE                  : {MODE}"
    )

    print(
        f"DATABASE WRITE        : {DATABASE_WRITE}"
    )

    print(
        f"ENGINE WRITE          : {ENGINE_WRITE}"
    )

    print(
        f"FORMULA WRITE         : {FORMULA_WRITE}"
    )

    print(
        f"PRODUCTION RECALCULATION : "
        f"{PRODUCTION_RECALCULATION}"
    )

    print(
        "PURPOSE               : "
        "VERIFY ACTUAL PRODUCTION "
        "SERIES WINDOW COMPOSITION "
        "AND RECONSTRUCT INDICATORS "
        "FROM THAT EXACT WINDOW"
    )

    # ========================================================
    # STEP 1
    # ========================================================

    section(
        "STEP 1 — ENGINE SOURCE RESOLUTION"
    )

    print(
        f"ENGINE PATH           : "
        f"{ENGINE_PATH}"
    )

    print(
        f"ENGINE FOUND          : "
        f"{os.path.exists(ENGINE_PATH)}"
    )

    source = load_engine_source()

    if source is None:

        print(
            "SOURCE STATUS         : UNRESOLVED"
        )

    else:

        print(
            f"SOURCE SIZE           : "
            f"{len(source)} characters"
        )

        print(
            f"SOURCE LINES          : "
            f"{len(source.splitlines())}"
        )

        tree = parse_engine(
            source
        )

        print(
            f"AST STATUS            : "
            f"{'SUCCESS' if tree else 'FAILED'}"
        )

        inventory = function_inventory(
            tree
        )

        for name in [
            "get_snapshot_history",
            "calculate_analysis",
            "ema",
            "ema_series",
            "rsi",
            "macd",
        ]:

            if name in inventory:

                start, end = inventory[name]

                print(
                    f"[FOUND] {name}() "
                    f"LINE {start}-{end}"
                )

    # ========================================================
    # STEP 2
    # ========================================================

    section(
        "STEP 2 — DATABASE RESOLUTION"
    )

    print(
        f"DATABASE PATH         : "
        f"{DB_PATH}"
    )

    print(
        f"DATABASE FOUND        : "
        f"{os.path.exists(DB_PATH)}"
    )

    if not os.path.exists(
        DB_PATH
    ):

        print(
            "FATAL: database not found"
        )

        return 1

    # IMPORTANT:
    # SQLite read-only connection.
    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        print(
            f"TABLE COUNT            : "
            f"{len(tables)}"
        )

        market_columns = get_columns(
            conn,
            "market_data",
        )

        print()
        print(
            "MARKET_DATA COLUMN COUNT"
        )
        line("-")

        print(
            len(market_columns)
        )

        # ====================================================
        # STEP 3
        # ====================================================

        section(
            "STEP 3 — ACTUAL PRODUCTION WINDOW FORENSICS"
        )

        results = {}

        for symbol in TARGET_SYMBOLS:

            results[symbol] = verify_symbol(
                conn,
                symbol,
            )

        # ====================================================
        # FINAL SUMMARY
        # ====================================================

        section(
            "FINAL PRODUCTION SERIES WINDOW "
            "COMPOSITION AND RECONSTRUCTION SUMMARY"
        )

        counts = Counter(
            results.values()
        )

        for status in [
            "RECONSTRUCTION_MATCH",
            "INDICATOR_MISMATCH",
            "WINDOW_INCOMPLETE",
            "DIFFERENCE_DETECTED",
            "UNRESOLVED",
        ]:

            print(
                f"{status:<24}: "
                f"{counts.get(status, 0)}"
            )

        print()
        print(
            "TARGET MATRIX"
        )
        line("-")

        for symbol in TARGET_SYMBOLS:

            print(
                f"  [{results[symbol]:>24}] : "
                f"{symbol}"
            )

        # ====================================================
        # GLOBAL VERDICT
        # ====================================================

        if all(
            results[symbol]
            == "RECONSTRUCTION_MATCH"
            for symbol in TARGET_SYMBOLS
        ):

            final_status = (
                "PRODUCTION_WINDOW_RECONSTRUCTION_VERIFIED"
            )

            final_reason = (
                "ALL PRODUCTION INDICATORS MATCH "
                "INDEPENDENT RECONSTRUCTION USING "
                "THE EXACT ACTUAL PRODUCTION ROW WINDOW"
            )

            next_frontier = (
                "COMPARE THE ACTUAL PRODUCTION WINDOW "
                "WITH THE ORIGINAL POST-REPAIR INDICATOR "
                "CONVENTION ONLY IF REQUIRED"
            )

        elif any(
            results[symbol]
            == "INDICATOR_MISMATCH"
            for symbol in TARGET_SYMBOLS
        ):

            final_status = (
                "ACTUAL_PRODUCTION_INDICATOR_MISMATCH"
            )

            final_reason = (
                "ONE OR MORE PRODUCTION INDICATORS "
                "DO NOT MATCH INDEPENDENT RECONSTRUCTION "
                "OF THEIR OWN ACTUAL INPUT WINDOW"
            )

            next_frontier = (
                "FORENSIC calculate_analysis() INDICATOR "
                "IMPLEMENTATION AND CLOSES TRANSFORMATION"
            )

        elif any(
            results[symbol]
            == "WINDOW_INCOMPLETE"
            for symbol in TARGET_SYMBOLS
        ):

            final_status = (
                "PRODUCTION_WINDOW_INCOMPLETE"
            )

            final_reason = (
                "ONE OR MORE SYMBOLS HAVE FEWER "
                "THAN 120 VALID PRODUCTION CLOSES"
            )

            next_frontier = (
                "FORENSIC PRODUCTION WINDOW ACQUISITION "
                "AND LOOKBACK AVAILABILITY"
            )

        else:

            final_status = (
                "PRODUCTION_WINDOW_FORENSICS_INCOMPLETE"
            )

            final_reason = (
                "PRODUCTION SERIES COMPOSITION OR "
                "RECONSTRUCTION REQUIRES FURTHER FORENSICS"
            )

            next_frontier = (
                "INSPECT THE SPECIFIC UNRESOLVED "
                "PRODUCTION WINDOW COMPONENT"
            )

        section(
            "FORENSIC CONCLUSION"
        )

        print(
            f"STATUS                  : "
            f"{final_status}"
        )

        print(
            f"REASON                  : "
            f"{final_reason}"
        )

        print(
            f"NEXT FRONTIER           : "
            f"{next_frontier}"
        )

        print()
        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )

        print(
            "ENGINE MODIFICATIONS      : NONE"
        )

        print(
            "FORMULA WRITE             : NONE"
        )

        print(
            "PRODUCTION RECALCULATION  : NONE"
        )

        print(
            "AUDIT COMPLETE"
        )

    finally:

        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )