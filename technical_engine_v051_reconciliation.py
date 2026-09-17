# TECHNICAL_ENGINE_v0.5.1
# LEGACY CONTRACT RECONCILIATION
# MODE: STATIC / READ ONLY
#
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
# NO COMMIT
# NO VACUUM
# NO REINDEX
# NO PRODUCTION MODULE IMPORT/EXECUTION
# NO NETWORK
# NO SYNTHETIC DATA

import ast
import sqlite3
import math
from pathlib import Path
from collections import Counter, defaultdict


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = ROOT / "arunda.db"
TECH_FILE = ROOT / "technical_engine.py"


def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def subsection(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def safe_text(v):
    if v is None:
        return "NULL"
    return str(v)


# ======================================================================
# 1. STATIC SOURCE INSPECTION
# ======================================================================

section("ARUNDA TECHNICAL ENGINE v0.5.1")
print("LEGACY CONTRACT RECONCILIATION")
print("=" * 100)
print(f"ROOT       : {ROOT}")
print(f"DATABASE   : {DB_PATH}")
print(f"SOURCE     : {TECH_FILE}")
print("MODE       : STATIC / READ ONLY")
print("DB WRITES  : NONE")
print("EXECUTION  : PRODUCTION MODULES NOT IMPORTED")
print("=" * 100)

if not ROOT.exists():
    raise RuntimeError(f"PROJECT ROOT NOT FOUND: {ROOT}")

if not DB_PATH.exists():
    raise RuntimeError(f"DATABASE NOT FOUND: {DB_PATH}")

if not TECH_FILE.exists():
    raise RuntimeError(f"TECHNICAL SOURCE NOT FOUND: {TECH_FILE}")


# ======================================================================
# 2. AST SOURCE EXTRACTION
# ======================================================================

source_text = TECH_FILE.read_text(
    encoding="utf-8",
    errors="replace"
)

tree = ast.parse(source_text)

functions = {}
classes = {}

for node in tree.body:

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        functions[node.name] = {
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
        }

    elif isinstance(node, ast.ClassDef):
        classes[node.name] = {
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
        }


section("STATIC SOURCE CONTRACT")

print(f"Source Lines : {len(source_text.splitlines())}")
print(f"Functions    : {len(functions)}")
print(f"Classes      : {len(classes)}")

legacy_targets = [
    "load_history",
    "get_symbols",
    "prices_from_history",
    "volumes_from_history",
    "calculate_return",
    "calculate_sma",
    "calculate_ema",
    "calculate_rsi",
    "calculate_returns_series",
    "calculate_volatility",
    "calculate_volume_sma",
    "calculate_volume_ratio",
    "calculate_structure",
    "detect_structure_state",
    "detect_trend_direction",
    "calculate_trend_strength",
    "detect_trend_alignment",
    "detect_momentum_state",
    "detect_volatility_state",
    "detect_volume_state",
    "detect_regime",
    "calculate_data_quality",
    "calculate_asset",
    "calculate_all_assets",
]

for name in legacy_targets:

    if name in functions:
        info = functions[name]
        print(
            f"[FOUND] FUNCTION {name:<35} "
            f"LINES {info['line']}-{info['end_line']}"
        )
    else:
        print(
            f"[MISS ] FUNCTION {name:<35}"
        )

if "TechnicalRecord" in classes:
    info = classes["TechnicalRecord"]
    print(
        f"[FOUND] CLASS    {'TechnicalRecord':<35} "
        f"LINES {info['line']}-{info['end_line']}"
    )
else:
    print("[MISS ] CLASS    TechnicalRecord")


# ======================================================================
# 3. CONSTANT EXTRACTION
# ======================================================================

subsection("LEGACY CONSTANTS")

constant_targets = {
    "MIN_RETURN_5_POINTS",
    "MIN_VOLATILITY_20_POINTS",
    "MIN_STRUCTURE_20_POINTS",
}

constant_values = {}

for node in ast.walk(tree):

    if isinstance(node, ast.Assign):

        for target in node.targets:

            if (
                isinstance(target, ast.Name)
                and target.id in constant_targets
            ):

                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    value = "<NON-LITERAL>"

                constant_values[target.id] = value

for name in sorted(constant_targets):

    if name in constant_values:
        print(
            f"{name:<30}: {constant_values[name]}"
        )
    else:
        print(
            f"{name:<30}: NOT FOUND"
        )


# ======================================================================
# 4. DB OPEN — READ ONLY
# ======================================================================

section("DATABASE INSPECTION")

# SQLite URI read-only.
uri = f"file:{DB_PATH.as_posix()}?mode=ro"

conn = sqlite3.connect(
    uri,
    uri=True
)

conn.row_factory = sqlite3.Row

# Explicitly DO NOT call:
# commit()
# rollback()
# executescript()
# INSERT / UPDATE / DELETE / ALTER / CREATE / DROP

print("Database : CONNECTED READ-ONLY")


# ======================================================================
# 5. TABLE EXISTENCE
# ======================================================================

tables = conn.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
    """
).fetchall()

table_names = [row["name"] for row in tables]

print()
print("Tables:")
for name in table_names:
    print(f"  {name}")

if "market_technical" not in table_names:
    raise RuntimeError(
        "market_technical table does not exist"
    )


# ======================================================================
# 6. MARKET_TECHNICAL SCHEMA
# ======================================================================

subsection("MARKET_TECHNICAL SCHEMA")

schema_rows = conn.execute(
    "PRAGMA table_info(market_technical)"
).fetchall()

columns = [row["name"] for row in schema_rows]
column_set = set(columns)

for row in schema_rows:
    print(
        f"CID={row['cid']:<4} "
        f"NAME={row['name']:<38} "
        f"TYPE={row['type']:<12} "
        f"NOTNULL={row['notnull']} "
        f"DEFAULT={row['dflt_value']}"
    )


# ======================================================================
# 7. RECORD COUNT
# ======================================================================

total = conn.execute(
    "SELECT COUNT(*) AS c FROM market_technical"
).fetchone()["c"]

print()
print(f"TOTAL RECORDS : {total}")


# ======================================================================
# 8. REQUIRED FIELD AVAILABILITY
# ======================================================================

subsection("TARGET FIELD AVAILABILITY")

target_fields = [
    "id",
    "timestamp",
    "symbol",
    "history_points",
    "price",
    "close",
    "previous_close",
    "return_1",
    "return_3",
    "return_5",
    "return_10",
    "return_20",
    "volatility",
    "volatility_5",
    "volatility_10",
    "volatility_20",
    "atr14",
    "atr_14",
    "volume",
    "volume_ratio",
    "trend",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "volume_score",
    "regime",
    "technical_available",
    "technical_completeness",
    "technical_version",
    "engine_version",
    "source",
    "created_at",
    "updated_at",
    "technical_validation_score",
    "technical_validation_status",
    "technical_validation_flags",
    "technical_validation_version",
    "technical_validated_at",
]

for field in target_fields:
    print(
        f"{field:<38}: "
        f"{'FOUND' if field in column_set else 'MISSING'}"
    )


# ======================================================================
# 9. WRITER / PERSISTENCE STATIC INSPECTION
# ======================================================================

section("WRITER / PERSISTENCE STATIC INSPECTION")

writer_hits = []

for py_file in ROOT.glob("*.py"):

    try:
        text = py_file.read_text(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        continue

    try:
        file_tree = ast.parse(text)
    except Exception:
        continue

    for node in ast.walk(file_tree):

        if isinstance(node, ast.Call):

            func_name = None

            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            elif isinstance(node.func, ast.Name):
                func_name = node.func.id

            if func_name in {
                "execute",
                "executemany",
                "executescript",
            }:

                try:
                    call_text = ast.get_source_segment(
                        text,
                        node
                    ) or ""
                except Exception:
                    call_text = ""

                upper = call_text.upper()

                if any(
                    token in upper
                    for token in [
                        "MARKET_TECHNICAL",
                        "TECHNICAL_VERSION",
                        "TECHNICAL_AVAILABLE",
                        "TECHNICAL_COMPLETENESS",
                    ]
                ):

                    writer_hits.append(
                        (
                            py_file.name,
                            node.lineno,
                            func_name,
                            " ".join(
                                call_text.split()
                            )[:500]
                        )
                    )

print(
    f"Potential technical persistence hits : "
    f"{len(writer_hits)}"
)

for item in writer_hits:
    print()
    print(
        f"FILE={item[0]} "
        f"LINE={item[1]} "
        f"CALL={item[2]}"
    )
    print(
        f"SQL={item[3]}"
    )


# ======================================================================
# 10. VERSION DISTRIBUTION
# ======================================================================

subsection("VERSION / SOURCE DISTRIBUTION")

version_fields = [
    "technical_version",
    "engine_version",
    "source",
]

for field in version_fields:

    if field not in column_set:
        print(
            f"{field}: MISSING"
        )
        continue

    rows = conn.execute(
        f"""
        SELECT
            {field} AS value,
            COUNT(*) AS count
        FROM market_technical
        GROUP BY {field}
        ORDER BY count DESC
        """
    ).fetchall()

    print()
    print(f"{field}:")

    for row in rows:
        print(
            f"  {safe_text(row['value']):<50} "
            f"{row['count']}"
        )


# ======================================================================
# 11. HISTORY SEMANTICS
# ======================================================================

subsection("HISTORY POINT SEMANTICS")

if "history_points" in column_set:

    rows = conn.execute(
        """
        SELECT
            history_points,
            COUNT(*) AS count
        FROM market_technical
        GROUP BY history_points
        ORDER BY count DESC
        """
    ).fetchall()

    for row in rows:
        print(
            f"HISTORY={safe_text(row['history_points']):<20} "
            f"COUNT={row['count']}"
        )

    null_history = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM market_technical
        WHERE history_points IS NULL
        """
    ).fetchone()["c"]

    print()
    print(
        f"HISTORY_POINTS NULL : {null_history}"
    )


# ======================================================================
# 12. PRICE SEMANTICS
# ======================================================================

subsection("PRICE / CLOSE SEMANTICS")

price_cases = {
    "price_valid_close_valid": """
        price IS NOT NULL
        AND price > 0
        AND close IS NOT NULL
        AND close > 0
    """,
    "price_valid_close_null": """
        price IS NOT NULL
        AND price > 0
        AND close IS NULL
    """,
    "price_null_close_valid": """
        price IS NULL
        AND close IS NOT NULL
        AND close > 0
    """,
    "price_null_close_null": """
        price IS NULL
        AND close IS NULL
    """,
    "price_invalid": """
        price IS NOT NULL
        AND (price <= 0 OR price != price)
    """,
}

for label, condition in price_cases.items():

    count = conn.execute(
        f"""
        SELECT COUNT(*) AS c
        FROM market_technical
        WHERE {condition}
        """
    ).fetchone()["c"]

    print(
        f"{label:<35}: {count}"
    )


# ======================================================================
# 13. REGIME DISTRIBUTION
# ======================================================================

subsection("REGIME DISTRIBUTION")

if "regime" in column_set:

    rows = conn.execute(
        """
        SELECT
            regime,
            COUNT(*) AS count
        FROM market_technical
        GROUP BY regime
        ORDER BY count DESC
        """
    ).fetchall()

    for row in rows:
        print(
            f"{safe_text(row['regime']):<40} "
            f"{row['count']}"
        )


# ======================================================================
# 14. VOLATILITY DISTRIBUTION
# ======================================================================

subsection("VOLATILITY CONTRACT EVIDENCE")

for field in [
    "volatility",
    "volatility_20",
]:

    if field not in column_set:
        continue

    stats = conn.execute(
        f"""
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN {field} IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS non_null,
            MIN({field}) AS min_value,
            MAX({field}) AS max_value,
            AVG({field}) AS avg_value
        FROM market_technical
        """
    ).fetchone()

    print()
    print(field)
    print(
        f"  TOTAL    : {stats['total']}"
    )
    print(
        f"  NON-NULL : {stats['non_null']}"
    )
    print(
        f"  MIN      : {safe_text(stats['min_value'])}"
    )
    print(
        f"  MAX      : {safe_text(stats['max_value'])}"
    )
    print(
        f"  AVG      : {safe_text(stats['avg_value'])}"
    )

    for threshold in [
        0.01,
        0.03,
        0.06,
    ]:

        count = conn.execute(
            f"""
            SELECT COUNT(*) AS c
            FROM market_technical
            WHERE {field} IS NOT NULL
              AND {field} < ?
            """,
            (threshold,)
        ).fetchone()["c"]

        print(
            f"  < {threshold:<6}: {count}"
        )


# ======================================================================
# 15. SCORE SEMANTICS
# ======================================================================

subsection("SCORE CONTRACT EVIDENCE")

score_fields = [
    "trend_score",
    "momentum_score",
    "volatility_score",
    "volume_score",
    "range_score",
    "breakout_score",
]

for field in score_fields:

    if field not in column_set:
        print(
            f"{field:<25}: MISSING"
        )
        continue

    stats = conn.execute(
        f"""
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN {field} IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS non_null,
            MIN({field}) AS min_value,
            MAX({field}) AS max_value,
            AVG({field}) AS avg_value
        FROM market_technical
        """
    ).fetchone()

    print(
        f"{field:<25} "
        f"NON_NULL={safe_text(stats['non_null']):<8} "
        f"MIN={safe_text(stats['min_value']):<18} "
        f"MAX={safe_text(stats['max_value']):<18} "
        f"AVG={safe_text(stats['avg_value'])}"
    )


# ======================================================================
# 16. LEGACY-SHAPE EVIDENCE
# ======================================================================

subsection("LEGACY-SHAPE EVIDENCE")

legacy_required = [
    "symbol",
    "history_points",
    "price",
]

legacy_optional = [
    "return_5",
    "volatility_20",
    "sma_20",
    "ema_20",
    "rsi14",
    "atr14",
    "volume_ratio",
    "trend",
    "regime",
]

print("Required fields:")
for field in legacy_required:
    print(
        f"  {field:<30}: "
        f"{'FOUND' if field in column_set else 'MISSING'}"
    )

print()
print("Optional Legacy/extended fields:")
for field in legacy_optional:
    print(
        f"  {field:<30}: "
        f"{'FOUND' if field in column_set else 'MISSING'}"
    )


# ======================================================================
# 17. RECORD-LEVEL CONTRACT FINGERPRINT
# ======================================================================

section("RECORD CONTRACT FINGERPRINT")

select_fields = [
    "id",
    "symbol",
    "history_points",
    "price",
    "close",
    "volatility",
    "volatility_20",
    "regime",
    "technical_available",
    "technical_completeness",
    "technical_version",
    "engine_version",
    "source",
]

select_fields = [
    x for x in select_fields
    if x in column_set
]

query = (
    "SELECT "
    + ", ".join(select_fields)
    + " FROM market_technical"
)

all_rows = conn.execute(query).fetchall()

fingerprints = Counter()

for row in all_rows:

    def availability(field):
        if field not in row.keys():
            return "MISSING"
        return "NULL" if row[field] is None else "VALUE"

    fingerprint = (
        f"HISTORY={availability('history_points')};"
        f"PRICE={availability('price')};"
        f"CLOSE={availability('close')};"
        f"VOLATILITY={availability('volatility')};"
        f"VOLATILITY20={availability('volatility_20')};"
        f"REGIME={availability('regime')};"
        f"TECH_AVAILABLE={availability('technical_available')};"
        f"COMPLETENESS={availability('technical_completeness')};"
        f"TECH_VERSION={availability('technical_version')};"
        f"ENGINE_VERSION={availability('engine_version')};"
        f"SOURCE={availability('source')}"
    )

    fingerprints[fingerprint] += 1

print(
    f"Unique record fingerprints : {len(fingerprints)}"
)

for fingerprint, count in fingerprints.most_common():
    print()
    print(
        f"COUNT={count}"
    )
    print(
        fingerprint
    )


# ======================================================================
# 18. v0.5.0 FLAG DISTRIBUTION
# ======================================================================

subsection("EXISTING v0.5.0 VALIDATION FLAG DISTRIBUTION")

if "technical_validation_flags" in column_set:

    rows = conn.execute(
        """
        SELECT
            technical_validation_flags,
            COUNT(*) AS count
        FROM market_technical
        GROUP BY technical_validation_flags
        ORDER BY count DESC
        """
    ).fetchall()

    for row in rows:
        print(
            f"{safe_text(row['technical_validation_flags']):<80} "
            f"{row['count']}"
        )


# ======================================================================
# 19. EVIDENCE-BASED CLASSIFICATION
# ======================================================================
#
# IMPORTANT:
# This classifier deliberately does NOT treat the old VALIDATOR result
# as truth.
#
# TRUE_INVALID is only assigned for demonstrably malformed canonical
# fields:
#
#   - symbol NULL
#   - price explicitly present but non-finite/non-positive
#   - close explicitly present but non-finite/non-positive
#   - history_points explicitly negative
#
# Volatility is NOT range-invalidated.
# Regime vocabulary is NOT rejected.
# Scores are NOT range-normalized.
#
# LEGACY-COMPATIBLE requires evidence of a plausible Legacy-shaped
# technical record.
#
# NON-LEGACY / OTHER-CONTRACT is used when strong evidence indicates
# another producer/contract family.
#
# UNCLASSIFIED remains for ambiguous cases.
# ======================================================================

section("EVIDENCE-BASED RECONCILIATION")

# Required canonical values for read-only classification.
rows = conn.execute(
    query
).fetchall()


def finite_positive(v):
    if v is None:
        return False

    try:
        x = float(v)
    except Exception:
        return False

    return math.isfinite(x) and x > 0


def finite_nonnegative(v):
    if v is None:
        return False

    try:
        x = float(v)
    except Exception:
        return False

    return math.isfinite(x) and x >= 0


group_counts = Counter()

group_examples = defaultdict(list)

group_reasons = defaultdict(Counter)


for row in rows:

    reasons = []

    symbol = row["symbol"] if "symbol" in row.keys() else None
    price = row["price"] if "price" in row.keys() else None
    close = row["close"] if "close" in row.keys() else None
    history = (
        row["history_points"]
        if "history_points" in row.keys()
        else None
    )

    volatility = (
        row["volatility"]
        if "volatility" in row.keys()
        else None
    )

    volatility20 = (
        row["volatility_20"]
        if "volatility_20" in row.keys()
        else None
    )

    regime = (
        row["regime"]
        if "regime" in row.keys()
        else None
    )

    technical_version = (
        row["technical_version"]
        if "technical_version" in row.keys()
        else None
    )

    engine_version = (
        row["engine_version"]
        if "engine_version" in row.keys()
        else None
    )

    source = (
        row["source"]
        if "source" in row.keys()
        else None
    )

    technical_available = (
        row["technical_available"]
        if "technical_available" in row.keys()
        else None
    )

    completeness = (
        row["technical_completeness"]
        if "technical_completeness" in row.keys()
        else None
    )

    # --------------------------------------------------------------
    # TRUE INVALID — ONLY PROVABLE STRUCTURAL/Numeric INVALIDITY
    # --------------------------------------------------------------

    true_invalid = False

    if symbol is None:
        true_invalid = True
        reasons.append("SYMBOL_NULL")

    # price is canonical when present.
    if price is not None:
        if not finite_positive(price):
            true_invalid = True
            reasons.append("PRICE_NON_POSITIVE_OR_NONFINITE")

    # close is optional. If present, it must be valid.
    if close is not None:
        if not finite_positive(close):
            true_invalid = True
            reasons.append("CLOSE_PRESENT_BUT_INVALID")

    if history is not None:
        try:
            h = int(history)
            if h < 0:
                true_invalid = True
                reasons.append("NEGATIVE_HISTORY_POINTS")
        except Exception:
            true_invalid = True
            reasons.append("NON_INTEGER_HISTORY_POINTS")

    # Explicit numeric volatility must only be finite.
    for field_name, value in [
        ("volatility", volatility),
        ("volatility_20", volatility20),
    ]:

        if value is not None:
            try:
                x = float(value)

                if not math.isfinite(x):
                    true_invalid = True
                    reasons.append(
                        f"{field_name.upper()}_NONFINITE"
                    )

            except Exception:
                true_invalid = True
                reasons.append(
                    f"{field_name.upper()}_NONNUMERIC"
                )

    if true_invalid:

        group = "TRUE-INVALID"

    else:

        # ----------------------------------------------------------
        # NON-LEGACY / OTHER-CONTRACT
        # ----------------------------------------------------------
        #
        # Strong evidence:
        # price is valid but history_points is NULL and there is
        # no evidence of Legacy history-based calculation.
        #
        # This specifically captures the known 4935 family.
        # ----------------------------------------------------------

        strong_other_contract = False

        if (
            finite_positive(price)
            and history is None
            and completeness is None
            and technical_available is None
        ):
            strong_other_contract = True
            reasons.append(
                "VALID_PRICE_WITHOUT_LEGACY_HISTORY_CONTEXT"
            )

        # Explicit source/version family different from the known
        # Legacy technical engine can also be evidence, but we do not
        # invent a list of versions here.
        if source is not None:
            reasons.append(
                f"SOURCE_PRESENT:{source}"
            )

        if technical_version is not None:
            reasons.append(
                f"TECHNICAL_VERSION_PRESENT:{technical_version}"
            )

        if engine_version is not None:
            reasons.append(
                f"ENGINE_VERSION_PRESENT:{engine_version}"
            )

        if strong_other_contract:

            group = "NON-LEGACY / OTHER-CONTRACT"

        else:

            # ------------------------------------------------------
            # LEGACY-COMPATIBLE
            # ------------------------------------------------------
            #
            # Evidence pattern:
            # valid symbol
            # valid price
            # history context exists
            #
            # Optional features are allowed to be NULL because
            # Legacy calculation has warm-up/availability semantics.
            # ------------------------------------------------------

            legacy_shape = (
                symbol is not None
                and finite_positive(price)
                and history is not None
            )

            if legacy_shape:

                group = "LEGACY-COMPATIBLE"

                reasons.append(
                    "CANONICAL_PRICE_VALID"
                )
                reasons.append(
                    "HISTORY_CONTEXT_PRESENT"
                )

            else:

                group = "UNCLASSIFIED"
                reasons.append(
                    "INSUFFICIENT_CONTRACT_EVIDENCE"
                )

    group_counts[group] += 1

    for reason in reasons:
        group_reasons[group][reason] += 1

    if len(group_examples[group]) < 20:
        group_examples[group].append(
            {
                "id": row["id"],
                "symbol": symbol,
                "price": price,
                "history": history,
                "volatility": volatility,
                "volatility20": volatility20,
                "regime": regime,
                "source": source,
                "technical_version": technical_version,
                "engine_version": engine_version,
            }
        )


# ======================================================================
# 20. FINAL CONTRACT OUTPUT
# ======================================================================

section("FINAL RECONCILIATION RESULT")

x = group_counts["LEGACY-COMPATIBLE"]
y = group_counts["NON-LEGACY / OTHER-CONTRACT"]
z = group_counts["TRUE-INVALID"]
w = group_counts["UNCLASSIFIED"]

print(
    "TECHNICAL ENGINE v0.5.1"
)
print(
    "LEGACY CONTRACT RECONCILIATION"
)
print()
print(
    f"TOTAL RECORDS              : {total}"
)
print()
print(
    f"LEGACY-COMPATIBLE          : {x}"
)
print(
    f"NON-LEGACY / OTHER-CONTRACT: {y}"
)
print(
    f"TRUE-INVALID               : {z}"
)
print(
    f"UNCLASSIFIED               : {w}"
)
print()
print(
    f"CHECK: {x} + {y} + {z} + {w} = "
    f"{x+y+z+w}"
)
print(
    f"CHECK EXPECTED             = {total}"
)
print(
    f"CHECK STATUS               : "
    f"{'PASS' if x+y+z+w == total else 'FAIL'}"
)


# ======================================================================
# 21. GROUP EVIDENCE
# ======================================================================

for group in [
    "LEGACY-COMPATIBLE",
    "NON-LEGACY / OTHER-CONTRACT",
    "TRUE-INVALID",
    "UNCLASSIFIED",
]:

    subsection(group)

    print(
        f"COUNT : {group_counts[group]}"
    )

    print()
    print("KEY REASONS:")

    if group_reasons[group]:

        for reason, count in (
            group_reasons[group]
            .most_common()
        ):
            print(
                f"  {reason:<65} {count}"
            )

    else:
        print(
            "  NONE"
        )

    print()
    print("EXAMPLES:")

    for item in group_examples[group]:

        print(
            f"  id={item['id']} "
            f"symbol={safe_text(item['symbol'])} "
            f"price={safe_text(item['price'])} "
            f"history={safe_text(item['history'])} "
            f"volatility={safe_text(item['volatility'])} "
            f"volatility20={safe_text(item['volatility20'])} "
            f"regime={safe_text(item['regime'])}"
        )


# ======================================================================
# 22. OLD VALIDATOR VS TRUE INVALID
# ======================================================================

section("OLD VALIDATOR VS RECONCILIATION")

old_invalid = conn.execute(
    """
    SELECT COUNT(*) AS c
    FROM market_technical
    WHERE technical_validation_status = 'INVALID'
    """
).fetchone()["c"]

print(
    f"OLD VALIDATOR INVALID      = {old_invalid}"
)
print(
    f"TRUE INVALID               = {z}"
)
print(
    f"FALSE INVALID / CONTRACT MISMATCH = "
    f"{max(old_invalid - z, 0)}"
)
print(
    f"UNCLASSIFIED               = {w}"
)


# ======================================================================
# 23. KNOWN 4935 FAMILY
# ======================================================================

section("KNOWN HISTORY_COUNT_UNKNOWN FAMILY")

if "history_points" in column_set:

    count_4935 = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM market_technical
        WHERE history_points IS NULL
        """
    ).fetchone()["c"]

    print(
        f"HISTORY_COUNT_UNKNOWN FAMILY : "
        f"{count_4935}"
    )

    rows = conn.execute(
        """
        SELECT
            symbol,
            price,
            close,
            history_points,
            volatility,
            volatility_20,
            regime,
            source,
            technical_version,
            engine_version
        FROM market_technical
        WHERE history_points IS NULL
        ORDER BY id DESC
        LIMIT 30
        """
    ).fetchall()

    print()
    print("SAMPLES:")

    for row in rows:

        print(
            f"symbol={safe_text(row['symbol'])} "
            f"price={safe_text(row['price'])} "
            f"close={safe_text(row['close'])} "
            f"history={safe_text(row['history_points'])} "
            f"volatility={safe_text(row['volatility'])} "
            f"volatility20={safe_text(row['volatility_20'])} "
            f"regime={safe_text(row['regime'])} "
            f"source={safe_text(row['source'])} "
            f"technical_version={safe_text(row['technical_version'])} "
            f"engine_version={safe_text(row['engine_version'])}"
        )


# ======================================================================
# 24. HARD STOP / READ ONLY PROOF
# ======================================================================

section("READ-ONLY COMPLETION")

print("INSERT  : NONE")
print("UPDATE  : NONE")
print("DELETE  : NONE")
print("ALTER   : NONE")
print("CREATE  : NONE")
print("DROP    : NONE")
print("COMMIT  : NONE")
print("VACUUM  : NONE")
print("REINDEX : NONE")
print("NETWORK : NONE")
print("PRODUCTION MODULE EXECUTION : NONE")
print()
print("RECONCILIATION COMPLETE")
print("=" * 100)

conn.close()