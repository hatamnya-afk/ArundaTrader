import ast
import re
import sqlite3
from pathlib import Path


# =============================================================================
# ARUNDA MARKET TECHNICAL VALIDATION RUNTIME FORENSIC v0.2
# =============================================================================
#
# MODE:
#   READ ONLY
#
# PURPOSE:
#   Forensic inspection of the REAL persisted market_technical state and
#   discovery of Python source paths related to technical validation.
#
# GUARANTEES:
#   - SQLite connection uses mode=ro
#   - PRAGMA query_only = 1
#   - No INSERT
#   - No UPDATE
#   - No DELETE
#   - No ALTER
#   - No CREATE
#   - No DROP
#   - No schema modification
#   - No synthetic data
#   - No interpolation
#   - No forward fill
#   - No back fill
#
# IMPORTANT:
#   This script DOES NOT repair market_technical.
#   This script DOES NOT modify production source.
#   This script is schema-tolerant: missing optional columns are reported,
#   not treated as fatal errors.
#
# =============================================================================


PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "arunda.db"

TARGET_TABLE = "market_technical"

STATUS_FIELD = "technical_validation_status"
SCORE_FIELD = "technical_validation_score"
AVAILABLE_FIELD = "technical_available"
VALIDATED_AT_FIELD = "technical_validated_at"

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

VALIDATION_KEYWORDS = [
    "technical_validation",
    "technical_validation_status",
    "technical_validation_score",
    "technical_validation_flags",
    "technical_validation_version",
    "technical_validated_at",
    "technical_completeness",
    "technical_available",
    "validation_status",
]

TECHNICAL_CORE_FIELDS = [
    "close",
    "return_5",
    "return_10",
    "return_20",
    "sma_3",
    "sma_5",
    "sma_10",
    "sma_20",
    "ema_5",
    "ema_10",
    "ema_20",
    "momentum_5",
    "momentum_10",
    "momentum_20",
    "volatility_5",
    "volatility_10",
    "volatility_20",
    "rsi_14",
    "volume_change_1",
    "volume_change_3",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "volume_score",
    "range_score",
    "breakout_score",
    "fibonacci_position",
    "ichimoku_cloud_distance",
    "sma20_distance",
    "ema20_distance",
    "ema20_slope",
    "price_vs_vwap",
]

WRITE_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|ALTER|CREATE|DROP|REPLACE)\b",
    re.IGNORECASE,
)


# =============================================================================
# UTILS
# =============================================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def safe(value):
    if value is None:
        return "NULL"
    return str(value)


def pct(numerator, denominator):
    if not denominator:
        return 0.0
    return (numerator / denominator) * 100.0


def print_kv(key, value):
    print(f"{key:<38}: {value}")


def quote_identifier(name):
    """
    Safe SQLite identifier quoting.
    """
    return '"' + str(name).replace('"', '""') + '"'


# =============================================================================
# READ-ONLY DATABASE
# =============================================================================

def connect_read_only():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    uri = (
        f"file:{DB_PATH.as_posix()}"
        f"?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True,
    )

    conn.row_factory = sqlite3.Row

    # Explicit SQLite read-only execution contract.
    conn.execute("PRAGMA query_only = ON")

    return conn


def assert_read_only_connection(conn):
    row = conn.execute(
        "PRAGMA query_only"
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "Unable to verify SQLite query_only state."
        )

    if int(row[0]) != 1:
        raise RuntimeError(
            "READ-ONLY DATABASE CONTRACT NOT SATISFIED."
        )


# =============================================================================
# SCHEMA
# =============================================================================

def table_exists(conn, table):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table,),
    ).fetchone()

    return row is not None


def get_columns(conn, table):
    rows = conn.execute(
        f"PRAGMA table_info({quote_identifier(table)})"
    ).fetchall()

    return [row["name"] for row in rows]


def print_schema(conn):
    banner("MARKET_TECHNICAL SCHEMA")

    rows = conn.execute(
        f"PRAGMA table_info({quote_identifier(TARGET_TABLE)})"
    ).fetchall()

    print_kv("Column Count", len(rows))

    for index, row in enumerate(rows, 1):
        print(
            f"{index:03d}. "
            f"{row['name']}"
            f" | type={row['type']}"
            f" | notnull={row['notnull']}"
            f" | pk={row['pk']}"
            f" | default={safe(row['dflt_value'])}"
        )


# =============================================================================
# GLOBAL COUNTS
# =============================================================================

def print_global_counts(conn, columns):
    banner("GLOBAL MARKET_TECHNICAL COUNTS")

    table = quote_identifier(TARGET_TABLE)

    total = conn.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print_kv("Total Rows", total)

    if "symbol" in columns:
        symbols = conn.execute(
            f"""
            SELECT COUNT(DISTINCT {quote_identifier("symbol")})
            FROM {table}
            """
        ).fetchone()[0]

        print_kv("Distinct Symbols", symbols)
    else:
        print_kv("Distinct Symbols", "symbol column NOT PRESENT")

    fields = [
        AVAILABLE_FIELD,
        "available",
        STATUS_FIELD,
        SCORE_FIELD,
        VALIDATED_AT_FIELD,
        "technical_completeness",
        "technical_version",
        "technical_validation_version",
    ]

    for field in fields:
        if field not in columns:
            print_kv(field, "NOT PRESENT")
            continue

        qfield = quote_identifier(field)

        nonnull = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {table}
            WHERE {qfield} IS NOT NULL
            """
        ).fetchone()[0]

        nulls = total - nonnull

        print(
            f"{field:<38}: "
            f"nonnull={nonnull:<10} "
            f"null={nulls:<10}"
        )


# =============================================================================
# STATUS
# =============================================================================

def print_status_distribution(conn, columns):
    banner("VALIDATION STATUS DISTRIBUTION")

    if STATUS_FIELD not in columns:
        print(
            f"{STATUS_FIELD} : NOT PRESENT"
        )
        return

    table = quote_identifier(TARGET_TABLE)
    field = quote_identifier(STATUS_FIELD)

    rows = conn.execute(
        f"""
        SELECT
            {field} AS status,
            COUNT(*) AS cnt
        FROM {table}
        GROUP BY {field}
        ORDER BY cnt DESC
        """
    ).fetchall()

    total = sum(row["cnt"] for row in rows)

    if not rows:
        print("No rows returned.")
        return

    for row in rows:
        print(
            f"  {safe(row['status']):<25}"
            f"{row['cnt']:<12}"
            f"({pct(row['cnt'], total):7.2f}%)"
        )


# =============================================================================
# SCORE
# =============================================================================

def print_score_distribution(conn, columns):
    banner("TECHNICAL VALIDATION SCORE DISTRIBUTION")

    if SCORE_FIELD not in columns:
        print(
            f"{SCORE_FIELD} : NOT PRESENT"
        )
        return

    table = quote_identifier(TARGET_TABLE)
    field = quote_identifier(SCORE_FIELD)

    rows = conn.execute(
        f"""
        SELECT
            {field} AS score,
            COUNT(*) AS cnt
        FROM {table}
        GROUP BY {field}
        ORDER BY cnt DESC
        LIMIT 50
        """
    ).fetchall()

    if not rows:
        print("No rows returned.")
        return

    for row in rows:
        print(
            f"  score={safe(row['score']):<15}"
            f"rows={row['cnt']}"
        )


# =============================================================================
# STATUS / SCORE
# =============================================================================

def print_status_score_cross(conn, columns):
    banner("STATUS / SCORE CROSS DISTRIBUTION")

    if STATUS_FIELD not in columns:
        print(f"{STATUS_FIELD} : NOT PRESENT")
        return

    if SCORE_FIELD not in columns:
        print(f"{SCORE_FIELD} : NOT PRESENT")
        return

    table = quote_identifier(TARGET_TABLE)

    rows = conn.execute(
        f"""
        SELECT
            {quote_identifier(STATUS_FIELD)} AS status,
            {quote_identifier(SCORE_FIELD)} AS score,
            COUNT(*) AS cnt
        FROM {table}
        GROUP BY
            {quote_identifier(STATUS_FIELD)},
            {quote_identifier(SCORE_FIELD)}
        ORDER BY cnt DESC
        """
    ).fetchall()

    for row in rows:
        print(
            f"  status={safe(row['status']):<25}"
            f"score={safe(row['score']):<15}"
            f"rows={row['cnt']}"
        )


# =============================================================================
# VERSION DISTRIBUTION
# =============================================================================

def print_version_distribution(conn, columns):
    banner("VALIDATION VERSION DISTRIBUTION")

    table = quote_identifier(TARGET_TABLE)

    for field in [
        "technical_validation_version",
        "technical_version",
        "engine_version",
    ]:
        print()
        print(f"[{field}]")

        if field not in columns:
            print("  NOT PRESENT")
            continue

        qfield = quote_identifier(field)

        rows = conn.execute(
            f"""
            SELECT
                {qfield} AS value,
                COUNT(*) AS cnt
            FROM {table}
            GROUP BY {qfield}
            ORDER BY cnt DESC
            """
        ).fetchall()

        if not rows:
            print("  NO ROWS")

        for row in rows:
            print(
                f"  {safe(row['value']):<35}"
                f"{row['cnt']}"
            )


# =============================================================================
# VALIDATED AT
# =============================================================================

def print_validation_timestamp_analysis(conn, columns):
    banner("VALIDATION TIMESTAMP FORENSIC")

    if VALIDATED_AT_FIELD not in columns:
        print(
            f"{VALIDATED_AT_FIELD} : NOT PRESENT"
        )
        return

    table = quote_identifier(TARGET_TABLE)
    field = quote_identifier(VALIDATED_AT_FIELD)

    total = conn.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    nonnull = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE {field} IS NOT NULL
        """
    ).fetchone()[0]

    print_kv("Total Rows", total)
    print_kv("Validated At Non-NULL", nonnull)
    print_kv("Validated At NULL", total - nonnull)

    row = conn.execute(
        f"""
        SELECT
            MIN({field}) AS min_ts,
            MAX({field}) AS max_ts
        FROM {table}
        WHERE {field} IS NOT NULL
        """
    ).fetchone()

    print_kv(
        f"MIN {VALIDATED_AT_FIELD}",
        safe(row["min_ts"]),
    )

    print_kv(
        f"MAX {VALIDATED_AT_FIELD}",
        safe(row["max_ts"]),
    )


# =============================================================================
# SOURCE TIMESTAMP
# =============================================================================

def print_source_timestamp_analysis(conn, columns):
    banner("SOURCE TIMESTAMP FORENSIC")

    if "timestamp" not in columns:
        print("timestamp : NOT PRESENT")
        return

    table = quote_identifier(TARGET_TABLE)
    field = quote_identifier("timestamp")

    row = conn.execute(
        f"""
        SELECT
            MIN({field}) AS min_ts,
            MAX({field}) AS max_ts,
            COUNT(*) AS cnt
        FROM {table}
        """
    ).fetchone()

    print_kv("Rows", row["cnt"])
    print_kv("MIN timestamp", safe(row["min_ts"]))
    print_kv("MAX timestamp", safe(row["max_ts"]))


# =============================================================================
# TIMESTAMP RELATIONSHIP
# =============================================================================

def print_timestamp_relationship(conn, columns):
    banner("SOURCE / VALIDATION TIMESTAMP RELATIONSHIP")

    if "timestamp" not in columns:
        print("timestamp : NOT PRESENT")
        return

    if VALIDATED_AT_FIELD not in columns:
        print(
            f"{VALIDATED_AT_FIELD} : NOT PRESENT"
        )
        return

    table = quote_identifier(TARGET_TABLE)

    row = conn.execute(
        f"""
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN {quote_identifier(VALIDATED_AT_FIELD)} IS NOT NULL
                     AND {quote_identifier("timestamp")} IS NOT NULL
                    THEN 1
                    ELSE 0
                END
            ) AS both_present
        FROM {table}
        """
    ).fetchone()

    print_kv("Rows", row["total"])
    print_kv(
        "Both timestamps present",
        safe(row["both_present"]),
    )

    if "symbol" not in columns:
        return

    status_select = (
        f"{quote_identifier(STATUS_FIELD)} AS status"
        if STATUS_FIELD in columns
        else "NULL AS status"
    )

    score_select = (
        f"{quote_identifier(SCORE_FIELD)} AS score"
        if SCORE_FIELD in columns
        else "NULL AS score"
    )

    sample = conn.execute(
        f"""
        SELECT
            {quote_identifier("symbol")} AS symbol,
            {quote_identifier("timestamp")} AS timestamp,
            {quote_identifier(VALIDATED_AT_FIELD)} AS validated_at,
            {status_select},
            {score_select}
        FROM {table}
        WHERE {quote_identifier(VALIDATED_AT_FIELD)} IS NOT NULL
        ORDER BY {quote_identifier(VALIDATED_AT_FIELD)} DESC
        LIMIT 20
        """
    ).fetchall()

    print()
    print(
        f"{'SYMBOL':<12}"
        f"{'SOURCE TIMESTAMP':<32}"
        f"{'VALIDATED AT':<32}"
        f"{'STATUS':<18}"
        f"{'SCORE':<12}"
    )

    print("-" * 106)

    for row in sample:
        print(
            f"{safe(row['symbol']):<12}"
            f"{safe(row['timestamp']):<32}"
            f"{safe(row['validated_at']):<32}"
            f"{safe(row['status']):<18}"
            f"{safe(row['score']):<12}"
        )


# =============================================================================
# EXPECTED ASSETS
# =============================================================================

def print_expected_asset_validation(conn, columns):
    banner("EXPECTED ASSET VALIDATION FORENSIC")

    if "symbol" not in columns:
        print("symbol : NOT PRESENT")
        return

    if STATUS_FIELD not in columns:
        print(
            f"{STATUS_FIELD} : NOT PRESENT"
        )
        return

    table = quote_identifier(TARGET_TABLE)
    symbol_field = quote_identifier("symbol")
    status_field = quote_identifier(STATUS_FIELD)

    placeholders = ",".join(
        "?" for _ in EXPECTED_ASSETS
    )

    rows = conn.execute(
        f"""
        SELECT
            {symbol_field} AS symbol,
            COUNT(*) AS rows,
            SUM(
                CASE
                    WHEN {status_field} = 'VALID'
                    THEN 1 ELSE 0
                END
            ) AS valid_rows,
            SUM(
                CASE
                    WHEN {status_field} = 'PARTIAL'
                    THEN 1 ELSE 0
                END
            ) AS partial_rows,
            SUM(
                CASE
                    WHEN {status_field} = 'UNAVAILABLE'
                    THEN 1 ELSE 0
                END
            ) AS unavailable_rows
        FROM {table}
        WHERE {symbol_field} IN ({placeholders})
        GROUP BY {symbol_field}
        ORDER BY {symbol_field}
        """,
        EXPECTED_ASSETS,
    ).fetchall()

    found = {
        row["symbol"]
        for row in rows
    }

    print(
        f"{'SYMBOL':<12}"
        f"{'ROWS':<10}"
        f"{'VALID':<10}"
        f"{'PARTIAL':<10}"
        f"{'UNAVAILABLE':<14}"
    )

    print("-" * 66)

    for row in rows:
        print(
            f"{safe(row['symbol']):<12}"
            f"{row['rows']:<10}"
            f"{row['valid_rows']:<10}"
            f"{row['partial_rows']:<10}"
            f"{row['unavailable_rows']:<14}"
        )

    missing = [
        symbol
        for symbol in EXPECTED_ASSETS
        if symbol not in found
    ]

    print()
    print_kv(
        "Expected Assets",
        len(EXPECTED_ASSETS),
    )
    print_kv(
        "Expected Present",
        len(found),
    )
    print_kv(
        "Expected Missing",
        len(missing),
    )
    print_kv(
        "Missing Symbols",
        missing if missing else "NONE",
    )


# =============================================================================
# UNAVAILABLE
# =============================================================================

def print_unavailable_score_forensic(conn, columns):
    banner("UNAVAILABLE SCORE FORENSIC")

    if STATUS_FIELD not in columns:
        print(
            f"{STATUS_FIELD} : NOT PRESENT"
        )
        return

    if SCORE_FIELD not in columns:
        print(
            f"{SCORE_FIELD} : NOT PRESENT"
        )
        return

    table = quote_identifier(TARGET_TABLE)

    rows = conn.execute(
        f"""
        SELECT
            {quote_identifier(SCORE_FIELD)} AS score,
            COUNT(*) AS cnt
        FROM {table}
        WHERE {quote_identifier(STATUS_FIELD)} = 'UNAVAILABLE'
        GROUP BY {quote_identifier(SCORE_FIELD)}
        ORDER BY cnt DESC
        """
    ).fetchall()

    total = sum(
        row["cnt"]
        for row in rows
    )

    print_kv("UNAVAILABLE Rows", total)

    for row in rows:
        print(
            f"  score={safe(row['score']):<15}"
            f"rows={row['cnt']:<10}"
            f"({pct(row['cnt'], total):.2f}%)"
        )


# =============================================================================
# PARTIAL
# =============================================================================

def print_partial_forensic(conn, columns):
    banner("PARTIAL VALIDATION FORENSIC")

    if STATUS_FIELD not in columns:
        print(
            f"{STATUS_FIELD} : NOT PRESENT"
        )
        return

    required = [
        "symbol",
        "timestamp",
        AVAILABLE_FIELD,
        "technical_completeness",
        SCORE_FIELD,
        STATUS_FIELD,
        "technical_validation_flags",
        "technical_validation_version",
        VALIDATED_AT_FIELD,
    ]

    available_fields = [
        field
        for field in required
        if field in columns
    ]

    if not available_fields:
        print("No compatible fields available.")
        return

    table = quote_identifier(TARGET_TABLE)

    select_parts = []

    for field in available_fields:
        select_parts.append(
            f"{quote_identifier(field)} AS {quote_identifier(field)}"
        )

    sql = f"""
        SELECT
            {", ".join(select_parts)}
        FROM {table}
        WHERE {quote_identifier(STATUS_FIELD)} = 'PARTIAL'
    """

    if "symbol" in columns:
        sql += f" ORDER BY {quote_identifier('symbol')}"

    if "timestamp" in columns:
        sql += f", {quote_identifier('timestamp')}"

    sql += " LIMIT 100"

    rows = conn.execute(sql).fetchall()

    print_kv("Rows displayed", len(rows))

    for index, row in enumerate(rows, 1):
        print()
        print(f"[PARTIAL ROW {index}]")

        for field in available_fields:
            print(
                f"  {field:<34}: "
                f"{safe(row[field])}"
            )


# =============================================================================
# VALID
# =============================================================================

def print_valid_forensic(conn, columns):
    banner("VALID TECHNICAL ROW FORENSIC")

    if STATUS_FIELD not in columns:
        print(
            f"{STATUS_FIELD} : NOT PRESENT"
        )
        return

    desired = [
        "symbol",
        "timestamp",
        "close",
        AVAILABLE_FIELD,
        "technical_completeness",
        "trend_score",
        "momentum_score",
        "volatility_score",
        "volume_score",
        "range_score",
        "breakout_score",
        SCORE_FIELD,
        STATUS_FIELD,
        "technical_validation_version",
    ]

    fields = [
        field
        for field in desired
        if field in columns
    ]

    if not fields:
        print("No compatible fields available.")
        return

    table = quote_identifier(TARGET_TABLE)

    select_parts = [
        f"{quote_identifier(field)} AS {quote_identifier(field)}"
        for field in fields
    ]

    sql = f"""
        SELECT
            {", ".join(select_parts)}
        FROM {table}
        WHERE {quote_identifier(STATUS_FIELD)} = 'VALID'
    """

    if "timestamp" in columns:
        sql += (
            f" ORDER BY {quote_identifier('timestamp')} DESC"
        )

    sql += " LIMIT 50"

    rows = conn.execute(sql).fetchall()

    print_kv("Rows displayed", len(rows))

    for index, row in enumerate(rows, 1):
        print()
        print(f"[VALID ROW {index}]")

        for field in fields:
            print(
                f"  {field:<34}: "
                f"{safe(row[field])}"
            )


# =============================================================================
# CORE FIELD INTEGRITY
# =============================================================================

def print_core_field_integrity(conn, columns):
    banner("TECHNICAL CORE FIELD INTEGRITY")

    table = quote_identifier(TARGET_TABLE)

    total = conn.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(
        f"{'FIELD':<34}"
        f"{'PRESENT':<12}"
        f"{'NONNULL':<12}"
        f"{'NULL':<12}"
        f"{'COMPLETE %':<12}"
    )

    print("-" * 82)

    for field in TECHNICAL_CORE_FIELDS:
        if field not in columns:
            print(
                f"{field:<34}"
                f"{'NO':<12}"
                f"{'N/A':<12}"
                f"{'N/A':<12}"
                f"{'N/A':<12}"
            )
            continue

        qfield = quote_identifier(field)

        nonnull = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {table}
            WHERE {qfield} IS NOT NULL
            """
        ).fetchone()[0]

        nulls = total - nonnull

        print(
            f"{field:<34}"
            f"{'YES':<12}"
            f"{nonnull:<12}"
            f"{nulls:<12}"
            f"{pct(nonnull, total):<12.2f}"
        )


# =============================================================================
# SOURCE / ENGINE
# =============================================================================

def print_source_engine_distribution(conn, columns):
    banner("SOURCE / ENGINE VERSION DISTRIBUTION")

    table = quote_identifier(TARGET_TABLE)

    for field in [
        "source",
        "engine_version",
    ]:
        print()
        print(f"[{field}]")

        if field not in columns:
            print("  NOT PRESENT")
            continue

        qfield = quote_identifier(field)

        rows = conn.execute(
            f"""
            SELECT
                {qfield} AS value,
                COUNT(*) AS cnt
            FROM {table}
            GROUP BY {qfield}
            ORDER BY cnt DESC
            """
        ).fetchall()

        if not rows:
            print("  NO ROWS")

        for row in rows:
            print(
                f"  {safe(row['value']):<40}"
                f"{row['cnt']}"
            )


# =============================================================================
# LATEST ROWS
# =============================================================================

def print_latest_rows(conn, columns):
    banner("LATEST MARKET_TECHNICAL ROWS")

    desired = [
        "symbol",
        "timestamp",
        "close",
        AVAILABLE_FIELD,
        "technical_completeness",
        "technical_version",
        SCORE_FIELD,
        STATUS_FIELD,
        "technical_validation_flags",
        "technical_validation_version",
        VALIDATED_AT_FIELD,
    ]

    fields = [
        field
        for field in desired
        if field in columns
    ]

    if not fields:
        print("No compatible fields available.")
        return

    table = quote_identifier(TARGET_TABLE)

    select_parts = [
        f"{quote_identifier(field)} AS {quote_identifier(field)}"
        for field in fields
    ]

    order_clause = ""

    if "timestamp" in columns:
        order_clause = (
            f" ORDER BY {quote_identifier('timestamp')} DESC"
        )

    sql = f"""
        SELECT
            {", ".join(select_parts)}
        FROM {table}
        {order_clause}
        LIMIT 30
    """

    rows = conn.execute(sql).fetchall()

    print_kv("Rows displayed", len(rows))

    for index, row in enumerate(rows, 1):
        print()
        print(f"[ROW {index}]")

        for field in fields:
            print(
                f"  {field:<38}: "
                f"{safe(row[field])}"
            )


# =============================================================================
# PRODUCER DISCOVERY
# =============================================================================

def discover_validation_scripts():
    banner("VALIDATION PRODUCER SCRIPT DISCOVERY")

    candidates = []

    current_script = Path(__file__).resolve()

    for path in sorted(PROJECT_DIR.glob("*.py")):
        try:
            resolved = path.resolve()
        except Exception:
            continue

        if resolved == current_script:
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        hits = sorted({
            keyword
            for keyword in VALIDATION_KEYWORDS
            if keyword.lower() in text.lower()
        })

        if hits:
            candidates.append(
                (
                    path,
                    hits,
                )
            )

    if not candidates:
        print(
            "No Python source file containing "
            "validation keywords found."
        )
        return []

    candidates.sort(
        key=lambda item: (
            -len(item[1]),
            item[0].name.lower(),
        )
    )

    for path, hits in candidates:
        print()
        print(f"FILE : {path.name}")
        print(
            f"HITS : {', '.join(hits)}"
        )

    print()
    print_kv(
        "Candidate Files",
        len(candidates),
    )

    return candidates


# =============================================================================
# SOURCE CODE FORENSIC
# =============================================================================

def source_code_forensic(candidates):
    banner("VALIDATION SOURCE CODE FORENSIC")

    for path, _hits in candidates[:30]:
        print()
        print("-" * 100)
        print(f"FILE : {path.name}")
        print("-" * 100)

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception as exc:
            print(
                f"READ ERROR : {exc}"
            )
            continue

        lines = text.splitlines()

        matched_lines = []

        for index, line in enumerate(lines, 1):
            lower = line.lower()

            if any(
                keyword.lower() in lower
                for keyword in VALIDATION_KEYWORDS
            ):
                matched_lines.append(index)

        if not matched_lines:
            continue

        shown = 0

        for line_number in matched_lines:
            start = max(
                1,
                line_number - 3,
            )

            end = min(
                len(lines),
                line_number + 3,
            )

            print()
            print(
                f"[LINES {start}-{end}]"
            )

            for number in range(
                start,
                end + 1,
            ):
                marker = (
                    ">>>"
                    if number == line_number
                    else "   "
                )

                print(
                    f"{marker} "
                    f"{number:5d}: "
                    f"{lines[number - 1]}"
                )

            shown += 1

            if shown >= 12:
                print()
                print(
                    "... additional matches omitted ..."
                )
                break


# =============================================================================
# AST DISCOVERY
# =============================================================================

def ast_function_discovery(candidates):
    banner("VALIDATION FUNCTION / CLASS DISCOVERY")

    for path, _hits in candidates[:30]:
        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            tree = ast.parse(
                text,
                filename=str(path),
            )

        except Exception as exc:
            print()
            print(
                f"AST ERROR : {path.name}"
            )
            print(
                f"  {type(exc).__name__}: {exc}"
            )
            continue

        functions = []
        classes = []

        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                name_lower = node.name.lower()

                if any(
                    token in name_lower
                    for token in [
                        "valid",
                        "technical",
                        "quality",
                        "complete",
                    ]
                ):
                    functions.append(
                        (
                            node.name,
                            node.lineno,
                        )
                    )

            elif isinstance(
                node,
                ast.ClassDef,
            ):
                name_lower = node.name.lower()

                if any(
                    token in name_lower
                    for token in [
                        "valid",
                        "technical",
                        "quality",
                    ]
                ):
                    classes.append(
                        (
                            node.name,
                            node.lineno,
                        )
                    )

        if not functions and not classes:
            continue

        print()
        print(
            f"FILE : {path.name}"
        )

        for name, line_number in sorted(
            classes,
            key=lambda item: item[1],
        ):
            print(
                f"  class   ={name:<50}"
                f"line={line_number}"
            )

        for name, line_number in sorted(
            functions,
            key=lambda item: item[1],
        ):
            print(
                f"  function={name:<50}"
                f"line={line_number}"
            )


# =============================================================================
# WRITE BOUNDARY
# =============================================================================

def source_write_boundary_check(candidates):
    banner(
        "VALIDATION PRODUCER WRITE-BOUNDARY FORENSIC"
    )

    for path, _hits in candidates[:30]:
        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        matches = list(
            WRITE_SQL_PATTERN.finditer(text)
        )

        if not matches:
            continue

        print()
        print(
            f"FILE : {path.name}"
        )

        lines = text.splitlines()

        reported = set()

        for match in matches:
            line_number = (
                text[:match.start()]
                .count("\n")
                + 1
            )

            if line_number in reported:
                continue

            reported.add(line_number)

            if (
                1 <= line_number <= len(lines)
            ):
                line = lines[
                    line_number - 1
                ].strip()
            else:
                line = ""

            print(
                f"  line={line_number:<7}"
                f"{line[:180]}"
            )

            if len(reported) >= 20:
                print(
                    "  ... additional write "
                    "references omitted ..."
                )
                break


# =============================================================================
# DATABASE OBJECTS
# =============================================================================

def print_db_objects(conn):
    banner("DATABASE OBJECT FORENSIC")

    rows = conn.execute(
        """
        SELECT
            type,
            name,
            sql
        FROM sqlite_master
        WHERE type IN ('trigger', 'view')
        ORDER BY type, name
        """
    ).fetchall()

    if not rows:
        print(
            "No triggers/views found."
        )
        return

    for row in rows:
        print()
        print(
            f"TYPE : {row['type']}"
        )
        print(
            f"NAME : {row['name']}"
        )
        print(
            f"SQL  : {safe(row['sql'])[:1500]}"
        )


# =============================================================================
# FINAL CONTRACT
# =============================================================================

def final_contract(conn, columns):
    banner(
        "FINAL RUNTIME FORENSIC CONTRACT"
    )

    table = quote_identifier(TARGET_TABLE)

    total = conn.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    statuses = {}

    if STATUS_FIELD in columns:
        rows = conn.execute(
            f"""
            SELECT
                {quote_identifier(STATUS_FIELD)} AS status,
                COUNT(*) AS cnt
            FROM {table}
            GROUP BY {quote_identifier(STATUS_FIELD)}
            ORDER BY cnt DESC
            """
        ).fetchall()

        statuses = {
            safe(row["status"]): row["cnt"]
            for row in rows
        }

    print_kv(
        "Rows Inspected",
        total,
    )

    print_kv(
        "Validation Statuses",
        statuses,
    )

    print()
    print_kv(
        "READ ONLY",
        "YES",
    )

    print_kv(
        "SQLite mode",
        "mode=ro",
    )

    print_kv(
        "SQLite query_only",
        "1",
    )

    print_kv(
        "INSERT",
        "NONE",
    )

    print_kv(
        "UPDATE",
        "NONE",
    )

    print_kv(
        "DELETE",
        "NONE",
    )

    print_kv(
        "ALTER",
        "NONE",
    )

    print_kv(
        "CREATE",
        "NONE",
    )

    print_kv(
        "DROP",
        "NONE",
    )

    print_kv(
        "SYNTHETIC DATA",
        "NONE",
    )

    print_kv(
        "INTERPOLATION",
        "NONE",
    )

    print_kv(
        "FORWARD FILL",
        "NONE",
    )

    print_kv(
        "BACK FILL",
        "NONE",
    )

    print()
    print(
        "FORENSIC STATUS : COMPLETE"
    )

    print()
    print(
        "NOTE: This script performs read-only forensic "
        "inspection of persisted market_technical state "
        "and discovers validation-related source paths."
    )

    print(
        "NOTE: Missing optional schema fields are reported "
        "without aborting the forensic run."
    )

    print(
        "NOTE: No production repair or data mutation is performed."
    )


# =============================================================================
# MAIN
# =============================================================================

def main():
    banner(
        "ARUNDA MARKET TECHNICAL VALIDATION "
        "RUNTIME FORENSIC v0.2"
    )

    print_kv(
        "Database",
        str(DB_PATH),
    )

    print_kv(
        "Project Directory",
        str(PROJECT_DIR),
    )

    print_kv(
        "Mode",
        "READ ONLY",
    )

    print_kv(
        "Target",
        TARGET_TABLE,
    )

    print_kv(
        "Writes",
        "NONE",
    )

    print_kv(
        "Schema Modification",
        "NONE",
    )

    conn = None

    try:
        banner(
            "DATABASE CONNECTION / READ-ONLY GATE"
        )

        conn = connect_read_only()

        assert_read_only_connection(
            conn
        )

        print(
            "Database              : CONNECTED"
        )

        print(
            "SQLite mode           : mode=ro"
        )

        print(
            "SQLite query_only     : ENABLED"
        )

        if not table_exists(
            conn,
            TARGET_TABLE,
        ):
            raise RuntimeError(
                f"Required table does not exist: "
                f"{TARGET_TABLE}"
            )

        print(
            f"{TARGET_TABLE:<23}: EXISTS"
        )

        columns = get_columns(
            conn,
            TARGET_TABLE,
        )

        print()
        print(
            f"Detected Columns      : "
            f"{len(columns)}"
        )

        print_schema(
            conn
        )

        print_global_counts(
            conn,
            columns,
        )

        print_status_distribution(
            conn,
            columns,
        )

        print_score_distribution(
            conn,
            columns,
        )

        print_status_score_cross(
            conn,
            columns,
        )

        print_version_distribution(
            conn,
            columns,
        )

        print_validation_timestamp_analysis(
            conn,
            columns,
        )

        print_source_timestamp_analysis(
            conn,
            columns,
        )

        print_timestamp_relationship(
            conn,
            columns,
        )

        print_expected_asset_validation(
            conn,
            columns,
        )

        print_unavailable_score_forensic(
            conn,
            columns,
        )

        print_partial_forensic(
            conn,
            columns,
        )

        print_valid_forensic(
            conn,
            columns,
        )

        print_core_field_integrity(
            conn,
            columns,
        )

        print_source_engine_distribution(
            conn,
            columns,
        )

        print_latest_rows(
            conn,
            columns,
        )

        candidates = (
            discover_validation_scripts()
        )

        if candidates:
            source_code_forensic(
                candidates
            )

            ast_function_discovery(
                candidates
            )

            source_write_boundary_check(
                candidates
            )

        print_db_objects(
            conn
        )

        final_contract(
            conn,
            columns,
        )

    except Exception as exc:
        banner(
            "MARKET TECHNICAL VALIDATION "
            "RUNTIME FORENSIC ERROR"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        raise

    finally:
        if conn is not None:
            conn.close()

    print()
    print("=" * 100)
    print(
        "ARUNDA MARKET TECHNICAL VALIDATION "
        "RUNTIME FORENSIC v0.2 COMPLETE"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()