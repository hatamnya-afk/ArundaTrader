import os
import ast
import re
import sqlite3
from pathlib import Path

DB_PATH = "arunda.db"
TARGET_TABLE = "market_technical"

BASE_DIR = Path(__file__).resolve().parent

SQL_WRITE_PATTERNS = [
    r"\bINSERT\s+INTO\s+market_technical\b",
    r"\bUPDATE\s+market_technical\b",
    r"\bDELETE\s+FROM\s+market_technical\b",
    r"\bALTER\s+TABLE\s+market_technical\b",
    r"\bREPLACE\s+INTO\s+market_technical\b",
]

FEATURE_NAMES = [
    "price",
    "close",
    "history_points",
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
    "rsi14",
    "rsi_14",
    "breakout_20",
    "available",
    "technical_available",
    "fib_available",
    "fib_236",
    "fib_382",
    "fib_500",
    "fib_618",
    "fib_786",
    "ichimoku_available",
    "tenkan",
    "kijun",
    "senkou_a",
    "senkou_b",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "volume_score",
    "range_score",
    "breakout_score",
    "ema20",
    "ema_20",
    "sma_20",
    "volume_ratio",
    "trend",
]


def print_header(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def safe_read_text(path):
    try:
        return path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
    except Exception as exc:
        print(
            f"READ ERROR : {path.name} : "
            f"{type(exc).__name__}: {exc}"
        )
        return ""


def is_python_file(path):
    return (
        path.is_file()
        and path.suffix.lower() == ".py"
    )


def discover_python_files():
    files = []

    for path in BASE_DIR.iterdir():
        if is_python_file(path):
            files.append(path)

    return sorted(
        files,
        key=lambda p: p.name.lower(),
    )


def parse_ast(path, source):
    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
        return tree
    except SyntaxError as exc:
        print(
            f"AST ERROR : {path.name}"
        )
        print(
            f"  {type(exc).__name__}: {exc}"
        )
        return None
    except Exception as exc:
        print(
            f"AST ERROR : {path.name}"
        )
        print(
            f"  {type(exc).__name__}: {exc}"
        )
        return None


def function_index(tree):
    result = []

    if tree is None:
        return result

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            result.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                    "node": node,
                }
            )

    return result


def find_validation_functions(tree):
    candidates = []

    if tree is None:
        return candidates

    validation_keywords = (
        "valid",
        "validation",
        "validate",
        "check",
        "integrity",
        "contract",
    )

    for item in function_index(tree):

        name = item["name"].lower()

        if any(
            keyword in name
            for keyword in validation_keywords
        ):
            candidates.append(item)

    return candidates


def extract_function_source(source, item):
    lines = source.splitlines()

    start = max(
        0,
        item["line"] - 1,
    )

    end = min(
        len(lines),
        item["end_line"],
    )

    return "\n".join(
        lines[start:end]
    )


def find_feature_references(
    source,
    feature_names,
):
    found = {}

    for feature in feature_names:

        pattern = (
            r"\b"
            + re.escape(feature)
            + r"\b"
        )

        matches = list(
            re.finditer(
                pattern,
                source,
                flags=re.IGNORECASE,
            )
        )

        if matches:
            lines = set()

            for match in matches:

                line_no = (
                    source.count(
                        "\n",
                        0,
                        match.start(),
                    )
                    + 1
                )

                lines.add(line_no)

            found[feature] = sorted(
                lines
            )

    return found


def find_sql_writes(source):
    results = []

    lines = source.splitlines()

    for line_number, line in enumerate(
        lines,
        start=1,
    ):

        for pattern in SQL_WRITE_PATTERNS:

            if re.search(
                pattern,
                line,
                flags=re.IGNORECASE,
            ):
                results.append(
                    {
                        "line": line_number,
                        "sql": line.strip(),
                        "pattern": pattern,
                    }
                )

    return results


def find_sql_strings(tree):
    results = []

    if tree is None:
        return results

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Constant,
        ) and isinstance(
            node.value,
            str,
        ):

            value = node.value

            if re.search(
                r"\bmarket_technical\b",
                value,
                flags=re.IGNORECASE,
            ):
                results.append(
                    {
                        "line": getattr(
                            node,
                            "lineno",
                            None,
                        ),
                        "value": value,
                    }
                )

    return results


def get_table_schema(conn):
    rows = conn.execute(
        "PRAGMA table_info(market_technical)"
    ).fetchall()

    return rows


def get_db_objects(conn):
    return conn.execute(
        """
        SELECT
            type,
            name,
            tbl_name
        FROM sqlite_master
        WHERE type IN (
            'trigger',
            'view'
        )
        ORDER BY type, name
        """
    ).fetchall()


def get_sample_rows(conn):
    columns = [
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(market_technical)"
        ).fetchall()
    ]

    rows = conn.execute(
        """
        SELECT *
        FROM market_technical
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()

    return columns, rows


def value_state(value):
    if value is None:
        return "NULL"

    if isinstance(value, str):
        if not value.strip():
            return "EMPTY_TEXT"

    return "PRESENT"


def inspect_feature_population(
    columns,
    rows,
):
    index = {
        name: i
        for i, name in enumerate(columns)
    }

    result = {}

    for feature in FEATURE_NAMES:

        if feature not in index:
            result[feature] = {
                "column": False,
                "present": 0,
                "null": 0,
            }
            continue

        position = index[feature]

        present = 0
        null_count = 0

        for row in rows:

            state = value_state(
                row[position]
            )

            if state == "NULL":
                null_count += 1
            else:
                present += 1

        result[feature] = {
            "column": True,
            "present": present,
            "null": null_count,
        }

    return result


def main():

    print_header(
        "ARUNDA TRADER "
        "MARKET TECHNICAL "
        "PRODUCER DISCOVERY "
        "READ ONLY v0.1"
    )

    print(
        f"BASE DIR       : {BASE_DIR}"
    )

    print(
        f"DATABASE       : "
        f"{BASE_DIR / DB_PATH}"
    )

    print(
        "MODE           : READ ONLY"
    )

    print(
        "TARGET         : market_technical"
    )

    print(
        "WRITE          : NONE"
    )

    print(
        "SYNTHETIC DATA : NONE"
    )

    print(
        "INTERPOLATION  : NONE"
    )

    print(
        "FORWARD FILL   : NONE"
    )

    print(
        "BACK FILL      : NONE"
    )

    python_files = discover_python_files()

    print_header(
        "PYTHON SOURCE DISCOVERY"
    )

    print(
        f"Python Sources : "
        f"{len(python_files)}"
    )

    all_records = []

    ast_errors = 0
    bom_files = 0

    for path in python_files:

        source = safe_read_text(path)

        if source.startswith(
            "\ufeff"
        ):
            bom_files += 1

        tree = parse_ast(
            path,
            source,
        )

        if tree is None:
            ast_errors += 1

        all_records.append(
            {
                "path": path,
                "source": source,
                "tree": tree,
            }
        )

    print(
        f"AST Parse Errors : "
        f"{ast_errors}"
    )

    print(
        f"UTF-8 BOM Files  : "
        f"{bom_files}"
    )

    print_header(
        "VALIDATION FUNCTION DISCOVERY"
    )

    total_candidates = 0

    for record in all_records:

        candidates = find_validation_functions(
            record["tree"]
        )

        if not candidates:
            continue

        print()
        print(
            f"FILE : "
            f"{record['path'].name}"
        )

        for item in candidates:

            total_candidates += 1

            print(
                f"  function="
                f"{item['name']}"
                f"  line="
                f"{item['line']}"
            )

    print()
    print(
        f"TOTAL VALIDATION "
        f"CANDIDATES : "
        f"{total_candidates}"
    )

    print_header(
        "MARKET_TECHNICAL WRITE-BOUNDARY FORENSIC"
    )

    total_write_refs = 0
    write_files = []

    for record in all_records:

        writes = find_sql_writes(
            record["source"]
        )

        if not writes:
            continue

        write_files.append(
            record["path"].name
        )

        print()
        print(
            f"FILE : "
            f"{record['path'].name}"
        )

        for item in writes:

            total_write_refs += 1

            print(
                f"  line="
                f"{item['line']:<8}"
                f"{item['sql']}"
            )

    print()
    print(
        f"TOTAL TECHNICAL WRITE "
        f"REFERENCES : "
        f"{total_write_refs}"
    )

    print_header(
        "PRODUCER → FEATURE DISCOVERY"
    )

    producer_records = []

    for record in all_records:

        features = find_feature_references(
            record["source"],
            FEATURE_NAMES,
        )

        if not features:
            continue

        producer_records.append(
            (
                record,
                features,
            )
        )

    for record, features in producer_records:

        print()
        print(
            f"FILE : "
            f"{record['path'].name}"
        )

        for feature, lines in sorted(
            features.items()
        ):

            print(
                f"  FEATURE "
                f"{feature:<28} "
                f"lines={lines}"
            )

    print()
    print(
        f"Files referencing target "
        f"features : "
        f"{len(producer_records)}"
    )

    print_header(
        "VALIDATION FUNCTION FEATURE MAP"
    )

    validation_feature_hits = 0

    for record in all_records:

        candidates = find_validation_functions(
            record["tree"]
        )

        if not candidates:
            continue

        for item in candidates:

            function_source = (
                extract_function_source(
                    record["source"],
                    item,
                )
            )

            features = find_feature_references(
                function_source,
                FEATURE_NAMES,
            )

            if not features:
                continue

            print()
            print(
                f"FILE : "
                f"{record['path'].name}"
            )

            print(
                f"FUNCTION : "
                f"{item['name']}"
                f" "
                f"(line "
                f"{item['line']})"
            )

            for feature, lines in sorted(
                features.items()
            ):

                validation_feature_hits += 1

                print(
                    f"  {feature:<28}"
                    f"relative_lines={lines}"
                )

    print()
    print(
        f"Validation Function "
        f"Feature References : "
        f"{validation_feature_hits}"
    )

    print_header(
        "SQL STRING DISCOVERY"
    )

    sql_string_count = 0

    for record in all_records:

        strings = find_sql_strings(
            record["tree"]
        )

        if not strings:
            continue

        for item in strings:

            sql_string_count += 1

            print()
            print(
                f"FILE : "
                f"{record['path'].name}"
            )

            print(
                f"LINE : "
                f"{item['line']}"
            )

            compact = (
                item["value"]
                .replace(
                    "\n",
                    " ",
                )
            )

            print(
                f"SQL : "
                f"{compact[:500]}"
            )

    print()
    print(
        f"market_technical SQL strings : "
        f"{sql_string_count}"
    )

    print_header(
        "DATABASE SCHEMA FORENSIC"
    )

    db_path = (
        BASE_DIR / DB_PATH
    )

    if not db_path.exists():

        print(
            "DATABASE STATUS : "
            "NOT FOUND"
        )

        return

    conn = None

    try:

        conn = sqlite3.connect(
            f"file:{db_path}"
            "?mode=ro",
            uri=True,
        )

        conn.execute(
            "PRAGMA query_only = 1"
        )

        mode = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        print(
            f"SQLite mode    : "
            f"READ ONLY"
        )

        print(
            f"query_only     : "
            f"{mode}"
        )

        schema = get_table_schema(
            conn
        )

        print()
        print(
            "market_technical columns:"
        )

        for row in schema:

            cid = row[0]
            name = row[1]
            data_type = row[2]
            not_null = row[3]
            default = row[4]
            pk = row[5]

            print(
                f"  {cid:<4}"
                f"{name:<36}"
                f"{data_type:<12}"
                f"NOTNULL={not_null} "
                f"PK={pk}"
            )

        objects = get_db_objects(
            conn
        )

        print()
        print(
            "DATABASE TRIGGERS / VIEWS:"
        )

        if not objects:

            print(
                "  NONE"
            )

        else:

            for obj in objects:

                print(
                    f"  "
                    f"{obj[0]:<10}"
                    f"{obj[1]}"
                    f" "
                    f"(table={obj[2]})"
                )

        columns, rows = get_sample_rows(
            conn
        )

        print()
        print(
            f"Sample Rows : "
            f"{len(rows)}"
        )

        population = (
            inspect_feature_population(
                columns,
                rows,
            )
        )

        print_header(
            "FEATURE POPULATION "
            "ON REAL PERSISTED ROWS"
        )

        for feature, info in sorted(
            population.items()
        ):

            if not info["column"]:
                continue

            print(
                f"{feature:<30}"
                f"PRESENT={info['present']:<4}"
                f"NULL={info['null']:<4}"
            )

        print_header(
            "REAL PERSISTED SAMPLE"
        )

        if not rows:

            print(
                "No rows found."
            )

        else:

            index = {
                name: i
                for i, name in enumerate(
                    columns
                )
            }

            interesting = [
                "id",
                "symbol",
                "price",
                "close",
                "history_points",
                "technical_completeness",
                "completeness",
                "technical_available",
                "available",
                "rsi14",
                "rsi_14",
                "atr14",
                "atr_14",
                "trend_score",
                "momentum_score",
                "volatility_score",
                "volume_score",
            ]

            for row in rows:

                print()
                print(
                    "-" * 100
                )

                for field in interesting:

                    if field not in index:
                        continue

                    print(
                        f"{field:<30}"
                        f": "
                        f"{row[index[field]]}"
                    )

    finally:

        if conn is not None:
            conn.close()

    print_header(
        "FINAL PRODUCER DISCOVERY CONTRACT"
    )

    print(
        f"Python Sources Inspected : "
        f"{len(python_files)}"
    )

    print(
        f"Validation Candidates    : "
        f"{total_candidates}"
    )

    print(
        f"AST Parse Errors          : "
        f"{ast_errors}"
    )

    print(
        f"UTF-8 BOM Files           : "
        f"{bom_files}"
    )

    print(
        f"Files With Technical "
        f"Writes                   : "
        f"{len(write_files)}"
    )

    print(
        f"Technical Write References:"
        f" {total_write_refs}"
    )

    print(
        f"Producer Feature Files    : "
        f"{len(producer_records)}"
    )

    print(
        f"Validation Feature Hits   : "
        f"{validation_feature_hits}"
    )

    print()
    print(
        "READ ONLY                 : YES"
    )

    print(
        "SQLite mode               : mode=ro"
    )

    print(
        "query_only                : 1"
    )

    print(
        "INSERT                    : NONE"
    )

    print(
        "UPDATE                    : NONE"
    )

    print(
        "DELETE                    : NONE"
    )

    print(
        "ALTER                     : NONE"
    )

    print(
        "CREATE                    : NONE"
    )

    print(
        "DROP                      : NONE"
    )

    print(
        "REPLACE                   : NONE"
    )

    print(
        "COMMIT                    : NONE"
    )

    print(
        "SOURCE MODIFICATION      : NONE"
    )

    print(
        "SYNTHETIC DATA           : NONE"
    )

    print(
        "INTERPOLATION            : NONE"
    )

    print(
        "FORWARD FILL             : NONE"
    )

    print(
        "BACK FILL                : NONE"
    )

    print()
    print(
        "FORENSIC STATUS : COMPLETE"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This script is strictly "
        "read-only."
    )

    print(
        "It discovers producer "
        "references, feature "
        "references, validation "
        "functions, SQL write "
        "references and persisted "
        "schema/population."
    )

    print(
        "It does NOT execute "
        "market_technical_engine."
    )

    print(
        "It does NOT modify the "
        "production database."
    )

    print(
        "It does NOT repair "
        "production state."
    )

    print(
        "It does NOT generate "
        "synthetic data."
    )

    print()
    print(
        "ARUNDA TRADER "
        "MARKET TECHNICAL "
        "PRODUCER DISCOVERY "
        "READONLY v0.1 COMPLETE"
    )


if __name__ == "__main__":
    main()