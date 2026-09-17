from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_INFORMATION_ARMS_RUNTIME_VERIFICATION_REPORT.json"
)

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

PYTHON_FILES = [
    p
    for p in PROJECT_ROOT.rglob("*.py")
    if not any(part in EXCLUDED_DIRS for part in p.parts)
    and p.name != Path(__file__).name
]

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
    ],
    "technical": [
        "technical",
        "indicator",
        "rsi",
        "macd",
        "ema",
        "sma",
        "bollinger",
        "atr",
        "adx",
        "technical_analysis",
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
        "orderbook",
        "order_book",
        "ticker",
        "ohlcv",
        "price",
        "volume",
        "market_data",
    ],
    "tradingview": [
        "tradingview",
        "trading_view",
    ],
    "fusion": [
        "fusion",
        "signal_fusion",
        "fusion_signal",
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
    "fetch",
    "fetch_data",
    "collect",
    "collect_data",
}


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def contains_keyword(text: str, keyword: str) -> bool:
    return keyword.lower() in text.lower()


def extract_functions(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    result: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append(node.name)

    return sorted(set(result))


def extract_imports(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
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


def find_main_execution(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test

            if (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "__name__"
            ):
                return True

    return False


def inspect_file(path: Path) -> dict[str, Any]:
    source = safe_read(path)

    functions = extract_functions(source)
    imports = extract_imports(source)

    matched_arms: dict[str, list[str]] = {}

    for arm, keywords in ARM_KEYWORDS.items():
        matches = [
            keyword
            for keyword in keywords
            if contains_keyword(source, keyword)
        ]

        if matches:
            matched_arms[arm] = sorted(set(matches))

    runtime_functions = [
        name
        for name in functions
        if name in RUNTIME_FUNCTION_NAMES
    ]

    return {
        "file": relative_path(path),
        "size_bytes": path.stat().st_size,
        "syntax_valid": _syntax_valid(source),
        "arms": matched_arms,
        "functions": functions,
        "runtime_functions": runtime_functions,
        "has_main_execution": find_main_execution(source),
        "imports": imports,
    }


def _syntax_valid(source: str) -> bool:
    try:
        ast.parse(source)
        return True
    except SyntaxError:
        return False


def build_arm_index(file_records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {
        arm: []
        for arm in ARM_KEYWORDS
    }

    for record in file_records:
        for arm in record["arms"]:
            result[arm].append(
                {
                    "file": record["file"],
                    "matched_keywords": record["arms"][arm],
                    "runtime_functions": record["runtime_functions"],
                    "has_main_execution": record["has_main_execution"],
                    "syntax_valid": record["syntax_valid"],
                }
            )

    return result


def determine_arm_status(
    arm: str,
    records: list[dict[str, Any]],
) -> str:
    if not records:
        return "NOT_FOUND"

    syntax_valid_records = [
        record
        for record in records
        if record["syntax_valid"]
    ]

    if not syntax_valid_records:
        return "FOUND_BUT_SYNTAX_INVALID"

    runtime_records = [
        record
        for record in syntax_valid_records
        if record["runtime_functions"]
        or record["has_main_execution"]
    ]

    if runtime_records:
        return "RUNTIME_ENTRYPOINT_FOUND"

    return "SOURCE_PRESENT_RUNTIME_NOT_PROVEN"


def build_report(
    file_records: list[dict[str, Any]],
) -> dict[str, Any]:

    arm_index = build_arm_index(file_records)

    arm_status = {
        arm: determine_arm_status(
            arm,
            arm_index[arm],
        )
        for arm in ARM_KEYWORDS
    }

    return {
        "project": "ArundaTrader",
        "component": "LIVE_INFORMATION_ARMS_RUNTIME_VERIFICATION",
        "version": "v0.1",

        "mode": "READ_ONLY",

        "safety": {
            "database_write": False,
            "network_access": False,
            "producer_execution": False,
            "signal_creation": False,
            "signal_injection": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
            "artifact_mutation": False,
        },

        "discovery": {
            "project_root": str(PROJECT_ROOT),
            "python_file_count": len(file_records),
        },

        "arms": {
            arm: {
                "status": arm_status[arm],
                "candidate_count": len(arm_index[arm]),
                "candidates": arm_index[arm],
            }
            for arm in ARM_KEYWORDS
        },

        "runtime_verification": {
            "news": arm_status["news"],
            "technical": arm_status["technical"],
            "social": arm_status["social"],
            "market": arm_status["market"],
            "tradingview": arm_status["tradingview"],
            "fusion": arm_status["fusion"],
        },

        "verdict": {
            "status": (
                "DISCOVERY_COMPLETE_RUNTIME_EXECUTION_NOT_PERFORMED"
            ),
            "verified": False,
            "reason": (
                "This frontier only discovers and traces actual "
                "information-arm source/runtime entrypoints. "
                "No producer or network execution is performed."
            ),
        },

        "next_stage": {
            "status": "TRACE_ACTUAL_ARM_RUNTIME_BOUNDARIES",
            "requires_network": False,
            "requires_producer_execution": False,
        },
    }


def print_report(report: dict[str, Any]) -> None:
    print("=" * 100)
    print("ARUNDA TRADER")
    print("LIVE INFORMATION ARMS RUNTIME VERIFICATION v0.1")
    print("=" * 100)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ_ONLY")

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    for key, value in report["safety"].items():
        print(f"{key:24}: {value}")

    print("=" * 100)
    print("DISCOVERY")
    print("=" * 100)

    print(
        f"Python files discovered : "
        f"{report['discovery']['python_file_count']}"
    )

    print("=" * 100)
    print("INFORMATION ARMS")
    print("=" * 100)

    for arm, data in report["arms"].items():
        print()
        print(f"[{arm.upper()}]")
        print(f"STATUS           : {data['status']}")
        print(f"CANDIDATE COUNT  : {data['candidate_count']}")

        for candidate in data["candidates"][:10]:
            print(
                f"  - {candidate['file']}"
            )

            print(
                f"    keywords       : "
                f"{', '.join(candidate['matched_keywords'])}"
            )

            print(
                f"    runtime funcs  : "
                f"{', '.join(candidate['runtime_functions']) or 'NONE'}"
            )

            print(
                f"    main execution : "
                f"{candidate['has_main_execution']}"
            )

    print("=" * 100)
    print("RUNTIME VERIFICATION")
    print("=" * 100)

    for arm, status in report["runtime_verification"].items():
        print(
            f"{arm.upper():16} : {status}"
        )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    print(
        f"STATUS   : "
        f"{report['verdict']['status']}"
    )

    print(
        f"VERIFIED : "
        f"{report['verdict']['verified']}"
    )

    print(
        f"NEXT     : "
        f"{report['next_stage']['status']}"
    )

    print("=" * 100)
    print(
        f"REPORT WRITTEN : {OUTPUT_REPORT}"
    )
    print("=" * 100)


def main() -> int:
    file_records: list[dict[str, Any]] = []

    for path in sorted(PYTHON_FILES):
        try:
            file_records.append(
                inspect_file(path)
            )
        except OSError:
            continue

    report = build_report(file_records)

    OUTPUT_REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print_report(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())