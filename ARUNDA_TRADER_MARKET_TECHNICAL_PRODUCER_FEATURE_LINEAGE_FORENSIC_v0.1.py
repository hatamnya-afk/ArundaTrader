import ast
import os
import re
import sqlite3
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "arunda.db")

TARGET_ENGINE = "market_technical_engine.py"
TARGET_TABLE = "market_technical"

FEATURES = [
    "price",
    "close",
    "open",
    "high",
    "low",
    "volume",
    "history_points",
    "rsi14",
    "rsi_14",
    "atr14",
    "atr_14",
    "ema20",
    "ema_20",
    "sma20",
    "sma_20",
    "volatility",
    "volatility_5",
    "volatility_10",
    "volatility_20",
    "bb_width",
    "cloud_thickness",
    "trend",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "volume_score",
    "range_score",
    "breakout_20",
    "breakout_score",
    "volume_ratio",
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
    "technical_available",
    "available",
    "technical_completeness",
    "completeness",
]

PREREQUISITE_TERMS = [
    "market_history",
    "market_data",
    "history",
    "history_points",
    "ohlcv",
    "candles",
    "candle",
    "open",
    "high",
    "low",
    "close",
    "price",
    "volume",
    "timestamp",
    "time",
    "period",
    "window",
    "lookback",
]

SOURCE_TERMS = [
    "sqlite3",
    "SELECT",
    "fetchone",
    "fetchall",
    "cursor",
    "execute",
    "market_history",
    "market_data",
    "market_records",
    "market_universe",
]

WRITE_PATTERNS = [
    r"\bINSERT\s+(?:OR\s+\w+\s+)?INTO\s+market_technical\b",
    r"\bUPDATE\s+market_technical\b",
    r"\bDELETE\s+FROM\s+market_technical\b",
    r"\bREPLACE\s+INTO\s+market_technical\b",
    r"\bALTER\s+TABLE\s+market_technical\b",
]


def header(title):
    print()
    print("=" * 110)
    print(title)
    print("=" * 110)


def read_utf8(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()

        bom = raw.startswith(b"\xef\xbb\xbf")

        if bom:
            raw = raw[3:]

        return raw.decode("utf-8"), bom

    except Exception:
        return None, False


def line_context(source, line, radius=2):
    lines = source.splitlines()

    start = max(0, line - 1 - radius)
    end = min(len(lines), line + radius)

    return "\n".join(
        f"{i + 1:6}: {lines[i]}"
        for i in range(start, end)
    )


def node_line(node):
    return getattr(node, "lineno", 0)


def node_end_line(node):
    return getattr(
        node,
        "end_lineno",
        node_line(node),
    )


def function_nodes(tree):
    return [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]


def class_nodes(tree):
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    ]


def parent_function(functions, line):
    matches = []

    for fn in functions:
        if (
            fn.lineno <= line <= fn.end_lineno
        ):
            matches.append(fn)

    if not matches:
        return None

    return sorted(
        matches,
        key=lambda fn: (
            fn.end_lineno - fn.lineno,
            fn.lineno,
        ),
    )[0]


def parent_class(classes, line):
    matches = []

    for cls in classes:
        if (
            cls.lineno <= line <= cls.end_lineno
        ):
            matches.append(cls)

    if not matches:
        return None

    return sorted(
        matches,
        key=lambda cls: (
            cls.end_lineno - cls.lineno,
            cls.lineno,
        ),
    )[0]


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)

        if left:
            return left + "." + node.attr

        return node.attr

    return ""


def call_name(node):
    if not isinstance(node, ast.Call):
        return ""

    return dotted_name(node.func)


def string_value(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value

    return ""


def extract_strings(node):
    values = []

    for child in ast.walk(node):
        value = string_value(child)

        if value:
            values.append(value)

    return values


def extract_names(node):
    names = []

    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.append(child.id)

        elif isinstance(child, ast.Attribute):
            names.append(child.attr)

    return names


def extract_calls(node):
    calls = []

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = call_name(child)

            if name:
                calls.append(
                    (
                        name,
                        node_line(child),
                    )
                )

    return calls


def feature_matches_text(source, feature):
    pattern = re.compile(
        r"(?<![A-Za-z0-9_])"
        + re.escape(feature)
        + r"(?![A-Za-z0-9_])"
    )

    return [
        match.start()
        for match in pattern.finditer(source)
    ]


def line_from_offset(source, offset):
    return source.count(
        "\n",
        0,
        offset,
    ) + 1


def nearby_terms(
    source,
    line,
    terms,
    radius=8,
):
    lines = source.splitlines()

    start = max(
        0,
        line - 1 - radius,
    )

    end = min(
        len(lines),
        line + radius,
    )

    text = "\n".join(
        lines[start:end]
    ).lower()

    found = []

    for term in terms:
        if term.lower() in text:
            found.append(term)

    return sorted(set(found))


def analyze_function(
    source,
    function,
    classes,
):
    start = function.lineno
    end = function.end_lineno

    function_source = "\n".join(
        source.splitlines()[start - 1:end]
    )

    features = []
    feature_lines = defaultdict(list)

    for feature in FEATURES:
        offsets = feature_matches_text(
            function_source,
            feature,
        )

        if not offsets:
            continue

        features.append(feature)

        for offset in offsets:
            local_line = line_from_offset(
                function_source,
                offset,
            )

            absolute_line = (
                start
                + local_line
                - 1
            )

            feature_lines[
                feature
            ].append(
                absolute_line
            )

    prerequisites = nearby_terms(
        source,
        start,
        PREREQUISITE_TERMS,
        radius=25,
    )

    sources = nearby_terms(
        source,
        start,
        SOURCE_TERMS,
        radius=25,
    )

    calls = extract_calls(
        function
    )

    classes_name = parent_class(
        classes,
        start,
    )

    return {
        "function": function.name,
        "start": start,
        "end": end,
        "class": (
            classes_name.name
            if classes_name
            else None
        ),
        "features": sorted(
            set(features)
        ),
        "feature_lines": {
            key: sorted(set(value))
            for key, value
            in feature_lines.items()
        },
        "prerequisites": prerequisites,
        "sources": sources,
        "calls": calls,
    }


def analyze_engine():
    path = os.path.join(
        BASE_DIR,
        TARGET_ENGINE,
    )

    result = {
        "path": path,
        "exists": False,
        "source": None,
        "bom": False,
        "parse_error": None,
        "functions": [],
        "classes": [],
        "function_analysis": [],
        "write_hits": [],
    }

    source, bom = read_utf8(path)

    if source is None:
        return result

    result["exists"] = True
    result["source"] = source
    result["bom"] = bom

    try:
        tree = ast.parse(
            source,
            filename=path,
        )

    except SyntaxError as exc:
        result["parse_error"] = str(exc)
        return result

    functions = function_nodes(tree)
    classes = class_nodes(tree)

    result["functions"] = functions
    result["classes"] = classes

    for function in functions:
        result["function_analysis"].append(
            analyze_function(
                source,
                function,
                classes,
            )
        )

    for pattern in WRITE_PATTERNS:
        for match in re.finditer(
            pattern,
            source,
            flags=re.IGNORECASE,
        ):
            line = line_from_offset(
                source,
                match.start(),
            )

            result["write_hits"].append(
                {
                    "line": line,
                    "text": match.group(0),
                }
            )

    return result


def inspect_database():
    result = {
        "connected": False,
        "error": None,
        "query_only": None,
        "table_exists": False,
        "row_count": 0,
        "columns": [],
        "feature_population": {},
    }

    if not os.path.exists(DB_PATH):
        result["error"] = (
            "Database not found"
        )
        return result

    conn = None

    try:
        uri = (
            "file:"
            + DB_PATH.replace("\\", "/")
            + "?mode=ro"
        )

        conn = sqlite3.connect(
            uri,
            uri=True,
        )

        conn.execute(
            "PRAGMA query_only = ON"
        )

        result["connected"] = True

        result["query_only"] = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        table = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            """,
            (TARGET_TABLE,),
        ).fetchone()

        result["table_exists"] = (
            table is not None
        )

        if not result["table_exists"]:
            return result

        columns = conn.execute(
            f'PRAGMA table_info("{TARGET_TABLE}")'
        ).fetchall()

        result["columns"] = [
            row[1]
            for row in columns
        ]

        result["row_count"] = conn.execute(
            f'SELECT COUNT(*) FROM "{TARGET_TABLE}"'
        ).fetchone()[0]

        for feature in FEATURES:
            if feature not in result["columns"]:
                continue

            count = conn.execute(
                f'''
                SELECT COUNT(*)
                FROM "{TARGET_TABLE}"
                WHERE "{feature}" IS NOT NULL
                '''
            ).fetchone()[0]

            result[
                "feature_population"
            ][feature] = count

    except Exception as exc:
        result["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    finally:
        if conn is not None:
            conn.close()

    return result


def print_engine_header(engine):
    header(
        "TARGET ENGINE FORENSIC"
    )

    print(
        f"Target File       : {TARGET_ENGINE}"
    )

    print(
        f"Exists             : "
        f"{'YES' if engine['exists'] else 'NO'}"
    )

    print(
        f"UTF-8 BOM          : "
        f"{'YES' if engine['bom'] else 'NO'}"
    )

    if engine["parse_error"]:
        print(
            f"AST Parse Error    : "
            f"{engine['parse_error']}"
        )


def print_write_boundary(engine):
    header(
        "MARKET_TECHNICAL WRITE BOUNDARY"
    )

    hits = engine["write_hits"]

    print(
        f"Write References : {len(hits)}"
    )

    for hit in hits:
        print(
            f"line={hit['line']:<6} "
            f"{hit['text']}"
        )

        print(
            line_context(
                engine["source"],
                hit["line"],
                radius=2,
            )
        )


def print_function_lineage(engine):
    header(
        "FUNCTION-LEVEL PRODUCER → FEATURE LINEAGE"
    )

    analyses = engine[
        "function_analysis"
    ]

    producer_candidates = [
        item
        for item in analyses
        if item["features"]
    ]

    print(
        f"Functions Inspected        : "
        f"{len(analyses)}"
    )

    print(
        f"Feature-Producing Functions: "
        f"{len(producer_candidates)}"
    )

    for item in producer_candidates:

        print()
        print("-" * 110)

        if item["class"]:
            print(
                f"FUNCTION : "
                f"{item['class']}.{item['function']}()"
            )
        else:
            print(
                f"FUNCTION : "
                f"{item['function']}()"
            )

        print(
            f"RANGE    : "
            f"{item['start']}-{item['end']}"
        )

        print(
            "FEATURES : "
            + ", ".join(
                item["features"]
            )
        )

        print(
            "PREREQUISITES : "
            + (
                ", ".join(
                    item["prerequisites"]
                )
                if item["prerequisites"]
                else "NONE DETECTED"
            )
        )

        print(
            "SOURCES : "
            + (
                ", ".join(
                    item["sources"]
                )
                if item["sources"]
                else "NONE DETECTED"
            )
        )

        print(
            "CALLS : "
            + (
                ", ".join(
                    name
                    for name, line
                    in item["calls"]
                )
                if item["calls"]
                else "NONE"
            )
        )

        print()
        print(
            "FEATURE LINE LOCATIONS:"
        )

        for feature in item[
            "features"
        ]:
            lines = item[
                "feature_lines"
            ].get(
                feature,
                [],
            )

            print(
                f"  {feature:<32} "
                f"lines={lines}"
            )


def print_feature_lineage_matrix(engine):
    header(
        "FEATURE → PRODUCER FUNCTION MATRIX"
    )

    mapping = defaultdict(list)

    for item in engine[
        "function_analysis"
    ]:
        for feature in item[
            "features"
        ]:
            qualified = (
                f"{item['class']}."
                if item["class"]
                else ""
            )

            qualified += (
                item["function"]
                + "()"
            )

            mapping[
                feature
            ].append(
                (
                    qualified,
                    item["start"],
                    item["end"],
                )
            )

    for feature in FEATURES:

        producers = mapping.get(
            feature,
            [],
        )

        if not producers:
            continue

        print()
        print(
            f"FEATURE : {feature}"
        )

        for name, start, end in producers:
            print(
                f"  PRODUCER : "
                f"{name:<45} "
                f"range={start}-{end}"
            )


def print_feature_population(db):
    header(
        "PERSISTED FEATURE POPULATION"
    )

    if db["error"]:
        print(
            f"Database Error : "
            f"{db['error']}"
        )
        return

    print(
        f"Table Exists : "
        f"{'YES' if db['table_exists'] else 'NO'}"
    )

    print(
        f"Persisted Rows: "
        f"{db['row_count']}"
    )

    if not db["table_exists"]:
        return

    for feature in FEATURES:
        if feature not in db[
            "feature_population"
        ]:
            continue

        count = db[
            "feature_population"
        ][feature]

        ratio = 0.0

        if db["row_count"] > 0:
            ratio = (
                count
                / db["row_count"]
            )

        print(
            f"{feature:<32} "
            f"non_null={count:>8} "
            f"ratio={ratio:>8.3f}"
        )


def print_high_value_features(engine, db):
    header(
        "PRODUCER / PERSISTENCE GAP ANALYSIS"
    )

    mapping = defaultdict(list)

    for item in engine[
        "function_analysis"
    ]:
        for feature in item[
            "features"
        ]:
            qualified = (
                f"{item['class']}."
                if item["class"]
                else ""
            )

            qualified += (
                item["function"]
                + "()"
            )

            mapping[
                feature
            ].append(
                qualified
            )

    persisted = db[
        "feature_population"
    ]

    for feature in FEATURES:

        producers = mapping.get(
            feature,
            [],
        )

        if not producers:
            continue

        if feature not in persisted:
            persistence = (
                "COLUMN_NOT_FOUND"
            )
        else:
            persistence = str(
                persisted[feature]
            )

        print()
        print(
            f"FEATURE : {feature}"
        )

        print(
            "  PRODUCER FUNCTIONS:"
        )

        for producer in sorted(
            set(producers)
        ):
            print(
                f"    - {producer}"
            )

        print(
            f"  DB NON-NULL ROWS : "
            f"{persistence}"
        )


def print_contract_targets(engine):
    header(
        "REPAIR TARGET CANDIDATES"
    )

    analyses = engine[
        "function_analysis"
    ]

    targets = []

    for item in analyses:

        feature_count = len(
            item["features"]
        )

        prerequisite_count = len(
            item["prerequisites"]
        )

        source_count = len(
            item["sources"]
        )

        if feature_count == 0:
            continue

        if (
            prerequisite_count == 0
            and source_count == 0
        ):
            confidence = (
                "PRODUCER_WITHOUT_VISIBLE_INPUT"
            )
        elif (
            prerequisite_count > 0
            and source_count > 0
        ):
            confidence = (
                "PRODUCER_WITH_INPUT_CHAIN"
            )
        else:
            confidence = (
                "PRODUCER_PARTIAL_INPUT_CHAIN"
            )

        targets.append(
            (
                feature_count
                + prerequisite_count
                + source_count,
                item,
                confidence,
            )
        )

    targets.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    for score, item, confidence in targets:

        print()
        print(
            f"[LINEAGE SCORE {score}]"
        )

        print(
            f"FUNCTION : "
            f"{item['function']}()"
        )

        print(
            f"RANGE    : "
            f"{item['start']}-{item['end']}"
        )

        print(
            f"CONTRACT : {confidence}"
        )

        print(
            "FEATURES : "
            + ", ".join(
                item["features"]
            )
        )

        print(
            "INPUTS   : "
            + (
                ", ".join(
                    item["prerequisites"]
                )
                if item["prerequisites"]
                else "NONE"
            )
        )

        print(
            "SOURCES  : "
            + (
                ", ".join(
                    item["sources"]
                )
                if item["sources"]
                else "NONE"
            )
        )


def final_contract(engine, db):
    header(
        "FINAL MARKET TECHNICAL PRODUCER FEATURE LINEAGE CONTRACT"
    )

    producer_functions = [
        item
        for item in engine[
            "function_analysis"
        ]
        if item["features"]
    ]

    feature_set = set()

    for item in producer_functions:
        feature_set.update(
            item["features"]
        )

    print(
        f"Target Engine                 : "
        f"{TARGET_ENGINE}"
    )

    print(
        f"Producer Functions             : "
        f"{len(producer_functions)}"
    )

    print(
        f"Features With Producer Evidence: "
        f"{len(feature_set)}"
    )

    print(
        f"Persisted market_technical Rows : "
        f"{db['row_count']}"
    )

    print(
        f"Technical Write References      : "
        f"{len(engine['write_hits'])}"
    )

    print()

    print(
        "READ ONLY                       : YES"
    )

    print(
        "SQLite mode                     : mode=ro"
    )

    print(
        "query_only                      : "
        f"{db['query_only']}"
    )

    print(
        "INSERT                          : NONE"
    )

    print(
        "UPDATE                          : NONE"
    )

    print(
        "DELETE                          : NONE"
    )

    print(
        "ALTER                           : NONE"
    )

    print(
        "CREATE                          : NONE"
    )

    print(
        "DROP                            : NONE"
    )

    print(
        "REPLACE                         : NONE"
    )

    print(
        "COMMIT                          : NONE"
    )

    print(
        "SOURCE MODIFICATION             : NONE"
    )

    print(
        "SYNTHETIC DATA                  : NONE"
    )

    print(
        "INTERPOLATION                   : NONE"
    )

    print(
        "FORWARD FILL                    : NONE"
    )

    print(
        "BACK FILL                       : NONE"
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
        "This forensic is strictly read-only."
    )

    print(
        "It analyzes the actual "
        "market_technical_engine.py "
        "at function and line level."
    )

    print(
        "It maps producer functions to "
        "technical features and visible "
        "prerequisite/source references."
    )

    print(
        "It inspects persisted "
        "market_technical feature population."
    )

    print(
        "It does NOT execute "
        "market_technical_engine."
    )

    print(
        "It does NOT modify production code."
    )

    print(
        "It does NOT modify the production database."
    )

    print(
        "It does NOT repair production state."
    )

    print(
        "It does NOT generate synthetic data."
    )

    print()
    print(
        "NEXT REPAIR DECISION:"
    )

    print(
        "Use the function-level lineage output "
        "to identify the exact producer/input "
        "contract mismatch before editing "
        "market_technical_engine.py."
    )


def main():
    print("=" * 110)
    print(
        "ARUNDA TRADER MARKET TECHNICAL "
        "PRODUCER FEATURE LINEAGE FORENSIC v0.1"
    )
    print("=" * 110)

    print(
        f"BASE DIR : {BASE_DIR}"
    )

    print(
        f"DB PATH  : {DB_PATH}"
    )

    print(
        "MODE     : READ ONLY"
    )

    engine = analyze_engine()
    db = inspect_database()

    print_engine_header(
        engine
    )

    if not engine["exists"]:
        print()
        print(
            "ERROR: target engine file not found:"
        )
        print(
            os.path.join(
                BASE_DIR,
                TARGET_ENGINE,
            )
        )

        return

    if engine["parse_error"]:
        print()
        print(
            "FORENSIC STOP:"
        )

        print(
            "market_technical_engine.py "
            "cannot be AST analyzed until "
            "its syntax is valid."
        )

        print(
            "No production code or database "
            "was modified."
        )

        return

    print_write_boundary(
        engine
    )

    print_function_lineage(
        engine
    )

    print_feature_lineage_matrix(
        engine
    )

    print_feature_population(
        db
    )

    print_high_value_features(
        engine,
        db,
    )

    print_contract_targets(
        engine
    )

    final_contract(
        engine,
        db,
    )

    print()
    print("=" * 110)
    print(
        "ARUNDA TRADER MARKET TECHNICAL "
        "PRODUCER FEATURE LINEAGE FORENSIC v0.1 COMPLETE"
    )
    print("=" * 110)


if __name__ == "__main__":
    main()