from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_INFORMATION_ARMS_RUNTIME_BOUNDARY_TRACE_REPORT.json"
)

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "_backups",
}

ARM_KEYWORDS = {
    "news": [
        "news",
        "headline",
        "breaking",
        "newsapi",
        "news_api",
        "rss",
        "feed",
        "article",
        "market_news",
        "news_intelligence",
    ],
    "technical": [
        "technical",
        "technical_analysis",
        "indicator",
        "rsi",
        "macd",
        "ema",
        "sma",
        "bollinger",
        "atr",
        "adx",
    ],
    "social": [
        "social",
        "sentiment",
        "lunarcrush",
        "lunar_crush",
        "social_volume",
        "social_score",
        "engagement",
    ],
    "market": [
        "market",
        "market_data",
        "market_records",
        "orderbook",
        "order_book",
        "ticker",
        "ohlcv",
        "price",
        "volume",
    ],
    "tradingview": [
        "tradingview",
        "trading_view",
    ],
    "fusion": [
        "fusion",
        "fusion_signal",
        "fusion_signals",
    ],
}

RUNTIME_FUNCTION_NAMES = {
    "main",
    "run",
    "start",
    "execute",
    "process",
    "process_signals",
    "generate",
    "generate_signal",
    "build_signal",
    "analyze",
    "analyze_market",
    "fetch",
    "fetch_data",
    "collect",
    "collect_data",
    "load",
    "load_data",
    "update",
    "update_market",
}

DATA_ACCESS_KEYWORDS = {
    "sqlite3",
    "connect(",
    "SELECT ",
    "INSERT ",
    "UPDATE ",
    "requests.",
    "httpx.",
    "urllib",
    "websocket",
    "ccxt",
    "bitpin",
    "api.",
    "fetch(",
    "get(",
    "post(",
}

NETWORK_KEYWORDS = {
    "requests",
    "httpx",
    "urllib",
    "aiohttp",
    "websocket",
    "socket",
    "ccxt",
    "api.bitpin",
    "lunarcrush",
    "tradingview",
    "newsapi",
}

DB_KEYWORDS = {
    "sqlite3",
    "sqlite",
    "arunda.db",
    "market_data",
    "market_records",
    "market_history",
    "fusion_signals",
}


def safe_read(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def syntax_check(source: str) -> tuple[bool, str | None]:
    try:
        ast.parse(source)
        return True, None
    except SyntaxError as exc:
        return False, (
            f"{exc.msg} "
            f"(line={exc.lineno}, column={exc.offset})"
        )


def parse_tree(source: str) -> ast.AST | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def extract_functions(tree: ast.AST | None) -> list[str]:
    if tree is None:
        return []

    functions: list[str] = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            functions.append(node.name)

    return sorted(set(functions))


def extract_imports(tree: ast.AST | None) -> list[str]:
    if tree is None:
        return []

    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return sorted(set(imports))


def extract_call_names(tree: ast.AST | None) -> list[str]:
    if tree is None:
        return []

    calls: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        if isinstance(func, ast.Name):
            calls.append(func.id)

        elif isinstance(func, ast.Attribute):
            calls.append(func.attr)

    return sorted(set(calls))


def extract_string_literals(tree: ast.AST | None) -> list[str]:
    if tree is None:
        return []

    values: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                values.append(node.value)

    return values


def find_main_execution(tree: ast.AST | None) -> bool:
    if tree is None:
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue

        test = node.test

        if not isinstance(test, ast.Compare):
            continue

        if not isinstance(test.left, ast.Name):
            continue

        if test.left.id != "__name__":
            continue

        for comparator in test.comparators:
            if (
                isinstance(comparator, ast.Constant)
                and comparator.value == "__main__"
            ):
                return True

    return False


def keyword_matches(
    source: str,
    keywords: list[str],
) -> list[str]:
    lowered = source.lower()

    return sorted(
        {
            keyword
            for keyword in keywords
            if keyword.lower() in lowered
        }
    )


def detect_network_usage(
    source: str,
    imports: list[str],
) -> list[str]:
    matches: set[str] = set()

    lowered = source.lower()

    for keyword in NETWORK_KEYWORDS:
        if keyword.lower() in lowered:
            matches.add(keyword)

    for imported in imports:
        lowered_import = imported.lower()

        for keyword in NETWORK_KEYWORDS:
            if keyword.lower() in lowered_import:
                matches.add(keyword)

    return sorted(matches)


def detect_database_usage(
    source: str,
    imports: list[str],
) -> list[str]:
    matches: set[str] = set()

    lowered = source.lower()

    for keyword in DB_KEYWORDS:
        if keyword.lower() in lowered:
            matches.add(keyword)

    for imported in imports:
        lowered_import = imported.lower()

        for keyword in DB_KEYWORDS:
            if keyword.lower() in lowered_import:
                matches.add(keyword)

    return sorted(matches)


def detect_data_access(
    source: str,
) -> list[str]:
    lowered = source.lower()

    return sorted(
        {
            keyword
            for keyword in DATA_ACCESS_KEYWORDS
            if keyword.lower() in lowered
        }
    )


def extract_runtime_boundaries(
    functions: list[str],
    calls: list[str],
) -> list[str]:
    boundaries = set()

    for name in functions:
        if name in RUNTIME_FUNCTION_NAMES:
            boundaries.add(f"function:{name}")

    for name in calls:
        if name in RUNTIME_FUNCTION_NAMES:
            boundaries.add(f"call:{name}")

    return sorted(boundaries)


def infer_arm_roles(
    source: str,
    matched_arms: dict[str, list[str]],
) -> list[str]:
    roles: set[str] = set()

    lowered = source.lower()

    if "fetch" in lowered:
        roles.add("data_fetch")

    if "request" in lowered or "httpx" in lowered:
        roles.add("external_source")

    if "select " in lowered:
        roles.add("database_read")

    if "insert " in lowered:
        roles.add("database_insert_reference")

    if "update " in lowered:
        roles.add("database_update_reference")

    if "calculate" in lowered:
        roles.add("calculation")

    if "indicator" in lowered:
        roles.add("indicator_calculation")

    if "sentiment" in lowered:
        roles.add("sentiment_processing")

    if "fusion" in lowered:
        roles.add("signal_fusion")

    if "signal" in lowered:
        roles.add("signal_processing")

    if matched_arms:
        roles.add("information_arm_candidate")

    return sorted(roles)


def inspect_file(path: Path) -> dict[str, Any]:
    source = safe_read(path)

    tree = parse_tree(source)

    syntax_valid, syntax_error = syntax_check(source)

    functions = extract_functions(tree)
    imports = extract_imports(tree)
    calls = extract_call_names(tree)

    matched_arms: dict[str, list[str]] = {}

    for arm, keywords in ARM_KEYWORDS.items():
        matches = keyword_matches(
            source,
            keywords,
        )

        if matches:
            matched_arms[arm] = matches

    runtime_boundaries = extract_runtime_boundaries(
        functions,
        calls,
    )

    network_usage = detect_network_usage(
        source,
        imports,
    )

    database_usage = detect_database_usage(
        source,
        imports,
    )

    data_access = detect_data_access(
        source,
    )

    roles = infer_arm_roles(
        source,
        matched_arms,
    )

    return {
        "file": relative_path(path),
        "size_bytes": path.stat().st_size,
        "syntax_valid": syntax_valid,
        "syntax_error": syntax_error,
        "matched_arms": matched_arms,
        "functions": functions,
        "imports": imports,
        "calls": calls,
        "runtime_boundaries": runtime_boundaries,
        "network_usage": network_usage,
        "database_usage": database_usage,
        "data_access": data_access,
        "roles": roles,
        "main_execution": find_main_execution(tree),
    }


def discover_files() -> list[Path]:
    files: list[Path] = []

    for path in PROJECT_ROOT.rglob("*.py"):
        if any(
            part in EXCLUDED_DIRS
            for part in path.parts
        ):
            continue

        if path.name == Path(__file__).name:
            continue

        files.append(path)

    return sorted(files)


def build_arm_candidates(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:

    result: dict[str, list[dict[str, Any]]] = {
        arm: []
        for arm in ARM_KEYWORDS
    }

    for record in records:
        for arm in record["matched_arms"]:
            result[arm].append(
                {
                    "file": record["file"],
                    "matched_keywords": record[
                        "matched_arms"
                    ][arm],
                    "runtime_boundaries": record[
                        "runtime_boundaries"
                    ],
                    "main_execution": record[
                        "main_execution"
                    ],
                    "syntax_valid": record[
                        "syntax_valid"
                    ],
                    "network_usage": record[
                        "network_usage"
                    ],
                    "database_usage": record[
                        "database_usage"
                    ],
                    "data_access": record[
                        "data_access"
                    ],
                    "roles": record[
                        "roles"
                    ],
                }
            )

    return result


def rank_candidate(
    candidate: dict[str, Any],
) -> int:
    score = 0

    if candidate["syntax_valid"]:
        score += 10

    if candidate["runtime_boundaries"]:
        score += 10

    if candidate["main_execution"]:
        score += 5

    if candidate["network_usage"]:
        score += 5

    if candidate["database_usage"]:
        score += 5

    if candidate["data_access"]:
        score += 5

    return score


def select_runtime_candidates(
    candidates: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:

    selected: dict[str, list[dict[str, Any]]] = {}

    for arm, records in candidates.items():
        ranked = sorted(
            records,
            key=lambda record: (
                rank_candidate(record),
                record["file"],
            ),
            reverse=True,
        )

        selected[arm] = ranked[:10]

    return selected


def classify_boundary_status(
    records: list[dict[str, Any]],
) -> str:

    if not records:
        return "NO_RUNTIME_BOUNDARY_FOUND"

    valid = [
        record
        for record in records
        if record["syntax_valid"]
    ]

    if not valid:
        return "BOUNDARY_CANDIDATES_SYNTAX_INVALID"

    runtime = [
        record
        for record in valid
        if record["runtime_boundaries"]
    ]

    if not runtime:
        return "SOURCE_FOUND_RUNTIME_BOUNDARY_UNPROVEN"

    network = [
        record
        for record in runtime
        if record["network_usage"]
    ]

    database = [
        record
        for record in runtime
        if record["database_usage"]
    ]

    if network:
        return "RUNTIME_BOUNDARY_FOUND_NETWORK_DEPENDENCY_PRESENT"

    if database:
        return "RUNTIME_BOUNDARY_FOUND_DATABASE_DEPENDENCY_PRESENT"

    return "RUNTIME_BOUNDARY_FOUND_READ_ONLY_TRACEABLE"


def build_report(
    records: list[dict[str, Any]],
) -> dict[str, Any]:

    candidates = build_arm_candidates(
        records
    )

    selected = select_runtime_candidates(
        candidates
    )

    statuses = {
        arm: classify_boundary_status(
            selected[arm]
        )
        for arm in ARM_KEYWORDS
    }

    return {
        "project": "ArundaTrader",
        "component": (
            "LIVE_INFORMATION_ARMS_RUNTIME_BOUNDARY_TRACE"
        ),
        "version": "v0.1",
        "mode": "READ_ONLY",

        "safety": {
            "database_write": False,
            "network_access": False,
            "producer_execution": False,
            "signal_creation": False,
            "signal_injection": False,
            "replay_execution": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
            "artifact_mutation": False,
        },

        "discovery": {
            "python_files_scanned": len(records),
            "backups_excluded": True,
            "syntax_invalid_files": sum(
                1
                for record in records
                if not record["syntax_valid"]
            ),
        },

        "arm_status": statuses,

        "runtime_boundaries": {
            arm: {
                "status": statuses[arm],
                "candidate_count": len(
                    candidates[arm]
                ),
                "selected_candidates": selected[arm],
            }
            for arm in ARM_KEYWORDS
        },

        "important_trace_rule": (
            "Candidate discovery does not constitute runtime "
            "verification. No producer, network source, exchange, "
            "signal creation, replay, or order execution was run."
        ),

        "final_verdict": {
            "status": (
                "BOUNDARIES_IDENTIFIED_RUNTIME_NOT_EXECUTED"
            ),
            "verified": False,
            "reason": (
                "Actual source/runtime boundaries have been "
                "identified from project code only. "
                "Live runtime execution has intentionally not "
                "been performed on this frontier."
            ),
        },

        "next_stage": {
            "status": (
                "SELECT_EXACT_RUNTIME_ENTRYPOINT_PER_ARM"
            ),
            "requires_network": False,
            "requires_producer_execution": False,
        },
    }


def print_section(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_report(
    report: dict[str, Any],
) -> None:

    print_section(
        "ARUNDA TRADER\n"
        "LIVE INFORMATION ARMS RUNTIME BOUNDARY TRACE v0.1"
    )

    print(
        f"PROJECT ROOT : "
        f"{PROJECT_ROOT}"
    )

    print(
        "MODE         : "
        "READ_ONLY"
    )

    print_section("SAFETY")

    for key, value in report["safety"].items():
        print(
            f"{key:24}: {value}"
        )

    print_section("DISCOVERY")

    print(
        "Python files scanned : "
        f"{report['discovery']['python_files_scanned']}"
    )

    print(
        "Backups excluded     : "
        f"{report['discovery']['backups_excluded']}"
    )

    print(
        "Syntax-invalid files : "
        f"{report['discovery']['syntax_invalid_files']}"
    )

    print_section("ARM RUNTIME BOUNDARIES")

    for arm, data in report[
        "runtime_boundaries"
    ].items():

        print()
        print(
            f"[{arm.upper()}]"
        )

        print(
            f"STATUS          : "
            f"{data['status']}"
        )

        print(
            f"CANDIDATES      : "
            f"{data['candidate_count']}"
        )

        for candidate in data[
            "selected_candidates"
        ][:5]:

            print(
                f"  FILE          : "
                f"{candidate['file']}"
            )

            print(
                f"  KEYWORDS      : "
                f"{', '.join(candidate['matched_keywords'])}"
            )

            print(
                f"  RUNTIME       : "
                f"{', '.join(candidate['runtime_boundaries']) or 'NONE'}"
            )

            print(
                f"  MAIN          : "
                f"{candidate['main_execution']}"
            )

            print(
                f"  NETWORK       : "
                f"{', '.join(candidate['network_usage']) or 'NONE'}"
            )

            print(
                f"  DATABASE      : "
                f"{', '.join(candidate['database_usage']) or 'NONE'}"
            )

            print(
                f"  DATA ACCESS   : "
                f"{', '.join(candidate['data_access']) or 'NONE'}"
            )

    print_section("FINAL VERDICT")

    print(
        "STATUS   : "
        f"{report['final_verdict']['status']}"
    )

    print(
        "VERIFIED : "
        f"{report['final_verdict']['verified']}"
    )

    print(
        "NEXT     : "
        f"{report['next_stage']['status']}"
    )

    print_section("OUTPUT")

    print(
        f"REPORT WRITTEN : "
        f"{OUTPUT_REPORT}"
    )


def main() -> int:

    paths = discover_files()

    records: list[dict[str, Any]] = []

    for path in paths:
        try:
            records.append(
                inspect_file(path)
            )
        except OSError:
            continue
        except Exception:
            continue

    report = build_report(
        records
    )

    OUTPUT_REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print_report(
        report
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )