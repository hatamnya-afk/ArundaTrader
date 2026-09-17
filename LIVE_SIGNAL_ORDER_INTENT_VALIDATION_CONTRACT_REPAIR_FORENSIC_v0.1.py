# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
LIVE SIGNAL ORDER INTENT VALIDATION CONTRACT REPAIR FORENSIC v0.1

Purpose:
    Trace the REAL production path:

        fusion_signals
            ->
        order-intent generation
            ->
        order-intent validation
            ->
        validation contract

Rules:
    - READ ONLY FORENSIC
    - NO production source modification
    - NO database writes
    - NO schema changes
    - REAL production invocation where discoverable
"""

import os
import sys
import sqlite3
import importlib
import inspect
import traceback
from datetime import datetime, timezone


# ============================================================================
# CONFIG
# ============================================================================

DB_PATH = os.path.abspath("arunda.db")

EXPECTED_ENGINE_VERSIONS = (
    "FUSION_v0.5",
    "FUSION_v0.4",
)

TARGET_TABLE = "fusion_signals"


# ============================================================================
# HEADER
# ============================================================================

print("=" * 100)
print("ARUNDA LIVE SIGNAL ORDER INTENT VALIDATION CONTRACT REPAIR FORENSIC v0.1")
print("=" * 100)
print(
    "Started UTC : "
    + datetime.now(timezone.utc).isoformat()
)
print("Database    :", DB_PATH)
print("Mode        : READ ONLY FORENSIC")
print("Writes      : NONE")
print("=" * 100)


# ============================================================================
# DATABASE
# ============================================================================

if not os.path.exists(DB_PATH):
    print()
    print("FATAL : DATABASE NOT FOUND")
    print(DB_PATH)
    sys.exit(1)


conn = sqlite3.connect(
    f"file:{DB_PATH}?mode=ro",
    uri=True,
)

conn.row_factory = sqlite3.Row

print()
print("DATABASE CONNECTION : OK")


# ============================================================================
# SCHEMA INSPECTION
# ============================================================================

print()
print("-" * 100)
print("FUSION SIGNALS CONTRACT")
print("-" * 100)

columns = conn.execute(
    "PRAGMA table_info(fusion_signals)"
).fetchall()

column_names = [
    row["name"]
    for row in columns
]

print("Columns:")
for name in column_names:
    print("   ", name)


# ============================================================================
# RUNTIME SIGNAL SNAPSHOT
# ============================================================================

print()
print("-" * 100)
print("LATEST FUSION SIGNALS")
print("-" * 100)

rows = conn.execute(
    """
    SELECT *
    FROM fusion_signals
    ORDER BY id DESC
    LIMIT 10
    """
).fetchall()

print("Rows inspected :", len(rows))

for row in rows:
    print()
    print("ID              :", row["id"])

    for key in (
        "timestamp",
        "asset",
        "fused_score",
        "confidence",
        "direction",
        "signal_strength",
        "entry_price",
        "engine_version",
        "snapshot_id",
        "data_quality",
        "market_available",
        "positioning_available",
        "news_available",
    ):
        if key in row.keys():
            print(f"{key:<18}:", row[key])


# ============================================================================
# PRODUCTION MODULE DISCOVERY
# ============================================================================

print()
print("-" * 100)
print("PRODUCTION MODULE DISCOVERY")
print("-" * 100)


candidate_modules = [
    "order_intent",
    "order_intent_engine",
    "order_intent_generator",
    "order_intent_validation",
    "order_intent_validator",
    "execution_gate",
    "execution_preflight",
    "signal_execution",
    "live_signal",
]


loaded_modules = {}

for module_name in candidate_modules:

    try:

        module = importlib.import_module(module_name)

        loaded_modules[module_name] = module

        print(
            f"MODULE : {module_name:<35} -> LOADED"
        )

    except Exception as exc:

        print(
            f"MODULE : {module_name:<35} -> NOT LOADED"
        )


# ============================================================================
# PROJECT MODULE SEARCH
# ============================================================================

print()
print("-" * 100)
print("PROJECT PYTHON MODULE INVENTORY")
print("-" * 100)

project_dir = os.path.dirname(
    os.path.abspath(__file__)
)

python_files = sorted(
    filename
    for filename in os.listdir(project_dir)
    if filename.endswith(".py")
)

for filename in python_files:
    print("   ", filename)


# ============================================================================
# FUNCTION DISCOVERY
# ============================================================================

print()
print("-" * 100)
print("ORDER-INTENT / VALIDATION FUNCTION DISCOVERY")
print("-" * 100)


keywords = (
    "order",
    "intent",
    "valid",
    "signal",
    "execution",
    "preflight",
    "gate",
)


discovered_functions = []


for module_name, module in loaded_modules.items():

    print()
    print("MODULE :", module_name)

    try:

        members = inspect.getmembers(
            module,
            inspect.isfunction,
        )

        found = False

        for function_name, function in members:

            lowered = function_name.lower()

            if any(
                keyword in lowered
                for keyword in keywords
            ):

                found = True

                try:
                    signature = inspect.signature(
                        function
                    )
                except Exception:
                    signature = "<signature unavailable>"

                print(
                    "   FUNCTION :",
                    function_name,
                )

                print(
                    "   SIGNATURE:",
                    signature,
                )

                discovered_functions.append(
                    (
                        module_name,
                        function_name,
                        function,
                    )
                )

        if not found:
            print(
                "   No relevant functions discovered."
            )

    except Exception as exc:

        print(
            "   DISCOVERY ERROR:",
            repr(exc)
        )


# ============================================================================
# SOURCE INSPECTION
# ============================================================================

print()
print("-" * 100)
print("VALIDATION CONTRACT SOURCE INSPECTION")
print("-" * 100)


for module_name, function_name, function in discovered_functions:

    if any(
        token in function_name.lower()
        for token in (
            "valid",
            "intent",
            "order",
        )
    ):

        print()
        print(
            f"[FUNCTION] {module_name}.{function_name}"
        )

        try:

            source = inspect.getsource(
                function
            )

            print(source)

        except Exception as exc:

            print(
                "SOURCE ERROR:",
                repr(exc)
            )


# ============================================================================
# DATABASE ORDER-INTENT TABLE DISCOVERY
# ============================================================================

print()
print("-" * 100)
print("DATABASE ORDER / INTENT / VALIDATION TABLE DISCOVERY")
print("-" * 100)


tables = conn.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
    """
).fetchall()


relevant_tables = []

for row in tables:

    table_name = row["name"]

    lowered = table_name.lower()

    if any(
        keyword in lowered
        for keyword in (
            "order",
            "intent",
            "execution",
            "signal",
            "validation",
        )
    ):

        relevant_tables.append(
            table_name
        )

        print(
            "TABLE :",
            table_name
        )


# ============================================================================
# TABLE SCHEMAS
# ============================================================================

print()
print("-" * 100)
print("RELEVANT TABLE SCHEMAS")
print("-" * 100)


for table_name in relevant_tables:

    print()
    print(
        "TABLE :",
        table_name
    )

    try:

        schema = conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        for row in schema:

            print(
                f"   {row['name']:<35}"
                f" type={row['type']}"
                f" notnull={row['notnull']}"
                f" pk={row['pk']}"
            )

    except Exception as exc:

        print(
            "   SCHEMA ERROR:",
            repr(exc)
        )


# ============================================================================
# RECENT ORDER / INTENT RECORDS
# ============================================================================

print()
print("-" * 100)
print("RECENT ORDER / INTENT RECORDS")
print("-" * 100)


for table_name in relevant_tables:

    lowered = table_name.lower()

    if (
        "order" in lowered
        or "intent" in lowered
    ):

        print()
        print(
            "TABLE :",
            table_name
        )

        try:

            recent = conn.execute(
                f"""
                SELECT *
                FROM {table_name}
                ORDER BY rowid DESC
                LIMIT 10
                """
            ).fetchall()

            print(
                "Rows inspected :",
                len(recent)
            )

            for row in recent:

                print()

                for key in row.keys():

                    print(
                        f"{key:<30}:",
                        row[key]
                    )

        except Exception as exc:

            print(
                "READ ERROR:",
                repr(exc)
            )


# ============================================================================
# CONTRACT FIELD ANALYSIS
# ============================================================================

print()
print("-" * 100)
print("ORDER-INTENT CONTRACT FIELD ANALYSIS")
print("-" * 100)


expected_fields = [
    "asset",
    "direction",
    "entry_price",
    "fused_score",
    "confidence",
    "signal_strength",
    "engine_version",
    "snapshot_id",
]


print()
print("Expected upstream signal fields:")

for field in expected_fields:

    present = field in column_names

    print(
        f"   {field:<25}: "
        f"{'PRESENT' if present else 'MISSING'}"
    )


# ============================================================================
# NULL / CONTRACT VIOLATION CHECK
# ============================================================================

print()
print("-" * 100)
print("UPSTREAM SIGNAL CONTRACT CHECK")
print("-" * 100)


latest_signals = conn.execute(
    """
    SELECT *
    FROM fusion_signals
    WHERE engine_version IN (?, ?)
    ORDER BY id DESC
    LIMIT 20
    """,
    EXPECTED_ENGINE_VERSIONS,
).fetchall()


print(
    "Signals inspected :",
    len(latest_signals)
)


for row in latest_signals:

    print()
    print(
        "SIGNAL ID :",
        row["id"],
        "ASSET :",
        row["asset"]
    )

    for field in expected_fields:

        if field not in row.keys():

            print(
                f"   {field:<25}: FIELD MISSING"
            )

            continue

        value = row[field]

        if value is None:

            print(
                f"   {field:<25}: NULL"
            )

        else:

            print(
                f"   {field:<25}: OK -> {value}"
            )


# ============================================================================
# MODULE ENTRYPOINT INSPECTION
# ============================================================================

print()
print("-" * 100)
print("ENTRYPOINT / MAIN DISCOVERY")
print("-" * 100)


for module_name, module in loaded_modules.items():

    print()
    print(
        "MODULE :",
        module_name
    )

    if hasattr(module, "main"):

        main_function = getattr(
            module,
            "main",
        )

        try:
            print(
                "MAIN SIGNATURE:",
                inspect.signature(main_function)
            )
        except Exception:
            print(
                "MAIN SIGNATURE: unavailable"
            )

        try:

            source = inspect.getsource(
                main_function
            )

            print(
                "MAIN SOURCE:"
            )

            print(source)

        except Exception as exc:

            print(
                "MAIN SOURCE ERROR:",
                repr(exc)
            )


# ============================================================================
# FINAL FORENSIC STATUS
# ============================================================================

print()
print("=" * 100)
print("FORENSIC CONTRACT REPAIR STATUS")
print("=" * 100)

print()
print(
    "This v0.1 harness is DISCOVERY/CONTRACT FORENSIC ONLY."
)

print(
    "No production code was modified."
)

print(
    "No database writes were performed."
)

print(
    "No automatic repair was applied."
)

print()
print(
    "IMPORTANT:"
)

print(
    "The actual validation failure must be repaired only after"
)

print(
    "the concrete runtime contract mismatch is identified."
)

print()
print("=" * 100)
print("DATABASE CONNECTION : CLOSED")
print("=" * 100)

conn.close()