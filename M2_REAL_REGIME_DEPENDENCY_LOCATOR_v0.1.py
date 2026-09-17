import os
import inspect
import ast
from typing import Any, Mapping


# =============================================================================
# ARUNDA TRADER — M2
# REAL_REGIME_DEPENDENCY_LOCATOR_v0.1
# =============================================================================
#
# PURPOSE
# -------
# Locate the REAL production dependency chain behind:
#
#     market_regime_contract.load_market_regime_contract()
#
# Current observed blocker:
#
#     RuntimeError:
#     market_regime.py must expose load_market_regime()
#
# This script is READ ONLY.
#
# RULES
# -----
# - NO database write
# - NO database modification
# - NO production source modification
# - NO synthetic regime
# - NO scoring
# - NO signal generation
# - NO decision
# - NO execution
#
# TARGET
# ------
# Identify the exact production API mismatch.
#
# =============================================================================


ENGINE_VERSION = "M2_REAL_REGIME_DEPENDENCY_LOCATOR_v0.1"

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

EXPECTED_MODULES = (
    "market_regime_contract",
    "market_regime",
)


# =============================================================================
# TERMINAL
# =============================================================================

def line(char="=", length=100):
    print(char * length)


def fail(message):
    raise RuntimeError(message)


# =============================================================================
# SELF TEST
# =============================================================================

def self_test():

    assert isinstance(
        ENGINE_VERSION,
        str,
    )

    assert len(EXPECTED_MODULES) == 2

    assert len(set(EXPECTED_MODULES)) == 2

    print("SELF TEST : PASS")


# =============================================================================
# FILE RESOLUTION
# =============================================================================

def resolve_file(
    filename,
):

    path = os.path.join(
        PROJECT_DIR,
        filename,
    )

    exists = os.path.isfile(path)

    print(
        f"{filename:<35}: "
        f"{path}"
    )

    print(
        f"{'':35}  "
        f"STATUS : {'FOUND' if exists else 'MISSING'}"
    )

    return path if exists else None


# =============================================================================
# MODULE IMPORT
# =============================================================================

def import_module(
    name,
):

    try:

        module = __import__(
            name
        )

        print(
            f"{name:<35}: IMPORT OK"
        )

        return module

    except Exception as exc:

        print(
            f"{name:<35}: "
            f"IMPORT FAILED"
        )

        print(
            f"{'':35}  "
            f"ERROR : "
            f"{type(exc).__name__}: {exc}"
        )

        return None


# =============================================================================
# SOURCE READER
# =============================================================================

def read_source(
    path,
):

    if path is None:
        return None

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:

            return handle.readlines()

    except Exception as exc:

        print(
            "SOURCE READ FAILED : "
            f"{type(exc).__name__}: {exc}"
        )

        return None


# =============================================================================
# CONTEXT PRINTER
# =============================================================================

def print_context(
    lines,
    center,
    radius=12,
):

    if not lines:
        return

    start = max(
        1,
        center - radius,
    )

    end = min(
        len(lines),
        center + radius,
    )

    for number in range(
        start,
        end + 1,
    ):

        prefix = ">>" if number == center else "  "

        print(
            f"{prefix} "
            f"{number:5d} | "
            f"{lines[number - 1].rstrip()}"
        )


# =============================================================================
# FUNCTION LOCATOR
# =============================================================================

def locate_functions(
    path,
    names,
):

    lines = read_source(
        path
    )

    found = {}

    if not lines:
        return found

    for number, text in enumerate(
        lines,
        start=1,
    ):

        stripped = text.strip()

        for name in names:

            if (
                stripped.startswith(
                    f"def {name}("
                )
                or
                stripped.startswith(
                    f"async def {name}("
                )
            ):

                found[name] = number

    return found


# =============================================================================
# SYMBOL SEARCH
# =============================================================================

def search_source(
    path,
    patterns,
):

    lines = read_source(
        path
    )

    matches = []

    if not lines:
        return matches

    for number, text in enumerate(
        lines,
        start=1,
    ):

        for pattern in patterns:

            if pattern in text:

                matches.append(
                    (
                        number,
                        pattern,
                        text.rstrip(),
                    )
                )

    return matches


# =============================================================================
# AST ANALYSIS
# =============================================================================

def analyze_ast(
    path,
):

    result = {
        "functions": [],
        "imports": [],
        "calls": [],
    }

    lines = read_source(
        path
    )

    if not lines:
        return result

    source = "".join(
        lines
    )

    try:

        tree = ast.parse(
            source
        )

    except Exception as exc:

        print(
            "AST ANALYSIS FAILED : "
            f"{type(exc).__name__}: {exc}"
        )

        return result

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            result[
                "functions"
            ].append(
                (
                    node.name,
                    node.lineno,
                )
            )

        elif isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        ):

            result[
                "imports"
            ].append(
                (
                    getattr(
                        node,
                        "lineno",
                        None,
                    ),
                    ast.unparse(node),
                )
            )

        elif isinstance(
            node,
            ast.Call,
        ):

            try:
                expression = ast.unparse(
                    node
                )
            except Exception:
                expression = "<unparse-failed>"

            result[
                "calls"
            ].append(
                (
                    getattr(
                        node,
                        "lineno",
                        None,
                    ),
                    expression,
                )
            )

    return result


# =============================================================================
# PUBLIC API INSPECTION
# =============================================================================

def inspect_public_api(
    module,
    names,
):

    print()
    print(
        f"MODULE : {module.__name__}"
    )

    print(
        "PUBLIC API CANDIDATES"
    )

    print("-" * 100)

    for name in names:

        value = getattr(
            module,
            name,
            None,
        )

        if callable(value):

            try:
                signature = inspect.signature(
                    value
                )
            except Exception:
                signature = "<signature unavailable>"

            print(
                f"{name:<40} "
                f"FOUND    "
                f"{signature}"
            )

        elif value is None:

            print(
                f"{name:<40} "
                f"MISSING"
            )

        else:

            print(
                f"{name:<40} "
                f"PRESENT / NOT CALLABLE    "
                f"{type(value).__name__}"
            )


# =============================================================================
# CONTRACT MODULE ANALYSIS
# =============================================================================

def analyze_contract(
    module,
    path,
):

    print()
    line("-")
    print(
        "1. MARKET REGIME CONTRACT"
    )
    line("-")

    functions = locate_functions(
        path,
        (
            "load_market_regime_contract",
            "build_market_regime_contract",
        ),
    )

    for name, line_number in functions.items():

        print(
            f"{name:<40}: LINE {line_number}"
        )

        lines = read_source(
            path
        )

        print_context(
            lines,
            line_number,
            radius=14,
        )

    print()
    print(
        "RELEVANT REGIME REFERENCES"
    )
    line("-")

    matches = search_source(
        path,
        (
            "market_regime",
            "load_market_regime",
            "build_market_regime",
            "must expose",
            "RuntimeError",
        ),
    )

    shown = set()

    for number, pattern, text in matches:

        key = (
            number,
            text,
        )

        if key in shown:
            continue

        shown.add(key)

        print(
            f"{number:5d} | "
            f"{text}"
        )

    inspect_public_api(
        module,
        (
            "load_market_regime_contract",
            "build_market_regime_contract",
        ),
    )


# =============================================================================
# MARKET REGIME MODULE ANALYSIS
# =============================================================================

def analyze_market_regime(
    module,
    path,
):

    print()
    line("-")
    print(
        "2. MARKET REGIME MODULE"
    )
    line("-")

    functions = locate_functions(
        path,
        (
            "load_market_regime",
            "build_market_regime",
            "calculate_market_regime",
            "get_market_regime",
        ),
    )

    print(
        "EXPECTED / CANDIDATE FUNCTIONS"
    )

    for name in (
        "load_market_regime",
        "build_market_regime",
        "calculate_market_regime",
        "get_market_regime",
    ):

        if name in functions:

            line_number = functions[
                name
            ]

            print(
                f"{name:<40}: FOUND @ LINE {line_number}"
            )

        else:

            print(
                f"{name:<40}: NOT FOUND"
            )

    inspect_public_api(
        module,
        (
            "load_market_regime",
            "build_market_regime",
            "calculate_market_regime",
            "get_market_regime",
        ),
    )

    print()
    print(
        "REGIME-RELATED SOURCE REFERENCES"
    )
    line("-")

    matches = search_source(
        path,
        (
            "load_market_regime",
            "build_market_regime",
            "market_regime",
            "regime",
            "RuntimeError",
        ),
    )

    shown = set()

    for number, pattern, text in matches:

        key = (
            number,
            text,
        )

        if key in shown:
            continue

        shown.add(key)

        print(
            f"{number:5d} | "
            f"{text}"
        )


# =============================================================================
# AST DEPENDENCY CHAIN
# =============================================================================

def analyze_dependency_chain(
    contract_path,
    regime_path,
):

    print()
    line("-")
    print(
        "3. STATIC DEPENDENCY CHAIN"
    )
    line("-")

    contract_ast = analyze_ast(
        contract_path
    )

    regime_ast = analyze_ast(
        regime_path
    )

    print()
    print(
        "MARKET_REGIME_CONTRACT FUNCTIONS"
    )

    for name, line_number in sorted(
        contract_ast[
            "functions"
        ],
        key=lambda item: item[1],
    ):

        if (
            "regime" in name.lower()
            or
            "market" in name.lower()
        ):

            print(
                f"LINE {line_number:<6} "
                f"{name}"
            )

    print()
    print(
        "MARKET_REGIME FUNCTIONS"
    )

    for name, line_number in sorted(
        regime_ast[
            "functions"
        ],
        key=lambda item: item[1],
    ):

        if (
            "regime" in name.lower()
            or
            "market" in name.lower()
        ):

            print(
                f"LINE {line_number:<6} "
                f"{name}"
            )

    print()
    print(
        "MARKET_REGIME_CONTRACT CALLS"
    )

    for line_number, expression in sorted(
        contract_ast[
            "calls"
        ],
        key=lambda item: (
            item[0]
            if item[0] is not None
            else 0
        ),
    ):

        if (
            "regime" in expression.lower()
            or
            "market" in expression.lower()
        ):

            print(
                f"LINE {line_number:<6} "
                f"{expression}"
            )


# =============================================================================
# RUNTIME CONTRACT PROBE
# =============================================================================

def runtime_contract_probe(
    contract_module,
):

    print()
    line("-")
    print(
        "4. REAL RUNTIME CONTRACT PROBE"
    )
    line("-")

    loader = getattr(
        contract_module,
        "load_market_regime_contract",
        None,
    )

    if not callable(loader):

        print(
            "load_market_regime_contract : MISSING"
        )

        return

    print(
        "Calling REAL production API:"
    )

    print(
        "    market_regime_contract."
        "load_market_regime_contract()"
    )

    print()
    print(
        "NO WRITE OPERATION IS PERFORMED."
    )

    try:

        result = loader()

        print()
        print(
            "RUNTIME RESULT : SUCCESS"
        )

        print(
            f"TYPE           : "
            f"{type(result).__name__}"
        )

        if isinstance(
            result,
            Mapping,
        ):

            print(
                f"ASSETS         : "
                f"{len(result)}"
            )

            keys = list(
                result.keys()
            )

            print(
                f"KEY SAMPLE     : "
                f"{keys[:15]}"
            )

            for asset in keys[:3]:

                value = result[
                    asset
                ]

                print()
                print(
                    f"ASSET : {asset}"
                )

                print(
                    f"TYPE  : "
                    f"{type(value).__name__}"
                )

                if isinstance(
                    value,
                    Mapping,
                ):

                    print(
                        f"KEYS  : "
                        f"{list(value.keys())}"
                    )

    except Exception as exc:

        print()
        print(
            "RUNTIME RESULT : BLOCKED"
        )

        print(
            f"ERROR          : "
            f"{type(exc).__name__}: {exc}"
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "The runtime blocker above is "
            "captured only."
        )

        print(
            "No repair is performed."
        )


# =============================================================================
# FINAL DIAGNOSTIC
# =============================================================================

def final_diagnostic(
    regime_module,
    regime_path,
):

    print()
    line("-")
    print(
        "5. DIAGNOSTIC SUMMARY"
    )
    line("-")

    expected_loader = getattr(
        regime_module,
        "load_market_regime",
        None,
    )

    candidate_functions = locate_functions(
        regime_path,
        (
            "load_market_regime",
            "build_market_regime",
            "calculate_market_regime",
            "get_market_regime",
        ),
    )

    print(
        "Expected production API"
    )

    print(
        "    market_regime.load_market_regime()"
    )

    print()

    if callable(
        expected_loader
    ):

        print(
            "load_market_regime : FOUND"
        )

        try:
            print(
                f"Signature          : "
                f"{inspect.signature(expected_loader)}"
            )
        except Exception:
            pass

    else:

        print(
            "load_market_regime : MISSING"
        )

    print()
    print(
        "Candidate regime APIs actually present:"
    )

    if not candidate_functions:

        print(
            "    NONE"
        )

    else:

        for name, line_number in sorted(
            candidate_functions.items()
        ):

            print(
                f"    {name:<30} "
                f"LINE {line_number}"
            )

    print()
    print(
        "INTERPRETATION"
    )

    if callable(
        expected_loader
    ):

        print(
            "    Expected API exists."
        )

        print(
            "    Runtime failure may be caused "
            "by another contract condition."
        )

    else:

        print(
            "    The required API "
            "market_regime.load_market_regime() "
            "is not exposed."
        )

        print(
            "    This is the exact dependency "
            "mismatch to repair."
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 100)

    print(
        "ARUNDA TRADER — M2"
    )

    print(
        "REAL_REGIME_DEPENDENCY_LOCATOR_v0.1"
    )

    print("=" * 100)

    print(
        f"PROJECT              : {PROJECT_DIR}"
    )

    print(
        "MODE                 : READ ONLY"
    )

    print(
        "DATABASE             : NOT USED"
    )

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
        "SCORING              : NOT EXECUTED"
    )

    print(
        "DECISION             : NOT USED"
    )

    print(
        "PREDICTION           : NOT USED"
    )

    print(
        "EXECUTION            : NOT USED"
    )

    print("=" * 100)

    try:

        print()
        print(
            "Running self-test..."
        )

        self_test()

        # =====================================================================
        # FILE RESOLUTION
        # =====================================================================

        print()
        line("-")
        print(
            "PRODUCTION FILE RESOLUTION"
        )
        line("-")

        contract_path = resolve_file(
            "market_regime_contract.py"
        )

        regime_path = resolve_file(
            "market_regime.py"
        )

        if contract_path is None:

            fail(
                "BLOCKER:MISSING_FILE:"
                "market_regime_contract.py"
            )

        if regime_path is None:

            fail(
                "BLOCKER:MISSING_FILE:"
                "market_regime.py"
            )

        # =====================================================================
        # IMPORT RESOLUTION
        # =====================================================================

        print()
        line("-")
        print(
            "PRODUCTION MODULE IMPORT CHECK"
        )
        line("-")

        contract_module = import_module(
            "market_regime_contract"
        )

        regime_module = import_module(
            "market_regime"
        )

        if contract_module is None:

            fail(
                "BLOCKER:IMPORT_MARKET_REGIME_CONTRACT"
            )

        if regime_module is None:

            fail(
                "BLOCKER:IMPORT_MARKET_REGIME"
            )

        # =====================================================================
        # CONTRACT ANALYSIS
        # =====================================================================

        analyze_contract(
            contract_module,
            contract_path,
        )

        # =====================================================================
        # MARKET REGIME ANALYSIS
        # =====================================================================

        analyze_market_regime(
            regime_module,
            regime_path,
        )

        # =====================================================================
        # STATIC DEPENDENCY GRAPH
        # =====================================================================

        analyze_dependency_chain(
            contract_path,
            regime_path,
        )

        # =====================================================================
        # RUNTIME PROBE
        # =====================================================================

        runtime_contract_probe(
            contract_module,
        )

        # =====================================================================
        # FINAL DIAGNOSTIC
        # =====================================================================

        final_diagnostic(
            regime_module,
            regime_path,
        )

        # =====================================================================
        # FINAL STATUS
        # =====================================================================

        print()
        line("=")
        print(
            "LOCATOR RESULT"
        )
        line("=")

        print(
            "REAL REGIME CONTRACT : "
            "market_regime_contract."
            "load_market_regime_contract()"
        )

        print(
            "UNDERLYING MODULE    : "
            "market_regime.py"
        )

        print(
            "DATABASE WRITE       : NONE"
        )

        print(
            "PRODUCTION MODIFIED  : NO"
        )

        print(
            "REPAIR PERFORMED     : NO"
        )

        line("=")

        print()
        print(
            "FINAL STATUS : "
            "REAL REGIME DEPENDENCY LOCATED"
        )

        print(
            "NEXT         : "
            "REPAIR ONLY AFTER EXACT API MISMATCH IS CONFIRMED"
        )

        return 0

    except KeyboardInterrupt:

        print()
        print(
            "LOCATOR INTERRUPTED"
        )

        return 130

    except Exception as exc:

        print()
        line("=")
        print(
            "LOCATOR STATUS : BLOCKED"
        )

        print(
            f"ERROR          : "
            f"{type(exc).__name__}: {exc}"
        )

        line("=")

        return 1


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )