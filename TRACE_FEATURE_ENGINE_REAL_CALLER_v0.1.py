# =============================================================================
# ARUNDA — TRACE FEATURE ENGINE REAL CALLER v0.1
# =============================================================================
#
# PURPOSE
# -------
# Trace the REAL caller chain around feature_engine.py.
#
# PRIMARY QUESTIONS
# -----------------
#
# 1. Who imports/calls feature_engine?
# 2. Which functions in feature_engine are actually referenced?
# 3. Who calls those functions?
# 4. Where do MARKET inputs originate?
# 5. Is there a runtime/main/run entrypoint above feature_engine?
#
# RULES
# -----
# READ ONLY
# AST ONLY
# NO PROJECT IMPORTS
# NO PIPELINE EXECUTION
# NO DATABASE ACCESS
# NO SOURCE MODIFICATION
# NO SYNTHETIC DATA
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

TARGET_MODULE = "feature_engine"

TARGET_FUNCTION_TERMS = {
    "build",
    "calculate",
    "generate",
    "load",
    "process",
    "run",
    "main",
    "feature",
    "indicator",
    "structure",
    "market",
    "bar",
}

MARKET_TERMS = {
    "market_data",
    "market",
    "bars",
    "bar",
    "ohlcv",
    "candles",
    "candle",
    "price",
    "prices",
    "ticker",
    "tickers",
    "symbol",
    "symbols",
    "records",
    "history",
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
# HELPERS
# =============================================================================

def call_name(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        parts = []

        current = node

        while isinstance(
            current,
            ast.Attribute,
        ):

            parts.append(
                current.attr
            )

            current = current.value

        if isinstance(
            current,
            ast.Name,
        ):

            parts.append(
                current.id
            )

        return ".".join(
            reversed(parts)
        )

    return ""


def get_source(source, node):

    try:
        return ast.get_source_segment(
            source,
            node,
        )
    except Exception:
        return None


def line(node):

    return getattr(
        node,
        "lineno",
        -1,
    )


def node_names(node):

    result = set()

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Name,
        ):

            result.add(
                child.id
            )

        elif isinstance(
            child,
            ast.Attribute,
        ):

            result.add(
                child.attr
            )

    return result


def is_main_block(node):

    if not isinstance(
        node,
        ast.If,
    ):
        return False

    test = node.test

    if not (
        isinstance(
            test,
            ast.Compare,
        )
        and len(test.ops) == 1
        and isinstance(
            test.ops[0],
            ast.Eq,
        )
    ):
        return False

    if not isinstance(
        test.left,
        ast.Name,
    ):
        return False

    if test.left.id != "__name__":
        return False

    if not test.comparators:
        return False

    right = test.comparators[0]

    return (
        isinstance(
            right,
            ast.Constant,
        )
        and right.value == "__main__"
    )


# =============================================================================
# DISCOVER PYTHON FILES
# =============================================================================

python_files = []

for root, dirs, filenames in os.walk(
    PROJECT_ROOT
):

    dirs[:] = [
        d
        for d in dirs
        if d not in EXCLUDED_DIRS
    ]

    for filename in filenames:

        path = Path(root) / filename

        if path.suffix.lower() != ".py":
            continue

        python_files.append(
            path
        )


# =============================================================================
# STORAGE
# =============================================================================

parsed = {}

parse_errors = []

imports_of_feature_engine = []

feature_engine_calls = []

function_definitions = []

caller_candidates = []

market_producers = []

main_blocks = []


# =============================================================================
# PARSE ALL VALID FILES
# =============================================================================

for path in python_files:

    try:

        source = path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

        parsed[str(path)] = (
            source,
            tree,
        )

    except Exception as error:

        parse_errors.append(
            (
                str(path),
                type(error).__name__,
                str(error),
            )
        )


# =============================================================================
# PASS 1
# FIND feature_engine IMPORTS
# =============================================================================

for path_str, (
    source,
    tree,
) in parsed.items():

    path = Path(path_str)

    for node in ast.walk(tree):

        # ---------------------------------------------------------------------
        # import feature_engine
        # ---------------------------------------------------------------------

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                if alias.name == TARGET_MODULE:

                    imports_of_feature_engine.append(
                        {
                            "file": path_str,
                            "line": line(node),
                            "type": "import",
                            "alias": alias.asname,
                            "source": get_source(
                                source,
                                node,
                            ),
                        }
                    )

        # ---------------------------------------------------------------------
        # from feature_engine import ...
        # ---------------------------------------------------------------------

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module == TARGET_MODULE:

                imports_of_feature_engine.append(
                    {
                        "file": path_str,
                        "line": line(node),
                        "type": "from_import",
                        "names": [
                            alias.name
                            for alias in node.names
                        ],
                        "source": get_source(
                            source,
                            node,
                        ),
                    }
                )


# =============================================================================
# PASS 2
# INSPECT feature_engine.py FUNCTIONS
# =============================================================================

feature_engine_path = (
    PROJECT_ROOT / "feature_engine.py"
)

feature_engine_data = parsed.get(
    str(feature_engine_path)
)

if feature_engine_data:

    source, tree = feature_engine_data

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

                params.append(
                    arg.arg
                )

            names = node_names(
                node
            )

            function_definitions.append(
                {
                    "name": node.name,
                    "line": line(node),
                    "params": params,
                    "market_terms": sorted(
                        names.intersection(
                            MARKET_TERMS
                        )
                    ),
                    "source": get_source(
                        source,
                        node,
                    ),
                }
            )


# =============================================================================
# PASS 3
# FIND ALL CALLS INTO feature_engine
# =============================================================================

for path_str, (
    source,
    tree,
) in parsed.items():

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

        parts = name.split(".")

        is_feature_engine_call = (
            TARGET_MODULE in parts
        )

        if not is_feature_engine_call:
            continue

        feature_engine_calls.append(
            {
                "file": path_str,
                "line": line(node),
                "call": name,
                "args": len(node.args),
                "kwargs": [
                    kw.arg
                    for kw in node.keywords
                ],
                "source": get_source(
                    source,
                    node,
                ),
            }
        )


# =============================================================================
# PASS 4
# FIND FUNCTIONS CONTAINING feature_engine CALLS
# =============================================================================

for path_str, (
    source,
    tree,
) in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        local_feature_calls = []

        for child in ast.walk(node):

            if not isinstance(
                child,
                ast.Call,
            ):
                continue

            name = call_name(
                child.func
            )

            if TARGET_MODULE in name.split("."):

                local_feature_calls.append(
                    {
                        "call": name,
                        "line": line(child),
                        "source": get_source(
                            source,
                            child,
                        ),
                    }
                )

        if not local_feature_calls:
            continue

        params = []

        for arg in (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        ):

            params.append(
                arg.arg
            )

        names = node_names(
            node
        )

        caller_candidates.append(
            {
                "file": path_str,
                "line": line(node),
                "function": node.name,
                "params": params,
                "market_terms": sorted(
                    names.intersection(
                        MARKET_TERMS
                    )
                ),
                "calls": local_feature_calls,
            }
        )


# =============================================================================
# PASS 5
# FIND MARKET-DATA PRODUCER CANDIDATES
# =============================================================================

for path_str, (
    source,
    tree,
) in parsed.items():

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        names = node_names(
            node
        )

        market_hits = names.intersection(
            MARKET_TERMS
        )

        if not market_hits:
            continue

        function_name = (
            node.name.lower()
        )

        if not any(
            term in function_name
            for term in (
                "load",
                "fetch",
                "get",
                "read",
                "build",
                "create",
                "collect",
                "prepare",
                "process",
                "market",
                "bar",
                "history",
                "data",
                "runtime",
                "main",
                "run",
            )
        ):
            continue

        params = []

        for arg in (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        ):

            params.append(
                arg.arg
            )

        market_producers.append(
            {
                "file": path_str,
                "line": line(node),
                "function": node.name,
                "params": params,
                "market_hits": sorted(
                    market_hits
                ),
                "source": get_source(
                    source,
                    node,
                ),
            }
        )


# =============================================================================
# PASS 6
# FIND DIRECT EXECUTION ENTRYPOINTS
# =============================================================================

for path_str, (
    source,
    tree,
) in parsed.items():

    for node in ast.walk(tree):

        if is_main_block(node):

            main_blocks.append(
                {
                    "file": path_str,
                    "line": line(node),
                    "source": get_source(
                        source,
                        node,
                    ),
                }
            )


# =============================================================================
# OUTPUT
# =============================================================================

print("=" * 100)
print(
    "ARUNDA — TRACE FEATURE ENGINE REAL CALLER v0.1"
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


# =============================================================================
# FILE COUNT
# =============================================================================

print()
print(
    "PYTHON FILES FOUND :",
    len(python_files),
)

print(
    "FILES PARSED       :",
    len(parsed),
)

print(
    "PARSE ERRORS       :",
    len(parse_errors),
)


# =============================================================================
# PASS 1 OUTPUT
# =============================================================================

print()
print("=" * 100)
print(
    "PASS 1 : FILES IMPORTING feature_engine"
)
print("=" * 100)

if not imports_of_feature_engine:

    print(
        "NO feature_engine IMPORT FOUND."
    )

else:

    for item in imports_of_feature_engine:

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
            "TYPE :",
            item["type"],
        )

        print(
            "SOURCE :",
            item["source"],
        )


# =============================================================================
# PASS 2 OUTPUT
# =============================================================================

print()
print("=" * 100)
print(
    "PASS 2 : FUNCTIONS INSIDE feature_engine.py"
)
print("=" * 100)

if not function_definitions:

    print(
        "feature_engine.py NOT PARSED."
    )

else:

    for item in function_definitions:

        print("-" * 100)

        print(
            "FUNCTION :",
            item["name"],
        )

        print(
            "LINE     :",
            item["line"],
        )

        print(
            "PARAMS   :",
            item["params"],
        )

        print(
            "MARKET TERMS :",
            item["market_terms"],
        )


# =============================================================================
# PASS 3 OUTPUT
# =============================================================================

print()
print("=" * 100)
print(
    "PASS 3 : DIRECT CALLS INTO feature_engine"
)
print("=" * 100)

if not feature_engine_calls:

    print(
        "NO feature_engine CALLS FOUND."
    )

else:

    for item in feature_engine_calls:

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
            item["call"],
        )

        print(
            "ARGS :",
            item["args"],
        )

        print(
            "KWARGS :",
            item["kwargs"],
        )

        print(
            "SOURCE :",
            item["source"],
        )


# =============================================================================
# PASS 4 OUTPUT
# =============================================================================

print()
print("=" * 100)
print(
    "PASS 4 : FUNCTIONS THAT CALL feature_engine"
)
print("=" * 100)

if not caller_candidates:

    print(
        "NO CALLER FUNCTION FOUND."
    )

else:

    for item in caller_candidates:

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
            item["function"],
        )

        print(
            "PARAMS :",
            item["params"],
        )

        print(
            "MARKET TERMS :",
            item["market_terms"],
        )

        print(
            "FEATURE CALLS :"
        )

        for call in item["calls"]:

            print(
                "   ",
                call["line"],
                call["call"],
                "->",
                call["source"],
            )


# =============================================================================
# PASS 5 OUTPUT
# =============================================================================

print()
print("=" * 100)
print(
    "PASS 5 : REALISTIC MARKET DATA PRODUCER CANDIDATES"
)
print("=" * 100)

if not market_producers:

    print(
        "NO MARKET PRODUCER CANDIDATES."
    )

else:

    for index, item in enumerate(
        market_producers,
        1,
    ):

        print("-" * 100)

        print(
            "[{}] FILE :".format(index),
            item["file"],
        )

        print(
            "LINE :",
            item["line"],
        )

        print(
            "FUNCTION :",
            item["function"],
        )

        print(
            "PARAMS :",
            item["params"],
        )

        print(
            "MARKET TERMS :",
            item["market_hits"],
        )


# =============================================================================
# PASS 6 OUTPUT
# =============================================================================

print()
print("=" * 100)
print(
    "PASS 6 : DIRECT __main__ ENTRYPOINTS"
)
print("=" * 100)

if not main_blocks:

    print(
        "NO __main__ ENTRYPOINTS."
    )

else:

    for item in main_blocks:

        print("-" * 100)

        print(
            "FILE :",
            item["file"],
        )

        print(
            "LINE :",
            item["line"],
        )


# =============================================================================
# FORENSIC CONCLUSION
# =============================================================================

print()
print("=" * 100)
print(
    "FORENSIC CONCLUSION"
)
print("=" * 100)

print()

if caller_candidates:

    print(
        "feature_engine CALLERS FOUND :",
        len(caller_candidates),
    )

    print()

    for item in caller_candidates:

        print(
            "CALLER :",
            item["file"],
            "::",
            item["function"],
            "()",
        )

        print(
            "LINE   :",
            item["line"],
        )

        print(
            "MARKET INPUT TERMS :",
            item["market_terms"],
        )

        print()

else:

    print(
        "NO STATIC CALLER TO feature_engine FOUND."
    )

print(
    "feature_engine CALL SITES :",
    len(feature_engine_calls),
)

print(
    "MARKET PRODUCER CANDIDATES :",
    len(market_producers),
)

print(
    "DIRECT __main__ BLOCKS :",
    len(main_blocks),
)

print()

print(
    "IMPORTANT:"
)

print(
    "Do NOT modify feature_engine.py yet."
)

print(
    "Do NOT modify decision_engine.py yet."
)

print(
    "Do NOT create a bridge yet."
)

print(
    "The purpose of this scan is only to establish"
)

print(
    "the REAL upstream runtime chain."
)

print()
print(
    "NEXT REQUIRED EVIDENCE:"
)

print(
    "feature_engine caller"
)

print(
    "-> market-data producer"
)

print(
    "-> bars producer"
)

print(
    "-> indicators producer"
)

print(
    "-> structures producer"
)

print(
    "-> feature_engine"
)

print(
    "-> signal_scorer"
)

print(
    "-> decision_engine"
)

print()
print("=" * 100)
print(
    "SCAN COMPLETE — NO SOURCE CHANGES"
)
print("=" * 100)