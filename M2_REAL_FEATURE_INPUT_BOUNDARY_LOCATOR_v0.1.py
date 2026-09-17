# =============================================================================
# ARUNDA TRADER — M2
# M2_REAL_FEATURE_INPUT_BOUNDARY_LOCATOR_v0.1
# =============================================================================
#
# PURPOSE
# -------
# Locate the REAL production runtime boundary supplying:
#
#     bars_by_asset
#     indicators_by_asset
#     structures_by_asset
#
# to:
#
#     feature_contract.load_feature_snapshot()
#     signal_scorer.load_features()
#
# MODE
# ----
# READ ONLY
#
# GUARANTEES
# ----------
# - No database writes
# - No INSERT / UPDATE / DELETE / ALTER / CREATE / DROP
# - No synthetic data
# - No feature fabrication
# - No production repair
# - No scoring
# - No decision
# - No prediction
# - No execution
#
# =============================================================================

from __future__ import annotations

import ast
import inspect
import os
import re
import sys
from pathlib import Path
from typing import Any


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_MODULES = [
    "signal_scorer.py",
    "feature_contract.py",
    "feature_engine.py",
    "signal_engine.py",
    "market_data_engine.py",
    "market_indicator_engine.py",
    "indicator_engine.py",
    "market_history_engine.py",
    "market_state_engine.py",
    "market_structure_engine.py",
]

SEARCH_TERMS = [
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
    "indicator_records",
    "bars",
    "load_bars",
    "build_bars",
    "get_bars",
    "load_market_data",
    "build_market_data",
    "get_market_data",
    "market_data",
    "load_indicators",
    "build_indicators",
    "get_indicators",
    "calculate_indicators",
    "indicator",
    "indicators",
    "calculate_feature_records",
    "load_feature_snapshot",
    "load_features",
]

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

DB_WRITE_PATTERN = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|ALTER|CREATE|DROP|REPLACE|TRUNCATE"
    r")\b",
    re.IGNORECASE,
)


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

WIDTH = 100


def banner(title: str) -> None:
    print("=" * WIDTH)
    print(title)
    print("=" * WIDTH)


def section(title: str) -> None:
    print()
    print("-" * WIDTH)
    print(title)
    print("-" * WIDTH)


def safe_signature(obj: Any) -> str:
    try:
        return str(inspect.signature(obj))
    except Exception:
        return "SIGNATURE_UNAVAILABLE"


def safe_source_file(obj: Any) -> str:
    try:
        path = inspect.getsourcefile(obj)
        return str(path) if path else "SOURCE_UNAVAILABLE"
    except Exception:
        return "SOURCE_UNAVAILABLE"


def safe_line(obj: Any) -> str:
    try:
        _, line = inspect.getsourcelines(obj)
        return str(line)
    except Exception:
        return "LINE_UNAVAILABLE"


# =============================================================================
# SELF TEST
# =============================================================================

def self_test() -> bool:
    assert PROJECT_DIR.exists()
    assert PROJECT_DIR.is_dir()

    assert isinstance(TARGET_MODULES, list)
    assert len(TARGET_MODULES) > 0

    assert isinstance(SEARCH_TERMS, list)
    assert len(SEARCH_TERMS) > 0

    return True


# =============================================================================
# MODULE IMPORT
# =============================================================================

def import_production_module(module_name: str):
    """
    Import a production module without modifying it.

    Import itself is allowed because the purpose of this forensic locator
    is runtime API inspection.
    """

    module_name = module_name.removesuffix(".py")

    original_path = list(sys.path)

    try:
        sys.path.insert(0, str(PROJECT_DIR))

        if module_name in sys.modules:
            del sys.modules[module_name]

        module = __import__(module_name)
        return module, None

    except Exception as exc:
        return None, repr(exc)

    finally:
        sys.path[:] = original_path


# =============================================================================
# FILE DISCOVERY
# =============================================================================

def discover_python_files() -> list[Path]:
    files: list[Path] = []

    for root, dirs, filenames in os.walk(PROJECT_DIR):
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS
        ]

        for filename in filenames:
            if filename.endswith(".py"):
                files.append(Path(root) / filename)

    return sorted(files)


# =============================================================================
# STATIC SOURCE SEARCH
# =============================================================================

def read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def source_matches(path: Path) -> list[tuple[int, str, str]]:
    """
    Return:
        line_number, matched_term, source_line
    """

    text = read_text(path)

    if not text:
        return []

    result = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        lowered = line.lower()

        for term in SEARCH_TERMS:
            if term.lower() in lowered:
                result.append(
                    (
                        line_number,
                        term,
                        line.strip(),
                    )
                )

    return result


# =============================================================================
# AST FUNCTION INDEX
# =============================================================================

def ast_function_index(path: Path) -> list[dict[str, Any]]:
    text = read_text(path)

    if not text:
        return []

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except Exception:
        return []

    result = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            result.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "signature": ast_signature(node),
                }
            )

    return sorted(
        result,
        key=lambda x: x["line"],
    )


def ast_signature(node: ast.FunctionDef) -> str:
    args = []

    positional = list(node.args.posonlyargs)
    positional += list(node.args.args)

    defaults = list(node.args.defaults)

    default_offset = len(positional) - len(defaults)

    for index, arg in enumerate(positional):

        annotation = ""

        if arg.annotation is not None:
            try:
                annotation = (
                    ": "
                    + ast.unparse(arg.annotation)
                )
            except Exception:
                annotation = ""

        default = ""

        if index >= default_offset:
            try:
                default = (
                    " = "
                    + ast.unparse(
                        defaults[
                            index - default_offset
                        ]
                    )
                )
            except Exception:
                default = ""

        args.append(
            arg.arg
            + annotation
            + default
        )

    if node.args.vararg:
        args.append(
            "*"
            + node.args.vararg.arg
        )

    for kwarg, default in zip(
        node.args.kwonlyargs,
        node.args.kw_defaults,
    ):
        annotation = ""

        if kwarg.annotation is not None:
            try:
                annotation = (
                    ": "
                    + ast.unparse(
                        kwarg.annotation
                    )
                )
            except Exception:
                annotation = ""

        value = ""

        if default is not None:
            try:
                value = (
                    " = "
                    + ast.unparse(default)
                )
            except Exception:
                value = ""

        args.append(
            kwarg.arg
            + annotation
            + value
        )

    if node.args.kwarg:
        args.append(
            "**"
            + node.args.kwarg.arg
        )

    return (
        "("
        + ", ".join(args)
        + ")"
    )


# =============================================================================
# AST CALL GRAPH EXTRACTION
# =============================================================================

def ast_calls(path: Path) -> list[dict[str, Any]]:
    text = read_text(path)

    if not text:
        return []

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except Exception:
        return []

    result = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.Call,
            ),
        ):
            continue

        function_name = None

        if isinstance(
            node.func,
            ast.Name,
        ):
            function_name = node.func.id

        elif isinstance(
            node.func,
            ast.Attribute,
        ):
            function_name = node.func.attr

        if not function_name:
            continue

        if any(
            term.lower() in function_name.lower()
            for term in SEARCH_TERMS
        ):
            result.append(
                {
                    "line": node.lineno,
                    "function": function_name,
                }
            )

    return sorted(
        result,
        key=lambda x: x["line"],
    )


# =============================================================================
# PARAMETER / INPUT BOUNDARY ANALYSIS
# =============================================================================

def analyze_function_parameters(
    path: Path,
) -> list[dict[str, Any]]:

    text = read_text(path)

    if not text:
        return []

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )
    except Exception:
        return []

    results = []

    target_names = {
        "bars_by_asset",
        "indicators_by_asset",
        "structures_by_asset",
        "bars",
        "indicator_records",
        "structure_records",
    }

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        params = []

        for arg in (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        ):
            if arg.arg in target_names:
                params.append(arg.arg)

        if params:
            results.append(
                {
                    "function": node.name,
                    "line": node.lineno,
                    "parameters": params,
                }
            )

    return results


# =============================================================================
# DATABASE WRITE FORENSIC
# =============================================================================

def detect_db_write_references(
    path: Path,
) -> list[tuple[int, str]]:

    text = read_text(path)

    if not text:
        return []

    result = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        if DB_WRITE_PATTERN.search(line):
            result.append(
                (
                    line_number,
                    line.strip(),
                )
            )

    return result


# =============================================================================
# RUNTIME OBJECT INSPECTION
# =============================================================================

def runtime_function_inventory(
    module: Any,
) -> list[dict[str, str]]:

    result = []

    for name, obj in inspect.getmembers(
        module,
        inspect.isfunction,
    ):

        lower = name.lower()

        if any(
            term.lower() in lower
            for term in SEARCH_TERMS
        ):
            result.append(
                {
                    "name": name,
                    "signature": safe_signature(obj),
                    "line": safe_line(obj),
                    "source": safe_source_file(obj),
                }
            )

    return result


# =============================================================================
# EXACT RUNTIME API PROBE
# =============================================================================

def probe_zero_input_api(
    module: Any,
    function_name: str,
) -> dict[str, Any]:

    result = {
        "module": module.__name__,
        "function": function_name,
        "exists": False,
        "signature": None,
        "runtime": "NOT_EXECUTED",
        "reason": None,
    }

    obj = getattr(
        module,
        function_name,
        None,
    )

    if obj is None:
        result["reason"] = "MISSING"
        return result

    result["exists"] = True
    result["signature"] = safe_signature(obj)

    try:
        signature = inspect.signature(obj)

        required = []

        for parameter in signature.parameters.values():

            if (
                parameter.default
                is inspect.Parameter.empty
                and parameter.kind
                not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            ):
                required.append(
                    parameter.name
                )

        if required:
            result["runtime"] = "NOT_ZERO_INPUT"
            result["reason"] = (
                "Required parameters: "
                + str(required)
            )
            return result

        value = obj()

        result["runtime"] = "SUCCESS"
        result["type"] = type(value).__name__

        if isinstance(value, dict):
            result["mapping"] = True
            result["count"] = len(value)
            result["keys"] = list(value.keys())[:15]

        elif isinstance(value, (list, tuple)):
            result["sequence"] = True
            result["count"] = len(value)

        else:
            result["mapping"] = False
            result["sequence"] = False

    except Exception as exc:

        result["runtime"] = "FAILED"
        result["reason"] = repr(exc)

    return result


# =============================================================================
# CANDIDATE INPUT FUNCTIONS
# =============================================================================

INPUT_FUNCTION_CANDIDATES = [
    "load_bars",
    "build_bars",
    "get_bars",
    "load_market_data",
    "build_market_data",
    "get_market_data",
    "load_indicators",
    "build_indicators",
    "get_indicators",
    "calculate_indicators",
    "load_indicator_records",
    "build_indicator_records",
    "get_indicator_records",
]


# =============================================================================
# MAIN FORENSIC ROUTINE
# =============================================================================

def main() -> None:

    banner(
        "ARUNDA TRADER — M2\n"
        "M2_REAL_FEATURE_INPUT_BOUNDARY_LOCATOR_v0.1"
    )

    print(
        "PROJECT              :",
        PROJECT_DIR,
    )
    print("MODE                 : READ ONLY")
    print("DATABASE             : NOT USED")
    print("DATABASE WRITE       : NONE")
    print("PRODUCTION MODIFIED  : NO")
    print("SCORING              : NOT EXECUTED")
    print("DECISION             : NOT USED")
    print("PREDICTION           : NOT USED")
    print("EXECUTION            : NOT USED")
    print("=" * WIDTH)

    print()
    print("Running self-test...")

    try:
        self_test()
        print("SELF TEST : PASS")
    except Exception as exc:
        print(
            "SELF TEST : FAIL",
            repr(exc),
        )
        return

    # -------------------------------------------------------------------------
    # PROJECT FILE DISCOVERY
    # -------------------------------------------------------------------------

    section(
        "PROJECT PYTHON FILE DISCOVERY"
    )

    all_files = discover_python_files()

    print(
        "Python files discovered :",
        len(all_files),
    )

    for path in all_files:
        relative = path.relative_to(
            PROJECT_DIR
        )

        if path.name in TARGET_MODULES:
            print(
                "TARGET :",
                relative,
            )

    # -------------------------------------------------------------------------
    # TARGET MODULE RESOLUTION
    # -------------------------------------------------------------------------

    section(
        "TARGET PRODUCTION MODULE RESOLUTION"
    )

    resolved_modules = []

    for filename in TARGET_MODULES:

        path = PROJECT_DIR / filename

        if path.exists():

            print(
                f"{filename:<35} : FOUND"
            )
            print(
                " " * 35,
                str(path),
            )

            resolved_modules.append(
                path
            )

        else:

            print(
                f"{filename:<35} : NOT FOUND"
            )

    # -------------------------------------------------------------------------
    # STATIC INPUT BOUNDARY SEARCH
    # -------------------------------------------------------------------------

    section(
        "STATIC REAL FEATURE INPUT REFERENCES"
    )

    global_matches = []

    for path in all_files:

        matches = source_matches(path)

        if not matches:
            continue

        relative = path.relative_to(
            PROJECT_DIR
        )

        for line_number, term, line in matches:

            global_matches.append(
                (
                    relative,
                    line_number,
                    term,
                    line,
                )
            )

    for (
        relative,
        line_number,
        term,
        line,
    ) in global_matches:

        print(
            f"{str(relative):<38} "
            f"LINE {line_number:<5} "
            f"[{term}] "
            f"{line}"
        )

    print()
    print(
        "Total relevant source matches :",
        len(global_matches),
    )

    # -------------------------------------------------------------------------
    # FUNCTION INDEX
    # -------------------------------------------------------------------------

    section(
        "FUNCTIONS DEFINING / ACCEPTING REAL FEATURE INPUT"
    )

    for path in resolved_modules:

        candidates = analyze_function_parameters(
            path
        )

        if not candidates:
            continue

        print()
        print(
            "MODULE :",
            path.name,
        )

        for item in candidates:

            print(
                f"  {item['function']}"
                f"  LINE {item['line']}"
                f"  PARAMETERS={item['parameters']}"
            )

    # -------------------------------------------------------------------------
    # AST CALL GRAPH
    # -------------------------------------------------------------------------

    section(
        "REAL FEATURE INPUT CALL REFERENCES"
    )

    for path in resolved_modules:

        calls = ast_calls(path)

        relevant = [
            call
            for call in calls
            if call["function"]
            in {
                "load_feature_snapshot",
                "calculate_feature_records",
                "load_features",
                "load_bars",
                "build_bars",
                "get_bars",
                "load_market_data",
                "build_market_data",
                "get_market_data",
                "load_indicators",
                "build_indicators",
                "get_indicators",
                "calculate_indicators",
                "load_indicator_records",
                "build_indicator_records",
                "get_indicator_records",
            }
        ]

        if not relevant:
            continue

        print()
        print(
            "MODULE :",
            path.name,
        )

        for call in relevant:

            print(
                f"  LINE {call['line']:<5}"
                f" -> {call['function']}()"
            )

    # -------------------------------------------------------------------------
    # DATABASE WRITE FORENSIC
    # -------------------------------------------------------------------------

    section(
        "DATABASE WRITE REFERENCE CHECK"
    )

    write_found = False

    for path in resolved_modules:

        writes = detect_db_write_references(
            path
        )

        if not writes:
            continue

        write_found = True

        print()
        print(
            "MODULE :",
            path.name,
        )

        for line_number, line in writes:

            print(
                f"  LINE {line_number:<5} "
                f"{line}"
            )

    if not write_found:
        print(
            "No SQL write keyword references "
            "found in inspected target modules."
        )

    # -------------------------------------------------------------------------
    # RUNTIME MODULE IMPORT
    # -------------------------------------------------------------------------

    section(
        "PRODUCTION MODULE IMPORT CHECK"
    )

    imported_modules = {}

    for path in resolved_modules:

        module_name = path.stem

        module, error = import_production_module(
            module_name
        )

        if module is not None:

            imported_modules[
                module_name
            ] = module

            print(
                f"{module_name:<35} : IMPORT OK"
            )

        else:

            print(
                f"{module_name:<35} : IMPORT FAILED"
            )
            print(
                " " * 35,
                error,
            )

    # -------------------------------------------------------------------------
    # RUNTIME FUNCTION INVENTORY
    # -------------------------------------------------------------------------

    section(
        "RUNTIME FEATURE / MARKET-DATA API CANDIDATES"
    )

    for module_name, module in imported_modules.items():

        inventory = runtime_function_inventory(
            module
        )

        if not inventory:
            continue

        print()
        print(
            "MODULE :",
            module_name,
        )

        for item in inventory:

            print(
                f"  {item['name']:<35}"
                f" LINE {item['line']:<6}"
            )
            print(
                f"      SIGNATURE : "
                f"{item['signature']}"
            )

    # -------------------------------------------------------------------------
    # ZERO-INPUT RUNTIME PROBES
    # -------------------------------------------------------------------------

    section(
        "ZERO-INPUT REAL INPUT API RUNTIME PROBES"
    )

    zero_input_hits = []

    for module_name, module in imported_modules.items():

        for function_name in INPUT_FUNCTION_CANDIDATES:

            result = probe_zero_input_api(
                module,
                function_name,
            )

            if result["exists"]:

                zero_input_hits.append(
                    result
                )

                print()
                print(
                    "MODULE   :",
                    module_name,
                )
                print(
                    "FUNCTION :",
                    function_name,
                )
                print(
                    "SIGNATURE:",
                    result["signature"],
                )
                print(
                    "RUNTIME  :",
                    result["runtime"],
                )

                if result.get("type"):
                    print(
                        "TYPE     :",
                        result["type"],
                    )
                if result.get("count") is not None:
                    print(
                        "COUNT    :",
                        result["count"],
                    )   
                if result.get("keys"):
                    print(
                        "KEYS     :",
                        result["keys"],
                    )

                if result.get("reason"):
                    print(
                        "REASON   :",
                        result["reason"],
                    )

    if not zero_input_hits:

        print(
            "ZERO-INPUT REAL INPUT API : NONE"
        )

    # -------------------------------------------------------------------------
    # MODULE-SPECIFIC AST INDEX
    # -------------------------------------------------------------------------

    section(
        "PRODUCTION FEATURE PIPELINE FUNCTION INDEX"
    )

    for path in resolved_modules:

        functions = ast_function_index(
            path
        )

        relevant = []

        for item in functions:

            name_lower = item["name"].lower()

            if any(
                term.lower() in name_lower
                for term in SEARCH_TERMS
            ):
                relevant.append(item)

        if not relevant:
            continue

        print()
        print(
            "MODULE :",
            path.name,
        )

        for item in relevant:

            print(
                f"  {item['name']:<40}"
                f" LINE {item['line']:<6}"
            )
            print(
                f"      SIGNATURE : "
                f"{item['signature']}"
            )

    # -------------------------------------------------------------------------
    # FINAL DIAGNOSTIC
    # -------------------------------------------------------------------------

    section(
        "DIAGNOSTIC SUMMARY"
    )

    print(
        "Target modules inspected :",
        len(resolved_modules),
    )

    print(
        "Relevant source matches  :",
        len(global_matches),
    )

    print(
        "Zero-input runtime APIs  :",
        len(zero_input_hits),
    )

    print()

    print(
        "TRACE TARGET:"
    )

    print(
        "    REAL MARKET DATA"
    )
    print(
        "        ↓"
    )
    print(
        "    bars_by_asset"
    )
    print(
        "        ↓"
    )
    print(
        "    indicators_by_asset"
    )
    print(
        "        ↓"
    )
    print(
        "    structures_by_asset"
    )
    print(
        "        ↓"
    )
    print(
        "    feature_contract.load_feature_snapshot()"
    )
    print(
        "        ↓"
    )
    print(
        "    feature_engine.calculate_feature_records()"
    )
    print(
        "        ↓"
    )
    print(
        "    signal_scorer.load_features()"
    )

    print()

    if zero_input_hits:

        print(
            "LOCATOR RESULT : "
            "ZERO-INPUT REAL INPUT CANDIDATE(S) FOUND"
        )

        print(
            "NEXT : "
            "VERIFY WHICH CANDIDATE IS THE ACTUAL "
            "PRODUCTION BOUNDARY."
        )

    else:

        print(
            "LOCATOR RESULT : "
            "NO ZERO-INPUT REAL INPUT API FOUND"
        )

        print(
            "NEXT : "
            "TRACE CALLERS OF load_features() / "
            "load_feature_snapshot() TO THEIR "
            "ACTUAL bars / indicators PRODUCER."
        )

    print()

    print(
        "DATABASE WRITE       : NONE"
    )
    print(
        "PRODUCTION MODIFIED  : NO"
    )
    print(
        "SYNTHETIC DATA       : NONE"
    )
    print(
        "REPAIR PERFORMED     : NO"
    )

    print("=" * WIDTH)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()