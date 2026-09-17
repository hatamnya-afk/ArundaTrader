# -*- coding: utf-8 -*-

"""
====================================================================================================
ARUNDA TRADER
INFORMATION ARMS ARCHITECTURE FORENSIC AND SCOPE RECONCILIATION v0.1
====================================================================================================

PURPOSE
-------
Forensic, read-only architectural reconciliation of ArundaTrader information arms.

TARGET ARMS
-----------
1. MARKET
2. TECHNICAL
3. NEWS
4. SOCIAL
5. FUNDAMENTAL
6. TRADINGVIEW

OBJECTIVES
----------
- Discover actual production-relevant modules for each arm.
- Exclude backups and forensic/audit/reconstruction scripts.
- Detect runtime entrypoints without importing project modules.
- Detect network dependencies.
- Detect database dependencies.
- Detect database writes.
- Detect signal creation / mutation.
- Detect input markers.
- Detect transformation markers.
- Detect output markers.
- Detect consumer relationships.
- Detect duplicated responsibilities between arms.
- Detect incomplete / weak / oversized scopes.
- Detect likely architectural overlaps.
- Produce a scope recommendation:
      KEEP
      REPAIR
      EXPAND
      MERGE
      DEPRECATE
      UNKNOWN
- Never execute discovered project modules.
- Never call network.
- Never write to production DB.
- Never create or inject signals.
- Never mutate production artifacts.

SAFETY
------
READ ONLY.
AST/static inspection only.
No project-module imports.
No runtime execution of discovered modules.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


# ==================================================================================================
# CONFIG
# ==================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_INFORMATION_ARMS_ARCHITECTURE_FORENSIC_AND_SCOPE_RECONCILIATION_REPORT.json"
)

PYTHON_SUFFIX = ".py"

MAX_FILE_BYTES = 3_000_000

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "env",
    ".env",
}

EXCLUDED_NAME_PATTERNS = [
    r"^_.*",
    r".*backup.*",
    r".*forensic.*",
    r".*audit.*",
    r".*diagnostic.*",
    r".*reconciliation.*",
    r".*verification.*",
    r".*verify.*",
    r".*repair.*",
    r".*reconstruction.*",
    r".*stress.*",
    r".*consistency.*",
    r".*trace.*",
    r".*fingerprint.*",
    r".*contract.*",
    r".*runtime.*",
    r".*scope.*",
]

# We deliberately do NOT classify this script as an information-arm producer.
SELF_FILENAME = Path(__file__).name


# ==================================================================================================
# ARM DEFINITIONS
# ==================================================================================================

ARM_DEFINITIONS: Dict[str, Dict[str, Set[str]]] = {
    "MARKET": {
        "keywords": {
            "market",
            "market_data",
            "market_records",
            "ohlc",
            "price",
            "volume",
            "ticker",
            "orderbook",
            "order_book",
            "candles",
            "candle",
            "bid",
            "ask",
            "spread",
            "liquidity",
            "exchange",
            "symbol",
        },
        "inputs": {
            "price",
            "volume",
            "ohlc",
            "ticker",
            "symbol",
            "market_data",
            "market_records",
            "orderbook",
            "order_book",
        },
        "transformations": {
            "normalize",
            "aggregate",
            "resample",
            "ohlc",
            "price",
            "volume",
            "spread",
            "liquidity",
            "depth",
            "snapshot",
        },
        "outputs": {
            "market_data",
            "price",
            "volume",
            "ohlc",
            "market_state",
            "snapshot",
            "feature",
        },
    },

    "TECHNICAL": {
        "keywords": {
            "technical",
            "indicator",
            "indicators",
            "ema",
            "sma",
            "wma",
            "rsi",
            "macd",
            "atr",
            "adx",
            "bollinger",
            "stochastic",
            "ichimoku",
            "tenkan",
            "kijun",
            "senkou",
            "chikou",
            "support",
            "resistance",
            "trend",
            "momentum",
            "volatility",
            "signal",
        },
        "inputs": {
            "ohlc",
            "price",
            "volume",
            "market_data",
            "candles",
            "close",
            "open",
            "high",
            "low",
        },
        "transformations": {
            "ema",
            "sma",
            "wma",
            "rsi",
            "macd",
            "atr",
            "adx",
            "bollinger",
            "stochastic",
            "ichimoku",
            "tenkan",
            "kijun",
            "senkou",
            "chikou",
            "indicator",
            "trend",
            "momentum",
            "volatility",
        },
        "outputs": {
            "indicator",
            "indicators",
            "technical",
            "technical_score",
            "feature",
            "signal",
            "trend",
            "momentum",
            "volatility",
        },
    },

    "NEWS": {
        "keywords": {
            "news",
            "headline",
            "article",
            "articles",
            "feed",
            "rss",
            "newsapi",
            "sentiment",
            "breaking",
            "announcement",
            "press_release",
            "media",
        },
        "inputs": {
            "article",
            "headline",
            "feed",
            "rss",
            "news",
            "newsapi",
            "announcement",
        },
        "transformations": {
            "sentiment",
            "classify",
            "score",
            "deduplicate",
            "normalize",
            "parse",
            "extract",
            "rank",
        },
        "outputs": {
            "news",
            "headline",
            "sentiment",
            "news_score",
            "catalyst",
            "feature",
            "signal",
        },
    },

    "SOCIAL": {
        "keywords": {
            "social",
            "social_score",
            "social_volume",
            "engagement",
            "mentions",
            "lunarcrush",
            "community",
            "twitter",
            "telegram",
            "reddit",
            "discord",
            "followers",
            "interactions",
        },
        "inputs": {
            "social",
            "social_score",
            "social_volume",
            "engagement",
            "mentions",
            "lunarcrush",
            "followers",
            "interactions",
        },
        "transformations": {
            "social_score",
            "engagement",
            "mentions",
            "sentiment",
            "normalize",
            "score",
            "trend",
            "velocity",
        },
        "outputs": {
            "social",
            "social_score",
            "social_volume",
            "engagement",
            "mentions",
            "catalyst",
            "feature",
            "signal",
        },
    },

    "FUNDAMENTAL": {
        "keywords": {
            "fundamental",
            "fundamentals",
            "tokenomics",
            "market_cap",
            "fdv",
            "fully_diluted",
            "circulating_supply",
            "total_supply",
            "max_supply",
            "supply",
            "on_chain",
            "onchain",
            "holders",
            "holder",
            "unlock",
            "vesting",
            "emission",
            "inflation",
            "treasury",
            "revenue",
            "protocol",
            "tvl",
        },
        "inputs": {
            "market_cap",
            "fdv",
            "circulating_supply",
            "total_supply",
            "max_supply",
            "supply",
            "on_chain",
            "onchain",
            "holders",
            "tokenomics",
            "tvl",
            "revenue",
        },
        "transformations": {
            "fdv",
            "market_cap",
            "supply",
            "ratio",
            "valuation",
            "tokenomics",
            "dilution",
            "unlock",
            "vesting",
            "score",
            "normalize",
        },
        "outputs": {
            "fundamental",
            "fundamental_score",
            "tokenomics",
            "valuation",
            "dilution",
            "feature",
            "signal",
        },
    },

    "TRADINGVIEW": {
        "keywords": {
            "tradingview",
            "trading_view",
            "tv_",
            "tv_symbol",
            "tv_signal",
            "technical_analysis",
        },
        "inputs": {
            "tradingview",
            "trading_view",
            "tv_symbol",
            "symbol",
            "ticker",
        },
        "transformations": {
            "tradingview",
            "technical_analysis",
            "scan",
            "screen",
            "screener",
            "signal",
        },
        "outputs": {
            "tradingview",
            "tv_signal",
            "signal",
            "feature",
            "analysis",
        },
    },
}


NETWORK_MARKERS = {
    "requests",
    "urllib",
    "urllib3",
    "httpx",
    "aiohttp",
    "websocket",
    "socket",
    "ccxt",
    "newsapi",
    "lunarcrush",
    "tradingview",
    "api",
    "http",
    "https",
    "feedparser",
}

DATABASE_MARKERS = {
    "sqlite",
    "sqlite3",
    "arunda.db",
    "market_records",
    "market_data",
    "market_history",
    "market_state",
    "fusion_signals",
    "signal_outcomes",
}

DATABASE_WRITE_MARKERS = {
    "insert",
    "insert or replace",
    "insert or ignore",
    "update",
    "delete",
    "alter",
    "create table",
    "drop table",
    "replace into",
    "executemany",
    "commit",
}

SIGNAL_MUTATION_MARKERS = {
    "fusion_signals",
    "signal_outcomes",
    "create_signal",
    "generate_signal",
    "insert_signal",
    "update_signal",
    "signal_creation",
    "signal_injection",
}

CONSUMER_MARKERS = {
    "fusion",
    "fusion_engine",
    "fusion_signals",
    "signal",
    "signal_engine",
    "opportunity",
    "catalyst",
    "decision",
    "execution",
    "order_intent",
    "feature",
    "market_state",
}

RUNTIME_MARKERS = {
    "main",
    "execute",
    "run",
    "process",
    "generate",
    "build",
    "analyze",
    "calculate",
    "score",
}


# ==================================================================================================
# DATA STRUCTURES
# ==================================================================================================

@dataclass
class FunctionInfo:
    name: str
    line: int
    calls: Set[str] = field(default_factory=set)
    returns: Set[str] = field(default_factory=set)


@dataclass
class FileAnalysis:
    path: str
    relative_path: str
    size: int
    sha256: str

    syntax_valid: bool = False
    syntax_error: Optional[str] = None

    main_defined: bool = False
    main_executed: bool = False

    functions: List[FunctionInfo] = field(default_factory=list)

    imports: Set[str] = field(default_factory=set)
    calls: Set[str] = field(default_factory=set)

    keywords: Set[str] = field(default_factory=set)
    input_markers: Set[str] = field(default_factory=set)
    transformation_markers: Set[str] = field(default_factory=set)
    output_markers: Set[str] = field(default_factory=set)
    consumer_markers: Set[str] = field(default_factory=set)

    network_dependencies: Set[str] = field(default_factory=set)
    database_dependencies: Set[str] = field(default_factory=set)
    database_write_markers: Set[str] = field(default_factory=set)
    signal_mutation_markers: Set[str] = field(default_factory=set)

    runtime_functions: Set[str] = field(default_factory=set)

    arm_scores: Dict[str, int] = field(default_factory=dict)

    @property
    def executable(self) -> bool:
        return self.main_executed or bool(self.runtime_functions)

    @property
    def has_network(self) -> bool:
        return bool(self.network_dependencies)

    @property
    def has_database(self) -> bool:
        return bool(self.database_dependencies)

    @property
    def has_db_write(self) -> bool:
        return bool(self.database_write_markers)

    @property
    def has_signal_mutation(self) -> bool:
        return bool(self.signal_mutation_markers)


# ==================================================================================================
# UTILITIES
# ==================================================================================================

def normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def safe_read_text(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def is_excluded(path: Path) -> bool:
    try:
        rel = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return True

    parts = rel.parts

    for part in parts[:-1]:
        if part in EXCLUDED_DIRS:
            return True

    name = path.name

    if name == SELF_FILENAME:
        return True

    for pattern in EXCLUDED_NAME_PATTERNS:
        if re.match(pattern, name, flags=re.IGNORECASE):
            return True

    return False


def discover_python_files() -> List[Path]:
    result: List[Path] = []

    if not PROJECT_ROOT.exists():
        return result

    for root, dirs, files in os.walk(PROJECT_ROOT):
        root_path = Path(root)

        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS
        ]

        for filename in files:
            if not filename.endswith(PYTHON_SUFFIX):
                continue

            path = root_path / filename

            if is_excluded(path):
                continue

            result.append(path)

    return sorted(result)


def contains_any(text: str, markers: Iterable[str]) -> Set[str]:
    lower = text.lower()
    found = set()

    for marker in markers:
        if marker.lower() in lower:
            found.add(marker)

    return found


def get_call_name(node: ast.Call) -> str:
    func = node.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        parts = []

        current: Any = func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ""


# ==================================================================================================
# AST ANALYZER
# ==================================================================================================

class ASTAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: List[FunctionInfo] = []
        self.current_function: Optional[FunctionInfo] = None

        self.imports: Set[str] = set()
        self.calls: Set[str] = set()

        self.main_defined = False
        self.main_executed = False

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            self.imports.add(alias.name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        if node.module:
            self.imports.add(node.module)

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        info = FunctionInfo(
            name=node.name,
            line=node.lineno,
        )

        self.functions.append(info)

        if node.name == "main":
            self.main_defined = True

        previous = self.current_function
        self.current_function = info

        self.generic_visit(node)

        self.current_function = previous

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        info = FunctionInfo(
            name=node.name,
            line=node.lineno,
        )

        self.functions.append(info)

        if node.name == "main":
            self.main_defined = True

        previous = self.current_function
        self.current_function = info

        self.generic_visit(node)

        self.current_function = previous

    def visit_Call(self, node: ast.Call) -> Any:
        call_name = get_call_name(node)

        if call_name:
            self.calls.add(call_name)

            if self.current_function:
                self.current_function.calls.add(call_name)

        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> Any:
        if self.current_function and node.value is not None:
            try:
                value = ast.unparse(node.value)
            except Exception:
                value = ""

            if value:
                self.current_function.returns.add(value[:300])

        self.generic_visit(node)


def detect_main_execution(tree: ast.AST) -> bool:
    """
    Detect conventional:

        if __name__ == "__main__":
            main()

    without executing anything.
    """

    class MainGuardVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.found = False

        def visit_If(self, node: ast.If) -> Any:
            try:
                condition = ast.unparse(node.test)
            except Exception:
                condition = ""

            normalized = condition.replace(" ", "")

            if (
                "__name__" in normalized
                and "__main__" in normalized
            ):
                self.found = True

            self.generic_visit(node)

    visitor = MainGuardVisitor()
    visitor.visit(tree)

    return visitor.found


# ==================================================================================================
# FILE ANALYSIS
# ==================================================================================================

def analyze_file(path: Path) -> FileAnalysis:
    text = safe_read_text(path)

    try:
        relative = str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        relative = str(path)

    analysis = FileAnalysis(
        path=str(path),
        relative_path=relative,
        size=path.stat().st_size if path.exists() else 0,
        sha256=sha256_text(text),
    )

    if not text:
        analysis.syntax_valid = False
        analysis.syntax_error = "EMPTY_OR_UNREADABLE"
        return analysis

    try:
        tree = ast.parse(text, filename=str(path))
        analysis.syntax_valid = True
    except SyntaxError as exc:
        analysis.syntax_valid = False
        analysis.syntax_error = (
            f"{exc.__class__.__name__}: "
            f"line={getattr(exc, 'lineno', None)} "
            f"offset={getattr(exc, 'offset', None)} "
            f"{exc.msg}"
        )
        return analysis
    except Exception as exc:
        analysis.syntax_valid = False
        analysis.syntax_error = f"{type(exc).__name__}: {exc}"
        return analysis

    visitor = ASTAnalyzer()
    visitor.visit(tree)

    analysis.functions = visitor.functions
    analysis.imports = visitor.imports
    analysis.calls = visitor.calls
    analysis.main_defined = visitor.main_defined
    analysis.main_executed = detect_main_execution(tree)

    lower = text.lower()

    all_keywords: Set[str] = set()

    for arm_data in ARM_DEFINITIONS.values():
        all_keywords |= arm_data["keywords"]

    analysis.keywords = contains_any(lower, all_keywords)

    all_inputs: Set[str] = set()
    all_transformations: Set[str] = set()
    all_outputs: Set[str] = set()

    for arm_data in ARM_DEFINITIONS.values():
        all_inputs |= arm_data["inputs"]
        all_transformations |= arm_data["transformations"]
        all_outputs |= arm_data["outputs"]

    analysis.input_markers = contains_any(lower, all_inputs)
    analysis.transformation_markers = contains_any(lower, all_transformations)
    analysis.output_markers = contains_any(lower, all_outputs)
    analysis.consumer_markers = contains_any(lower, CONSUMER_MARKERS)

    analysis.network_dependencies = contains_any(
        lower,
        NETWORK_MARKERS,
    )

    analysis.database_dependencies = contains_any(
        lower,
        DATABASE_MARKERS,
    )

    analysis.database_write_markers = contains_any(
        lower,
        DATABASE_WRITE_MARKERS,
    )

    analysis.signal_mutation_markers = contains_any(
        lower,
        SIGNAL_MUTATION_MARKERS,
    )

    analysis.runtime_functions = {
        fn.name
        for fn in analysis.functions
        if normalize(fn.name) in {
            normalize(value)
            for value in RUNTIME_MARKERS
        }
        or any(
            normalize(value) in normalize(fn.name)
            for value in RUNTIME_MARKERS
        )
    }

    analysis.arm_scores = score_file_for_arms(
        analysis,
        lower,
    )

    return analysis


# ==================================================================================================
# ARM SCORING
# ==================================================================================================

def score_file_for_arms(
    analysis: FileAnalysis,
    text: str,
) -> Dict[str, int]:

    scores: Dict[str, int] = {}

    for arm, definition in ARM_DEFINITIONS.items():
        score = 0

        keywords = definition["keywords"]
        inputs = definition["inputs"]
        transformations = definition["transformations"]
        outputs = definition["outputs"]

        for marker in keywords:
            if marker.lower() in text:
                score += 2

        for marker in inputs:
            if marker.lower() in text:
                score += 2

        for marker in transformations:
            if marker.lower() in text:
                score += 3

        for marker in outputs:
            if marker.lower() in text:
                score += 2

        if analysis.executable:
            score += 3

        if analysis.has_network:
            score += 1

        if analysis.has_database:
            score += 1

        scores[arm] = score

    return scores


# ==================================================================================================
# CANDIDATE SELECTION
# ==================================================================================================

def select_arm_candidates(
    analyses: List[FileAnalysis],
    arm: str,
) -> List[FileAnalysis]:

    candidates = []

    for analysis in analyses:
        if not analysis.syntax_valid:
            continue

        score = analysis.arm_scores.get(arm, 0)

        if score <= 0:
            continue

        candidates.append(analysis)

    return sorted(
        candidates,
        key=lambda item: (
            item.arm_scores.get(arm, 0),
            item.executable,
            item.has_network,
            item.has_database,
        ),
        reverse=True,
    )


def select_primary_candidate(
    candidates: List[FileAnalysis],
    arm: str,
) -> Optional[FileAnalysis]:

    if not candidates:
        return None

    # Strong preference:
    # 1. meaningful score
    # 2. executable runtime
    # 3. direct arm-specific markers
    # 4. avoid generic infrastructure
    ranked = sorted(
        candidates,
        key=lambda item: (
            item.arm_scores.get(arm, 0),
            int(item.executable),
            len(item.transformation_markers),
            len(item.output_markers),
            len(item.input_markers),
            int(item.has_network),
        ),
        reverse=True,
    )

    return ranked[0]


# ==================================================================================================
# RESPONSIBILITY ANALYSIS
# ==================================================================================================

def analyze_scope(
    arm: str,
    candidates: List[FileAnalysis],
) -> Dict[str, Any]:

    if not candidates:
        return {
            "status": "NO_CANDIDATE",
            "recommendation": "EXPAND",
            "reason": "No production-relevant implementation candidate identified.",
        }

    primary = select_primary_candidate(candidates, arm)

    if primary is None:
        return {
            "status": "NO_PRIMARY",
            "recommendation": "EXPAND",
            "reason": "Candidates exist but no primary runtime candidate was selectable.",
        }

    strong_candidates = [
        item
        for item in candidates
        if item.arm_scores.get(arm, 0) >= 12
    ]

    executable_candidates = [
        item
        for item in candidates
        if item.executable
    ]

    network_candidates = [
        item
        for item in candidates
        if item.has_network
    ]

    db_write_candidates = [
        item
        for item in candidates
        if item.has_db_write
    ]

    signal_mutation_candidates = [
        item
        for item in candidates
        if item.has_signal_mutation
    ]

    transformation_union: Set[str] = set()
    input_union: Set[str] = set()
    output_union: Set[str] = set()
    consumer_union: Set[str] = set()

    for item in candidates:
        transformation_union |= item.transformation_markers
        input_union |= item.input_markers
        output_union |= item.output_markers
        consumer_union |= item.consumer_markers

    findings: List[str] = []
    recommendations: List[str] = []

    # ----------------------------------------------------------------------------------------------
    # RUNTIME
    # ----------------------------------------------------------------------------------------------

    if not executable_candidates:
        findings.append("NO_RUNTIME_EXECUTABLE_CANDIDATE")
        recommendations.append("EXPAND_RUNTIME_BOUNDARY")

    # ----------------------------------------------------------------------------------------------
    # INPUT
    # ----------------------------------------------------------------------------------------------

    if len(input_union) < 2:
        findings.append("WEAK_INPUT_SCOPE")
        recommendations.append("DEFINE_EXPLICIT_INPUT_CONTRACT")

    # ----------------------------------------------------------------------------------------------
    # TRANSFORMATION
    # ----------------------------------------------------------------------------------------------

    if len(transformation_union) == 0:
        findings.append("NO_CLEAR_TRANSFORMATION")
        recommendations.append("REPAIR_TRANSFORMATION_LAYER")

    elif len(transformation_union) == 1:
        findings.append("MINIMAL_TRANSFORMATION_SCOPE")
        recommendations.append("REVIEW_TRANSFORMATION_COMPLETENESS")

    # ----------------------------------------------------------------------------------------------
    # OUTPUT
    # ----------------------------------------------------------------------------------------------

    if len(output_union) == 0:
        findings.append("NO_CLEAR_OUTPUT")
        recommendations.append("DEFINE_EXPLICIT_OUTPUT_CONTRACT")

    # ----------------------------------------------------------------------------------------------
    # CONSUMER
    # ----------------------------------------------------------------------------------------------

    if len(consumer_union) == 0:
        findings.append("NO_CLEAR_CONSUMER")
        recommendations.append("TRACE_DOWNSTREAM_CONSUMER")

    # ----------------------------------------------------------------------------------------------
    # NETWORK
    # ----------------------------------------------------------------------------------------------

    if network_candidates:
        findings.append("NETWORK_DEPENDENCY_PRESENT")

    # ----------------------------------------------------------------------------------------------
    # DB WRITE
    # ----------------------------------------------------------------------------------------------

    if db_write_candidates:
        findings.append("DATABASE_WRITE_PRESENT")
        recommendations.append("ISOLATE_INFORMATION_ARM_FROM_STATE_MUTATION")

    # ----------------------------------------------------------------------------------------------
    # SIGNAL MUTATION
    # ----------------------------------------------------------------------------------------------

    if signal_mutation_candidates:
        findings.append("SIGNAL_MUTATION_PRESENT")
        recommendations.append("MOVE_SIGNAL_CREATION_TO_FUSION_OR_SIGNAL_LAYER")

    # ----------------------------------------------------------------------------------------------
    # DUPLICATION
    # ----------------------------------------------------------------------------------------------

    if len(strong_candidates) > 1:
        findings.append("MULTIPLE_STRONG_CANDIDATES")
        recommendations.append("RECONCILE_DUPLICATE_IMPLEMENTATIONS")

    # ----------------------------------------------------------------------------------------------
    # ARM-SPECIFIC RECOMMENDATIONS
    # ----------------------------------------------------------------------------------------------

    if arm == "TECHNICAL":
        ichimoku_present = any(
            any(
                token in item.transformation_markers
                for token in {
                    "ichimoku",
                    "tenkan",
                    "kijun",
                    "senkou",
                    "chikou",
                }
            )
            for item in candidates
        )

        if not ichimoku_present:
            findings.append("ICHIMOKU_NOT_DETECTED")
            recommendations.append("EXPAND_TECHNICAL_ARM_WITH_ICHIMOKU")

    if arm == "NEWS":
        if not network_candidates:
            findings.append("NO_LIVE_NEWS_NETWORK_BOUNDARY")
            recommendations.append("VERIFY_NEWS_PROVIDER_RUNTIME")

    if arm == "SOCIAL":
        if not any(
            "lunarcrush" in dep
            for item in candidates
            for dep in item.network_dependencies
        ):
            findings.append("LUNARCRUSH_RUNTIME_NOT_CONFIRMED")
            recommendations.append("VERIFY_SOCIAL_PROVIDER_RUNTIME")

    if arm == "FUNDAMENTAL":
        if len(input_union) < 3:
            findings.append("FUNDAMENTAL_INPUT_SCOPE_TOO_NARROW")
            recommendations.append("EXPAND_TOKENOMICS_ONCHAIN_VALUATION_INPUTS")

    if arm == "TRADINGVIEW":
        if not network_candidates:
            findings.append("TRADINGVIEW_NETWORK_BOUNDARY_NOT_CONFIRMED")
            recommendations.append("VERIFY_TRADINGVIEW_RUNTIME_BOUNDARY")

    # ----------------------------------------------------------------------------------------------
    # RECOMMENDATION
    # ----------------------------------------------------------------------------------------------

    recommendation = "KEEP"

    if "NO_RUNTIME_EXECUTABLE_CANDIDATE" in findings:
        recommendation = "EXPAND"

    elif "SIGNAL_MUTATION_PRESENT" in findings:
        recommendation = "REPAIR"

    elif "DATABASE_WRITE_PRESENT" in findings:
        recommendation = "REPAIR"

    elif "MULTIPLE_STRONG_CANDIDATES" in findings:
        recommendation = "MERGE"

    elif (
        "NO_CLEAR_TRANSFORMATION" in findings
        or "NO_CLEAR_OUTPUT" in findings
    ):
        recommendation = "REPAIR"

    elif arm == "TECHNICAL" and "ICHIMOKU_NOT_DETECTED" in findings:
        recommendation = "EXPAND"

    elif len(findings) >= 4:
        recommendation = "REPAIR"

    return {
        "status": "ANALYZED",
        "primary_candidate": primary.relative_path,
        "primary_score": primary.arm_scores.get(arm, 0),
        "candidate_count": len(candidates),
        "strong_candidate_count": len(strong_candidates),
        "executable_candidate_count": len(executable_candidates),
        "network_candidate_count": len(network_candidates),
        "database_write_candidate_count": len(db_write_candidates),
        "signal_mutation_candidate_count": len(signal_mutation_candidates),
        "input_scope": sorted(input_union),
        "transformation_scope": sorted(transformation_union),
        "output_scope": sorted(output_union),
        "consumer_scope": sorted(consumer_union),
        "findings": sorted(set(findings)),
        "recommendations": sorted(set(recommendations)),
        "recommendation": recommendation,
    }


# ==================================================================================================
# CROSS-ARM DUPLICATION
# ==================================================================================================

def calculate_cross_arm_overlap(
    analyses: List[FileAnalysis],
) -> List[Dict[str, Any]]:

    result = []

    for arm_a, definition_a in ARM_DEFINITIONS.items():
        candidates_a = select_arm_candidates(analyses, arm_a)

        for arm_b, definition_b in ARM_DEFINITIONS.items():

            if arm_a >= arm_b:
                continue

            candidates_b = select_arm_candidates(analyses, arm_b)

            if not candidates_a or not candidates_b:
                continue

            files_a = {
                item.relative_path
                for item in candidates_a
                if item.arm_scores.get(arm_a, 0) >= 10
            }

            files_b = {
                item.relative_path
                for item in candidates_b
                if item.arm_scores.get(arm_b, 0) >= 10
            }

            shared_files = sorted(files_a & files_b)

            if not shared_files:
                continue

            result.append(
                {
                    "arm_a": arm_a,
                    "arm_b": arm_b,
                    "shared_strong_files": shared_files,
                    "shared_file_count": len(shared_files),
                    "severity": (
                        "HIGH"
                        if len(shared_files) >= 3
                        else "MEDIUM"
                    ),
                }
            )

    return result


# ==================================================================================================
# ARCHITECTURE RECONCILIATION
# ==================================================================================================

def build_architecture_reconciliation(
    analyses: List[FileAnalysis],
) -> Dict[str, Any]:

    arms: Dict[str, Any] = {}

    for arm in ARM_DEFINITIONS:
        candidates = select_arm_candidates(analyses, arm)

        arms[arm] = {
            "candidate_files": [
                {
                    "file": item.relative_path,
                    "score": item.arm_scores.get(arm, 0),
                    "executable": item.executable,
                    "main_defined": item.main_defined,
                    "main_executed": item.main_executed,
                    "runtime_functions": sorted(item.runtime_functions),
                    "network_dependencies": sorted(item.network_dependencies),
                    "database_dependencies": sorted(item.database_dependencies),
                    "database_write_markers": sorted(item.database_write_markers),
                    "signal_mutation_markers": sorted(item.signal_mutation_markers),
                    "inputs": sorted(item.input_markers),
                    "transformations": sorted(item.transformation_markers),
                    "outputs": sorted(item.output_markers),
                    "consumers": sorted(item.consumer_markers),
                    "sha256": item.sha256,
                }
                for item in candidates[:20]
            ],
            "scope_analysis": analyze_scope(
                arm,
                candidates,
            ),
        }

    overlap = calculate_cross_arm_overlap(analyses)

    return {
        "arms": arms,
        "cross_arm_overlap": overlap,
    }


# ==================================================================================================
# ARCHITECTURAL HEALTH
# ==================================================================================================

def calculate_architecture_health(
    reconciliation: Dict[str, Any],
) -> Dict[str, Any]:

    scores: Dict[str, int] = {}
    critical_findings: List[Dict[str, Any]] = []

    for arm, data in reconciliation["arms"].items():
        scope = data["scope_analysis"]

        score = 100

        findings = scope.get("findings", [])

        penalties = {
            "NO_RUNTIME_EXECUTABLE_CANDIDATE": 35,
            "WEAK_INPUT_SCOPE": 15,
            "NO_CLEAR_TRANSFORMATION": 20,
            "MINIMAL_TRANSFORMATION_SCOPE": 8,
            "NO_CLEAR_OUTPUT": 20,
            "NO_CLEAR_CONSUMER": 15,
            "DATABASE_WRITE_PRESENT": 20,
            "SIGNAL_MUTATION_PRESENT": 25,
            "MULTIPLE_STRONG_CANDIDATES": 10,
            "ICHIMOKU_NOT_DETECTED": 10,
            "FUNDAMENTAL_INPUT_SCOPE_TOO_NARROW": 10,
        }

        for finding in findings:
            score -= penalties.get(finding, 5)

        score = max(0, min(100, score))

        scores[arm] = score

        if score < 60:
            critical_findings.append(
                {
                    "arm": arm,
                    "health_score": score,
                    "findings": findings,
                    "recommendation": scope.get("recommendation"),
                }
            )

    average = (
        sum(scores.values()) / len(scores)
        if scores
        else 0
    )

    return {
        "arm_health_scores": scores,
        "average_health_score": round(average, 2),
        "critical_arms": critical_findings,
    }


# ==================================================================================================
# FINAL RECONCILIATION DECISION
# ==================================================================================================

def build_final_decision(
    reconciliation: Dict[str, Any],
    health: Dict[str, Any],
) -> Dict[str, Any]:

    recommendations = {}

    for arm, data in reconciliation["arms"].items():
        recommendations[arm] = data["scope_analysis"].get(
            "recommendation",
            "UNKNOWN",
        )

    expand = [
        arm
        for arm, recommendation in recommendations.items()
        if recommendation == "EXPAND"
    ]

    repair = [
        arm
        for arm, recommendation in recommendations.items()
        if recommendation == "REPAIR"
    ]

    merge = [
        arm
        for arm, recommendation in recommendations.items()
        if recommendation == "MERGE"
    ]

    deprecate = [
        arm
        for arm, recommendation in recommendations.items()
        if recommendation == "DEPRECATE"
    ]

    if deprecate:
        status = "ARCHITECTURE_REQUIRES_DEPRECATION_REVIEW"
    elif merge:
        status = "ARCHITECTURE_REQUIRES_SCOPE_MERGE_REVIEW"
    elif repair:
        status = "ARCHITECTURE_REQUIRES_TARGETED_REPAIR"
    elif expand:
        status = "ARCHITECTURE_REQUIRES_TARGETED_EXPANSION"
    else:
        status = "ARCHITECTURE_SCOPE_RECONCILED"

    next_frontier = "INFORMATION_ARMS_SELECTED_ARM_CALL_CHAIN_FORENSICS"

    if expand:
        next_frontier = "INFORMATION_ARMS_SCOPE_EXPANSION_FORENSICS"

    if repair:
        next_frontier = "INFORMATION_ARMS_TARGETED_ARCHITECTURAL_REPAIR"

    if merge:
        next_frontier = "INFORMATION_ARMS_DUPLICATION_RECONCILIATION"

    return {
        "status": status,
        "recommendations": recommendations,
        "expand_arms": expand,
        "repair_arms": repair,
        "merge_arms": merge,
        "deprecate_arms": deprecate,
        "average_health_score": health["average_health_score"],
        "next_frontier": next_frontier,
    }


# ==================================================================================================
# REPORT
# ==================================================================================================

def build_report(
    analyses: List[FileAnalysis],
) -> Dict[str, Any]:

    syntax_invalid = [
        item
        for item in analyses
        if not item.syntax_valid
    ]

    reconciliation = build_architecture_reconciliation(
        analyses
    )

    health = calculate_architecture_health(
        reconciliation
    )

    final_decision = build_final_decision(
        reconciliation,
        health,
    )

    return {
        "project": "ArundaTrader",
        "component": "INFORMATION_ARMS_ARCHITECTURE",
        "version": "INFORMATION_ARMS_ARCHITECTURE_FORENSIC_AND_SCOPE_RECONCILIATION_v0.1",

        "mode": "READ_ONLY",

        "safety": {
            "database_write": False,
            "network_access": False,
            "producer_execution": False,
            "producer_import": False,
            "signal_creation": False,
            "signal_injection": False,
            "replay_execution": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
            "artifact_mutation": False,
        },

        "discovery": {
            "project_root": str(PROJECT_ROOT),
            "python_files_analyzed": len(analyses),
            "syntax_invalid_files": len(syntax_invalid),
            "excluded_backups": True,
            "excluded_forensic_scripts": True,
            "self_excluded": True,
        },

        "syntax_invalid": [
            {
                "file": item.relative_path,
                "error": item.syntax_error,
            }
            for item in syntax_invalid
        ],

        "architecture_reconciliation": reconciliation,

        "architecture_health": health,

        "final_decision": final_decision,
    }


# ==================================================================================================
# OUTPUT
# ==================================================================================================

def write_report(report: Dict[str, Any]) -> None:
    OUTPUT_REPORT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


# ==================================================================================================
# CONSOLE
# ==================================================================================================

def print_header() -> None:
    print("=" * 100)
    print("ARUNDA TRADER")
    print("INFORMATION ARMS ARCHITECTURE FORENSIC AND SCOPE RECONCILIATION v0.1")
    print("=" * 100)
    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ_ONLY")
    print("=" * 100)


def print_safety() -> None:
    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    fields = {
        "database_write": False,
        "network_access": False,
        "producer_execution": False,
        "producer_import": False,
        "signal_creation": False,
        "signal_injection": False,
        "replay_execution": False,
        "order_creation": False,
        "order_submission": False,
        "order_execution": False,
        "artifact_mutation": False,
    }

    for key, value in fields.items():
        print(f"{key:<25}: {value}")


def print_arm_summary(
    arm: str,
    data: Dict[str, Any],
) -> None:

    scope = data["scope_analysis"]

    print("=" * 100)
    print(f"[{arm}]")
    print("=" * 100)

    print(
        f"CANDIDATES              : "
        f"{scope.get('candidate_count', 0)}"
    )

    print(
        f"PRIMARY                 : "
        f"{scope.get('primary_candidate', '')}"
    )

    print(
        f"PRIMARY SCORE           : "
        f"{scope.get('primary_score', 0)}"
    )

    print(
        f"EXECUTABLE CANDIDATES   : "
        f"{scope.get('executable_candidate_count', 0)}"
    )

    print(
        f"NETWORK CANDIDATES      : "
        f"{scope.get('network_candidate_count', 0)}"
    )

    print(
        f"DB WRITE CANDIDATES     : "
        f"{scope.get('database_write_candidate_count', 0)}"
    )

    print(
        f"SIGNAL MUTATION         : "
        f"{scope.get('signal_mutation_candidate_count', 0)}"
    )

    print(
        f"INPUT SCOPE             : "
        f"{', '.join(scope.get('input_scope', []))}"
    )

    print(
        f"TRANSFORMATION SCOPE    : "
        f"{', '.join(scope.get('transformation_scope', []))}"
    )

    print(
        f"OUTPUT SCOPE            : "
        f"{', '.join(scope.get('output_scope', []))}"
    )

    print(
        f"CONSUMER SCOPE          : "
        f"{', '.join(scope.get('consumer_scope', []))}"
    )

    print(
        f"FINDINGS                : "
        f"{', '.join(scope.get('findings', [])) or 'NONE'}"
    )

    print(
        f"RECOMMENDATION         : "
        f"{scope.get('recommendation', 'UNKNOWN')}"
    )


def print_cross_arm_overlap(
    overlap: List[Dict[str, Any]],
) -> None:

    print("=" * 100)
    print("CROSS-ARM DUPLICATION / OVERLAP")
    print("=" * 100)

    if not overlap:
        print("NO_STRONG_CROSS_ARM_FILE_OVERLAP")
        return

    for item in overlap:
        print(
            f"{item['arm_a']} <-> {item['arm_b']} "
            f"| severity={item['severity']} "
            f"| shared={item['shared_file_count']}"
        )

        for filename in item["shared_strong_files"]:
            print(f"  - {filename}")


def print_final(
    report: Dict[str, Any],
) -> None:

    health = report["architecture_health"]
    final = report["final_decision"]

    print("=" * 100)
    print("ARCHITECTURE HEALTH")
    print("=" * 100)

    print(
        f"AVERAGE HEALTH SCORE : "
        f"{health['average_health_score']}"
    )

    for arm, score in health["arm_health_scores"].items():
        print(f"{arm:<20}: {score}")

    print("=" * 100)
    print("FINAL RECONCILIATION")
    print("=" * 100)

    print(
        f"STATUS          : "
        f"{final['status']}"
    )

    print(
        f"KEEP            : "
        f"{', '.join(
            arm
            for arm, rec in final['recommendations'].items()
            if rec == 'KEEP'
        ) or 'NONE'}"
    )

    print(
        f"REPAIR          : "
        f"{', '.join(final['repair_arms']) or 'NONE'}"
    )

    print(
        f"EXPAND          : "
        f"{', '.join(final['expand_arms']) or 'NONE'}"
    )

    print(
        f"MERGE           : "
        f"{', '.join(final['merge_arms']) or 'NONE'}"
    )

    print(
        f"DEPRECATE       : "
        f"{', '.join(final['deprecate_arms']) or 'NONE'}"
    )

    print(
        f"NEXT FRONTIER   : "
        f"{final['next_frontier']}"
    )

    print("=" * 100)
    print("OUTPUT")
    print("=" * 100)
    print(f"REPORT WRITTEN : {OUTPUT_REPORT}")


# ==================================================================================================
# MAIN
# ==================================================================================================

def main() -> int:

    print_header()
    print_safety()

    print("=" * 100)
    print("DISCOVERY")
    print("=" * 100)

    files = discover_python_files()

    print(
        f"Python files discovered : {len(files)}"
    )

    analyses: List[FileAnalysis] = []

    for path in files:
        analysis = analyze_file(path)
        analyses.append(analysis)

    syntax_invalid_count = sum(
        1
        for item in analyses
        if not item.syntax_valid
    )

    print(
        f"Syntax-invalid files    : "
        f"{syntax_invalid_count}"
    )

    report = build_report(analyses)

    arms = report[
        "architecture_reconciliation"
    ]["arms"]

    for arm, data in arms.items():
        print_arm_summary(
            arm,
            data,
        )

    print_cross_arm_overlap(
        report[
            "architecture_reconciliation"
        ]["cross_arm_overlap"]
    )

    print_final(report)

    write_report(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())