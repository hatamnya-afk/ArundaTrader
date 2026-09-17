from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_INFORMATION_ARMS_EXACT_ENTRYPOINT_TRACE_REPORT.json"
)

EXCLUDED_DIRS = {
    "_backups",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
}

ARM_KEYWORDS = {
    "MARKET": {
        "market",
        "price",
        "ohlc",
        "ticker",
        "volume",
        "market_data",
        "market_records",
    },
    "NEWS": {
        "news",
        "article",
        "headline",
        "rss",
        "feed",
        "sentiment",
        "newsapi",
    },
    "SOCIAL": {
        "social",
        "lunarcrush",
        "engagement",
        "social_score",
        "social_volume",
        "mentions",
    },
    "FUNDAMENTAL": {
        "fundamental",
        "market_cap",
        "circulating_supply",
        "total_supply",
        "fdv",
        "tokenomics",
        "on_chain",
        "onchain",
        "supply",
    },
    "TRADINGVIEW": {
        "tradingview",
        "trading_view",
        "tv_",
    },
}

NETWORK_MARKERS = {
    "requests",
    "httpx",
    "aiohttp",
    "urllib",
    "urllib3",
    "websocket",
    "websockets",
    "ccxt",
    "socket",
    "newsapi",
    "lunarcrush",
    "tradingview",
}

DB_MARKERS = {
    "sqlite",
    "sqlite3",
    "arunda.db",
    "market_data",
    "market_records",
    "fusion_signals",
    "market_history",
}

OUTPUT_MARKERS = {
    "signal",
    "score",
    "feature",
    "sentiment",
    "catalyst",
    "analysis",
    "market_data",
    "market_state",
    "fusion",
    "result",
    "output",
}


def normalize(text: str) -> str:
    return text.lower().replace("-", "_")


def safe_literal(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


def contains_keyword(text: str, keywords: set[str]) -> list[str]:
    normalized = normalize(text)
    hits = []

    for keyword in keywords:
        if normalize(keyword) in normalized:
            hits.append(keyword)

    return sorted(set(hits))


def is_excluded(path: Path) -> bool:
    try:
        relative = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return True

    return any(part in EXCLUDED_DIRS for part in relative.parts)


def discover_python_files() -> list[Path]:
    files = []

    for path in PROJECT_ROOT.rglob("*.py"):
        if is_excluded(path):
            continue
        files.append(path)

    return sorted(files)


def get_call_name(node: ast.Call) -> str:
    func = node.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        parts = []

        current: ast.AST | None = func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return safe_literal(func)


class PythonFileAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: dict[str, dict[str, Any]] = {}
        self.calls: list[dict[str, Any]] = []
        self.imports: list[str] = []
        self.network_hits: set[str] = set()
        self.database_hits: set[str] = set()
        self.input_hits: set[str] = set()
        self.output_hits: set[str] = set()
        self.main_exists = False
        self.main_execution = False
        self.current_function: str | None = None

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            name = alias.name
            self.imports.append(name)

            if any(
                normalize(marker) in normalize(name)
                for marker in NETWORK_MARKERS
            ):
                self.network_hits.add(name)

            if any(
                normalize(marker) in normalize(name)
                for marker in DB_MARKERS
            ):
                self.database_hits.add(name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        module = node.module or ""

        self.imports.append(module)

        if any(
            normalize(marker) in normalize(module)
            for marker in NETWORK_MARKERS
        ):
            self.network_hits.add(module)

        if any(
            normalize(marker) in normalize(module)
            for marker in DB_MARKERS
        ):
            self.database_hits.add(module)

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        previous = self.current_function
        self.current_function = node.name

        self.functions[node.name] = {
            "name": node.name,
            "line": node.lineno,
            "args": [
                arg.arg
                for arg in node.args.args
            ],
            "calls": [],
            "returns": [],
        }

        if node.name == "main":
            self.main_exists = True

        self.generic_visit(node)

        self.current_function = previous

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        previous = self.current_function
        self.current_function = node.name

        self.functions[node.name] = {
            "name": node.name,
            "line": node.lineno,
            "args": [
                arg.arg
                for arg in node.args.args
            ],
            "calls": [],
            "returns": [],
        }

        if node.name == "main":
            self.main_exists = True

        self.generic_visit(node)

        self.current_function = previous

    def visit_Call(self, node: ast.Call) -> Any:
        call_name = get_call_name(node)

        record = {
            "line": node.lineno,
            "function": self.current_function,
            "call": call_name,
        }

        self.calls.append(record)

        if self.current_function in self.functions:
            self.functions[self.current_function]["calls"].append(
                {
                    "line": node.lineno,
                    "call": call_name,
                }
            )

        normalized = normalize(call_name)

        if any(
            normalize(marker) in normalized
            for marker in NETWORK_MARKERS
        ):
            self.network_hits.add(call_name)

        if any(
            normalize(marker) in normalized
            for marker in DB_MARKERS
        ):
            self.database_hits.add(call_name)

        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> Any:
        if self.current_function in self.functions:
            value = (
                safe_literal(node.value)
                if node.value is not None
                else "None"
            )

            self.functions[self.current_function]["returns"].append(
                {
                    "line": node.lineno,
                    "value": value[:300],
                }
            )

            output_hits = contains_keyword(
                value,
                set().union(*ARM_KEYWORDS.values())
                | OUTPUT_MARKERS,
            )

            self.output_hits.update(output_hits)

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> Any:
        target_text = " ".join(
            safe_literal(target)
            for target in node.targets
        )

        value_text = safe_literal(node.value)

        combined = f"{target_text} {value_text}"

        self.input_hits.update(
            contains_keyword(
                combined,
                set().union(*ARM_KEYWORDS.values()),
            )
        )

        self.output_hits.update(
            contains_keyword(
                combined,
                OUTPUT_MARKERS,
            )
        )

        self.generic_visit(node)


def detect_main_execution(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue

        try:
            test = ast.unparse(node.test)
        except Exception:
            continue

        normalized = normalize(test)

        if "__name__" in normalized and "__main__" in normalized:
            return True

    return False


def analyze_file(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "syntax_valid": False,
        "size_bytes": 0,
        "functions": {},
        "calls": [],
        "imports": [],
        "network": [],
        "database": [],
        "input_hits": [],
        "output_hits": [],
        "main_exists": False,
        "main_execution": False,
        "syntax_error": None,
    }

    try:
        result["size_bytes"] = path.stat().st_size
    except OSError:
        pass

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        result["syntax_error"] = f"READ_ERROR: {exc}"
        return result

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except SyntaxError as exc:
        result["syntax_error"] = (
            f"SyntaxError line={exc.lineno} "
            f"offset={exc.offset} "
            f"msg={exc.msg}"
        )
        return result

    result["syntax_valid"] = True

    analyzer = PythonFileAnalyzer()
    analyzer.visit(tree)

    result["functions"] = analyzer.functions
    result["calls"] = analyzer.calls
    result["imports"] = sorted(set(analyzer.imports))
    result["network"] = sorted(analyzer.network_hits)
    result["database"] = sorted(analyzer.database_hits)
    result["input_hits"] = sorted(analyzer.input_hits)
    result["output_hits"] = sorted(analyzer.output_hits)
    result["main_exists"] = analyzer.main_exists
    result["main_execution"] = detect_main_execution(tree)

    return result


def score_arm_candidate(
    analysis: dict[str, Any],
    keywords: set[str],
) -> tuple[int, list[str]]:
    text = json.dumps(
        analysis,
        ensure_ascii=False,
    ).lower()

    hits = contains_keyword(
        text,
        keywords,
    )

    score = 0

    if hits:
        score += len(hits) * 2

    if analysis["main_exists"]:
        score += 3

    if analysis["main_execution"]:
        score += 3

    if analysis["calls"]:
        score += 2

    if analysis["network"]:
        score += 2

    if analysis["database"]:
        score += 1

    if analysis["output_hits"]:
        score += 2

    return score, hits


def build_candidates(
    analyses: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = {}

    for arm, keywords in ARM_KEYWORDS.items():
        rows = []

        for analysis in analyses:
            if not analysis["syntax_valid"]:
                continue

            score, hits = score_arm_candidate(
                analysis,
                keywords,
            )

            if score <= 0:
                continue

            rows.append(
                {
                    "path": analysis["path"],
                    "score": score,
                    "keyword_hits": hits,
                    "main_exists": analysis["main_exists"],
                    "main_execution": analysis["main_execution"],
                    "functions": sorted(
                        analysis["functions"].keys()
                    ),
                    "network": analysis["network"],
                    "database": analysis["database"],
                    "input_hits": analysis["input_hits"],
                    "output_hits": analysis["output_hits"],
                }
            )

        rows.sort(
            key=lambda row: (
                -row["score"],
                row["path"],
            )
        )

        candidates[arm] = rows

    return candidates


def build_function_call_edges(
    analyses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    edges = []

    known_functions: dict[str, list[str]] = {}

    for analysis in analyses:
        if not analysis["syntax_valid"]:
            continue

        path = analysis["path"]

        for function_name in analysis["functions"]:
            known_functions.setdefault(
                function_name,
                [],
            ).append(path)

    for analysis in analyses:
        if not analysis["syntax_valid"]:
            continue

        path = analysis["path"]

        for call in analysis["calls"]:
            call_name = call["call"]

            short_name = call_name.split(".")[-1]

            if short_name not in known_functions:
                continue

            edges.append(
                {
                    "source_file": path,
                    "source_function": call["function"],
                    "line": call["line"],
                    "called_function": short_name,
                    "possible_targets": known_functions[
                        short_name
                    ],
                }
            )

    return edges


def classify_runtime_boundary(
    candidate: dict[str, Any],
) -> str:
    if not candidate["main_exists"]:
        return "FUNCTION_ENTRYPOINT_ONLY"

    if candidate["main_execution"]:
        if candidate["network"]:
            return "MAIN_RUNTIME_ENTRYPOINT_NETWORK_DEPENDENCY"

        return "MAIN_RUNTIME_ENTRYPOINT"

    return "MAIN_DEFINED_NOT_AUTO_EXECUTED"


def select_exact_candidates(
    candidates: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any] | None]:
    selected: dict[str, dict[str, Any] | None] = {}

    for arm, rows in candidates.items():
        if not rows:
            selected[arm] = None
            continue

        ranked = sorted(
            rows,
            key=lambda row: (
                -(
                    row["score"]
                    + (5 if row["main_execution"] else 0)
                    + (3 if row["main_exists"] else 0)
                ),
                row["path"],
            ),
        )

        selected[arm] = ranked[0]

    return selected


def build_report(
    analyses: list[dict[str, Any]],
    candidates: dict[str, list[dict[str, Any]]],
    selected: dict[str, dict[str, Any] | None],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:

    syntax_invalid = [
        {
            "path": analysis["path"],
            "error": analysis["syntax_error"],
        }
        for analysis in analyses
        if not analysis["syntax_valid"]
    ]

    arm_results = {}

    for arm, candidate in selected.items():
        if candidate is None:
            arm_results[arm] = {
                "status": "NO_EXACT_CANDIDATE_SELECTED",
                "selected": None,
            }
            continue

        arm_results[arm] = {
            "status": "CANDIDATE_SELECTED_STATICALLY",
            "selected": candidate,
            "runtime_boundary": classify_runtime_boundary(
                candidate
            ),
            "trace_state": {
                "entrypoint": candidate["path"],
                "call_chain": "NOT_RUNTIME_TRACED",
                "input": "STATIC_INPUT_MARKERS_ONLY",
                "transformation": "STATIC_TRANSFORMATION_MARKERS_ONLY",
                "output": "STATIC_OUTPUT_MARKERS_ONLY",
                "consumer": "NOT_RUNTIME_TRACED",
            },
        }

    verified = False

    return {
        "project": "ArundaTrader",
        "component": "LIVE_INFORMATION_ARMS_EXACT_ENTRYPOINT_TRACE",
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
            "verified": True,
        },
        "discovery": {
            "python_files_scanned": len(analyses),
            "syntax_invalid_files": len(syntax_invalid),
            "backups_excluded": True,
        },
        "syntax_invalid_files": syntax_invalid,
        "arms": arm_results,
        "candidate_counts": {
            arm: len(rows)
            for arm, rows in candidates.items()
        },
        "selected_entrypoints": {
            arm: (
                candidate["path"]
                if candidate is not None
                else None
            )
            for arm, candidate in selected.items()
        },
        "function_call_edges": edges,
        "verification": {
            "entrypoints_verified": False,
            "call_chains_verified": False,
            "inputs_verified": False,
            "transformations_verified": False,
            "outputs_verified": False,
            "consumers_verified": False,
            "overall_verified": verified,
        },
        "final_verdict": (
            "BOUNDARIES_SELECTED_STATIC_TRACE_ONLY"
        ),
        "next_stage": (
            "TRACE_SELECTED_ARM_CALL_CHAINS"
        ),
    }


def print_header() -> None:
    print("=" * 100)
    print("ARUNDA TRADER")
    print("LIVE INFORMATION ARMS EXACT ENTRYPOINT TRACE v0.1")
    print("=" * 100)
    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ_ONLY")
    print("=" * 100)


def print_safety() -> None:
    print("SAFETY")
    print("=" * 100)
    print("database_write          : False")
    print("network_access          : False")
    print("producer_execution      : False")
    print("signal_creation         : False")
    print("signal_injection        : False")
    print("replay_execution        : False")
    print("order_creation          : False")
    print("order_submission        : False")
    print("order_execution         : False")
    print("artifact_mutation       : False")
    print("=" * 100)


def print_arm(
    arm: str,
    candidates: list[dict[str, Any]],
    selected: dict[str, Any] | None,
) -> None:

    print(f"[{arm}]")
    print("=" * 100)

    if not candidates:
        print("STATUS          : NO_CANDIDATE")
        print("CANDIDATES      : 0")
        print()
        return

    print("STATUS          : CANDIDATES_IDENTIFIED")
    print(f"CANDIDATES      : {len(candidates)}")

    if selected is not None:
        print(
            f"SELECTED        : {selected['path']}"
        )
        print(
            f"SCORE           : {selected['score']}"
        )
        print(
            f"MAIN            : {selected['main_exists']}"
        )
        print(
            f"MAIN EXECUTION  : {selected['main_execution']}"
        )

        print(
            "NETWORK         : "
            + (
                ", ".join(selected["network"])
                if selected["network"]
                else "NONE"
            )
        )

        print(
            "DATABASE        : "
            + (
                ", ".join(selected["database"])
                if selected["database"]
                else "NONE"
            )
        )

        print(
            "FUNCTIONS       : "
            + (
                ", ".join(selected["functions"])
                if selected["functions"]
                else "NONE"
            )
        )

        print(
            "INPUT MARKERS   : "
            + (
                ", ".join(selected["input_hits"])
                if selected["input_hits"]
                else "NONE"
            )
        )

        print(
            "OUTPUT MARKERS  : "
            + (
                ", ".join(selected["output_hits"])
                if selected["output_hits"]
                else "NONE"
            )
        )

    print()
    print("TOP CANDIDATES")
    print("-" * 100)

    for index, candidate in enumerate(
        candidates[:10],
        start=1,
    ):
        print(
            f"[{index}] {candidate['path']}"
        )
        print(
            f"    score={candidate['score']} "
            f"main={candidate['main_exists']} "
            f"execute={candidate['main_execution']}"
        )
        print(
            "    keywords="
            + (
                ", ".join(candidate["keyword_hits"])
                if candidate["keyword_hits"]
                else "NONE"
            )
        )

    print("=" * 100)


def main() -> int:
    print_header()
    print_safety()

    print("DISCOVERY")
    print("=" * 100)

    files = discover_python_files()

    print(
        f"Python files discovered : {len(files)}"
    )

    print("=" * 100)

    analyses = []

    for path in files:
        analysis = analyze_file(path)
        analyses.append(analysis)

    syntax_invalid = sum(
        1
        for analysis in analyses
        if not analysis["syntax_valid"]
    )

    print(
        f"Syntax-invalid files    : {syntax_invalid}"
    )

    print("=" * 100)
    print("EXACT ENTRYPOINT CANDIDATE SELECTION")
    print("=" * 100)

    candidates = build_candidates(
        analyses
    )

    selected = select_exact_candidates(
        candidates
    )

    for arm in (
        "MARKET",
        "NEWS",
        "SOCIAL",
        "FUNDAMENTAL",
        "TRADINGVIEW",
    ):
        print_arm(
            arm,
            candidates[arm],
            selected[arm],
        )

    print("=" * 100)
    print("STATIC FUNCTION CALL EDGES")
    print("=" * 100)

    edges = build_function_call_edges(
        analyses
    )

    print(
        f"Internal function edges : {len(edges)}"
    )

    for edge in edges[:50]:
        print(
            f"{edge['source_file']}:{edge['line']} "
            f"{edge['source_function']}() "
            f"-> {edge['called_function']}()"
        )

    print("=" * 100)
    print("RUNTIME TRACE STATE")
    print("=" * 100)

    for arm in (
        "MARKET",
        "NEWS",
        "SOCIAL",
        "FUNDAMENTAL",
        "TRADINGVIEW",
    ):
        candidate = selected[arm]

        if candidate is None:
            print(
                f"{arm:<15}: NO_CANDIDATE"
            )
            continue

        boundary = classify_runtime_boundary(
            candidate
        )

        print(
            f"{arm:<15}: {boundary}"
        )

    print("=" * 100)
    print("VERIFICATION")
    print("=" * 100)
    print("Entrypoint verified    : False")
    print("Call chain verified    : False")
    print("Input verified         : False")
    print("Transformation verified: False")
    print("Output verified        : False")
    print("Consumer verified      : False")
    print("=" * 100)

    report = build_report(
        analyses,
        candidates,
        selected,
        edges,
    )

    OUTPUT_REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("FINAL VERDICT")
    print("=" * 100)
    print(
        "STATUS   : "
        "BOUNDARIES_SELECTED_STATIC_TRACE_ONLY"
    )
    print("VERIFIED : False")
    print(
        "NEXT     : TRACE_SELECTED_ARM_CALL_CHAINS"
    )
    print("=" * 100)
    print("OUTPUT")
    print("=" * 100)
    print(
        f"REPORT WRITTEN : {OUTPUT_REPORT}"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())