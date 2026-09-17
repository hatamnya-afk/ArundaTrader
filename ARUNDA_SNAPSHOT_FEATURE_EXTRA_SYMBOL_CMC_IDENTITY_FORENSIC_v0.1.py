# ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_CMC_IDENTITY_FORENSIC_v0.1.py
# READ ONLY / NETWORK FORBIDDEN / DATABASE WRITE FORBIDDEN
#
# Purpose:
#   For the two extra symbols:
#       4
#       ASSET
#
#   determine their observable CMC identity and cross-table identity
#   without modifying the database.
#
# No:
#   - DB write
#   - repair
#   - deletion
#   - universe rebuild
#   - network
#   - prediction
#   - decision

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# CONTRACT
# =============================================================================

SCRIPT_NAME = (
    "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_CMC_IDENTITY_FORENSIC_v0.1"
)

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE_DIR / "arunda.db"

NORMALIZATION_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

PROVENANCE_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)

SEMANTIC_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json"
)

ORIGIN_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1.json"
)

FIRST_INSERTION_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1.json"
)

OUTPUT_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_CMC_IDENTITY_FORENSIC_v0.1.json"
)

TARGET_SYMBOLS = {"4", "ASSET"}

SAMPLE_LIMIT = 5


# =============================================================================
# BASIC UTILITIES
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        obj = json.load(handle)

    if not isinstance(obj, dict):
        raise RuntimeError(
            f"Artifact root is not an object: {path}"
        )

    return obj


def json_safe(value: Any) -> Any:

    if isinstance(value, dict):
        return {
            str(key): json_safe(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, set):
        return sorted(
            json_safe(item)
            for item in value
        )

    if isinstance(value, bytes):
        return value.decode(
            "utf-8",
            errors="replace",
        )

    return value


def canonical_sha256(obj: Any) -> str:

    payload = json.dumps(
        json_safe(obj),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


# =============================================================================
# INPUT ARTIFACTS
# =============================================================================

def validate_input_artifacts() -> dict[str, Any]:

    paths = {
        "normalization": NORMALIZATION_ARTIFACT,
        "provenance": PROVENANCE_ARTIFACT,
        "semantic": SEMANTIC_ARTIFACT,
        "origin": ORIGIN_ARTIFACT,
        "first_insertion": FIRST_INSERTION_ARTIFACT,
    }

    result = {}

    for name, path in paths.items():

        if not path.exists():
            raise FileNotFoundError(
                f"Required artifact not found: {path}"
            )

        result[name] = {
            "path": str(path),
            "sha256": sha256_file(path),
        }

    return result


# =============================================================================
# SQLITE INVENTORY
# =============================================================================

def get_tables(
    conn: sqlite3.Connection,
) -> list[str]:

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return [
        str(row[0])
        for row in rows
    ]


def get_columns(
    conn: sqlite3.Connection,
    table: str,
) -> list[str]:

    rows = conn.execute(
        f"PRAGMA table_info({quote_identifier(table)})"
    ).fetchall()

    return [
        str(row[1])
        for row in rows
    ]


def row_to_dict(
    cursor: sqlite3.Cursor,
    row: sqlite3.Row,
) -> dict[str, Any]:

    return {
        str(cursor.description[index][0]):
        json_safe(row[index])
        for index in range(len(row))
    }


# =============================================================================
# TARGET RESOLUTION
# =============================================================================

def resolve_targets(
    provenance: dict[str, Any],
    semantic: dict[str, Any],
    origin: dict[str, Any],
    first_insertion: dict[str, Any],
) -> list[str]:

    discovered = set()

    # Provenance
    cross_source = provenance.get(
        "cross_source_extra_presence",
        {},
    )

    if isinstance(cross_source, dict):

        for source_info in cross_source.values():

            if not isinstance(source_info, dict):
                continue

            extras = source_info.get(
                "extra_symbols",
                [],
            )

            if isinstance(extras, list):

                for symbol in extras:
                    discovered.add(str(symbol))

    # Semantic
    for key in (
        "numeric_symbols",
        "generic_field_labels",
        "unresolved_symbols",
    ):

        values = semantic.get(key, [])

        if isinstance(values, list):

            for symbol in values:
                discovered.add(str(symbol))

    # Origin
    for key in (
        "symbols",
        "target_symbols",
        "resolved_symbols",
    ):

        values = origin.get(key, [])

        if isinstance(values, list):

            for symbol in values:
                discovered.add(str(symbol))

    # First insertion artifact
    for key in (
        "target_symbols",
        "symbols",
    ):

        values = (
            first_insertion.get(
                "target_contract",
                {},
            ).get(key, [])
            if isinstance(
                first_insertion.get(
                    "target_contract",
                    {},
                ),
                dict,
            )
            else []
        )

        if isinstance(values, list):

            for symbol in values:
                discovered.add(str(symbol))

    resolved = sorted(
        discovered.intersection(
            TARGET_SYMBOLS
        )
    )

    if set(resolved) != TARGET_SYMBOLS:

        raise RuntimeError(
            "Could not resolve both required target "
            f"symbols. Found={resolved}"
        )

    return resolved


# =============================================================================
# COLUMN DETECTION
# =============================================================================

IDENTITY_COLUMNS = {
    "symbol",
    "asset",
    "asset_symbol",
    "asset_symbols",
    "name",
    "slug",
    "cmc_id",
    "cmc_rank",
    "rank",
    "source",
    "engine_version",
    "is_active",
    "date_added",
    "first_seen",
    "last_seen",
    "last_updated",
    "timestamp",
    "source_timestamp",
    "created_at",
    "updated_at",
}


def candidate_identity_columns(
    columns: list[str],
) -> list[str]:

    result = []

    for column in columns:

        if column.lower() in IDENTITY_COLUMNS:
            result.append(column)

    return result


def symbol_columns(
    columns: list[str],
) -> list[str]:

    result = []

    for column in columns:

        if column.lower() in {
            "symbol",
            "asset",
            "asset_symbol",
            "asset_symbols",
            "ticker",
        }:
            result.append(column)

    return result


# =============================================================================
# TIMESTAMP
# =============================================================================

TIMESTAMP_PRIORITY = [
    "timestamp",
    "source_timestamp",
    "date_added",
    "first_seen",
    "last_seen",
    "created_at",
    "updated_at",
    "last_updated",
]


def parse_datetime(
    value: Any,
) -> datetime | None:

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    candidates = [
        text,
        text.replace("Z", "+00:00"),
    ]

    for candidate in candidates:

        try:

            dt = datetime.fromisoformat(
                candidate
            )

            if dt.tzinfo is None:
                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            return dt.astimezone(
                timezone.utc
            )

        except ValueError:
            pass

    return None


def earliest_timestamp(
    row_dict: dict[str, Any],
) -> tuple[str | None, str | None]:

    candidates = []

    for column in TIMESTAMP_PRIORITY:

        actual = next(
            (
                key
                for key in row_dict
                if key.lower() == column
            ),
            None,
        )

        if actual is None:
            continue

        parsed = parse_datetime(
            row_dict.get(actual)
        )

        if parsed is not None:

            candidates.append(
                (
                    parsed,
                    actual,
                )
            )

    if not candidates:
        return None, None

    candidates.sort(
        key=lambda item: item[0]
    )

    return (
        candidates[0][0].isoformat(),
        candidates[0][1],
    )


# =============================================================================
# ROW SEARCH
# =============================================================================

def search_symbol_in_table(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    symbol: str,
) -> dict[str, Any]:

    q_table = quote_identifier(table)
    q_column = quote_identifier(column)

    cursor = conn.execute(
        f"""
        SELECT *
        FROM {q_table}
        WHERE CAST({q_column} AS TEXT) = ?
        """,
        (symbol,),
    )

    rows = cursor.fetchall()

    serialized = []

    for row in rows:

        row_dict = row_to_dict(
            cursor,
            row,
        )

        timestamp, timestamp_column = (
            earliest_timestamp(row_dict)
        )

        serialized.append(
            {
                "timestamp_utc": timestamp,
                "timestamp_column": timestamp_column,
                "row": row_dict,
            }
        )

    serialized.sort(
        key=lambda item: (
            item["timestamp_utc"]
            is None,
            item["timestamp_utc"]
            or "",
        )
    )

    first = (
        serialized[0]
        if serialized
        else None
    )

    return {
        "table": table,
        "column": column,
        "symbol": symbol,
        "row_count": len(rows),
        "first_timestamp_utc": (
            first["timestamp_utc"]
            if first
            else None
        ),
        "first_timestamp_column": (
            first["timestamp_column"]
            if first
            else None
        ),
        "first_row": (
            first["row"]
            if first
            else None
        ),
        "samples": serialized[:SAMPLE_LIMIT],
    }


# =============================================================================
# CMC IDENTITY EXTRACTION
# =============================================================================

def normalize_identity(
    row: dict[str, Any] | None,
) -> dict[str, Any]:

    if not row:
        return {
            "cmc_id": None,
            "name": None,
            "symbol": None,
            "slug": None,
            "cmc_rank": None,
            "rank": None,
            "source": None,
            "engine_version": None,
            "is_active": None,
            "date_added": None,
            "first_seen": None,
            "last_seen": None,
            "last_updated": None,
        }

    def get(
        name: str,
    ) -> Any:

        for key, value in row.items():

            if key.lower() == name.lower():
                return value

        return None

    return {
        "cmc_id": get("cmc_id"),
        "name": get("name"),
        "symbol": get("symbol"),
        "slug": get("slug"),
        "cmc_rank": get("cmc_rank"),
        "rank": get("rank"),
        "source": get("source"),
        "engine_version": get("engine_version"),
        "is_active": get("is_active"),
        "date_added": get("date_added"),
        "first_seen": get("first_seen"),
        "last_seen": get("last_seen"),
        "last_updated": get("last_updated"),
    }


# =============================================================================
# MARKET_UNIVERSE PRIMARY IDENTITY
# =============================================================================

def inspect_market_universe(
    conn: sqlite3.Connection,
    symbol: str,
) -> dict[str, Any]:

    tables = get_tables(conn)

    if "market_universe" not in tables:

        return {
            "available": False,
            "reason": "market_universe table not found",
        }

    columns = get_columns(
        conn,
        "market_universe",
    )

    candidates = symbol_columns(
        columns
    )

    if not candidates:

        return {
            "available": False,
            "reason": (
                "No symbol-like column found "
                "in market_universe"
            ),
        }

    evidence = []

    for column in candidates:

        evidence.append(
            search_symbol_in_table(
                conn,
                "market_universe",
                column,
                symbol,
            )
        )

    rows = []

    for item in evidence:

        first_row = item.get(
            "first_row"
        )

        if first_row:
            rows.append(first_row)

    identities = [
        normalize_identity(row)
        for row in rows
    ]

    return {
        "available": True,
        "symbol": symbol,
        "search_columns": candidates,
        "evidence": evidence,
        "identity_records": identities,
    }


# =============================================================================
# CROSS-TABLE CMC ID SEARCH
# =============================================================================

def search_cmc_id(
    conn: sqlite3.Connection,
    cmc_id: Any,
) -> list[dict[str, Any]]:

    if cmc_id is None:
        return []

    tables = get_tables(conn)

    matches = []

    for table in tables:

        columns = get_columns(
            conn,
            table,
        )

        cmc_columns = [
            column
            for column in columns
            if column.lower()
            in {
                "cmc_id",
                "coinmarketcap_id",
                "coinmarketcapid",
            }
        ]

        for column in cmc_columns:

            q_table = quote_identifier(table)
            q_column = quote_identifier(column)

            try:

                cursor = conn.execute(
                    f"""
                    SELECT *
                    FROM {q_table}
                    WHERE CAST({q_column} AS TEXT) = ?
                    LIMIT {SAMPLE_LIMIT}
                    """,
                    (str(cmc_id),),
                )

                rows = cursor.fetchall()

                for row in rows:

                    row_dict = row_to_dict(
                        cursor,
                        row,
                    )

                    timestamp, timestamp_column = (
                        earliest_timestamp(
                            row_dict
                        )
                    )

                    matches.append(
                        {
                            "table": table,
                            "column": column,
                            "cmc_id": json_safe(cmc_id),
                            "timestamp_utc": timestamp,
                            "timestamp_column": (
                                timestamp_column
                            ),
                            "row": row_dict,
                        }
                    )

            except sqlite3.DatabaseError:
                continue

    return matches


# =============================================================================
# SYMBOL + CMC ID CONSISTENCY
# =============================================================================

def assess_identity_consistency(
    symbol: str,
    universe_identity: dict[str, Any],
    cmc_matches: list[dict[str, Any]],
) -> dict[str, Any]:

    identities = []

    primary_records = (
        universe_identity.get(
            "identity_records",
            []
        )
    )

    for record in primary_records:

        if isinstance(record, dict):
            identities.append(record)

    cmc_symbols = set()
    cmc_names = set()
    cmc_slugs = set()

    for match in cmc_matches:

        row = match.get(
            "row",
            {}
        )

        identity = normalize_identity(
            row
        )

        if identity.get("symbol") is not None:
            cmc_symbols.add(
                str(identity["symbol"])
            )

        if identity.get("name") is not None:
            cmc_names.add(
                str(identity["name"])
            )

        if identity.get("slug") is not None:
            cmc_slugs.add(
                str(identity["slug"])
            )

    primary_symbols = {
        str(item["symbol"])
        for item in identities
        if item.get("symbol") is not None
    }

    primary_names = {
        str(item["name"])
        for item in identities
        if item.get("name") is not None
    }

    primary_slugs = {
        str(item["slug"])
        for item in identities
        if item.get("slug") is not None
    }

    symbol_consistent = (
        not primary_symbols
        or symbol in primary_symbols
    )

    cross_table_symbol_consistent = (
        not cmc_symbols
        or symbol in cmc_symbols
    )

    return {
        "target_symbol": symbol,
        "market_universe_symbols": sorted(
            primary_symbols
        ),
        "market_universe_names": sorted(
            primary_names
        ),
        "market_universe_slugs": sorted(
            primary_slugs
        ),
        "cmc_cross_table_symbols": sorted(
            cmc_symbols
        ),
        "cmc_cross_table_names": sorted(
            cmc_names
        ),
        "cmc_cross_table_slugs": sorted(
            cmc_slugs
        ),
        "market_universe_symbol_consistent": (
            symbol_consistent
        ),
        "cross_table_symbol_consistent": (
            cross_table_symbol_consistent
        ),
        "identity_consistency": (
            "CONSISTENT"
            if (
                symbol_consistent
                and cross_table_symbol_consistent
            )
            else "INCONSISTENT_OR_INCOMPLETE"
        ),
    }


# =============================================================================
# SEMANTIC ASSESSMENT
# =============================================================================

def semantic_assessment(
    symbol: str,
    identities: list[dict[str, Any]],
) -> dict[str, Any]:

    if not identities:

        return {
            "status": "NO_MARKET_UNIVERSE_IDENTITY",
            "identity_class": (
                "UNRESOLVED"
            ),
            "canonical_asset_evidence": False,
        }

    names = {
        str(item["name"])
        for item in identities
        if item.get("name") is not None
    }

    symbols = {
        str(item["symbol"])
        for item in identities
        if item.get("symbol") is not None
    }

    slugs = {
        str(item["slug"])
        for item in identities
        if item.get("slug") is not None
    }

    cmc_ids = {
        str(item["cmc_id"])
        for item in identities
        if item.get("cmc_id") is not None
    }

    sources = {
        str(item["source"])
        for item in identities
        if item.get("source") is not None
    }

    engine_versions = {
        str(item["engine_version"])
        for item in identities
        if item.get("engine_version") is not None
    }

    active_values = {
        item["is_active"]
        for item in identities
        if item.get("is_active") is not None
    }

    if cmc_ids and sources:

        identity_class = (
            "CMC_ASSET_IDENTITY_OBSERVED"
        )

        canonical_evidence = True

    else:

        identity_class = (
            "PARTIAL_ASSET_IDENTITY"
        )

        canonical_evidence = False

    return {
        "status": (
            "IDENTITY_OBSERVED"
        ),
        "identity_class": identity_class,
        "canonical_asset_evidence": (
            canonical_evidence
        ),
        "cmc_ids": sorted(cmc_ids),
        "names": sorted(names),
        "symbols": sorted(symbols),
        "slugs": sorted(slugs),
        "sources": sorted(sources),
        "engine_versions": sorted(
            engine_versions
        ),
        "is_active_values": sorted(
            active_values,
            key=lambda x: str(x),
        ),
    }


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL "
        "CMC IDENTITY FORENSIC v0.1"
    )
    print("=" * 90)

    print(
        f"Database       : {DB_PATH}"
    )
    print(
        f"Normalization  : {NORMALIZATION_ARTIFACT}"
    )
    print(
        f"Provenance     : {PROVENANCE_ARTIFACT}"
    )
    print(
        f"Semantic       : {SEMANTIC_ARTIFACT}"
    )
    print(
        f"Origin         : {ORIGIN_ARTIFACT}"
    )
    print(
        f"First Insertion: {FIRST_INSERTION_ARTIFACT}"
    )
    print("Mode           : READ ONLY")
    print("Network        : FORBIDDEN")
    print("Database Write : FORBIDDEN")
    print("Prediction     : FORBIDDEN")
    print("Decision       : FORBIDDEN")
    print("-" * 90)

    # -------------------------------------------------------------------------
    # Load contracts
    # -------------------------------------------------------------------------

    input_artifacts = (
        validate_input_artifacts()
    )

    normalization = load_json(
        NORMALIZATION_ARTIFACT
    )

    provenance = load_json(
        PROVENANCE_ARTIFACT
    )

    semantic = load_json(
        SEMANTIC_ARTIFACT
    )

    origin = load_json(
        ORIGIN_ARTIFACT
    )

    first_insertion = load_json(
        FIRST_INSERTION_ARTIFACT
    )

    targets = resolve_targets(
        provenance,
        semantic,
        origin,
        first_insertion,
    )

    expected_universe = (
        normalization.get(
            "expected_universe"
        )
    )

    print("=" * 90)
    print("INPUT CONTRACT")
    print("=" * 90)
    print(
        f"Expected Universe : "
        f"{expected_universe}"
    )
    print(
        f"Target Symbols    : "
        f"{', '.join(targets)}"
    )
    print("-" * 90)

    # -------------------------------------------------------------------------
    # Read-only database connection
    # -------------------------------------------------------------------------

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    db_uri = (
        "file:"
        + str(DB_PATH).replace("\\", "/")
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        db_uri,
        uri=True,
        timeout=30,
    )

    conn.row_factory = sqlite3.Row

    try:

        tables = get_tables(conn)

        print("=" * 90)
        print("DATABASE INVENTORY")
        print("=" * 90)
        print(
            f"Database Tables : {len(tables)}"
        )

        results = {}

        for symbol in targets:

            print("=" * 90)
            print(
                f"SYMBOL : {symbol}"
            )
            print("=" * 90)

            # -------------------------------------------------------------
            # market_universe identity
            # -------------------------------------------------------------

            universe = inspect_market_universe(
                conn,
                symbol,
            )

            identities = universe.get(
                "identity_records",
                [],
            )

            primary_identity = (
                identities[0]
                if identities
                else {}
            )

            print(
                "MARKET_UNIVERSE IDENTITY"
            )

            if primary_identity:

                print(
                    f"CMC ID       : "
                    f"{primary_identity.get('cmc_id')}"
                )

                print(
                    f"NAME         : "
                    f"{primary_identity.get('name')}"
                )

                print(
                    f"SYMBOL       : "
                    f"{primary_identity.get('symbol')}"
                )

                print(
                    f"SLUG         : "
                    f"{primary_identity.get('slug')}"
                )

                print(
                    f"CMC RANK     : "
                    f"{primary_identity.get('cmc_rank')}"
                )

                print(
                    f"RANK         : "
                    f"{primary_identity.get('rank')}"
                )

                print(
                    f"SOURCE       : "
                    f"{primary_identity.get('source')}"
                )

                print(
                    f"ENGINE       : "
                    f"{primary_identity.get('engine_version')}"
                )

                print(
                    f"IS ACTIVE    : "
                    f"{primary_identity.get('is_active')}"
                )

                print(
                    f"DATE ADDED   : "
                    f"{primary_identity.get('date_added')}"
                )

                print(
                    f"FIRST SEEN   : "
                    f"{primary_identity.get('first_seen')}"
                )

                print(
                    f"LAST UPDATED : "
                    f"{primary_identity.get('last_updated')}"
                )

            else:

                print(
                    "NO market_universe identity found."
                )

            # -------------------------------------------------------------
            # CMC ID cross-table evidence
            # -------------------------------------------------------------

            cmc_id = primary_identity.get(
                "cmc_id"
            )

            cmc_matches = search_cmc_id(
                conn,
                cmc_id,
            )

            print(
                f"CMC ID CROSS-TABLE MATCHES : "
                f"{len(cmc_matches)}"
            )

            for match in cmc_matches[:SAMPLE_LIMIT]:

                print(
                    f"  {match['table']}"
                    f".{match['column']}"
                )

            # -------------------------------------------------------------
            # Consistency
            # -------------------------------------------------------------

            consistency = (
                assess_identity_consistency(
                    symbol,
                    universe,
                    cmc_matches,
                )
            )

            print(
                "IDENTITY CONSISTENCY : "
                f"{consistency['identity_consistency']}"
            )

            # -------------------------------------------------------------
            # Semantic identity
            # -------------------------------------------------------------

            semantic_result = (
                semantic_assessment(
                    symbol,
                    identities,
                )
            )

            print(
                "IDENTITY CLASS : "
                f"{semantic_result['identity_class']}"
            )

            print(
                "CANONICAL ASSET EVIDENCE : "
                f"{semantic_result['canonical_asset_evidence']}"
            )

            # -------------------------------------------------------------
            # Temporal evidence
            # -------------------------------------------------------------

            earliest = None
            latest = None

            all_timestamps = []

            for item in universe.get(
                "evidence",
                [],
            ):

                for sample in item.get(
                    "samples",
                    [],
                ):

                    timestamp = sample.get(
                        "timestamp_utc"
                    )

                    parsed = parse_datetime(
                        timestamp
                    )

                    if parsed is not None:
                        all_timestamps.append(
                            parsed
                        )

            if all_timestamps:

                all_timestamps.sort()

                earliest = (
                    all_timestamps[0].isoformat()
                )

                latest = (
                    all_timestamps[-1].isoformat()
                )

            print(
                f"EARLIEST MARKET_UNIVERSE OBSERVATION : "
                f"{earliest}"
            )

            print(
                f"LATEST SAMPLE OBSERVATION             : "
                f"{latest}"
            )

            results[symbol] = {
                "symbol": symbol,
                "market_universe": universe,
                "primary_identity": (
                    primary_identity
                ),
                "cmc_id_cross_table_evidence": (
                    cmc_matches
                ),
                "identity_consistency": (
                    consistency
                ),
                "semantic_identity": (
                    semantic_result
                ),
                "temporal_evidence": {
                    "earliest_sample_timestamp_utc": (
                        earliest
                    ),
                    "latest_sample_timestamp_utc": (
                        latest
                    ),
                },
            }

        # ---------------------------------------------------------------------
        # Cross-symbol comparison
        # ---------------------------------------------------------------------

        print("=" * 90)
        print(
            "CROSS-SYMBOL CMC IDENTITY SUMMARY"
        )
        print("=" * 90)

        cmc_identity_count = 0
        unresolved_count = 0

        for symbol in targets:

            semantic_result = results[
                symbol
            ][
                "semantic_identity"
            ]

            identity_class = (
                semantic_result[
                    "identity_class"
                ]
            )

            print("-" * 90)
            print(
                f"SYMBOL : {symbol}"
            )
            print(
                f"IDENTITY CLASS : "
                f"{identity_class}"
            )

            print(
                f"CMC IDs : "
                f"{semantic_result.get('cmc_ids', [])}"
            )

            print(
                f"NAMES : "
                f"{semantic_result.get('names', [])}"
            )

            print(
                f"SYMBOLS : "
                f"{semantic_result.get('symbols', [])}"
            )

            print(
                f"SLUGS : "
                f"{semantic_result.get('slugs', [])}"
            )

            print(
                f"SOURCES : "
                f"{semantic_result.get('sources', [])}"
            )

            if (
                semantic_result[
                    "canonical_asset_evidence"
                ]
            ):
                cmc_identity_count += 1
            else:
                unresolved_count += 1

        # ---------------------------------------------------------------------
        # Final forensic status
        # ---------------------------------------------------------------------

        if cmc_identity_count == len(targets):

            forensic_status = (
                "CMC_ASSET_IDENTITIES_OBSERVED_FOR_ALL_TARGETS"
            )

        elif cmc_identity_count > 0:

            forensic_status = (
                "PARTIAL_CMC_ASSET_IDENTITY_OBSERVED"
            )

        else:

            forensic_status = (
                "CMC_ASSET_IDENTITY_NOT_ESTABLISHED"
            )

        print("=" * 90)
        print(
            "FORENSIC STATUS"
        )
        print("=" * 90)

        print(
            f"FORENSIC STATUS : "
            f"{forensic_status}"
        )

        print(
            "PREDICTIVE CLAIM : NOT ESTABLISHED"
        )

        print(
            "RELATIONSHIP CALCULATION : NOT PERFORMED"
        )

        print(
            "DATABASE WRITE : NOT PERFORMED"
        )

        print(
            "DATABASE REPAIR : NOT PERFORMED"
        )

        # ---------------------------------------------------------------------
        # Artifact
        # ---------------------------------------------------------------------

        artifact = {
            "artifact": {
                "name": OUTPUT_ARTIFACT.name,
                "version": "v0.1",
                "generated_at_utc": utc_now(),
            },

            "contract": {
                "script": SCRIPT_NAME,
                "database": str(DB_PATH),
                "mode": "READ ONLY",
                "network": "FORBIDDEN",
                "database_write": "FORBIDDEN",
                "prediction": "FORBIDDEN",
                "decision": "FORBIDDEN",
            },

            "input_artifacts": input_artifacts,

            "target_contract": {
                "expected_universe": (
                    expected_universe
                ),
                "target_symbols": targets,
                "target_count": len(targets),
            },

            "database_inventory": {
                "table_count": len(tables),
                "tables": tables,
            },

            "symbol_results": results,

            "cross_symbol_summary": {
                "target_count": len(targets),
                "cmc_identity_count": (
                    cmc_identity_count
                ),
                "unresolved_identity_count": (
                    unresolved_count
                ),
            },

            "forensic_status": forensic_status,

            "claims": {
                "predictive_claim": (
                    "NOT ESTABLISHED"
                ),
                "relationship_calculation": (
                    "NOT PERFORMED"
                ),
                "database_write": (
                    "NOT PERFORMED"
                ),
                "database_repair": (
                    "NOT PERFORMED"
                ),
            },

            "important_limitation": (
                "CMC identity observed in the local database "
                "does not prove that the current expected "
                "universe should contain the symbol. It only "
                "establishes locally observable identity "
                "metadata and cross-table consistency."
            ),
        }

        artifact = json_safe(
            artifact
        )

        artifact["artifact"][
            "content_sha256"
        ] = canonical_sha256(
            artifact
        )

        with OUTPUT_ARTIFACT.open(
            "w",
            encoding="utf-8",
        ) as handle:

            json.dump(
                artifact,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

        artifact_sha256 = (
            sha256_file(
                OUTPUT_ARTIFACT
            )
        )

        # ---------------------------------------------------------------------
        # Final artifact report
        # ---------------------------------------------------------------------

        print("=" * 90)
        print("ARTIFACT")
        print("=" * 90)

        print(
            f"Artifact : "
            f"{OUTPUT_ARTIFACT}"
        )

        print(
            f"SHA256   : "
            f"{artifact_sha256}"
        )

        print("=" * 90)

    finally:

        conn.close()


if __name__ == "__main__":
    main()