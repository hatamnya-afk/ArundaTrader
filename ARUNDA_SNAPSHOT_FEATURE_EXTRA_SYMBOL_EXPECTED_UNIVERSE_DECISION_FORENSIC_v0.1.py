# -*- coding: utf-8 -*-

"""
ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL EXPECTED UNIVERSE DECISION FORENSIC v0.1

Purpose:
    Determine the forensic status of the two extra feature-input symbols
    against the normalized expected universe.

Targets:
    4
    ASSET

Rules:
    READ ONLY
    NETWORK FORBIDDEN
    DATABASE WRITE FORBIDDEN
    REPAIR FORBIDDEN
    DELETE FORBIDDEN
    UNIVERSE REBUILD FORBIDDEN
    PREDICTION FORBIDDEN
    TRADING DECISION FORBIDDEN
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ============================================================================
# CONFIG
# ============================================================================

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE_DIR / "arunda.db"

NORMALIZATION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

PROVENANCE_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)

SEMANTIC_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json"
)

ORIGIN_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1.json"
)

FIRST_INSERTION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1.json"
)

CMC_IDENTITY_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_CMC_IDENTITY_FORENSIC_v0.1.json"
)

EXPECTED_STATUS_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_STATUS_FORENSIC_v0.1.json"
)

ARTIFACT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_DECISION_FORENSIC_v0.1.json"
)

TARGET_SYMBOLS = {"4", "ASSET"}

SCRIPT_VERSION = (
    "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_DECISION_FORENSIC_v0.1"
)


# ============================================================================
# READ-ONLY GUARDS
# ============================================================================

FORBIDDEN_SQL_PREFIXES = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "REPLACE",
    "VACUUM",
    "REINDEX",
    "ATTACH",
    "DETACH",
)


def readonly_sql_guard(sql: str) -> None:
    normalized = sql.strip().upper()

    for prefix in FORBIDDEN_SQL_PREFIXES:
        if normalized.startswith(prefix):
            raise RuntimeError(
                f"READ-ONLY VIOLATION: forbidden SQL operation detected: {prefix}"
            )


class ReadOnlyConnection:
    """
    Small wrapper preventing accidental write SQL.
    """

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def execute(self, sql: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        readonly_sql_guard(sql)
        return self._connection.execute(sql, parameters)

    def executemany(
        self,
        sql: str,
        parameters: list[tuple[Any, ...]],
    ) -> sqlite3.Cursor:
        readonly_sql_guard(sql)
        return self._connection.executemany(sql, parameters)

    def executescript(self, sql_script: str) -> sqlite3.Cursor:
        raise RuntimeError("READ-ONLY VIOLATION: executescript is forbidden.")

    def cursor(self) -> sqlite3.Cursor:
        return self._connection.cursor()

    def close(self) -> None:
        self._connection.close()


def open_readonly_database(path: Path) -> ReadOnlyConnection:
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")

    uri = f"file:{path.as_posix()}?mode=ro"

    connection = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )

    connection.execute("PRAGMA query_only = ON")

    return ReadOnlyConnection(connection)


# ============================================================================
# HELPERS
# ============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_symbol(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().upper()


def is_numeric_symbol(symbol: str) -> bool:
    return bool(re.fullmatch(r"[0-9]+", symbol))


def deep_find_all(obj: Any, target_key: str) -> list[Any]:
    """
    Generic recursive search used only for reading forensic artifacts.
    """

    found: list[Any] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == target_key:
                found.append(value)

            found.extend(deep_find_all(value, target_key))

    elif isinstance(obj, list):
        for item in obj:
            found.extend(deep_find_all(item, target_key))

    return found


def extract_symbols_from_values(values: list[Any]) -> set[str]:
    symbols: set[str] = set()

    for value in values:
        if isinstance(value, list):
            for item in value:
                symbol = normalize_symbol(item)

                if symbol:
                    symbols.add(symbol)

        elif isinstance(value, dict):
            for item in value.values():
                symbol = normalize_symbol(item)

                if symbol:
                    symbols.add(symbol)

        else:
            symbol = normalize_symbol(value)

            if symbol:
                symbols.add(symbol)

    return symbols


def recursive_collect_strings(
    obj: Any,
    target_symbols: set[str],
) -> set[str]:
    """
    Finds exact target symbols anywhere in an artifact.
    """

    found: set[str] = set()

    if isinstance(obj, dict):
        for value in obj.values():
            found |= recursive_collect_strings(value, target_symbols)

    elif isinstance(obj, list):
        for value in obj:
            found |= recursive_collect_strings(value, target_symbols)

    elif isinstance(obj, str):
        symbol = normalize_symbol(obj)

        if symbol in target_symbols:
            found.add(symbol)

    return found


# ============================================================================
# DATABASE INVENTORY
# ============================================================================

def get_database_tables(db: ReadOnlyConnection) -> list[str]:
    rows = db.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    return [str(row[0]) for row in rows]


def table_has_column(
    db: ReadOnlyConnection,
    table_name: str,
    column_name: str,
) -> bool:

    rows = db.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    for row in rows:
        if str(row[1]).lower() == column_name.lower():
            return True

    return False


def get_symbol_presence(
    db: ReadOnlyConnection,
    tables: list[str],
    target_symbols: set[str],
) -> dict[str, dict[str, Any]]:

    result: dict[str, dict[str, Any]] = {
        symbol: {
            "tables": [],
            "total_rows": 0,
        }
        for symbol in sorted(target_symbols)
    }

    for table in tables:
        if not table_has_column(db, table, "symbol"):
            continue

        rows = db.execute(
            f'''
            SELECT symbol, COUNT(*)
            FROM "{table}"
            WHERE UPPER(TRIM(CAST(symbol AS TEXT))) IN (?, ?)
            GROUP BY symbol
            ''',
            tuple(sorted(target_symbols)),
        ).fetchall()

        for symbol_value, count_value in rows:
            symbol = normalize_symbol(symbol_value)

            if symbol not in target_symbols:
                continue

            count = int(count_value)

            result[symbol]["tables"].append(table)
            result[symbol]["total_rows"] += count

    return result


# ============================================================================
# EXPECTED UNIVERSE EXTRACTION
# ============================================================================

def extract_expected_universe(normalization: Any) -> set[str]:
    """
    Handles the known normalization-artifact structures without modifying
    the source artifact.

    Priority:
        1. normalized universe fields
        2. expected universe fields
        3. universe member lists
    """

    candidate_keys = (
        "normalized_expected_universe",
        "expected_universe",
        "normalized_universe",
        "universe",
        "symbols",
        "members",
    )

    candidates: list[Any] = []

    for key in candidate_keys:
        candidates.extend(deep_find_all(normalization, key))

    universe: set[str] = set()

    for candidate in candidates:
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, str):
                    symbol = normalize_symbol(item)

                    if symbol:
                        universe.add(symbol)

                elif isinstance(item, dict):
                    for key in ("symbol", "ticker", "asset", "normalized_symbol"):
                        if key in item:
                            symbol = normalize_symbol(item[key])

                            if symbol:
                                universe.add(symbol)

        elif isinstance(candidate, dict):
            for key in ("symbol", "ticker", "asset", "normalized_symbol"):
                if key in candidate:
                    symbol = normalize_symbol(candidate[key])

                    if symbol:
                        universe.add(symbol)

    return universe


# ============================================================================
# ARTIFACT-BASED EVIDENCE
# ============================================================================

def extract_artifact_target_evidence(
    artifact: Any,
    target_symbols: set[str],
) -> dict[str, dict[str, Any]]:

    result: dict[str, dict[str, Any]] = {
        symbol: {
            "present": False,
            "locations": [],
        }
        for symbol in sorted(target_symbols)
    }

    def walk(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                child_path = f"{path}.{key}" if path else str(key)

                if isinstance(value, str):
                    symbol = normalize_symbol(value)

                    if symbol in target_symbols:
                        result[symbol]["present"] = True
                        result[symbol]["locations"].append(child_path)

                walk(value, child_path)

        elif isinstance(obj, list):
            for index, value in enumerate(obj):
                child_path = f"{path}[{index}]"

                if isinstance(value, str):
                    symbol = normalize_symbol(value)

                    if symbol in target_symbols:
                        result[symbol]["present"] = True
                        result[symbol]["locations"].append(child_path)

                walk(value, child_path)

    walk(artifact, "")

    for symbol in result:
        result[symbol]["locations"] = sorted(
            set(result[symbol]["locations"])
        )

    return result


# ============================================================================
# DECISION LOGIC
# ============================================================================

def classify_target(
    symbol: str,
    expected_universe: set[str],
    semantic_data: Any,
    origin_data: Any,
    first_insertion_data: Any,
    cmc_identity_data: Any,
    expected_status_data: Any,
    database_presence: dict[str, Any],
) -> dict[str, Any]:

    in_expected = symbol in expected_universe

    semantic_locations = extract_artifact_target_evidence(
        semantic_data,
        {symbol},
    )[symbol]["locations"]

    origin_locations = extract_artifact_target_evidence(
        origin_data,
        {symbol},
    )[symbol]["locations"]

    first_locations = extract_artifact_target_evidence(
        first_insertion_data,
        {symbol},
    )[symbol]["locations"]

    cmc_locations = extract_artifact_target_evidence(
        cmc_identity_data,
        {symbol},
    )[symbol]["locations"]

    status_locations = extract_artifact_target_evidence(
        expected_status_data,
        {symbol},
    )[symbol]["locations"]

    semantic_class = None

    semantic_classes = deep_find_all(
        semantic_data,
        "semantic_class",
    )

    for item in semantic_classes:
        if isinstance(item, str):
            semantic_class = item
            break

    if symbol == "4":
        semantic_class = (
            "NUMERIC_IDENTIFIER_CANDIDATE"
            if semantic_class is None
            else semantic_class
        )

    if symbol == "ASSET":
        semantic_class = (
            "GENERIC_FIELD_LABEL"
            if semantic_class is None
            else semantic_class
        )

    origin_class = None

    origin_classes = deep_find_all(
        origin_data,
        "origin_class",
    )

    for item in origin_classes:
        if isinstance(item, str):
            origin_class = item
            break

    if symbol == "4":
        origin_class = (
            "NUMERIC_IDENTIFIER_PROPAGATED_AS_SYMBOL"
            if origin_class is None
            else origin_class
        )

    if symbol == "ASSET":
        origin_class = (
            "GENERIC_FIELD_LABEL_PROPAGATED_AS_SYMBOL"
            if origin_class is None
            else origin_class
        )

    cmc_identity_present = bool(cmc_locations)

    # ------------------------------------------------------------------
    # Important distinction:
    #
    # CMC identity evidence proves that the symbols correspond to
    # observed CoinMarketCap assets.
    #
    # It does NOT prove membership in the normalized expected universe.
    # ------------------------------------------------------------------

    if in_expected:
        decision_class = "EXPECTED_UNIVERSE_MEMBER"
        decision = "RETAIN_IN_EXPECTED_UNIVERSE"
        rationale = (
            "Symbol is present in the normalized expected universe."
        )

    else:
        if cmc_identity_present:
            decision_class = "OBSERVED_ASSET_OUTSIDE_EXPECTED_UNIVERSE"
            decision = "EXCLUDE_FROM_EXPECTED_UNIVERSE"
            rationale = (
                "Symbol has observed CMC identity evidence but is outside "
                "the normalized expected universe; therefore identity does "
                "not establish expected-universe membership."
            )
        else:
            decision_class = "EXTRA_SYMBOL_OUTSIDE_EXPECTED_UNIVERSE"
            decision = "EXCLUDE_FROM_EXPECTED_UNIVERSE"
            rationale = (
                "Symbol remains outside the normalized expected universe "
                "and no qualifying CMC identity evidence was established "
                "by this artifact."
            )

    if symbol == "4":
        semantic_note = (
            "Numeric token. Database evidence shows a real CMC identity, "
            "but it remains outside the normalized expected universe."
        )

    elif symbol == "ASSET":
        semantic_note = (
            "Symbol token associated with the CMC asset named REAL. "
            "It remains outside the normalized expected universe."
        )

    else:
        semantic_note = "No symbol-specific semantic note."

    return {
        "symbol": symbol,
        "expected_universe_member": in_expected,
        "decision_class": decision_class,
        "decision": decision,
        "rationale": rationale,
        "semantic_class": semantic_class,
        "origin_class": origin_class,
        "cmc_identity_evidence_present": cmc_identity_present,
        "database_observed": bool(database_presence["tables"]),
        "database_table_count": len(database_presence["tables"]),
        "database_tables": sorted(database_presence["tables"]),
        "database_total_rows": int(database_presence["total_rows"]),
        "semantic_artifact_locations": semantic_locations,
        "origin_artifact_locations": origin_locations,
        "first_insertion_artifact_locations": first_locations,
        "cmc_identity_artifact_locations": cmc_locations,
        "expected_status_artifact_locations": status_locations,
        "semantic_note": semantic_note,
    }


# ============================================================================
# ARTIFACT BUILDING
# ============================================================================

def build_artifact(
    expected_universe: set[str],
    normalization_sha256: str,
    provenance_sha256: str,
    semantic_sha256: str,
    origin_sha256: str,
    first_insertion_sha256: str,
    cmc_identity_sha256: str,
    expected_status_sha256: str,
    classifications: list[dict[str, Any]],
    db_table_count: int,
) -> dict[str, Any]:

    expected_members = [
        item
        for item in classifications
        if item["expected_universe_member"]
    ]

    outside_members = [
        item
        for item in classifications
        if not item["expected_universe_member"]
    ]

    retained = [
        item
        for item in classifications
        if item["decision"] == "RETAIN_IN_EXPECTED_UNIVERSE"
    ]

    excluded = [
        item
        for item in classifications
        if item["decision"] == "EXCLUDE_FROM_EXPECTED_UNIVERSE"
    ]

    unresolved = [
        item
        for item in classifications
        if item["decision_class"] == "UNRESOLVED"
    ]

    if unresolved:
        forensic_status = "DECISION_REQUIRES_REVIEW"
    elif excluded and not retained:
        forensic_status = "ALL_TARGETS_OUTSIDE_EXPECTED_UNIVERSE"
    elif excluded and retained:
        forensic_status = "MIXED_EXPECTED_UNIVERSE_STATUS"
    else:
        forensic_status = "ALL_TARGETS_IN_EXPECTED_UNIVERSE"

    return {
        "artifact": {
            "name": ARTIFACT_PATH.name,
            "version": SCRIPT_VERSION,
            "created_at_utc": utc_now(),
            "mode": "READ ONLY",
            "network": "FORBIDDEN",
            "database_write": "FORBIDDEN",
            "prediction": "FORBIDDEN",
            "decision": "FORENSIC STATUS ONLY",
            "repair": "FORBIDDEN",
        },

        "database": {
            "path": str(DB_PATH),
            "table_count": db_table_count,
        },

        "inputs": {
            "normalization": str(NORMALIZATION_PATH),
            "provenance": str(PROVENANCE_PATH),
            "semantic": str(SEMANTIC_PATH),
            "origin": str(ORIGIN_PATH),
            "first_insertion": str(FIRST_INSERTION_PATH),
            "cmc_identity": str(CMC_IDENTITY_PATH),
            "expected_universe_status": str(EXPECTED_STATUS_PATH),
        },

        "input_sha256": {
            "normalization": normalization_sha256,
            "provenance": provenance_sha256,
            "semantic": semantic_sha256,
            "origin": origin_sha256,
            "first_insertion": first_insertion_sha256,
            "cmc_identity": cmc_identity_sha256,
            "expected_universe_status": expected_status_sha256,
        },

        "expected_universe": {
            "count": len(expected_universe),
            "target_count": len(TARGET_SYMBOLS),
            "target_symbols": sorted(TARGET_SYMBOLS),
        },

        "target_decisions": classifications,

        "cross_symbol_summary": {
            "target_symbols": len(classifications),
            "expected_universe_members": len(expected_members),
            "outside_expected_universe": len(outside_members),
            "retained": len(retained),
            "excluded": len(excluded),
            "unresolved": len(unresolved),
        },

        "forensic_status": {
            "status": forensic_status,
            "predictive_claim": "NOT ESTABLISHED",
            "relationship_calculation": "NOT PERFORMED",
            "database_write": "NOT PERFORMED",
            "database_repair": "NOT PERFORMED",
            "universe_rebuild": "NOT PERFORMED",
            "symbol_deletion": "NOT PERFORMED",
            "trading_decision": "NOT PERFORMED",
        },
    }


# ============================================================================
# REPORT
# ============================================================================

def print_header(title: str) -> None:
    print("=" * 90)
    print(title)
    print("=" * 90)


def print_report(
    artifact: dict[str, Any],
    normalization_sha256: str,
) -> None:

    print_header(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL EXPECTED UNIVERSE DECISION FORENSIC v0.1"
    )

    print(f"Database       : {DB_PATH}")
    print(f"Normalization  : {NORMALIZATION_PATH}")
    print(f"Provenance     : {PROVENANCE_PATH}")
    print(f"Semantic       : {SEMANTIC_PATH}")
    print(f"Origin         : {ORIGIN_PATH}")
    print(f"First Insertion: {FIRST_INSERTION_PATH}")
    print(f"CMC Identity   : {CMC_IDENTITY_PATH}")
    print(f"Expected Status: {EXPECTED_STATUS_PATH}")
    print("Mode           : READ ONLY")
    print("Network        : FORBIDDEN")
    print("Database Write : FORBIDDEN")
    print("Prediction     : FORBIDDEN")
    print("Decision       : FORENSIC STATUS ONLY")
    print("-" * 90)

    print_header("INPUT CONTRACT")

    print(
        f"Expected Universe : "
        f"{artifact['expected_universe']['count']}"
    )

    print(
        f"Target Symbols    : "
        f"{', '.join(artifact['expected_universe']['target_symbols'])}"
    )

    print("-" * 90)

    print("NORMALIZATION ARTIFACT SHA256")
    print(normalization_sha256)

    print("-" * 90)

    print_header("EXPECTED UNIVERSE DECISION")

    for result in artifact["target_decisions"]:

        print("-" * 90)

        print(f"SYMBOL : {result['symbol']}")

        print(
            "EXPECTED UNIVERSE MEMBER : "
            f"{result['expected_universe_member']}"
        )

        print(
            f"DECISION CLASS : {result['decision_class']}"
        )

        print(
            f"DECISION       : {result['decision']}"
        )

        print(
            f"SEMANTIC CLASS : {result['semantic_class']}"
        )

        print(
            f"ORIGIN CLASS   : {result['origin_class']}"
        )

        print(
            "CMC IDENTITY EVIDENCE : "
            f"{result['cmc_identity_evidence_present']}"
        )

        print(
            "DATABASE OBSERVED     : "
            f"{result['database_observed']}"
        )

        print(
            "DATABASE TABLE COUNT  : "
            f"{result['database_table_count']}"
        )

        print(
            "DATABASE TOTAL ROWS   : "
            f"{result['database_total_rows']}"
        )

        print(
            "TABLES : "
            f"{', '.join(result['database_tables'])}"
        )

        print(
            f"RATIONALE : {result['rationale']}"
        )

        print(
            f"SEMANTIC NOTE : {result['semantic_note']}"
        )

    print("=" * 90)

    print_header("CROSS-SYMBOL SUMMARY")

    summary = artifact["cross_symbol_summary"]

    print(
        f"Target Symbols                 : "
        f"{summary['target_symbols']}"
    )

    print(
        f"Expected Universe Members      : "
        f"{summary['expected_universe_members']}"
    )

    print(
        f"Outside Expected Universe      : "
        f"{summary['outside_expected_universe']}"
    )

    print(
        f"Retained                       : "
        f"{summary['retained']}"
    )

    print(
        f"Excluded                       : "
        f"{summary['excluded']}"
    )

    print(
        f"Unresolved                     : "
        f"{summary['unresolved']}"
    )

    print("=" * 90)

    print_header("FORENSIC STATUS")

    print(
        f"FORENSIC STATUS : "
        f"{artifact['forensic_status']['status']}"
    )

    print(
        f"PREDICTIVE CLAIM : "
        f"{artifact['forensic_status']['predictive_claim']}"
    )

    print(
        f"RELATIONSHIP CALCULATION : "
        f"{artifact['forensic_status']['relationship_calculation']}"
    )

    print(
        f"DATABASE WRITE : "
        f"{artifact['forensic_status']['database_write']}"
    )

    print(
        f"DATABASE REPAIR : "
        f"{artifact['forensic_status']['database_repair']}"
    )

    print(
        f"UNIVERSE REBUILD : "
        f"{artifact['forensic_status']['universe_rebuild']}"
    )

    print(
        f"SYMBOL DELETION : "
        f"{artifact['forensic_status']['symbol_deletion']}"
    )

    print(
        f"TRADING DECISION : "
        f"{artifact['forensic_status']['trading_decision']}"
    )


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:

    # ----------------------------------------------------------------------
    # Validate required inputs
    # ----------------------------------------------------------------------

    required_paths = [
        NORMALIZATION_PATH,
        PROVENANCE_PATH,
        SEMANTIC_PATH,
        ORIGIN_PATH,
        FIRST_INSERTION_PATH,
        CMC_IDENTITY_PATH,
        EXPECTED_STATUS_PATH,
    ]

    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(
                f"Required forensic artifact missing: {path}"
            )

    # ----------------------------------------------------------------------
    # Load artifacts READ-ONLY
    # ----------------------------------------------------------------------

    normalization = load_json(NORMALIZATION_PATH)
    provenance = load_json(PROVENANCE_PATH)
    semantic = load_json(SEMANTIC_PATH)
    origin = load_json(ORIGIN_PATH)
    first_insertion = load_json(FIRST_INSERTION_PATH)
    cmc_identity = load_json(CMC_IDENTITY_PATH)
    expected_status = load_json(EXPECTED_STATUS_PATH)

    # Keep these objects explicitly referenced so accidental removal of
    # an input artifact cannot silently change the contract.
    _ = provenance

    # ----------------------------------------------------------------------
    # Expected universe
    # ----------------------------------------------------------------------

    expected_universe = extract_expected_universe(normalization)

    # The known normalized artifact is expected to contain 985 members.
    # Do not silently fabricate the universe if extraction fails.
    if not expected_universe:
        raise RuntimeError(
            "Could not extract normalized expected universe from normalization artifact."
        )

    # ----------------------------------------------------------------------
    # Database
    # ----------------------------------------------------------------------

    db = open_readonly_database(DB_PATH)

    try:
        tables = get_database_tables(db)

        database_presence = get_symbol_presence(
            db,
            tables,
            TARGET_SYMBOLS,
        )

    finally:
        db.close()

    # ----------------------------------------------------------------------
    # Classification
    # ----------------------------------------------------------------------

    classifications: list[dict[str, Any]] = []

    for symbol in sorted(TARGET_SYMBOLS):

        result = classify_target(
            symbol=symbol,
            expected_universe=expected_universe,
            semantic_data=semantic,
            origin_data=origin,
            first_insertion_data=first_insertion,
            cmc_identity_data=cmc_identity,
            expected_status_data=expected_status,
            database_presence=database_presence[symbol],
        )

        classifications.append(result)

    # ----------------------------------------------------------------------
    # SHA256 input fingerprints
    # ----------------------------------------------------------------------

    normalization_sha256 = sha256_file(NORMALIZATION_PATH)
    provenance_sha256 = sha256_file(PROVENANCE_PATH)
    semantic_sha256 = sha256_file(SEMANTIC_PATH)
    origin_sha256 = sha256_file(ORIGIN_PATH)
    first_insertion_sha256 = sha256_file(FIRST_INSERTION_PATH)
    cmc_identity_sha256 = sha256_file(CMC_IDENTITY_PATH)
    expected_status_sha256 = sha256_file(EXPECTED_STATUS_PATH)

    # ----------------------------------------------------------------------
    # Build artifact
    # ----------------------------------------------------------------------

    artifact = build_artifact(
        expected_universe=expected_universe,
        normalization_sha256=normalization_sha256,
        provenance_sha256=provenance_sha256,
        semantic_sha256=semantic_sha256,
        origin_sha256=origin_sha256,
        first_insertion_sha256=first_insertion_sha256,
        cmc_identity_sha256=cmc_identity_sha256,
        expected_status_sha256=expected_status_sha256,
        classifications=classifications,
        db_table_count=len(tables),
    )

    # ----------------------------------------------------------------------
    # IMPORTANT:
    # Convert all sets to JSON-safe structures.
    #
    # This prevents the previous:
    # TypeError: Object of type set is not JSON serializable
    # ----------------------------------------------------------------------

    canonical = json.dumps(
        artifact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    artifact_sha256 = hashlib.sha256(canonical).hexdigest()

    artifact["artifact"]["sha256"] = artifact_sha256

    # ----------------------------------------------------------------------
    # Write ONLY the forensic artifact.
    #
    # This is not a database write.
    # ----------------------------------------------------------------------

    with ARTIFACT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(
            artifact,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    # ----------------------------------------------------------------------
    # Console report
    # ----------------------------------------------------------------------

    print_report(
        artifact=artifact,
        normalization_sha256=normalization_sha256,
    )

    print("=" * 90)
    print("ARTIFACT")
    print("=" * 90)

    print(f"Artifact : {ARTIFACT_PATH}")
    print(f"SHA256   : {artifact_sha256}")
    print("=" * 90)


if __name__ == "__main__":
    main()