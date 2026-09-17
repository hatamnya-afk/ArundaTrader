# =============================================================================
# ARUNDA — FIND REAL PRODUCTION ENTRYPOINT v0.1
# =============================================================================
#
# PURPOSE
# -------
# Find the REAL production runtime entrypoint that starts the market-data
# pipeline and eventually produces:
#
#     bars_by_asset
#     indicators_by_asset
#     structures_by_asset
#
# This script is FORENSIC ONLY.
#
# RULES
# -----
# - READ ONLY
# - NO IMPORTS OF PROJECT MODULES
# - NO PIPELINE EXECUTION
# - NO DATABASE ACCESS
# - NO DATABASE WRITES
# - NO SOURCE MODIFICATION
# - AST ONLY
# - NO SYNTHETIC DATA
# - NO ASSUMPTIONS
#
# =============================================================================

from __future__ import annotations

import ast
import os
from pathlib import Path


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_ROOT = Path(
    r"C:\Users\ASUS\ArundaTrader"
)

TARGETS = {
    "market_data",
    "bars",
    "bars_by_asset",
    "indicators",
    "indicators_by_asset",
    "structures",
    "structures_by_asset",
    "signal_engine",
    "feature_contract",
    "signal_scorer",
    "decision_engine",
}

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".venv",
    "venv",
    "env",
    "node_modules",
}


# =============================================================================
# RESULT STORAGE
# =============================================================================

files = []

parse_errors = []

function_records = []

call_records = []

assignment_records = []

entrypoint_records = []

pipeline_records = []


# =============================================================================
# HELPERS
# =============================================================================

def line(node):
    return getattr(node, "lineno", -1)


def source_segment(source, node):
    try:
        return ast.get_source_segment(source, node)
    except Exception:
        return None


def is_project_python_file(path):
    return (
        path.suffix.lower() == ".py"
        and path.is_file()
    )


def should_skip(path):
    return any(
        part in EXCLUDED_DIRS
        for part in path.parts
    )


def call_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts = []

        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ""


def names_in_node(node):
    result = set()

    for child in ast.walk(node):

        if isinstance(child, ast.Name):
            result.add(child.id)

        elif isinstance(child, ast.Attribute):
            result.add(child.attr)

    return result


def contains_target_name(node):
    names = names_in_node(node)

    return bool(
        names.intersection(TARGETS)
    )


def contains_any_pipeline_term(node):
    names = names_in_node(node)

    pipeline_terms = {
        "market_data",
        "bars",
        "bars_by_asset",
        "indicators",
        "indicators_by_asset",
        "structures",
        "structures_by_asset",
        "build_all",
        "load_market_data",
        "load_bars",
        "build_bars",
        "get_bars",
        "load_indicators",
        "build_indicators",
        "calculate_indicators",
        "get_indicators",
        "load_structures",
        "build_structures",
        "calculate_structures",
        "get_structures",
        "signal_engine",
        "feature_contract",
        "signal_scorer",
        "decision_engine",
    }

    return bool(
        names.intersection(
            pipeline_terms
        )
    )


# =============================================================================
# PASS 1 — DISCOVER PYTHON FILES
# =============================================================================

for root, dirs, filenames in os.walk(PROJECT_ROOT):

    dirs[:] = [
        d
        for d in dirs
        if d not in EXCLUDED_DIRS
    ]

    for filename in filenames:

        path = Path(root) / filename

        if not is_project_python_file(path):
            continue

        if should_skip(path):
            continue

        files.append(path)


# =============================================================================
# PASS 2 — AST SCAN
# =============================================================================

for path in files:

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception as error:

        parse_errors.append(
            {
                "file": str(path),
                "error": (
                    type(error).__name__
                    + ": "
                    + str(error)
                ),
            }
        )

        continue

    # -------------------------------------------------------------------------
    # FUNCTIONS
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            params = []

            for arg in (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
            ):

                params.append(arg.arg)

            function_records.append(
                {
                    "file": str(path),
                    "line": line(node),
                    "name": node.name,
                    "params": params,
                }
            )

    # -------------------------------------------------------------------------
    # DIRECT EXECUTION BLOCKS
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        if not isinstance(node, ast.If):
            continue

        test = node.test

        if not (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(
                test.ops[0],
                ast.Eq,
            )
        ):
            continue

        left = test.left

        if not (
            isinstance(
                left,
                ast.Name,
            )
            and left.id == "__name__"
        ):
            continue

        right = test.comparators[0]

        if not (
            isinstance(
                right,
                ast.Constant,
            )
            and right.value == "__main__"
        ):
            continue

        entrypoint_records.append(
            {
                "file": str(path),
                "line": line(node),
                "source": source_segment(
                    source,
                    node,
                ),
            }
        )

    # -------------------------------------------------------------------------
    # CALLS
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        name = call_name(
            node.func
        )

        if not name:
            continue

        if (
            any(
                target in name
                for target in (
                    "market",
                    "bar",
                    "indicator",
                    "structure",
                    "signal_engine",
                    "feature_contract",
                    "signal_scorer",
                    "decision_engine",
                )
            )
            or contains_any_pipeline_term(node)
        ):

            call_records.append(
                {
                    "file": str(path),
                    "line": line(node),
                    "name": name,
                    "args": len(node.args),
                    "keywords": [
                        kw.arg
                        for kw in node.keywords
                    ],
                    "source": source_segment(
                        source,
                        node,
                    ),
                }
            )

    # -------------------------------------------------------------------------
    # ASSIGNMENTS
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.NamedExpr,
            ),
        ):
            continue

        value = getattr(
            node,
            "value",
            None,
        )

        if value is None:
            continue

        names = names_in_node(value)

        interesting = (
            names.intersection(
                {
                    "market_data",
                    "bars",
                    "bars_by_asset",
                    "indicators",
                    "indicators_by_asset",
                    "structures",
                    "structures_by_asset",
                }
            )
        )

        if not interesting:
            continue

        assignment_records.append(
            {
                "file": str(path),
                "line": line(node),
                "targets": sorted(
                    interesting
                ),
                "source": source_segment(
                    source,
                    node,
                ),
            }
        )


# =============================================================================
# PASS 3 — IDENTIFY FUNCTIONS THAT LOOK LIKE PRODUCERS
# =============================================================================

producer_keywords = (
    "load",
    "build",
    "create",
    "fetch",
    "get",
    "prepare",
    "collect",
    "calculate",
    "generate",
    "process",
    "update",
    "refresh",
    "pipeline",
    "runtime",
    "main",
    "run",
)

producer_functions = []

for record in function_records:

    name = record["name"].lower()

    if not any(
        key in name
        for key in producer_keywords
    ):
        continue

    params = set(
        record["params"]
    )

    interesting_params = params.intersection(
        {
            "market_data",
            "bars",
            "bars_by_asset",
            "indicators",
            "indicators_by_asset",
            "structures",
            "structures_by_asset",
        }
    )

    if interesting_params:

        producer_functions.append(
            {
                **record,
                "interesting_params":
                    sorted(
                        interesting_params
                    ),
            }
        )


# =============================================================================
# PASS 4 — SCORE POSSIBLE PRODUCTION ENTRYPOINTS
# =============================================================================

entrypoint_candidates = {}

for record in entrypoint_records:

    path = record["file"]

    entrypoint_candidates.setdefault(
        path,
        {
            "file": path,
            "direct_main": True,
            "calls": [],
            "score": 0,
        }
    )

    entrypoint_candidates[path]["score"] += 10


for record in call_records:

    path = record["file"]

    if path not in entrypoint_candidates:
        entrypoint_candidates[path] = {
            "file": path,
            "direct_main": False,
            "calls": [],
            "score": 0,
        }

    entrypoint_candidates[path][
        "calls"
    ].append(record)

    name = record["name"].lower()

    if any(
        x in name
        for x in (
            "market",
            "bar",
            "indicator",
            "structure",
        )
    ):
        entrypoint_candidates[path][
            "score"
        ] += 5

    if "signal_engine" in name:
        entrypoint_candidates[path][
            "score"
        ] += 8

    if "feature_contract" in name:
        entrypoint_candidates[path][
            "score"
        ] += 6

    if "signal_scorer" in name:
        entrypoint_candidates[path][
            "score"
        ] += 6

    if "decision_engine" in name:
        entrypoint_candidates[path][
            "score"
        ] += 6


# =============================================================================
# PASS 5 — FIND FILES THAT ACTUALLY CONNECT MULTIPLE PIPELINE LAYERS
# =============================================================================

for path in files:

    relevant = []

    for record in call_records:

        if record["file"] != str(path):
            continue

        relevant.append(
            record
        )

    names = {
        record["name"]
        for record in relevant
    }

    layer_hits = []

    layer_groups = {
        "MARKET": (
            "market",
            "bar",
        ),
        "INDICATOR": (
            "indicator",
        ),
        "STRUCTURE": (
            "structure",
        ),
        "SIGNAL": (
            "signal_engine",
        ),
        "FEATURE": (
            "feature_contract",
        ),
        "SCORE": (
            "signal_scorer",
        ),
        "DECISION": (
            "decision_engine",
        ),
    }

    for layer, terms in layer_groups.items():

        if any(
            any(
                term in name.lower()
                for term in terms
            )
            for name in names
        ):
            layer_hits.append(
                layer
            )

    if len(layer_hits) >= 2:

        pipeline_records.append(
            {
                "file": str(path),
                "layers": layer_hits,
                "call_count": len(relevant),
            }
        )


# =============================================================================
# OUTPUT
# =============================================================================

print("=" * 100)
print(
    "ARUNDA — REAL PRODUCTION ENTRYPOINT FINDER v0.1"
)
print("=" * 100)

print(
    "PROJECT ROOT :",
    PROJECT_ROOT,
)

print(
    "MODE         : READ ONLY"
)

print(
    "IMPORTS      : NONE"
)

print(
    "EXECUTION    : NONE"
)

print(
    "DATABASE     : NOT TOUCHED"
)

print(
    "SOURCE EDIT  : NONE"
)

print("=" * 100)

print()
print(
    "PYTHON FILES FOUND :",
    len(files),
)

print()
print("=" * 100)
print(
    "PASS 1 : DIRECT __main__ ENTRYPOINTS"
)
print("=" * 100)

if not entrypoint_records:

    print(
        "NO __main__ BLOCKS FOUND."
    )

else:

    for item in entrypoint_records:

        print("-" * 100)

        print(
            "FILE :",
            item["file"],
        )

        print(
            "LINE :",
            item["line"],
        )

        print(
            "TYPE : DIRECT EXECUTION BLOCK"
        )


print()
print("=" * 100)
print(
    "PASS 2 : FUNCTIONS RECEIVING REAL MARKET PIPELINE INPUTS"
)
print("=" * 100)

if not producer_functions:

    print(
        "NO PRODUCER FUNCTIONS FOUND."
    )

else:

    for item in producer_functions:

        print("-" * 100)

        print(
            "FILE :",
            item["file"],
        )

        print(
            "LINE :",
            item["line"],
        )

        print(
            "FUNCTION :",
            item["name"],
        )

        print(
            "PARAMS :",
            item["params"],
        )

        print(
            "PIPELINE PARAMS :",
            item["interesting_params"],
        )


print()
print("=" * 100)
print(
    "PASS 3 : MARKET / BAR / INDICATOR / STRUCTURE CALLS"
)
print("=" * 100)

market_calls = [
    x
    for x in call_records
    if any(
        term in x["name"].lower()
        for term in (
            "market",
            "bar",
            "indicator",
            "structure",
        )
    )
]

if not market_calls:

    print(
        "NO REALISTIC MARKET PIPELINE CALLS FOUND."
    )

else:

    for item in market_calls:

        print("-" * 100)

        print(
            "FILE :",
            item["file"],
        )

        print(
            "LINE :",
            item["line"],
        )

        print(
            "CALL :",
            item["name"],
        )

        print(
            "ARGS :",
            item["args"],
        )

        print(
            "KWARGS :",
            item["keywords"],
        )

        if item["source"]:
            print(
                "SOURCE :",
                item["source"].strip(),
            )


print()
print("=" * 100)
print(
    "PASS 4 : FILES CONNECTING MULTIPLE PIPELINE LAYERS"
)
print("=" * 100)

if not pipeline_records:

    print(
        "NO MULTI-LAYER PIPELINE FILE FOUND."
    )

else:

    pipeline_records.sort(
        key=lambda x: (
            -len(x["layers"]),
            -x["call_count"],
        )
    )

    for index, item in enumerate(
        pipeline_records,
        1,
    ):

        print("-" * 100)

        print(
            "[{}] FILE".format(index),
            ":",
            item["file"],
        )

        print(
            "LAYERS :",
            " -> ".join(
                item["layers"]
            ),
        )

        print(
            "CALLS  :",
            item["call_count"],
        )


print()
print("=" * 100)
print(
    "PASS 5 : POSSIBLE ENTRYPOINT CANDIDATES"
)
print("=" * 100)

candidates = list(
    entrypoint_candidates.values()
)

candidates.sort(
    key=lambda x: -x["score"]
)

if not candidates:

    print(
        "NO ENTRYPOINT CANDIDATES."
    )

else:

    for index, item in enumerate(
        candidates[:30],
        1,
    ):

        print("-" * 100)

        print(
            "[{}] FILE".format(index),
            ":",
            item["file"],
        )

        print(
            "SCORE :",
            item["score"],
        )

        print(
            "DIRECT __main__ :",
            item["direct_main"],
        )

        unique_calls = []

        for call in item["calls"]:

            if call["name"] not in unique_calls:
                unique_calls.append(
                    call["name"]
                )

        print(
            "CALLS :",
            unique_calls,
        )


print()
print("=" * 100)
print(
    "PASS 6 : TARGET VARIABLE PRODUCERS"
)
print("=" * 100)

if not assignment_records:

    print(
        "NO MARKET PIPELINE ASSIGNMENTS FOUND."
    )

else:

    for item in assignment_records:

        print("-" * 100)

        print(
            "FILE :",
            item["file"],
        )

        print(
            "LINE :",
            item["line"],
        )

        print(
            "TARGETS :",
            item["targets"],
        )

        print(
            "SOURCE :",
            item["source"],
        )


print()
print("=" * 100)
print(
    "FORENSIC CONCLUSION"
)
print("=" * 100)

print()

if pipeline_records:

    best = sorted(
        pipeline_records,
        key=lambda x: (
            -len(x["layers"]),
            -x["call_count"],
        )
    )[0]

    print(
        "BEST MULTI-LAYER PIPELINE CANDIDATE :"
    )

    print(
        "FILE   :",
        best["file"],
    )

    print(
        "LAYERS :",
        " -> ".join(
            best["layers"]
        ),
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This is a FORENSIC CANDIDATE only."
    )

    print(
        "It is NOT declared production entrypoint"
    )

    print(
        "unless its runtime call chain is verified."
    )

else:

    print(
        "NO MULTI-LAYER PRODUCTION PIPELINE"
    )

    print(
        "WAS IDENTIFIED BY STATIC AST EVIDENCE."
    )

    print()

    print(
        "This means the next investigation must"
    )

    print(
        "trace the actual market-data producer."
    )


print()
print(
    "PARSE ERRORS :",
    len(parse_errors),
)

if parse_errors:

    print()

    for item in parse_errors[:20]:

        print(
            item["file"],
            "->",
            item["error"],
        )


print()
print("=" * 100)
print(
    "SCAN COMPLETE — NO SOURCE CHANGES"
)
print("=" * 100)