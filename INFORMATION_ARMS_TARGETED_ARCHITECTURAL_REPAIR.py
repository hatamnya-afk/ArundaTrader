# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
INFORMATION ARMS TARGETED ARCHITECTURAL REPAIR v0.1

MODE:
    READ_ONLY

PURPOSE:
    Targeted architectural repair reconnaissance for all information arms.

ARMS:
    MARKET
    TECHNICAL
    NEWS
    SOCIAL
    FUNDAMENTAL
    TRADINGVIEW

SAFETY:
    - No DB writes
    - No source mutations
    - No imports of production modules
    - No network access
    - No signal creation
    - No execution
    - No deletion
    - No rename
    - No ALTER / CREATE / UPDATE / INSERT / DELETE

IMPORTANT:
    This script does NOT repair production architecture.
    It creates a forensic repair manifest only.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


# ============================================================================
# CONFIG
# ============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

REPORT_FILE = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_INFORMATION_ARMS_TARGETED_ARCHITECTURAL_REPAIR_REPORT.json"
)

MANIFEST_FILE = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_INFORMATION_ARMS_TARGETED_ARCHITECTURAL_REPAIR_MANIFEST.json"
)

MAX_FILE_SIZE = 3_000_000


ARMS = {
    "MARKET": {
        "primary_candidates": [
            "market_adapter.py",
            "market_data_engine.py",
            "market_state_reader.py",
            "market_regime.py",
            "market_structure_engine.py",
        ],
        "keywords": {
            "market",
            "market_data",
            "market_records",
            "order_book",
            "orderbook",
            "ohlc",
            "price",
            "volume",
            "spread",
            "depth",
            "ticker",
            "symbol",
            "snapshot",
            "volatility",
        },
    },

    "TECHNICAL": {
        "primary_candidates": [
            "indicator_engine.py",
            "technical_engine.py",
            "pattern_engine.py",
            "feature_engine.py",
            "market_structure_engine.py",
        ],
        "keywords": {
            "technical",
            "indicator",
            "indicators",
            "rsi",
            "macd",
            "ema",
            "sma",
            "wma",
            "atr",
            "adx",
            "bollinger",
            "stochastic",
            "ichimoku",
            "tenkan",
            "kijun",
            "senkou",
            "chikou",
            "momentum",
            "trend",
            "pattern",
            "technical_score",
        },
    },

    "NEWS": {
        "primary_candidates": [
            "news_adapter.py",
            "news_engine.py",
            "catalyst_engine.py",
        ],
        "keywords": {
            "news",
            "article",
            "rss",
            "headline",
            "catalyst",
            "sentiment",
            "news_score",
            "source",
            "feed",
        },
    },

    "SOCIAL": {
        "primary_candidates": [
            "social_engine.py",
            "lunarcrush.py",
            "lunar_hunter.py",
            "coinalyze_positioning.py",
        ],
        "keywords": {
            "social",
            "social_score",
            "social_volume",
            "engagement",
            "mentions",
            "holders",
            "lunarcrush",
            "community",
            "trend",
        },
    },

    "FUNDAMENTAL": {
        "primary_candidates": [
            "step10b_regime_quality_cross_feature_validation.py",
            "market_state_reader.py",
            "fundamental_engine.py",
        ],
        "keywords": {
            "fundamental",
            "valuation",
            "market_cap",
            "holders",
            "supply",
            "tokenomics",
            "revenue",
            "earnings",
            "valuation",
            "quality",
            "regime",
        },
    },

    "TRADINGVIEW": {
        "primary_candidates": [
            "tradingview_adapter.py",
            "tradingview_engine.py",
            "catalyst_engine.py",
        ],
        "keywords": {
            "tradingview",
            "tv",
            "technical",
            "indicator",
            "trend",
            "rating",
            "recommendation",
            "oscillator",
            "moving_average",
        },
    },
}


# ============================================================================
# SAFETY
# ============================================================================

WRITE_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bALTER\b",
    r"\bCREATE\s+TABLE\b",
    r"\bDROP\s+TABLE\b",
    r"\bREPLACE\s+INTO\b",
    r"\bUPSERT\b",
    r"\.execute\s*\(",
    r"\.executemany\s*\(",
    r"\.commit\s*\(",
    r"\.rollback\s*\(",
    r"\bto_sql\s*\(",
    r"\bwrite_text\s*\(",
    r"\bwrite_bytes\s*\(",
    r"\bopen\s*\([^)]*[\"']w",
]

NETWORK_PATTERNS = [
    r"\brequests\.",
    r"\burllib\.",
    r"\bhttpx\.",
    r"\baiohttp\.",
    r"\bsocket\.",
    r"\bwebsocket\b",
    r"\burlopen\s*\(",
    r"\bfetch\s*\(",
    r"\bcurl\b",
]

SIGNAL_MUTATION_PATTERNS = [
    r"\bsignal\b.*\b(insert|update|create|write|save|commit)\b",
    r"\bcreate_signal\b",
    r"\bemit_signal\b",
    r"\binject_signal\b",
    r"\bfusion_signals\b",
    r"\bsignal_outcomes\b",
    r"\bdecision\b.*=",
    r"\border_intent\b.*=",
]

EXECUTION_PATTERNS = [
    r"\border\b",
    r"\bexecute_order\b",
    r"\bsubmit_order\b",
    r"\bplace_order\b",
    r"\btrade\b",
    r"\bexecution\b",
    r"\bposition\b",
]


# ============================================================================
# HELPERS
# ============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def safe_read(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:
        return ""


def regex_hits(text: str, patterns: list[str]) -> list[str]:
    hits = []

    for pattern in patterns:
        try:
            if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                hits.append(pattern)
        except re.error:
            pass

    return hits


def normalized_tokens(text: str) -> set[str]:
    return set(
        re.findall(
            r"[A-Za-z_][A-Za-z0-9_]+",
            text.lower(),
        )
    )


def syntax_check(path: Path) -> tuple[bool, str | None]:

    try:
        source = safe_read(path)

        if not source:
            return False, "EMPTY_OR_UNREADABLE"

        ast.parse(source, filename=str(path))

        return True, None

    except SyntaxError as e:
        return False, (
            f"SyntaxError:{e.lineno}:{e.offset}:{e.msg}"
        )

    except Exception as e:
        return False, f"{type(e).__name__}:{e}"


def is_probable_archive(path: Path) -> bool:
    p = str(path).lower()

    archive_markers = [
        "\\backup",
        "\\backups",
        "\\archive",
        "\\deprecated",
        "\\old",
        "\\indicator_repair_backups",
        "_backup",
        "_deprecated",
        ".bak",
    ]

    return any(marker in p for marker in archive_markers)


def is_validation_script(path: Path) -> bool:
    name = path.name.lower()

    markers = [
        "validation",
        "forensic",
        "audit",
        "reconciliation",
        "repair",
        "verify",
        "verification",
        "quality",
        "discovery",
        "readiness",
        "gate",
    ]

    return any(marker in name for marker in markers)


def is_runtime_candidate(path: Path) -> bool:
    return (
        path.suffix.lower() == ".py"
        and not is_probable_archive(path)
        and not is_validation_script(path)
    )


def filename_score(path: Path, arm: str) -> int:

    name = path.name.lower()
    config = ARMS[arm]

    score = 0

    for candidate in config["primary_candidates"]:
        if name == candidate.lower():
            score += 100

    for keyword in config["keywords"]:
        if keyword.lower() in name:
            score += 10

    return score


def content_score(text: str, arm: str) -> int:

    if not text:
        return 0

    tokens = normalized_tokens(text)
    keywords = {
        k.lower()
        for k in ARMS[arm]["keywords"]
    }

    shared = tokens.intersection(keywords)

    score = min(len(shared) * 2, 40)

    return score


def classify_role(path: Path, text: str) -> str:

    name = path.name.lower()

    if is_probable_archive(path):
        return "ARCHIVE_OR_BACKUP"

    if is_validation_script(path):
        return "VALIDATION_FORENSIC"

    if "adapter" in name:
        return "ADAPTER"

    if "engine" in name:
        return "ENGINE"

    if "reader" in name:
        return "READER"

    if "recorder" in name:
        return "RECORDER"

    if "pipeline" in name:
        return "PIPELINE"

    if "runner" in name:
        return "RUNNER"

    if "gate" in name:
        return "GATE"

    if "scorer" in name:
        return "SCORER"

    return "OTHER"


def extract_imports(path: Path, text: str) -> list[str]:

    imports = []

    try:
        tree = ast.parse(text, filename=str(path))

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

    except Exception:
        pass

    return sorted(set(imports))


def find_local_dependencies(
    path: Path,
    imports: list[str],
) -> list[str]:

    local = []

    for imp in imports:

        module = imp.split(".")[0]

        candidate_py = PROJECT_ROOT / f"{module}.py"

        candidate_pkg = PROJECT_ROOT / module

        if candidate_py.exists():
            local.append(str(candidate_py.relative_to(PROJECT_ROOT)))

        elif candidate_pkg.exists():
            local.append(str(candidate_pkg.relative_to(PROJECT_ROOT)))

    return sorted(set(local))


# ============================================================================
# FILE FORENSICS
# ============================================================================

def analyze_file(path: Path) -> dict[str, Any]:

    text = safe_read(path)

    syntax_ok, syntax_error = syntax_check(path)

    imports = extract_imports(path, text)

    write_hits = regex_hits(text, WRITE_PATTERNS)
    network_hits = regex_hits(text, NETWORK_PATTERNS)
    signal_hits = regex_hits(text, SIGNAL_MUTATION_PATTERNS)
    execution_hits = regex_hits(text, EXECUTION_PATTERNS)

    return {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "size": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else None,
        "syntax_valid": syntax_ok,
        "syntax_error": syntax_error,
        "role": classify_role(path, text),
        "runtime_candidate": is_runtime_candidate(path),
        "archive_or_backup": is_probable_archive(path),
        "validation_or_forensic": is_validation_script(path),
        "db_write": bool(write_hits),
        "db_write_hits": write_hits,
        "network_dependency": bool(network_hits),
        "network_hits": network_hits,
        "signal_mutation": bool(signal_hits),
        "signal_hits": signal_hits,
        "execution_surface": bool(execution_hits),
        "execution_hits": execution_hits,
        "imports": imports,
        "local_dependencies": find_local_dependencies(path, imports),
    }


# ============================================================================
# ARM MAPPING
# ============================================================================

def map_arm_candidates(
    files: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:

    result = {}

    for arm, config in ARMS.items():

        candidates = []

        for item in files:

            path = PROJECT_ROOT / item["file"]

            name_score = filename_score(path, arm)

            text = safe_read(path)

            content_score_value = content_score(
                text,
                arm,
            )

            score = name_score + content_score_value

            if score > 0:

                enriched = dict(item)

                enriched["arm_score"] = score
                enriched["filename_score"] = name_score
                enriched["content_score"] = content_score_value

                candidates.append(enriched)

        candidates.sort(
            key=lambda x: (
                x["arm_score"],
                x["runtime_candidate"],
                not x["archive_or_backup"],
                not x["validation_or_forensic"],
            ),
            reverse=True,
        )

        result[arm] = candidates

    return result


# ============================================================================
# DUPLICATION
# ============================================================================

def calculate_duplicate_groups(
    files: list[dict[str, Any]]
) -> list[list[str]]:

    by_hash = defaultdict(list)

    for item in files:

        if item["sha256"]:
            by_hash[item["sha256"]].append(
                item["file"]
            )

    return [
        paths
        for paths in by_hash.values()
        if len(paths) > 1
    ]


def calculate_name_families(
    files: list[dict[str, Any]]
) -> dict[str, list[str]]:

    families = defaultdict(list)

    for item in files:

        stem = Path(item["file"]).stem.lower()

        normalized = re.sub(
            r"(_v\d+(\.\d+)*)",
            "",
            stem,
        )

        normalized = re.sub(
            r"_(audit|forensic|repair|validation|verify|verification)$",
            "",
            normalized,
        )

        families[normalized].append(
            item["file"]
        )

    return {
        k: sorted(v)
        for k, v in families.items()
        if len(v) > 1
    }


# ============================================================================
# ARM HEALTH
# ============================================================================

def determine_arm_state(
    arm: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:

    runtime = [
        x for x in candidates
        if x["runtime_candidate"]
    ]

    valid_runtime = [
        x for x in runtime
        if x["syntax_valid"]
    ]

    primary = candidates[:10]

    write_count = sum(
        x["db_write"]
        for x in candidates
    )

    network_count = sum(
        x["network_dependency"]
        for x in candidates
    )

    mutation_count = sum(
        x["signal_mutation"]
        for x in candidates
    )

    execution_count = sum(
        x["execution_surface"]
        for x in candidates
    )

    validation_count = sum(
        x["validation_or_forensic"]
        for x in candidates
    )

    archive_count = sum(
        x["archive_or_backup"]
        for x in candidates
    )

    syntax_invalid = sum(
        not x["syntax_valid"]
        for x in candidates
    )

    primary_runtime = None

    for candidate in ARMS[arm]["primary_candidates"]:

        match = next(
            (
                x
                for x in candidates
                if Path(x["file"]).name.lower()
                == candidate.lower()
            ),
            None,
        )

        if match:
            primary_runtime = match
            break

    problems = []

    if not primary_runtime:
        problems.append(
            "PRIMARY_OWNER_UNRESOLVED"
        )

    if len(runtime) == 0:
        problems.append(
            "NO_RUNTIME_CANDIDATE"
        )

    if len(valid_runtime) == 0:
        problems.append(
            "NO_SYNTAX_VALID_RUNTIME_CANDIDATE"
        )

    if len(candidates) > 20:
        problems.append(
            "EXCESSIVE_CANDIDATE_SURFACE"
        )

    if write_count:
        problems.append(
            "DB_WRITE_PRESENT_IN_ARM_CANDIDATES"
        )

    if network_count:
        problems.append(
            "NETWORK_DEPENDENCY_PRESENT"
        )

    if mutation_count:
        problems.append(
            "SIGNAL_MUTATION_PRESENT"
        )

    if execution_count:
        problems.append(
            "EXECUTION_SURFACE_CONTAMINATION"
        )

    if syntax_invalid:
        problems.append(
            "SYNTAX_INVALID_FILES_PRESENT"
        )

    if archive_count:
        problems.append(
            "ARCHIVE_BACKUP_CONTAMINATION"
        )

    if validation_count:
        problems.append(
            "VALIDATION_SCRIPT_CONTAMINATION"
        )

    # ------------------------------------------------------------------------
    # OWNER DECISION
    # ------------------------------------------------------------------------

    owner_candidates = [
        x for x in candidates
        if x["runtime_candidate"]
    ]

    owner_candidates.sort(
        key=lambda x: x["arm_score"],
        reverse=True,
    )

    owner = (
        owner_candidates[0]
        if owner_candidates
        else None
    )

    # ------------------------------------------------------------------------
    # DECISION
    # ------------------------------------------------------------------------

    if not owner:
        decision = "EXPAND"

    elif owner["db_write"] or owner["signal_mutation"]:
        decision = "REPAIR"

    elif len(owner_candidates) > 5:
        decision = "MERGE_OR_SPLIT"

    elif not owner["syntax_valid"]:
        decision = "REPAIR"

    elif owner["network_dependency"]:
        decision = "REPAIR"

    else:
        decision = "KEEP_WITH_TARGETED_REPAIR"

    # ------------------------------------------------------------------------
    # TECHNICAL SPECIAL CHECK
    # ------------------------------------------------------------------------

    technical_specific = {}

    if arm == "TECHNICAL":

        technical_keywords = [
            "rsi",
            "macd",
            "ema",
            "sma",
            "wma",
            "atr",
            "adx",
            "bollinger",
            "stochastic",
            "ichimoku",
            "tenkan",
            "kijun",
            "senkou",
            "chikou",
            "momentum",
            "trend",
            "pattern",
        ]

        coverage = Counter()

        for candidate in candidates:

            text = safe_read(
                PROJECT_ROOT / candidate["file"]
            ).lower()

            for keyword in technical_keywords:

                if keyword in text:
                    coverage[keyword] += 1

        technical_specific = {
            "indicator_coverage": dict(coverage),
            "missing_indicator_domains": [
                k
                for k in technical_keywords
                if coverage[k] == 0
            ],
            "multi_owner_indicators": {
                k: v
                for k, v in coverage.items()
                if v > 2
            },
        }

        if technical_specific[
            "missing_indicator_domains"
        ]:
            problems.append(
                "TECHNICAL_SCOPE_MAY_BE_INCOMPLETE"
            )

        if technical_specific[
            "multi_owner_indicators"
        ]:
            problems.append(
                "TECHNICAL_INDICATOR_DUPLICATION"
            )

    return {
        "arm": arm,
        "candidate_count": len(candidates),
        "runtime_candidates": len(runtime),
        "syntax_valid_runtime_candidates": len(valid_runtime),
        "db_write_candidates": write_count,
        "network_candidates": network_count,
        "signal_mutation_candidates": mutation_count,
        "execution_surface_candidates": execution_count,
        "validation_candidates": validation_count,
        "archive_candidates": archive_count,
        "syntax_invalid_candidates": syntax_invalid,
        "primary_owner_candidate": (
            primary_runtime["file"]
            if primary_runtime
            else None
        ),
        "resolved_owner": (
            owner["file"]
            if owner
            else None
        ),
        "decision": decision,
        "problems": sorted(set(problems)),
        "technical_specific": technical_specific,
    }


# ============================================================================
# CROSS ARM CONTAMINATION
# ============================================================================

def cross_arm_analysis(
    arm_candidates: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:

    result = []

    arms = list(arm_candidates.keys())

    file_to_arms = defaultdict(list)

    for arm in arms:

        for item in arm_candidates[arm]:

            file_to_arms[item["file"]].append(
                arm
            )

    for file, owners in file_to_arms.items():

        unique_owners = sorted(set(owners))

        if len(unique_owners) > 1:

            result.append({
                "file": file,
                "arms": unique_owners,
                "count": len(unique_owners),
                "severity": (
                    "HIGH"
                    if len(unique_owners) >= 3
                    else "MEDIUM"
                ),
            })

    result.sort(
        key=lambda x: (
            x["count"],
            x["severity"],
        ),
        reverse=True,
    )

    return result


# ============================================================================
# DEPENDENCY DIRECTION
# ============================================================================

def dependency_direction(
    files: list[dict[str, Any]]
) -> dict[str, Any]:

    arm_by_file = {}

    for arm, config in ARMS.items():

        for item in files:

            path = Path(item["file"])

            name = path.name.lower()

            if any(
                name == candidate.lower()
                for candidate in config["primary_candidates"]
            ):
                arm_by_file[item["file"]] = arm

    edges = Counter()

    for item in files:

        source_arm = arm_by_file.get(
            item["file"]
        )

        if not source_arm:
            continue

        for dependency in item[
            "local_dependencies"
        ]:

            target_arm = arm_by_file.get(
                dependency
            )

            if target_arm and target_arm != source_arm:

                edges[
                    f"{source_arm}->{target_arm}"
                ] += 1

    return {
        "cross_arm_edges": dict(edges),
        "edge_count": sum(edges.values()),
    }


# ============================================================================
# REPAIR MANIFEST
# ============================================================================

def build_repair_manifest(
    arm_health: dict[str, Any],
    cross_arm: list[dict[str, Any]],
    duplicates: list[list[str]],
    name_families: dict[str, list[str]],
) -> dict[str, Any]:

    manifest = {
        "version": "INFORMATION_ARMS_TARGETED_ARCHITECTURAL_REPAIR_MANIFEST_v0.1",
        "mode": "READ_ONLY",
        "project_root": str(PROJECT_ROOT),
        "repair_order": [],
        "arms": {},
        "global_actions": [],
    }

    # ------------------------------------------------------------------------
    # Priority order
    # ------------------------------------------------------------------------

    priority = []

    for arm, health in arm_health.items():

        score = 0

        score += health["db_write_candidates"] * 5
        score += health["signal_mutation_candidates"] * 5
        score += health["execution_surface_candidates"] * 4
        score += health["network_candidates"] * 3
        score += health["syntax_invalid_candidates"] * 2
        score += health["archive_candidates"]
        score += health["validation_candidates"]

        priority.append(
            (score, arm)
        )

    priority.sort(reverse=True)

    manifest["repair_order"] = [
        arm
        for _, arm in priority
    ]

    # ------------------------------------------------------------------------
    # Arm actions
    # ------------------------------------------------------------------------

    for arm, health in arm_health.items():

        actions = []

        if health[
            "primary_owner_candidate"
        ] is None:

            actions.append(
                "RESOLVE_PRIMARY_OWNER"
            )

        if health[
            "db_write_candidates"
        ]:

            actions.append(
                "REMOVE_INFORMATION_LAYER_DB_WRITE_RESPONSIBILITY"
            )

        if health[
            "signal_mutation_candidates"
        ]:

            actions.append(
                "REMOVE_SIGNAL_MUTATION_FROM_INFORMATION_ARM"
            )

        if health[
            "execution_surface_candidates"
        ]:

            actions.append(
                "REMOVE_EXECUTION_SURFACE_CONTAMINATION"
            )

        if health[
            "network_candidates"
        ]:

            actions.append(
                "ISOLATE_NETWORK_ACCESS_BEHIND_ADAPTER_BOUNDARY"
            )

        if health[
            "syntax_invalid_candidates"
        ]:

            actions.append(
                "ISOLATE_OR_REPAIR_SYNTAX_INVALID_FILES"
            )

        if health[
            "archive_candidates"
        ]:

            actions.append(
                "SEPARATE_ARCHIVE_BACKUP_FROM_RUNTIME_SCOPE"
            )

        if health[
            "validation_candidates"
        ]:

            actions.append(
                "SEPARATE_VALIDATION_FORENSIC_SCRIPTS_FROM_RUNTIME_SCOPE"
            )

        if health["decision"] == "MERGE_OR_SPLIT":

            actions.append(
                "RECONCILE_MULTIPLE_RUNTIME_OWNERS"
            )

        if health["decision"] == "EXPAND":

            actions.append(
                "EXPAND_ARM_RUNTIME_SCOPE"
            )

        if arm == "TECHNICAL":

            technical = health[
                "technical_specific"
            ]

            if technical.get(
                "missing_indicator_domains"
            ):

                actions.append(
                    "REVIEW_TECHNICAL_INDICATOR_COVERAGE"
                )

            if technical.get(
                "multi_owner_indicators"
            ):

                actions.append(
                    "CONSOLIDATE_TECHNICAL_INDICATOR_OWNERSHIP"
                )

        manifest["arms"][arm] = {
            "decision": health["decision"],
            "resolved_owner": health[
                "resolved_owner"
            ],
            "actions": sorted(set(actions)),
            "problems": health["problems"],
        }

    # ------------------------------------------------------------------------
    # Global actions
    # ------------------------------------------------------------------------

    if duplicates:

        manifest["global_actions"].append(
            "REVIEW_EXACT_DUPLICATE_FILE_GROUPS"
        )

    if name_families:

        manifest["global_actions"].append(
            "REVIEW_VERSIONED_AND_PARALLEL_RUNTIME_FAMILIES"
        )

    high_cross_arm = [
        x for x in cross_arm
        if x["severity"] == "HIGH"
    ]

    if high_cross_arm:

        manifest["global_actions"].append(
            "REPAIR_CROSS_ARM_OWNERSHIP_CONTAMINATION"
        )

    manifest["global_actions"].extend([
        "ESTABLISH_SINGLE_OWNER_PER_INFORMATION_ARM",
        "ENFORCE_INFORMATION_LAYER_READ_ONLY_CONTRACT",
        "SEPARATE_ADAPTER_ENGINE_ANALYSIS_AND_CONSUMER_BOUNDARIES",
        "PROHIBIT_SIGNAL_AND_EXECUTION_MUTATION_IN_INFORMATION_ARMS",
        "KEEP_FORENSIC_VALIDATION_SCRIPTS_OUT_OF_RUNTIME_OWNERSHIP",
    ])

    return manifest


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:

    print("=" * 100)
    print("ARUNDA TRADER")
    print("INFORMATION ARMS TARGETED ARCHITECTURAL REPAIR v0.1")
    print("=" * 100)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ_ONLY")
    print("=" * 100)

    if not PROJECT_ROOT.exists():

        print("ERROR: PROJECT ROOT NOT FOUND")

        return 1

    # ------------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------------

    python_files = sorted(
        PROJECT_ROOT.rglob("*.py")
    )

    print()
    print("DISCOVERY")
    print("-" * 100)
    print(
        f"Python files discovered : {len(python_files)}"
    )

    # ------------------------------------------------------------------------
    # File analysis
    # ------------------------------------------------------------------------

    analyzed = []

    for path in python_files:

        try:
            analyzed.append(
                analyze_file(path)
            )
        except Exception as e:

            analyzed.append({
                "file": str(
                    path.relative_to(PROJECT_ROOT)
                ),
                "analysis_error": str(e),
                "syntax_valid": False,
            })

    syntax_invalid = [
        x for x in analyzed
        if not x.get("syntax_valid", False)
    ]

    print(
        f"Syntax-invalid files    : {len(syntax_invalid)}"
    )

    # ------------------------------------------------------------------------
    # Arm mapping
    # ------------------------------------------------------------------------

    arm_candidates = map_arm_candidates(
        analyzed
    )

    # ------------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------------

    arm_health = {}

    for arm in ARMS:

        health = determine_arm_state(
            arm,
            arm_candidates[arm],
        )

        arm_health[arm] = health

    # ------------------------------------------------------------------------
    # Cross arm
    # ------------------------------------------------------------------------

    cross_arm = cross_arm_analysis(
        arm_candidates
    )

    # ------------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------------

    dependencies = dependency_direction(
        analyzed
    )

    # ------------------------------------------------------------------------
    # Duplicate groups
    # ------------------------------------------------------------------------

    duplicates = calculate_duplicate_groups(
        analyzed
    )

    name_families = calculate_name_families(
        analyzed
    )

    # ------------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------------

    manifest = build_repair_manifest(
        arm_health,
        cross_arm,
        duplicates,
        name_families,
    )

    # ------------------------------------------------------------------------
    # Final report
    # ------------------------------------------------------------------------

    report = {
        "version":
            "INFORMATION_ARMS_TARGETED_ARCHITECTURAL_REPAIR_v0.1",

        "mode":
            "READ_ONLY",

        "project_root":
            str(PROJECT_ROOT),

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
            "source_mutation": False,
            "file_deletion": False,
            "file_rename": False,
        },

        "discovery": {
            "python_files": len(python_files),
            "syntax_invalid": len(syntax_invalid),
            "exact_duplicate_groups": len(duplicates),
            "versioned_name_families": len(name_families),
        },

        "arms": {
            arm: {
                "health": arm_health[arm],
                "top_candidates":
                    arm_candidates[arm][:20],
            }
            for arm in ARMS
        },

        "cross_arm_ownership": cross_arm[:200],

        "dependency_direction": dependencies,

        "duplicate_groups": duplicates[:200],

        "name_families": {
            k: v
            for k, v in list(
                name_families.items()
            )[:300]
        },

        "repair_manifest": manifest,
    }

    # ------------------------------------------------------------------------
    # WRITE REPORT
    #
    # These are OUTPUT ARTIFACTS only.
    # No source / DB / production mutation occurs.
    # ------------------------------------------------------------------------

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    MANIFEST_FILE.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------------------------
    # Console summary
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("ARM RECONCILIATION")
    print("=" * 100)

    for arm, health in arm_health.items():

        print()
        print(f"[{arm}]")

        print(
            f"Candidates                 : "
            f"{health['candidate_count']}"
        )

        print(
            f"Runtime candidates         : "
            f"{health['runtime_candidates']}"
        )

        print(
            f"Syntax-valid runtime       : "
            f"{health['syntax_valid_runtime_candidates']}"
        )

        print(
            f"DB write candidates        : "
            f"{health['db_write_candidates']}"
        )

        print(
            f"Network candidates         : "
            f"{health['network_candidates']}"
        )

        print(
            f"Signal mutation candidates: "
            f"{health['signal_mutation_candidates']}"
        )

        print(
            f"Execution surface         : "
            f"{health['execution_surface_candidates']}"
        )

        print(
            f"Primary owner              : "
            f"{health['primary_owner_candidate']}"
        )

        print(
            f"Resolved owner             : "
            f"{health['resolved_owner']}"
        )

        print(
            f"Decision                   : "
            f"{health['decision']}"
        )

        if health["problems"]:

            print("Problems:")

            for problem in health["problems"]:
                print(
                    f"  - {problem}"
                )

    print()
    print("=" * 100)
    print("CROSS-ARM OWNERSHIP")
    print("=" * 100)

    print(
        f"Cross-arm shared files : "
        f"{len(cross_arm)}"
    )

    print(
        f"High severity          : "
        f"{sum(x['severity'] == 'HIGH' for x in cross_arm)}"
    )

    print()
    print("=" * 100)
    print("REPAIR ORDER")
    print("=" * 100)

    for index, arm in enumerate(
        manifest["repair_order"],
        start=1,
    ):

        print(
            f"{index}. {arm}"
        )

    print()
    print("=" * 100)
    print("OUTPUT")
    print("=" * 100)

    print(
        f"REPORT   : {REPORT_FILE}"
    )

    print(
        f"MANIFEST : {MANIFEST_FILE}"
    )

    print("=" * 100)
    print("STATUS : TARGETED_REPAIR_MANIFEST_READY")
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())