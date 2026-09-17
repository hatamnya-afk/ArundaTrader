# ARUNDA_LIVE_DATA_BOUNDARY_LAUNCH_READINESS_FORENSIC_v0.1.py

import ast
import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# ============================================================================
# CONFIG
# ============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"

ARTIFACT_JSON = PROJECT_ROOT / (
    "ARUNDA_LIVE_DATA_BOUNDARY_LAUNCH_READINESS_FORENSIC_v0.1.json"
)

ARTIFACT_TXT = PROJECT_ROOT / (
    "ARUNDA_LIVE_DATA_BOUNDARY_LAUNCH_READINESS_FORENSIC_v0.1.txt"
)

VERSION = "ARUNDA_LIVE_DATA_BOUNDARY_LAUNCH_READINESS_FORENSIC_v0.1"

# ============================================================================
# SAFETY CONTRACT
# ============================================================================

READ_ONLY = True
NETWORK_EXECUTION = False
DATABASE_WRITE = False
DATABASE_DELETE = False
DATABASE_UPDATE = False
DATABASE_INSERT = False
PRODUCTION_EXECUTION = False
PREDICTION = False
TRADING_DECISION = False


# ============================================================================
# KEYWORDS
# ============================================================================

NETWORK_KEYWORDS = {
    "requests",
    "httpx",
    "aiohttp",
    "urllib",
    "urllib3",
    "websocket",
    "websockets",
    "socket",
    "ccxt",
    "http",
    "https",
}

DB_WRITE_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE TABLE",
    "DROP TABLE",
    "REPLACE INTO",
}

SYNTHETIC_KEYWORDS = {
    "synthetic",
    "mock",
    "dummy",
    "fake",
    "random",
    "simulate",
    "simulation",
    "fixture",
    "fallback",
    "placeholder",
    "generated",
    "interpolate",
    "interpolation",
    "backfill",
    "forward_fill",
    "bfill",
    "ffill",
}

LIVE_KEYWORDS = {
    "live",
    "production",
    "ingest",
    "ingestion",
    "fetch",
    "fetcher",
    "collector",
    "provider",
    "exchange",
    "market_data",
    "market_history",
    "market_universe",
    "snapshot",
    "feature",
}

EXECUTION_KEYWORDS = {
    "order",
    "execution",
    "execute",
    "order_intent",
    "execution_gate",
    "preflight",
    "validation",
    "signal",
}


# ============================================================================
# HELPERS
# ============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def normalize_text(text):
    return " ".join(text.lower().split())


def safe_read(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        return ""


def get_python_files():
    files = []

    for path in PROJECT_ROOT.rglob("*.py"):

        if any(
            part in {
                ".git",
                "__pycache__",
                ".venv",
                "venv",
                "env",
            }
            for part in path.parts
        ):
            continue

        files.append(path)

    return sorted(files)


def get_db_tables():
    if not DB_PATH.exists():
        return {
            "exists": False,
            "tables": [],
            "count": 0,
            "error": "DATABASE_NOT_FOUND",
        }

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True
    )

    try:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        tables = [row[0] for row in rows]

        return {
            "exists": True,
            "tables": tables,
            "count": len(tables),
            "error": None,
        }

    except Exception as exc:

        return {
            "exists": True,
            "tables": [],
            "count": 0,
            "error": str(exc),
        }

    finally:
        conn.close()


# ============================================================================
# AST ANALYSIS
# ============================================================================

class SourceAnalyzer(ast.NodeVisitor):

    def __init__(self):
        self.functions = []
        self.imports = []
        self.calls = []
        self.db_writes = []
        self.network_calls = []
        self.execution_refs = []
        self.live_refs = []
        self.synthetic_refs = []

        self.current_function = None

    def visit_FunctionDef(self, node):

        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
        })

        previous = self.current_function
        self.current_function = node.name

        self.generic_visit(node)

        self.current_function = previous

    def visit_AsyncFunctionDef(self, node):

        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "async": True,
        })

        previous = self.current_function
        self.current_function = node.name

        self.generic_visit(node)

        self.current_function = previous

    def visit_Import(self, node):

        for alias in node.names:
            self.imports.append({
                "name": alias.name,
                "line": node.lineno,
            })

        self.generic_visit(node)

    def visit_ImportFrom(self, node):

        module = node.module or ""

        self.imports.append({
            "name": module,
            "line": node.lineno,
        })

        self.generic_visit(node)

    def visit_Call(self, node):

        name = self.get_call_name(node)

        if name:

            lowered = name.lower()

            self.calls.append({
                "name": name,
                "line": node.lineno,
                "function": self.current_function,
            })

            db_terms = (
                "execute",
                "executemany",
                "executescript",
                "cursor",
                "commit",
            )

            if any(term in lowered for term in db_terms):

                self.db_writes.append({
                    "call": name,
                    "line": node.lineno,
                    "function": self.current_function,
                })

            network_terms = (
                "requests.",
                "httpx.",
                "aiohttp.",
                "urllib.",
                "websocket",
                "socket.",
                "ccxt.",
            )

            if any(term in lowered for term in network_terms):

                self.network_calls.append({
                    "call": name,
                    "line": node.lineno,
                    "function": self.current_function,
                })

            if any(
                term in lowered
                for term in EXECUTION_KEYWORDS
            ):
                self.execution_refs.append({
                    "call": name,
                    "line": node.lineno,
                    "function": self.current_function,
                })

            if any(
                term in lowered
                for term in LIVE_KEYWORDS
            ):
                self.live_refs.append({
                    "call": name,
                    "line": node.lineno,
                    "function": self.current_function,
                })

        self.generic_visit(node)

    def get_call_name(self, node):

        func = node.func

        if isinstance(func, ast.Name):
            return func.id

        if isinstance(func, ast.Attribute):

            parts = []

            current = func

            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value

            if isinstance(current, ast.Name):
                parts.append(current.id)

            return ".".join(reversed(parts))

        return None


# ============================================================================
# TEXT LEVEL ANALYSIS
# ============================================================================

def keyword_hits(text, keywords):

    lowered = text.lower()

    found = []

    for keyword in sorted(keywords):

        if keyword.lower() in lowered:
            found.append(keyword)

    return found


def analyze_file(path):

    text = safe_read(path)

    result = {
        "path": str(path),
        "relative_path": str(path.relative_to(PROJECT_ROOT)),
        "size_bytes": len(text.encode("utf-8")),
        "sha256": sha256_file(path),

        "ast_parse_ok": False,
        "syntax_error": None,

        "functions": [],
        "imports": [],
        "calls": [],

        "network": {
            "keyword_hits": [],
            "calls": [],
        },

        "database": {
            "write_keyword_hits": [],
            "write_calls": [],
        },

        "synthetic": {
            "keyword_hits": [],
        },

        "live": {
            "keyword_hits": [],
            "references": [],
        },

        "execution": {
            "keyword_hits": [],
            "references": [],
        },

        "main_present": False,
    }

    # ------------------------------------------------------------------------
    # AST
    # ------------------------------------------------------------------------

    try:

        tree = ast.parse(text)

        analyzer = SourceAnalyzer()
        analyzer.visit(tree)

        result["ast_parse_ok"] = True

        result["functions"] = analyzer.functions
        result["imports"] = analyzer.imports
        result["calls"] = analyzer.calls

        result["network"]["calls"] = analyzer.network_calls
        result["database"]["write_calls"] = analyzer.db_writes

        result["live"]["references"] = analyzer.live_refs
        result["execution"]["references"] = analyzer.execution_refs

        result["main_present"] = any(
            f["name"] == "main"
            for f in analyzer.functions
        )

    except SyntaxError as exc:

        result["syntax_error"] = {
            "line": exc.lineno,
            "offset": exc.offset,
            "message": exc.msg,
        }

    except Exception as exc:

        result["syntax_error"] = {
            "line": None,
            "offset": None,
            "message": str(exc),
        }

    # ------------------------------------------------------------------------
    # TEXT
    # ------------------------------------------------------------------------

    result["network"]["keyword_hits"] = keyword_hits(
        text,
        NETWORK_KEYWORDS
    )

    result["database"]["write_keyword_hits"] = keyword_hits(
        text,
        DB_WRITE_KEYWORDS
    )

    result["synthetic"]["keyword_hits"] = keyword_hits(
        text,
        SYNTHETIC_KEYWORDS
    )

    result["live"]["keyword_hits"] = keyword_hits(
        text,
        LIVE_KEYWORDS
    )

    result["execution"]["keyword_hits"] = keyword_hits(
        text,
        EXECUTION_KEYWORDS
    )

    return result


# ============================================================================
# CLASSIFICATION
# ============================================================================

def classify_file(result):

    network = (
        bool(result["network"]["keyword_hits"])
        or bool(result["network"]["calls"])
    )

    db_write = (
        bool(result["database"]["write_keyword_hits"])
        or bool(result["database"]["write_calls"])
    )

    synthetic = bool(
        result["synthetic"]["keyword_hits"]
    )

    live = (
        bool(result["live"]["keyword_hits"])
        or bool(result["live"]["references"])
    )

    execution = (
        bool(result["execution"]["keyword_hits"])
        or bool(result["execution"]["references"])
    )

    if not result["ast_parse_ok"]:
        classification = "SYNTAX_PARSE_FAILURE"

    elif db_write:
        classification = "DB_WRITE_CAPABLE_SOURCE"

    elif network and live:
        classification = "LIVE_DATA_BOUNDARY_CANDIDATE"

    elif execution:
        classification = "EXECUTION_BOUNDARY_REFERENCE"

    elif synthetic:
        classification = "SYNTHETIC_OR_FALLBACK_REFERENCE"

    elif live:
        classification = "LIVE_PIPELINE_REFERENCE"

    else:
        classification = "NON_BOUNDARY_SOURCE"

    return classification


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 90)
    print(VERSION)
    print("=" * 90)

    print(f"Project Root   : {PROJECT_ROOT}")
    print(f"Database       : {DB_PATH}")
    print("Mode           : STATIC / READ ONLY")
    print("Network        : FORBIDDEN")
    print("Production Run : FORBIDDEN")
    print("Database Write : FORBIDDEN")
    print("Delete         : FORBIDDEN")
    print("Prediction     : FORBIDDEN")
    print("Decision       : FORBIDDEN")
    print("-" * 90)

    if not PROJECT_ROOT.exists():
        raise FileNotFoundError(
            f"Project root not found: {PROJECT_ROOT}"
        )

    python_files = get_python_files()

    db_inventory = get_db_tables()

    print()
    print("=" * 90)
    print("PROJECT INVENTORY")
    print("=" * 90)

    print(f"Python Files : {len(python_files)}")
    print(f"DB Exists    : {db_inventory['exists']}")
    print(f"DB Tables    : {db_inventory['count']}")

    results = []

    for path in python_files:

        result = analyze_file(path)

        result["classification"] = classify_file(result)

        results.append(result)

    # ------------------------------------------------------------------------
    # Aggregate
    # ------------------------------------------------------------------------

    syntax_failures = [
        r for r in results
        if r["classification"] == "SYNTAX_PARSE_FAILURE"
    ]

    live_boundary = [
        r for r in results
        if r["classification"]
        == "LIVE_DATA_BOUNDARY_CANDIDATE"
    ]

    db_write_sources = [
        r for r in results
        if r["classification"]
        == "DB_WRITE_CAPABLE_SOURCE"
    ]

    execution_sources = [
        r for r in results
        if r["classification"]
        == "EXECUTION_BOUNDARY_REFERENCE"
    ]

    synthetic_sources = [
        r for r in results
        if r["classification"]
        == "SYNTHETIC_OR_FALLBACK_REFERENCE"
    ]

    live_sources = [
        r for r in results
        if r["classification"]
        == "LIVE_PIPELINE_REFERENCE"
    ]

    network_files = [
        r for r in results
        if r["network"]["keyword_hits"]
        or r["network"]["calls"]
    ]

    # ------------------------------------------------------------------------
    # Print boundary candidates
    # ------------------------------------------------------------------------

    print()
    print("=" * 90)
    print("LIVE DATA BOUNDARY CANDIDATES")
    print("=" * 90)

    if not live_boundary:
        print("NONE FOUND")

    for result in live_boundary:

        print("-" * 90)
        print(
            f"FILE           : "
            f"{result['relative_path']}"
        )

        print(
            f"NETWORK HITS   : "
            f"{', '.join(result['network']['keyword_hits']) or 'None'}"
        )

        print(
            f"NETWORK CALLS  : "
            f"{len(result['network']['calls'])}"
        )

        print(
            f"LIVE REFERENCES: "
            f"{len(result['live']['references'])}"
        )

        print(
            f"SHA256         : "
            f"{result['sha256']}"
        )

    # ------------------------------------------------------------------------
    # DB writes
    # ------------------------------------------------------------------------

    print()
    print("=" * 90)
    print("DATABASE WRITE CAPABLE SOURCES")
    print("=" * 90)

    if not db_write_sources:
        print("NONE FOUND")

    for result in db_write_sources:

        print("-" * 90)
        print(
            f"FILE          : "
            f"{result['relative_path']}"
        )

        print(
            f"WRITE KEYWORDS: "
            f"{', '.join(result['database']['write_keyword_hits'])}"
        )

        print(
            f"DB CALLS      : "
            f"{len(result['database']['write_calls'])}"
        )

    # ------------------------------------------------------------------------
    # Synthetic/fallback
    # ------------------------------------------------------------------------

    print()
    print("=" * 90)
    print("SYNTHETIC / FALLBACK REFERENCES")
    print("=" * 90)

    if not synthetic_sources:
        print("NONE FOUND")

    for result in synthetic_sources:

        print("-" * 90)

        print(
            f"FILE    : "
            f"{result['relative_path']}"
        )

        print(
            f"KEYWORDS: "
            f"{', '.join(result['synthetic']['keyword_hits'])}"
        )

    # ------------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------------

    print()
    print("=" * 90)
    print("EXECUTION BOUNDARY REFERENCES")
    print("=" * 90)

    if not execution_sources:
        print("NONE FOUND")

    for result in execution_sources:

        print("-" * 90)

        print(
            f"FILE: "
            f"{result['relative_path']}"
        )

        print(
            f"REFERENCES: "
            f"{len(result['execution']['references'])}"
        )

    # ------------------------------------------------------------------------
    # Syntax
    # ------------------------------------------------------------------------

    print()
    print("=" * 90)
    print("SYNTAX STATUS")
    print("=" * 90)

    print(
        f"Python Files : {len(results)}"
    )

    print(
        f"Parse Passed : "
        f"{len(results) - len(syntax_failures)}"
    )

    print(
        f"Parse Failed : "
        f"{len(syntax_failures)}"
    )

    for result in syntax_failures:

        print("-" * 90)

        print(
            f"FILE : "
            f"{result['relative_path']}"
        )

        print(
            f"ERROR: "
            f"{result['syntax_error']}"
        )

    # ------------------------------------------------------------------------
    # DB
    # ------------------------------------------------------------------------

    print()
    print("=" * 90)
    print("DATABASE READ-ONLY INVENTORY")
    print("=" * 90)

    print(
        f"Tables : "
        f"{', '.join(db_inventory['tables'])}"
    )

    # ------------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------------

    blockers = []

    if syntax_failures:
        blockers.append("PYTHON_SYNTAX_FAILURES")

    if not live_boundary:
        blockers.append("LIVE_DATA_BOUNDARY_NOT_IDENTIFIED")

    status = (
        "LAUNCH_BOUNDARY_STATIC_MAP_ESTABLISHED"
        if not blockers
        else "LAUNCH_READINESS_BLOCKERS_IDENTIFIED"
    )

    # ------------------------------------------------------------------------
    # Artifact
    # ------------------------------------------------------------------------

    artifact = {
        "version": VERSION,
        "generated_at_utc": utc_now(),

        "safety": {
            "read_only": READ_ONLY,
            "network_execution": NETWORK_EXECUTION,
            "database_write": DATABASE_WRITE,
            "database_delete": DATABASE_DELETE,
            "database_update": DATABASE_UPDATE,
            "database_insert": DATABASE_INSERT,
            "production_execution": PRODUCTION_EXECUTION,
            "prediction": PREDICTION,
            "trading_decision": TRADING_DECISION,
        },

        "project": {
            "root": str(PROJECT_ROOT),
            "python_file_count": len(results),
        },

        "database": db_inventory,

        "summary": {
            "python_files": len(results),
            "syntax_failures": len(syntax_failures),
            "live_boundary_candidates": len(live_boundary),
            "network_files": len(network_files),
            "db_write_sources": len(db_write_sources),
            "synthetic_sources": len(synthetic_sources),
            "live_sources": len(live_sources),
            "execution_sources": len(execution_sources),
        },

        "launch_status": {
            "status": status,
            "blockers": blockers,
            "network_tested": False,
            "production_executed": False,
            "database_modified": False,
            "prediction_performed": False,
            "trading_decision_performed": False,
        },

        "boundary_candidates": [
            {
                "relative_path": r["relative_path"],
                "classification": r["classification"],
                "network_keyword_hits": r["network"]["keyword_hits"],
                "network_calls": r["network"]["calls"],
                "live_keyword_hits": r["live"]["keyword_hits"],
                "live_references": r["live"]["references"],
                "sha256": r["sha256"],
            }
            for r in live_boundary
        ],

        "db_write_sources": [
            {
                "relative_path": r["relative_path"],
                "write_keyword_hits": r["database"]["write_keyword_hits"],
                "write_calls": r["database"]["write_calls"],
                "sha256": r["sha256"],
            }
            for r in db_write_sources
        ],

        "synthetic_sources": [
            {
                "relative_path": r["relative_path"],
                "keywords": r["synthetic"]["keyword_hits"],
                "sha256": r["sha256"],
            }
            for r in synthetic_sources
        ],

        "execution_sources": [
            {
                "relative_path": r["relative_path"],
                "keyword_hits": r["execution"]["keyword_hits"],
                "references": r["execution"]["references"],
                "sha256": r["sha256"],
            }
            for r in execution_sources
        ],

        "syntax_failures": [
            {
                "relative_path": r["relative_path"],
                "error": r["syntax_error"],
            }
            for r in syntax_failures
        ],

        "files": results,
    }

    with open(
        ARTIFACT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            artifact,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ------------------------------------------------------------------------
    # Text report
    # ------------------------------------------------------------------------

    lines = []

    lines.append("=" * 90)
    lines.append(VERSION)
    lines.append("=" * 90)

    lines.append(
        f"Generated UTC : {artifact['generated_at_utc']}"
    )

    lines.append(
        f"Project Root  : {PROJECT_ROOT}"
    )

    lines.append(
        "Mode          : STATIC / READ ONLY"
    )

    lines.append(
        "Network       : FORBIDDEN"
    )

    lines.append(
        "Production Run: FORBIDDEN"
    )

    lines.append(
        "Database Write: FORBIDDEN"
    )

    lines.append("")

    lines.append("=" * 90)
    lines.append("SUMMARY")
    lines.append("=" * 90)

    lines.append(
        f"Python Files              : {len(results)}"
    )

    lines.append(
        f"Syntax Failures           : {len(syntax_failures)}"
    )

    lines.append(
        f"Live Boundary Candidates  : {len(live_boundary)}"
    )

    lines.append(
        f"Network Files             : {len(network_files)}"
    )

    lines.append(
        f"DB Write Sources          : {len(db_write_sources)}"
    )

    lines.append(
        f"Synthetic/Fallback Files  : {len(synthetic_sources)}"
    )

    lines.append(
        f"Execution References      : {len(execution_sources)}"
    )

    lines.append("")

    lines.append("=" * 90)
    lines.append("LAUNCH STATUS")
    lines.append("=" * 90)

    lines.append(
        f"STATUS   : {status}"
    )

    lines.append(
        f"BLOCKERS : "
        f"{', '.join(blockers) if blockers else 'NONE'}"
    )

    lines.append("")

    lines.append("=" * 90)
    lines.append("SAFETY STATUS")
    lines.append("=" * 90)

    lines.append("NETWORK TEST        : NOT PERFORMED")
    lines.append("PRODUCTION EXECUTION: NOT PERFORMED")
    lines.append("DATABASE WRITE      : NOT PERFORMED")
    lines.append("DATABASE DELETE     : NOT PERFORMED")
    lines.append("DATABASE REPAIR     : NOT PERFORMED")
    lines.append("PREDICTION          : NOT PERFORMED")
    lines.append("TRADING DECISION    : NOT PERFORMED")

    lines.append("")

    lines.append("=" * 90)
    lines.append("ARTIFACT")
    lines.append("=" * 90)

    lines.append(
        f"Artifact : {ARTIFACT_JSON}"
    )

    with open(
        ARTIFACT_TXT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("\n".join(lines))

    artifact_hash = sha256_file(
        ARTIFACT_JSON
    )

    print()
    print("=" * 90)
    print("FORENSIC STATUS")
    print("=" * 90)

    print(
        f"FORENSIC STATUS : {status}"
    )

    print(
        f"BLOCKERS        : "
        f"{', '.join(blockers) if blockers else 'NONE'}"
    )

    print(
        "DATABASE WRITE  : NOT PERFORMED"
    )

    print(
        "NETWORK         : NOT USED"
    )

    print(
        "PRODUCTION RUN  : NOT PERFORMED"
    )

    print()
    print("=" * 90)
    print("ARTIFACT")
    print("=" * 90)

    print(
        f"Artifact : {ARTIFACT_JSON}"
    )

    print(
        f"Report   : {ARTIFACT_TXT}"
    )

    print(
        f"SHA256   : {artifact_hash}"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()