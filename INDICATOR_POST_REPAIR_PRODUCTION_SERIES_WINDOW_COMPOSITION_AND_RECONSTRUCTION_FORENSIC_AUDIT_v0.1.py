import ast
import math
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone


# =====================================================================
# CONFIGURATION
# =====================================================================

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

ENGINE_PATH = os.path.join(
    BASE_DIR,
    "market_data_engine.py"
)

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "arunda.db"
)

TARGET_SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

LOOKBACK = 120

PRODUCTION_SOURCE = "COINMARKETCAP"
PRODUCTION_TIMEFRAME = "SNAPSHOT"

EMA20_PERIOD = 20
EMA50_PERIOD = 50
RSI14_PERIOD = 14

EPSILON = 1e-9


# =====================================================================
# PRINTING
# =====================================================================

def print_header(title):
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_subsection(title):
    print()
    print(title)
    print("-" * 100)


# =====================================================================
# FILE / ENGINE RESOLUTION
# =====================================================================

def read_engine_source():
    if not os.path.isfile(ENGINE_PATH):
        return None

    try:
        with open(
            ENGINE_PATH,
            "r",
            encoding="utf-8"
        ) as f:
            return f.read()
    except Exception:
        return None


def resolve_function_ranges(source):
    tree = ast.parse(source)

    functions = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            end_line = getattr(
                node,
                "end_lineno",
                node.lineno
            )

            functions[node.name] = (
                node.lineno,
                end_line,
            )

    return functions


def print_engine_resolution():
    print_subsection(
        "STEP 1 — ENGINE SOURCE RESOLUTION"
    )

    print(
        f"ENGINE PATH           : {ENGINE_PATH}"
    )

    exists = os.path.isfile(
        ENGINE_PATH
    )

    print(
        f"ENGINE FOUND          : {exists}"
    )

    if not exists:
        return None, {}

    source = read_engine_source()

    if source is None:
        print(
            "SOURCE READ          : FAILED"
        )
        return None, {}

    print(
        f"SOURCE SIZE           : {len(source)} characters"
    )

    print(
        f"SOURCE LINES          : {len(source.splitlines())}"
    )

    try:
        ast.parse(source)

        print(
            "AST STATUS            : SUCCESS"
        )

    except SyntaxError as exc:

        print(
            "AST STATUS            : FAILED"
        )

        print(
            f"SYNTAX ERROR          : {exc}"
        )

        return source, {}

    functions = resolve_function_ranges(
        source
    )

    required_functions = [
        "get_snapshot_history",
        "calculate_analysis",
        "ema",
        "ema_series",
        "rsi",
        "macd",
    ]

    for name in required_functions:

        if name in functions:

            start, end = functions[name]

            print(
                f"[FOUND] {name}() "
                f"LINE {start}-{end}"
            )

        else:

            print(
                f"[MISS ] {name}()"
            )

    return source, functions


# =====================================================================
# DATABASE
# =====================================================================

def connect_database():
    if not os.path.isfile(
        DATABASE_PATH
    ):
        raise FileNotFoundError(
            DATABASE_PATH
        )

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


def get_table_names(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def get_columns(conn, table_name):
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def print_database_resolution(conn):
    print_subsection(
        "STEP 2 — DATABASE RESOLUTION"
    )

    print(
        f"DATABASE PATH         : {DATABASE_PATH}"
    )

    print(
        f"DATABASE FOUND        : "
        f"{os.path.isfile(DATABASE_PATH)}"
    )

    tables = get_table_names(conn)

    print(
        f"TABLE COUNT           : {len(tables)}"
    )

    market_data_columns = get_columns(
        conn,
        "market_data"
    )

    print()
    print(
        "MARKET_DATA COLUMN COUNT"
    )

    print(
        "-" * 100
    )

    print(
        len(market_data_columns)
    )

    print()
    print(
        "MARKET_DATA COLUMNS"
    )

    print(
        "-" * 100
    )

    for index, column in enumerate(
        market_data_columns
    ):

        print(
            f"{index:02d} : {column}"
        )


# =====================================================================
# SCHEMA
# =====================================================================

def validate_market_data_schema(conn):

    required = [
        "id",
        "timestamp",
        "symbol",
        "timeframe",
        "close",
        "source",
        "source_timestamp",
        "engine_version",
    ]

    columns = set(
        get_columns(
            conn,
            "market_data"
        )
    )

    missing = [
        column
        for column in required
        if column not in columns
    ]

    if missing:
        raise RuntimeError(
            "Missing market_data columns: "
            + ", ".join(missing)
        )


# =====================================================================
# PRODUCTION WINDOW
# =====================================================================

def get_production_target(
    conn,
    symbol
):

    row = conn.execute(
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
            AND timeframe = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            symbol,
            PRODUCTION_SOURCE,
            PRODUCTION_TIMEFRAME,
        )
    ).fetchone()

    return row


def get_production_window(
    conn,
    symbol,
    target_id
):

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
            AND timeframe = ?
            AND id <= ?
            AND close IS NOT NULL
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            symbol,
            PRODUCTION_SOURCE,
            PRODUCTION_TIMEFRAME,
            target_id,
            LOOKBACK,
        )
    ).fetchall()

    rows = list(
        reversed(rows)
    )

    return rows


# =====================================================================
# WINDOW IDENTITY
# =====================================================================

def print_window_identity(rows):

    print_subsection(
        "PRODUCTION WINDOW IDENTITY"
    )

    if not rows:

        print(
            "ROW COUNT             : 0"
        )

        print(
            "STATUS                : NO_ROWS"
        )

        return

    first = rows[0]
    last = rows[-1]

    print(
        f"ROW COUNT             : {len(rows)}"
    )

    print(
        f"FIRST ID              : {first['id']}"
    )

    print(
        f"LAST ID               : {last['id']}"
    )

    print(
        f"FIRST TIMESTAMP       : {first['timestamp']}"
    )

    print(
        f"LAST TIMESTAMP        : {last['timestamp']}"
    )

    print(
        f"FIRST SOURCE TIME     : "
        f"{first['source_timestamp']}"
    )

    print(
        f"LAST SOURCE TIME      : "
        f"{last['source_timestamp']}"
    )

    print(
        f"FIRST CLOSE           : "
        f"{first['close']}"
    )

    print(
        f"LAST CLOSE            : "
        f"{last['close']}"
    )


# =====================================================================
# ENGINE DISTRIBUTION
# =====================================================================

def print_engine_distribution(rows):

    print_subsection(
        "ENGINE VERSION DISTRIBUTION"
    )

    if not rows:

        print(
            "ROWS                  : 0"
        )

        return

    counter = Counter(
        (
            row["engine_version"]
            if row["engine_version"] is not None
            else "<NULL>"
        )
        for row in rows
    )

    for engine, count in counter.most_common():

        print(
            f"ENGINE={engine} | ROWS={count}"
        )

    print()

    print(
        f"UNIQUE ENGINE VERSIONS : {len(counter)}"
    )

    if len(counter) == 1:

        only_engine = next(
            iter(counter)
        )

        print(
            f"WINDOW ENGINE IDENTITY : "
            f"{only_engine}"
        )

    else:

        print(
            "WINDOW ENGINE IDENTITY : MIXED"
        )


# =====================================================================
# SOURCE DISTRIBUTION
# =====================================================================

def print_source_distribution(rows):

    print_subsection(
        "PRODUCTION SOURCE DISTRIBUTION"
    )

    if not rows:

        print(
            "ROWS                  : 0"
        )

        return

    counter = Counter(
        (
            row["source"]
            if row["source"] is not None
            else "<NULL>"
        )
        for row in rows
    )

    for source, count in counter.most_common():

        print(
            f"SOURCE={source} | ROWS={count}"
        )


# =====================================================================
# TIMESTAMP ANALYSIS
# =====================================================================

def parse_timestamp(value):

    if value is None:
        return None

    text = str(value).strip()

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:

        dt = datetime.fromisoformat(
            text
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt

    except Exception:

        return None


def analyze_timestamp_spacing(rows):

    print_subsection(
        "TIMESTAMP SPACING"
    )

    if len(rows) < 2:

        print(
            "STATUS                : INSUFFICIENT_ROWS"
        )

        return

    intervals = []

    for previous, current in zip(
        rows,
        rows[1:]
    ):

        t1 = parse_timestamp(
            previous["timestamp"]
        )

        t2 = parse_timestamp(
            current["timestamp"]
        )

        if t1 is None or t2 is None:
            continue

        delta = (
            t2 - t1
        ).total_seconds()

        intervals.append(
            delta
        )

    if not intervals:

        print(
            "STATUS                : NO_VALID_TIMESTAMPS"
        )

        return

    counter = Counter(
        round(x, 6)
        for x in intervals
    )

    print(
        f"INTERVAL COUNT        : {len(intervals)}"
    )

    print(
        f"MIN INTERVAL SEC      : {min(intervals)}"
    )

    print(
        f"MAX INTERVAL SEC      : {max(intervals)}"
    )

    print(
        f"AVG INTERVAL SEC      : "
        f"{sum(intervals) / len(intervals)}"
    )

    print()

    print(
        "MOST COMMON INTERVALS"
    )

    for interval, count in (
        counter.most_common(10)
    ):

        print(
            f"{interval:>12} sec | COUNT={count}"
        )


# =====================================================================
# SOURCE TIMESTAMP SPACING
# =====================================================================

def analyze_source_timestamp_spacing(
    rows
):

    print_subsection(
        "SOURCE TIMESTAMP SPACING"
    )

    if len(rows) < 2:

        print(
            "STATUS                : INSUFFICIENT_ROWS"
        )

        return

    intervals = []

    for previous, current in zip(
        rows,
        rows[1:]
    ):

        t1 = parse_timestamp(
            previous["source_timestamp"]
        )

        t2 = parse_timestamp(
            current["source_timestamp"]
        )

        if t1 is None or t2 is None:
            continue

        intervals.append(
            (
                t2 - t1
            ).total_seconds()
        )

    if not intervals:

        print(
            "STATUS                : NO_VALID_SOURCE_TIMESTAMPS"
        )

        return

    print(
        f"INTERVAL COUNT        : {len(intervals)}"
    )

    print(
        f"MIN INTERVAL SEC      : {min(intervals)}"
    )

    print(
        f"MAX INTERVAL SEC      : {max(intervals)}"
    )

    print(
        f"AVG INTERVAL SEC      : "
        f"{sum(intervals) / len(intervals)}"
    )


# =====================================================================
# CLOSE SERIES
# =====================================================================

def extract_closes(rows):

    closes = []

    for row in rows:

        value = row["close"]

        if value is None:
            continue

        try:

            value = float(value)

        except (
            TypeError,
            ValueError,
        ):
            continue

        if not math.isfinite(value):
            continue

        if value <= 0:
            continue

        closes.append(
            value
        )

    return closes


# =====================================================================
# STANDARD EMA
# =====================================================================

def standard_ema(
    values,
    period
):

    values = [
        float(x)
        for x in values
        if x is not None
    ]

    if len(values) < period:
        return None

    seed = (
        sum(
            values[:period]
        )
        / period
    )

    multiplier = (
        2.0
        /
        (
            period + 1.0
        )
    )

    ema_value = seed

    for value in values[period:]:

        ema_value = (
            (
                value - ema_value
            )
            * multiplier
        ) + ema_value

    return ema_value


# =====================================================================
# STANDARD RSI
# =====================================================================

def standard_rsi(
    values,
    period=14
):

    values = [
        float(x)
        for x in values
        if x is not None
    ]

    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(
        1,
        len(values)
    ):

        delta = (
            values[i]
            -
            values[i - 1]
        )

        if delta > 0:

            gains.append(
                delta
            )

            losses.append(
                0.0
            )

        else:

            gains.append(
                0.0
            )

            losses.append(
                abs(delta)
            )

    avg_gain = (
        sum(
            gains[:period]
        )
        /
        period
    )

    avg_loss = (
        sum(
            losses[:period]
        )
        /
        period
    )

    for i in range(
        period,
        len(gains)
    ):

        avg_gain = (
            (
                avg_gain
                *
                (period - 1)
            )
            +
            gains[i]
        ) / period

        avg_loss = (
            (
                avg_loss
                *
                (period - 1)
            )
            +
            losses[i]
        ) / period

    if avg_loss == 0:

        if avg_gain == 0:
            return 50.0

        return 100.0

    rs = (
        avg_gain
        /
        avg_loss
    )

    return (
        100.0
        -
        (
            100.0
            /
            (1.0 + rs)
        )
    )


# =====================================================================
# ENGINE-FORMULA COMPATIBILITY CHECK
# =====================================================================

def compare_value(
    current,
    reconstructed,
    tolerance_abs=1e-8,
    tolerance_rel=1e-8
):

    if current is None:
        return False

    if reconstructed is None:
        return False

    try:

        current = float(current)
        reconstructed = float(
            reconstructed
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    if not (
        math.isfinite(current)
        and
        math.isfinite(reconstructed)
    ):
        return False

    absolute_error = abs(
        current - reconstructed
    )

    denominator = max(
        abs(reconstructed),
        EPSILON
    )

    relative_error = (
        absolute_error
        /
        denominator
    )

    return (
        absolute_error <= tolerance_abs
        or
        relative_error <= tolerance_rel
    )


def print_reconstruction(
    target,
    closes
):

    print_subsection(
        "EXACT PRODUCTION WINDOW RECONSTRUCTION"
    )

    print(
        f"VALID CLOSES          : {len(closes)}"
    )

    if not closes:

        print(
            "STATUS                : NO_VALID_CLOSES"
        )

        return {
            "status": "NO_VALID_CLOSES"
        }

    ema20 = standard_ema(
        closes,
        EMA20_PERIOD
    )

    ema50 = standard_ema(
        closes,
        EMA50_PERIOD
    )

    rsi14 = standard_rsi(
        closes,
        RSI14_PERIOD
    )

    print(
        f"STANDARD EMA20        : {ema20}"
    )

    print(
        f"STANDARD EMA50        : {ema50}"
    )

    print(
        f"STANDARD RSI14        : {rsi14}"
    )

    print()
    print(
        "PRODUCTION STORED VALUES"
    )

    print(
        f"CURRENT EMA20         : "
        f"{target['ema20']}"
    )

    print(
        f"CURRENT EMA50         : "
        f"{target['ema50']}"
    )

    print(
        f"CURRENT RSI14         : "
        f"{target['rsi14']}"
    )

    comparisons = []

    for name, current, reconstructed in [
        (
            "EMA20",
            target["ema20"],
            ema20,
        ),
        (
            "EMA50",
            target["ema50"],
            ema50,
        ),
        (
            "RSI14",
            target["rsi14"],
            rsi14,
        ),
    ]:

        if current is None:
            status = "UNRESOLVED"

            abs_error = None
            rel_error = None

        elif reconstructed is None:
            status = "UNRESOLVED"

            abs_error = None
            rel_error = None

        else:

            abs_error = abs(
                float(current)
                -
                float(reconstructed)
            )

            rel_error = (
                abs_error
                /
                max(
                    abs(
                        float(reconstructed)
                    ),
                    EPSILON
                )
            )

            status = (
                "MATCH"
                if compare_value(
                    current,
                    reconstructed
                )
                else "MISMATCH"
            )

        comparisons.append(
            status
        )

        print()
        print(
            f"INDICATOR : {name}"
        )

        print(
            f"CURRENT   : {current}"
        )

        print(
            f"STANDARD  : {reconstructed}"
        )

        print(
            f"ABS ERR   : {abs_error}"
        )

        print(
            f"REL ERR   : {rel_error}"
        )

        print(
            f"STATUS    : {status}"
        )

    matches = comparisons.count(
        "MATCH"
    )

    mismatches = comparisons.count(
        "MISMATCH"
    )

    unresolved = comparisons.count(
        "UNRESOLVED"
    )

    if unresolved:
        status = "UNRESOLVED"

    elif mismatches:
        status = "DIFFERENCE_DETECTED"

    else:
        status = "IDENTICAL"

    print_subsection(
        "WINDOW RECONSTRUCTION SUMMARY"
    )

    print(
        f"COMPARISONS            : "
        f"{len(comparisons)}"
    )

    print(
        f"MATCHES                : {matches}"
    )

    print(
        f"MISMATCHES             : "
        f"{mismatches}"
    )

    print(
        f"UNRESOLVED             : "
        f"{unresolved}"
    )

    print(
        f"WINDOW STATUS          : "
        f"{status}"
    )

    return {
        "status": status,
        "matches": matches,
        "mismatches": mismatches,
        "unresolved": unresolved,
        "ema20": ema20,
        "ema50": ema50,
        "rsi14": rsi14,
    }


# =====================================================================
# PRODUCTION WINDOW / HISTORY COMPARISON
# =====================================================================

def get_history_series(
    conn,
    symbol
):

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            cmc_id,
            symbol,
            name,
            price,
            source,
            source_timestamp,
            engine_version
        FROM market_history
        WHERE
            symbol = ?
            AND price IS NOT NULL
        ORDER BY timestamp ASC
        """,
        (
            symbol,
        )
    ).fetchall()

    return rows


def compare_with_history(
    production_rows,
    history_rows
):

    print_subsection(
        "MARKET_DATA ↔ MARKET_HISTORY SERIES COMPARISON"
    )

    production_closes = extract_closes(
        production_rows
    )

    history_closes = [
        float(row["price"])
        for row in history_rows
        if row["price"] is not None
        and float(row["price"]) > 0
        and math.isfinite(
            float(row["price"])
        )
    ]

    print(
        f"PRODUCTION ROWS       : "
        f"{len(production_closes)}"
    )

    print(
        f"HISTORY ROWS          : "
        f"{len(history_closes)}"
    )

    if production_closes:

        print(
            f"PRODUCTION FIRST      : "
            f"{production_closes[0]}"
        )

        print(
            f"PRODUCTION LAST       : "
            f"{production_closes[-1]}"
        )

    if history_closes:

        print(
            f"HISTORY FIRST         : "
            f"{history_closes[0]}"
        )

        print(
            f"HISTORY LAST          : "
            f"{history_closes[-1]}"
        )

    same_length = (
        len(production_closes)
        ==
        len(history_closes)
    )

    print(
        f"SAME LENGTH           : "
        f"{same_length}"
    )

    if production_closes and history_closes:

        print(
            f"SAME FIRST PRICE      : "
            f"{math.isclose(
                production_closes[0],
                history_closes[0],
                rel_tol=0,
                abs_tol=1e-12
            )}"
        )

        print(
            f"SAME LAST PRICE       : "
            f"{math.isclose(
                production_closes[-1],
                history_closes[-1],
                rel_tol=0,
                abs_tol=1e-12
            )}"
        )

    else:

        print(
            "SAME FIRST PRICE      : False"
        )

        print(
            "SAME LAST PRICE       : False"
        )

    production_timestamps = {
        str(row["timestamp"])
        for row in production_rows
        if row["timestamp"] is not None
    }

    history_timestamps = {
        str(row["timestamp"])
        for row in history_rows
        if row["timestamp"] is not None
    }

    timestamp_overlap = (
        production_timestamps
        &
        history_timestamps
    )

    print(
        f"TIMESTAMP OVERLAP     : "
        f"{len(timestamp_overlap)}"
    )

    price_overlap = (
        set(
            round(
                x,
                12
            )
            for x in production_closes
        )
        &
        set(
            round(
                x,
                12
            )
            for x in history_closes
        )
    )

    print(
        f"PRICE OVERLAP         : "
        f"{len(price_overlap)}"
    )

    exact_sequence = (
        production_closes
        ==
        history_closes
    )

    print(
        f"EXACT SEQUENCE MATCH  : "
        f"{exact_sequence}"
    )

    return {
        "production_count":
            len(production_closes),

        "history_count":
            len(history_closes),

        "timestamp_overlap":
            len(timestamp_overlap),

        "price_overlap":
            len(price_overlap),

        "exact_sequence":
            exact_sequence,
    }


# =====================================================================
# RECENT WINDOW DISPLAY
# =====================================================================

def print_recent_rows(
    rows,
    count=10
):

    print_subsection(
        f"LAST {count} PRODUCTION WINDOW ROWS"
    )

    for row in rows[-count:]:

        print(
            "ID={id} | "
            "TIME={timestamp} | "
            "SOURCE_TIME={source_timestamp} | "
            "CLOSE={close} | "
            "SOURCE={source} | "
            "ENGINE={engine}".format(
                id=row["id"],
                timestamp=row["timestamp"],
                source_timestamp=
                    row["source_timestamp"],
                close=row["close"],
                source=row["source"],
                engine=row["engine_version"],
            )
        )


# =====================================================================
# SINGLE SYMBOL
# =====================================================================

def verify_symbol(
    conn,
    symbol
):

    print_section(
        f"SYMBOL : {symbol}"
    )

    target = get_production_target(
        conn,
        symbol
    )

    if target is None:

        print(
            "PRODUCTION TARGET     : NOT FOUND"
        )

        return {
            "symbol": symbol,
            "status": "UNRESOLVED",
        }

    print_subsection(
        "PRODUCTION TARGET RECORD"
    )

    print(
        f"ID                    : "
        f"{target['id']}"
    )

    print(
        f"TIMESTAMP             : "
        f"{target['timestamp']}"
    )

    print(
        f"SOURCE_TIMESTAMP      : "
        f"{target['source_timestamp']}"
    )

    print(
        f"CLOSE                 : "
        f"{target['close']}"
    )

    print(
        f"EMA20                 : "
        f"{target['ema20']}"
    )

    print(
        f"EMA50                 : "
        f"{target['ema50']}"
    )

    print(
        f"RSI14                 : "
        f"{target['rsi14']}"
    )

    print(
        f"SOURCE                : "
        f"{target['source']}"
    )

    print(
        f"TIMEFRAME             : "
        f"{target['timeframe']}"
    )

    print(
        f"ENGINE_VERSION        : "
        f"{target['engine_version']}"
    )

    rows = get_production_window(
        conn,
        symbol,
        target["id"]
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

    analyze_timestamp_spacing(
        rows
    )

    analyze_source_timestamp_spacing(
        rows
    )

    print_recent_rows(
        rows
    )

    closes = extract_closes(
        rows
    )

    reconstruction = print_reconstruction(
        target,
        closes
    )

    history_rows = get_history_series(
        conn,
        symbol
    )

    history_comparison = compare_with_history(
        rows,
        history_rows
    )

    if (
        reconstruction["status"]
        ==
        "IDENTICAL"
    ):

        cause_status = (
            "PRODUCTION_WINDOW_RECONSTRUCTION_MATCH"
        )

    elif (
        reconstruction["status"]
        ==
        "DIFFERENCE_DETECTED"
    ):

        cause_status = (
            "PRODUCTION_WINDOW_RECONSTRUCTION_DIFFERENCE"
        )

    else:

        cause_status = (
            "PRODUCTION_WINDOW_RECONSTRUCTION_UNRESOLVED"
        )

    print_subsection(
        "SYMBOL FORENSIC VERDICT"
    )

    print(
        f"WINDOW RECONSTRUCTION : "
        f"{reconstruction['status']}"
    )

    print(
        f"HISTORY COMPARISON    : "
        f"{'DIFFERENT' if not history_comparison['exact_sequence'] else 'IDENTICAL'}"
    )

    print(
        f"CAUSE STATUS           : "
        f"{cause_status}"
    )

    return {
        "symbol": symbol,
        "status": cause_status,
        "reconstruction":
            reconstruction,
        "history":
            history_comparison,
    }


# =====================================================================
# FINAL SUMMARY
# =====================================================================

def print_final_summary(
    results
):

    print_section(
        "FINAL PRODUCTION SERIES WINDOW "
        "COMPOSITION AND RECONSTRUCTION FORENSIC SUMMARY"
    )

    total = len(results)

    reconstruction_matches = 0
    reconstruction_mismatches = 0
    unresolved = 0

    for result in results.values():

        reconstruction = result.get(
            "reconstruction",
            {}
        )

        status = reconstruction.get(
            "status"
        )

        if status == "IDENTICAL":

            reconstruction_matches += 1

        elif status == "DIFFERENCE_DETECTED":

            reconstruction_mismatches += 1

        else:

            unresolved += 1

    print(
        f"TARGETS CHECKED              : "
        f"{total}"
    )

    print(
        f"WINDOW RECONSTRUCTION MATCH  : "
        f"{reconstruction_matches}"
    )

    print(
        f"WINDOW RECONSTRUCTION MISMATCH: "
        f"{reconstruction_mismatches}"
    )

    print(
        f"UNRESOLVED                    : "
        f"{unresolved}"
    )

    print()

    print(
        "TARGET MATRIX"
    )

    print(
        "-" * 100
    )

    for symbol, result in results.items():

        reconstruction = result.get(
            "reconstruction",
            {}
        )

        status = reconstruction.get(
            "status",
            "UNRESOLVED"
        )

        print(
            f"  [{status:>24}] : {symbol}"
        )

    print_section(
        "FORENSIC CONCLUSION"
    )

    if unresolved:

        final_status = (
            "WINDOW_RECONSTRUCTION_INCOMPLETE"
        )

        reason = (
            "ONE OR MORE PRODUCTION WINDOWS "
            "COULD NOT BE RECONSTRUCTED"
        )

        next_frontier = (
            "INSPECT UNRESOLVED PRODUCTION WINDOW COMPONENTS"
        )

    elif reconstruction_mismatches:

        final_status = (
            "PRODUCTION_WINDOW_SERIES_DIFFERENCE_CONFIRMED"
        )

        reason = (
            "STORED PRODUCTION INDICATORS "
            "DO NOT RECONSTRUCT FROM THE ACTUAL "
            "PRODUCTION PRICE WINDOW"
        )

        next_frontier = (
            "TRACE EXACT INDICATOR CALCULATION INPUT "
            "ORDER / FILTER / WINDOW SEMANTICS"
        )

    else:

        final_status = (
            "PRODUCTION_WINDOW_RECONSTRUCTION_CONFIRMED"
        )

        reason = (
            "STORED PRODUCTION INDICATORS "
            "RECONSTRUCT FROM THE EXACT PRODUCTION "
            "PRICE WINDOW"
        )

        next_frontier = (
            "COMPARE CONFIRMED PRODUCTION WINDOW "
            "AGAINST REPAIRED HISTORY CONVENTION"
        )

    print(
        f"STATUS                  : "
        f"{final_status}"
    )

    print(
        f"REASON                  : "
        f"{reason}"
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


# =====================================================================
# MAIN
# =====================================================================

def main():

    print_header(
        "ARUNDA INDICATOR POST REPAIR "
        "PRODUCTION SERIES WINDOW COMPOSITION "
        "AND RECONSTRUCTION FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                  : READ ONLY"
    )

    print(
        "DATABASE WRITE        : NONE"
    )

    print(
        "ENGINE WRITE          : NONE"
    )

    print(
        "FORMULA WRITE         : NONE"
    )

    print(
        "PRODUCTION RECALCULATION : NONE"
    )

    print(
        "PURPOSE               : "
        "VERIFY ACTUAL PRODUCTION SERIES WINDOW "
        "COMPOSITION AND RECONSTRUCT INDICATORS "
        "FROM THAT EXACT WINDOW"
    )

    source, functions = (
        print_engine_resolution()
    )

    if source is None:
        return 1

    try:

        conn = connect_database()

    except Exception as exc:

        print()
        print(
            f"DATABASE CONNECTION FAILED : "
            f"{exc}"
        )

        return 1

    try:

        print_database_resolution(
            conn
        )

        validate_market_data_schema(
            conn
        )

        results = {}

        print_section(
            "STEP 3 — ACTUAL PRODUCTION WINDOW FORENSICS"
        )

        for symbol in TARGET_SYMBOLS:

            try:

                results[symbol] = (
                    verify_symbol(
                        conn,
                        symbol
                    )
                )

            except Exception as exc:

                print()
                print(
                    f"[ERROR] SYMBOL {symbol}"
                )

                print(
                    f"ERROR : {type(exc).__name__}: "
                    f"{exc}"
                )

                results[symbol] = {
                    "symbol": symbol,
                    "status": "UNRESOLVED",
                    "reconstruction": {
                        "status": "UNRESOLVED"
                    },
                }

        print_final_summary(
            results
        )

        return 0

    finally:

        conn.close()


if __name__ == "__main__":
    sys.exit(
        main()
    )