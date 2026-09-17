# ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.py
# READ ONLY FORENSIC
# No DB Write
# No Repair
# No Universe Rebuild
# No Network
# No Prediction
# No Decision

import json
import hashlib
import sqlite3
import re
from pathlib import Path
from datetime import datetime, timezone


SCRIPT_VERSION = "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1"

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

ALIGNMENT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_FEATURE_INPUT_ALIGNMENT_FORENSIC_v0.1.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json"
)


# ============================================================
# CONSTANTS
# ============================================================

TARGET_SYMBOLS = {"4", "ASSET"}

DATABASE_SOURCES = {
    "market_history": ("symbol",),
    "market_history_legacy": ("symbol",),
    "market_microstructure": ("symbol",),
    "market_opportunity": ("symbol",),
    "market_state": ("symbol",),
    "market_technical": ("symbol",),
    "market_universe": ("symbol",),

    "fusion_signals": ("asset",),
    "hunter_signals": ("asset",),
    "market_data": ("symbol",),
    "market_news": ("symbol",),
    "market_news_intelligence": ("symbol",),
    "market_records": ("asset",),
    "news_data": ("asset",),
    "news_signals": ("asset",),
    "opportunity_signals": ("asset",),
    "positioning_data": ("symbol",),
    "risk_decisions": ("asset",),
    "signal_outcomes": ("asset",),
    "social_metrics": ("asset",),
    "trade_decisions": ("asset",),
    "trade_gate_decisions": ("asset",),
    "market_whale": ("symbol",),
}


# ============================================================
# UTILITIES
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def canonical_json_bytes(obj):
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def normalize_symbol(value):
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    value = str(value).strip()

    if not value:
        return None

    return value.upper()


def recursive_json_safe(value):
    """
    Convert every non-JSON-native container recursively.

    Important fix:
    set -> sorted list

    This prevents:
    TypeError: Object of type set is not JSON serializable
    """

    if isinstance(value, dict):
        return {
            str(k): recursive_json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            recursive_json_safe(v)
            for v in value
        ]

    if isinstance(value, set):
        converted = [
            recursive_json_safe(v)
            for v in value
        ]

        try:
            return sorted(
                converted,
                key=lambda x: json.dumps(
                    x,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            )
        except Exception:
            return converted

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def is_numeric_symbol(symbol):
    if symbol is None:
        return False

    return bool(
        re.fullmatch(
            r"[+-]?\d+(?:\.\d+)?",
            symbol.strip(),
        )
    )


def is_generic_field_label(symbol):
    if symbol is None:
        return False

    generic_labels = {
        "ASSET",
        "SYMBOL",
        "TOKEN",
        "COIN",
        "TICKER",
        "MARKET",
        "NAME",
        "PAIR",
        "ID",
    }

    return symbol.upper() in generic_labels


# ============================================================
# DATABASE
# ============================================================

def open_read_only_database():
    """
    SQLite URI mode=ro guarantees read-only database access.
    """

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
    )


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_table_columns(conn, table_name):
    if not table_exists(conn, table_name):
        return []

    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


def quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def get_symbol_presence(conn, table_name, column_name, target_symbols):
    result = {
        symbol: {
            "present": False,
            "row_count": 0,
            "evidence": [],
        }
        for symbol in target_symbols
    }

    if not table_exists(conn, table_name):
        return result

    columns = get_table_columns(
        conn,
        table_name,
    )

    if column_name not in columns:
        return result

    qtable = quote_identifier(table_name)
    qcolumn = quote_identifier(column_name)

    rows = conn.execute(
        f"""
        SELECT
            CAST({qcolumn} AS TEXT) AS symbol_value,
            COUNT(*) AS row_count
        FROM {qtable}
        WHERE CAST({qcolumn} AS TEXT) IN (?, ?)
        GROUP BY CAST({qcolumn} AS TEXT)
        """,
        (
            "4",
            "ASSET",
        ),
    ).fetchall()

    for symbol_value, row_count in rows:
        symbol = normalize_symbol(symbol_value)

        if symbol in result:
            result[symbol]["present"] = True
            result[symbol]["row_count"] = int(row_count)

    return result


def collect_database_provenance(conn):
    provenance = {
        "4": {
            "evidence_sources": set(),
            "row_counts": {},
        },
        "ASSET": {
            "evidence_sources": set(),
            "row_counts": {},
        },
    }

    for table_name, columns in DATABASE_SOURCES.items():

        for column_name in columns:

            presence = get_symbol_presence(
                conn,
                table_name,
                column_name,
                TARGET_SYMBOLS,
            )

            source_name = (
                f"DATABASE_TABLE:{table_name.upper()}:{column_name.upper()}"
            )

            for symbol in TARGET_SYMBOLS:

                info = presence.get(symbol)

                if not info:
                    continue

                if info["present"]:
                    provenance[symbol][
                        "evidence_sources"
                    ].add(source_name)

                    provenance[symbol][
                        "row_counts"
                    ][source_name] = info["row_count"]

    return provenance


# ============================================================
# ARTIFACT SYMBOL EXTRACTION
# ============================================================

def get_path(obj, path, default=None):
    current = obj

    for key in path:
        if not isinstance(current, dict):
            return default

        if key not in current:
            return default

        current = current[key]

    return current


def find_symbol_list_candidates(obj, path=()):
    """
    Generic recursive search for lists that look like
    symbol collections.
    """

    candidates = []

    if isinstance(obj, dict):

        for key, value in obj.items():

            current_path = path + (str(key),)

            if isinstance(value, list):

                normalized = []

                for item in value:
                    symbol = normalize_symbol(item)

                    if symbol is not None:
                        normalized.append(symbol)

                if normalized:
                    candidates.append(
                        {
                            "path": ".".join(current_path),
                            "symbols": normalized,
                        }
                    )

            candidates.extend(
                find_symbol_list_candidates(
                    value,
                    current_path,
                )
            )

    elif isinstance(obj, list):

        for index, value in enumerate(obj):

            candidates.extend(
                find_symbol_list_candidates(
                    value,
                    path + (str(index),),
                )
            )

    return candidates


def resolve_extra_symbols_from_alignment(alignment):
    candidates = []

    direct_paths = [
        (
            "root.feature_input_inventory[3].comparison.extra_symbols",
            [
                "feature_input_inventory",
                3,
                "comparison",
                "extra_symbols",
            ],
        ),
    ]

    for label, path in direct_paths:

        value = alignment

        try:
            for key in path:
                value = value[key]

            if isinstance(value, list):
                symbols = {
                    normalize_symbol(v)
                    for v in value
                    if normalize_symbol(v) is not None
                }

                if symbols:
                    candidates.append(
                        {
                            "source": label,
                            "symbols": symbols,
                        }
                    )

        except (
            KeyError,
            IndexError,
            TypeError,
        ):
            pass

    if not candidates:

        recursive = find_symbol_list_candidates(
            alignment
        )

        for candidate in recursive:

            symbols = set(
                candidate["symbols"]
            )

            if TARGET_SYMBOLS.issubset(symbols):
                candidates.append(
                    {
                        "source": candidate["path"],
                        "symbols": symbols,
                    }
                )

    return candidates


def resolve_extra_symbols_from_provenance(provenance):
    candidates = []

    direct_paths = [
        (
            "root.cross_source_extra_presence.market_history.extra_symbols",
            [
                "cross_source_extra_presence",
                "market_history",
                "extra_symbols",
            ],
        ),
    ]

    for label, path in direct_paths:

        value = provenance

        try:
            for key in path:
                value = value[key]

            if isinstance(value, list):

                symbols = {
                    normalize_symbol(v)
                    for v in value
                    if normalize_symbol(v) is not None
                }

                if symbols:
                    candidates.append(
                        {
                            "source": label,
                            "symbols": symbols,
                        }
                    )

        except (
            KeyError,
            IndexError,
            TypeError,
        ):
            pass

    if not candidates:

        recursive = find_symbol_list_candidates(
            provenance
        )

        for candidate in recursive:

            symbols = set(
                candidate["symbols"]
            )

            if TARGET_SYMBOLS.issubset(symbols):
                candidates.append(
                    {
                        "source": candidate["path"],
                        "symbols": symbols,
                    }
                )

    return candidates


# ============================================================
# SEMANTIC CLASSIFICATION
# ============================================================

def classify_symbol(symbol, evidence_sources):
    if is_numeric_symbol(symbol):

        return {
            "semantic_class": "NUMERIC_IDENTIFIER_CANDIDATE",
            "meaning": (
                "Pure numeric token; not established as a market symbol."
            ),
            "artifact_likelihood": "MEDIUM",
            "market_symbol_likelihood": "LOW",
            "classification_basis": [
                "pure_numeric_token",
                "no_non_numeric_symbol_semantics",
                "database_presence_does_not_establish_market_identity",
            ],
        }

    if is_generic_field_label(symbol):

        return {
            "semantic_class": "GENERIC_FIELD_LABEL",
            "meaning": (
                "Generic field label rather than a market symbol."
            ),
            "artifact_likelihood": "HIGH",
            "market_symbol_likelihood": "VERY_LOW",
            "classification_basis": [
                "known_generic_field_label",
                "field_name_semantics",
                "database_presence_does_not_establish_market_identity",
            ],
        }

    return {
        "semantic_class": "UNRESOLVED_SYMBOL",
        "meaning": (
            "Symbol-like token whose market meaning is not "
            "established by this forensic pass."
        ),
        "artifact_likelihood": "UNKNOWN",
        "market_symbol_likelihood": "UNKNOWN",
        "classification_basis": [
            "not_numeric",
            "not_known_generic_field_label",
        ],
    }


# ============================================================
# MAIN FORENSIC
# ============================================================

def main():

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL SEMANTIC FORENSIC v0.1"
    )
    print("=" * 90)

    print(f"Database       : {DB_PATH}")
    print(f"Normalization  : {NORMALIZATION_PATH}")
    print(f"Provenance     : {PROVENANCE_PATH}")
    print(f"Alignment      : {ALIGNMENT_PATH}")
    print("Mode           : READ ONLY")
    print("Network        : FORBIDDEN")
    print("Database Write : FORBIDDEN")
    print("Prediction     : FORBIDDEN")
    print("Decision       : FORBIDDEN")
    print("-" * 90)

    # --------------------------------------------------------
    # Validate files
    # --------------------------------------------------------

    for path in (
        DB_PATH,
        NORMALIZATION_PATH,
        PROVENANCE_PATH,
        ALIGNMENT_PATH,
    ):
        if not path.exists():
            raise FileNotFoundError(
                f"Required input not found: {path}"
            )

    normalization = load_json(
        NORMALIZATION_PATH
    )

    provenance_artifact = load_json(
        PROVENANCE_PATH
    )

    alignment_artifact = load_json(
        ALIGNMENT_PATH
    )

    normalization_sha256 = sha256_file(
        NORMALIZATION_PATH
    )

    provenance_sha256 = sha256_file(
        PROVENANCE_PATH
    )

    alignment_sha256 = sha256_file(
        ALIGNMENT_PATH
    )

    # --------------------------------------------------------
    # Expected universe
    # --------------------------------------------------------

    expected_universe = get_path(
        normalization,
        ["normalized_expected_universe"],
        [],
    )

    expected_universe = {
        normalize_symbol(x)
        for x in expected_universe
        if normalize_symbol(x) is not None
    }

    # --------------------------------------------------------
    # Resolve extras
    # --------------------------------------------------------

    alignment_candidates = (
        resolve_extra_symbols_from_alignment(
            alignment_artifact
        )
    )

    provenance_candidates = (
        resolve_extra_symbols_from_provenance(
            provenance_artifact
        )
    )

    alignment_extra_symbols = set()

    for candidate in alignment_candidates:
        alignment_extra_symbols.update(
            candidate["symbols"]
        )

    provenance_extra_symbols = set()

    for candidate in provenance_candidates:
        provenance_extra_symbols.update(
            candidate["symbols"]
        )

    resolved_extras = (
        alignment_extra_symbols
        & provenance_extra_symbols
    )

    # Fallback: if both artifacts independently identify
    # 4 and ASSET, accept the intersection.
    if not TARGET_SYMBOLS.issubset(resolved_extras):

        combined = (
            alignment_extra_symbols
            | provenance_extra_symbols
        )

        if TARGET_SYMBOLS.issubset(combined):
            resolved_extras = (
                TARGET_SYMBOLS
                & combined
            )

    if not TARGET_SYMBOLS.issubset(
        resolved_extras
    ):
        raise RuntimeError(
            "Could not resolve both required extra symbols: "
            "4 and ASSET"
        )

    resolved_extras = set(
        TARGET_SYMBOLS
    )

    # --------------------------------------------------------
    # Database provenance
    # --------------------------------------------------------

    conn = open_read_only_database()

    try:
        database_provenance = (
            collect_database_provenance(
                conn
            )
        )
    finally:
        conn.close()

    # --------------------------------------------------------
    # Semantic classification
    # --------------------------------------------------------

    symbol_semantics = {}

    for symbol in sorted(resolved_extras):

        evidence = database_provenance.get(
            symbol,
            {
                "evidence_sources": set(),
                "row_counts": {},
            },
        )

        classification = classify_symbol(
            symbol,
            evidence["evidence_sources"],
        )

        evidence_sources = set(
            evidence["evidence_sources"]
        )

        symbol_semantics[symbol] = {
            "symbol": symbol,
            "semantic_class": classification[
                "semantic_class"
            ],
            "meaning": classification[
                "meaning"
            ],
            "artifact_likelihood": classification[
                "artifact_likelihood"
            ],
            "market_symbol_likelihood": classification[
                "market_symbol_likelihood"
            ],
            "classification_basis": classification[
                "classification_basis"
            ],
            "evidence_source_count": len(
                evidence_sources
            ),
            "evidence_sources": evidence_sources,
            "database_row_counts": evidence[
                "row_counts"
            ],
        }

    # --------------------------------------------------------
    # Print report
    # --------------------------------------------------------

    print("=" * 90)
    print("INPUT CONTRACT")
    print("=" * 90)

    print(
        f"Expected Universe : {len(expected_universe)}"
    )
    print(
        f"Resolved Extra    : {len(resolved_extras)}"
    )
    print(
        "Target Symbols    : "
        + ", ".join(
            sorted(resolved_extras)
        )
    )

    print("-" * 90)

    print("EXTRA SYMBOL RESOLUTION SOURCES")

    for candidate in alignment_candidates:

        print(
            f"ALIGNMENT -> {candidate['source']}"
        )
        print(
            "SYMBOL COUNT : "
            f"{len(candidate['symbols'])}"
        )

    for candidate in provenance_candidates:

        print(
            f"PROVENANCE -> {candidate['source']}"
        )
        print(
            "SYMBOL COUNT : "
            f"{len(candidate['symbols'])}"
        )

    print("-" * 90)

    print("=" * 90)
    print("SEMANTIC CLASSIFICATION")
    print("=" * 90)

    for symbol in sorted(resolved_extras):

        item = symbol_semantics[symbol]

        print("-" * 90)

        print(
            f"SYMBOL : {symbol}"
        )

        print(
            f"SEMANTIC CLASS : "
            f"{item['semantic_class']}"
        )

        print(
            f"MEANING : "
            f"{item['meaning']}"
        )

        print(
            f"ARTIFACT LIKELIHOOD : "
            f"{item['artifact_likelihood']}"
        )

        print(
            f"MARKET SYMBOL LIKELIHOOD : "
            f"{item['market_symbol_likelihood']}"
        )

        print(
            f"EVIDENCE SOURCE COUNT : "
            f"{item['evidence_source_count']}"
        )

        for source in sorted(
            item["evidence_sources"]
        ):
            print(
                f"  {source}"
            )

    # --------------------------------------------------------
    # Cross-symbol interpretation
    # --------------------------------------------------------

    numeric_symbols = sorted(
        [
            symbol
            for symbol in resolved_extras
            if symbol_semantics[symbol][
                "semantic_class"
            ] == "NUMERIC_IDENTIFIER_CANDIDATE"
        ]
    )

    generic_labels = sorted(
        [
            symbol
            for symbol in resolved_extras
            if symbol_semantics[symbol][
                "semantic_class"
            ] == "GENERIC_FIELD_LABEL"
        ]
    )

    unresolved_symbols = sorted(
        [
            symbol
            for symbol in resolved_extras
            if symbol_semantics[symbol][
                "semantic_class"
            ] == "UNRESOLVED_SYMBOL"
        ]
    )

    print("=" * 90)
    print("CROSS-SYMBOL SEMANTIC SUMMARY")
    print("=" * 90)

    print(
        "Numeric identifier candidates : "
        f"{len(numeric_symbols)}"
    )

    if numeric_symbols:
        print(
            "NUMERIC SYMBOLS : "
            + ", ".join(numeric_symbols)
        )

    print(
        "Generic field labels : "
        f"{len(generic_labels)}"
    )

    if generic_labels:
        print(
            "GENERIC FIELD LABELS : "
            + ", ".join(generic_labels)
        )

    print(
        "Unresolved symbols : "
        f"{len(unresolved_symbols)}"
    )

    if unresolved_symbols:
        print(
            "UNRESOLVED SYMBOLS : "
            + ", ".join(unresolved_symbols)
        )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    if (
        set(numeric_symbols) == {"4"}
        and set(generic_labels) == {"ASSET"}
        and not unresolved_symbols
    ):
        forensic_status = (
            "EXTRA_SYMBOLS_SEMANTICALLY_CLASSIFIED"
        )
    else:
        forensic_status = (
            "EXTRA_SYMBOL_SEMANTIC_CLASSIFICATION_INCOMPLETE"
        )

    print("=" * 90)
    print("FORENSIC STATUS")
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

    # --------------------------------------------------------
    # Artifact
    # --------------------------------------------------------

    artifact = {
        "artifact": {
            "name": OUTPUT_PATH.name,
            "script_version": SCRIPT_VERSION,
        },

        "database": {
            "path": str(DB_PATH),
            "mode": "READ ONLY",
        },

        "inputs": {
            "normalization": {
                "path": str(
                    NORMALIZATION_PATH
                ),
                "sha256": normalization_sha256,
            },
            "provenance": {
                "path": str(
                    PROVENANCE_PATH
                ),
                "sha256": provenance_sha256,
            },
            "alignment": {
                "path": str(
                    ALIGNMENT_PATH
                ),
                "sha256": alignment_sha256,
            },
        },

        "expected_universe": {
            "source": (
                "normalization."
                "normalized_expected_universe"
            ),
            "count": len(
                expected_universe
            ),
        },

        "extra_symbol_resolution": {
            "target_symbols": resolved_extras,

            "alignment_sources": [
                {
                    "source": candidate["source"],
                    "symbols": candidate["symbols"],
                }
                for candidate in alignment_candidates
            ],

            "provenance_sources": [
                {
                    "source": candidate["source"],
                    "symbols": candidate["symbols"],
                }
                for candidate in provenance_candidates
            ],

            "resolved_symbol_count": len(
                resolved_extras
            ),
        },

        "semantic_classification": {
            "symbols": symbol_semantics,

            "numeric_identifier_candidates":
                numeric_symbols,

            "generic_field_labels":
                generic_labels,

            "unresolved_symbols":
                unresolved_symbols,
        },

        "database_provenance": {
            symbol: database_provenance.get(
                symbol,
                {
                    "evidence_sources": set(),
                    "row_counts": {},
                },
            )
            for symbol in sorted(
                resolved_extras
            )
        },

        "forensic_constraints": {
            "mode": "READ ONLY",
            "network": "FORBIDDEN",
            "database_write": "FORBIDDEN",
            "database_repair": "FORBIDDEN",
            "universe_rebuild": "FORBIDDEN",
            "symbol_deletion": "FORBIDDEN",
            "prediction": "FORBIDDEN",
            "decision": "FORBIDDEN",
        },

        "forensic_status": forensic_status,

        "predictive_claim":
            "NOT ESTABLISHED",

        "relationship_calculation":
            "NOT PERFORMED",

        "database_write":
            "NOT PERFORMED",

        "database_repair":
            "NOT PERFORMED",

        "generated_at_utc":
            utc_now(),
    }

    # --------------------------------------------------------
    # CRITICAL FIX
    # --------------------------------------------------------
    # Convert all sets recursively before json.dumps.
    # This is the fix for:
    #
    # TypeError:
    # Object of type set is not JSON serializable
    # --------------------------------------------------------

    artifact = recursive_json_safe(
        artifact
    )

    # --------------------------------------------------------
    # Calculate artifact SHA256
    # --------------------------------------------------------

    canonical = canonical_json_bytes(
        artifact
    )

    artifact_sha256 = sha256_bytes(
        canonical
    )

    artifact["artifact_sha256"] = (
        artifact_sha256
    )

    # Final safety conversion
    artifact = recursive_json_safe(
        artifact
    )

    # --------------------------------------------------------
    # Write ONLY forensic artifact.
    #
    # This is not a database write.
    # Database remains untouched.
    # --------------------------------------------------------

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:

        json.dump(
            artifact,
            f,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        f.write("\n")

    # --------------------------------------------------------
    # Final fingerprint
    # --------------------------------------------------------

    final_sha256 = sha256_file(
        OUTPUT_PATH
    )

    print("=" * 90)
    print("ARTIFACT")
    print("=" * 90)

    print(
        f"Artifact : {OUTPUT_PATH}"
    )

    print(
        f"SHA256   : {final_sha256}"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()