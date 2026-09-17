import os
import inspect
import ast
import importlib
from typing import Any, Mapping


# =============================================================================
# ARUNDA TRADER — M2
# M2_REAL_REGIME_SOURCE_LOCATOR_v0.2
# =============================================================================
#
# PURPOSE
# -------
# Locate the EXACT REAL production source of market regime data.
#
# CURRENT BLOCKER
# ---------------
# market_regime_contract.load_market_regime_contract()
# expects:
#
#     market_regime.load_market_regime()
#
# but market_regime.py does not expose that API.
#
# THIS SCRIPT DOES NOT REPAIR ANYTHING.
#
# RULES
# -----
# - READ ONLY
# - NO DATABASE WRITE
# - NO INSERT
# - NO UPDATE
# - NO DELETE
# - NO ALTER
# - NO CREATE
# - NO synthetic regime
# - NO synthetic data
# - NO scorer execution
# - NO decision
# - NO prediction
# - NO execution
# - NO production modification
#
# TARGET
# ------
# Identify the REAL existing regime source and its exact runtime API.
#
# =============================================================================


ENGINE_VERSION = "M2_REAL_REGIME_SOURCE_LOCATOR_v0.2"

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

EXPECTED_ASSETS = (
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
)

MODULE_CANDIDATES = (
    "market_regime",
    "market_regime_engine",
    "market_state_engine",
)


# =============================================================================
# TERMINAL
# =============================================================================

def line(char="=", length=100):
    print(char * length)


def section(title):
    print()
    line("-", 100)
    print(title)
    line("-", 100)


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

    assert len(EXPECTED_ASSETS) == 15

    assert len(
        set(EXPECTED_ASSETS)
    ) == 15

    assert len(
        MODULE_CANDIDATES
    ) >= 1

    print("SELF TEST : PASS")


# =============================================================================
# MODULE RESOLUTION
# =============================================================================

def resolve_module(name):

    try:
        module = importlib.import_module(
            name
        )

        return module, None

    except Exception as exc:

        return (
            None,
            f"{type(exc).__name__}:{exc}",
        )


def module_path(module):

    value = getattr(
        module,
        "__file__",
        None,
    )

    if value is None:
        return "<NO __file__>"

    return os.path.abspath(
        value
    )


# =============================================================================
# SOURCE FILE
# =============================================================================

def read_source(module):

    path = module_path(
        module
    )

    if not os.path.isfile(path):

        return (
            None,
            f"FILE_NOT_FOUND:{path}",
        )

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:

            return (
                handle.read(),
                None,
            )

    except Exception as exc:

        return (
            None,
            f"{type(exc).__name__}:{exc}",
        )


# =============================================================================
# AST FUNCTION DISCOVERY
# =============================================================================

def discover_functions(source):

    if not source:
        return []

    try:

        tree = ast.parse(
            source
        )

    except Exception:

        return []

    functions = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            functions.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                }
            )

    return sorted(
        functions,
        key=lambda item: (
            item["line"],
            item["name"],
        ),
    )


# =============================================================================
# REGIME-RELATED FUNCTION DETECTION
# =============================================================================

REGIME_KEYWORDS = (
    "regime",
    "market_regime",
    "market_state",
    "state",
    "trend",
    "volatility",
    "classification",
    "classify",
    "environment",
    "condition",
)


def is_regime_candidate(name):

    lowered = name.lower()

    return any(
        keyword in lowered
        for keyword in REGIME_KEYWORDS
    )


def regime_candidates(functions):

    return [
        item
        for item in functions
        if is_regime_candidate(
            item["name"]
        )
    ]


# =============================================================================
# SOURCE CONTEXT
# =============================================================================

def print_source_context(
    source,
    line_number,
    radius=8,
):

    if not source:
        return

    lines = source.splitlines()

    start = max(
        0,
        line_number - radius - 1,
    )

    end = min(
        len(lines),
        line_number + radius,
    )

    for index in range(
        start,
        end,
    ):

        marker = ">>" if (
            index + 1 == line_number
        ) else "  "

        print(
            f"{marker} "
            f"{index + 1:4d} | "
            f"{lines[index]}"
        )


# =============================================================================
# CALL REFERENCE DISCOVERY
# =============================================================================

def discover_text_references(
    source,
    patterns,
):

    if not source:
        return []

    lines = source.splitlines()

    results = []

    for index, text in enumerate(
        lines,
        start=1,
    ):

        lowered = text.lower()

        if any(
            pattern.lower()
            in lowered
            for pattern in patterns
        ):

            results.append(
                (
                    index,
                    text,
                )
            )

    return results


# =============================================================================
# RUNTIME FUNCTION PROBE
# =============================================================================

def runtime_probe(
    module,
    function_name,
):

    candidate = getattr(
        module,
        function_name,
        None,
    )

    if not callable(candidate):

        return {
            "exists": False,
            "callable": False,
            "signature": None,
            "result": None,
            "error": None,
        }

    try:

        signature = str(
            inspect.signature(
                candidate
            )
        )

    except Exception as exc:

        signature = (
            f"<SIGNATURE_ERROR:"
            f"{type(exc).__name__}:"
            f"{exc}>"
        )

    #
    # STRICT ZERO-ARG PROBE ONLY.
    #
    # We never manufacture arguments.
    #

    try:

        sig = inspect.signature(
            candidate
        )

        required = [
            parameter
            for parameter
            in sig.parameters.values()
            if (
                parameter.default
                is inspect.Parameter.empty
                and
                parameter.kind
                in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
            )
        ]

        if required:

            return {
                "exists": True,
                "callable": True,
                "signature": signature,
                "result": None,
                "error": (
                    "REQUIRES_ARGUMENTS:"
                    + str(
                        [
                            parameter.name
                            for parameter
                            in required
                        ]
                    )
                ),
            }

        result = candidate()

        return {
            "exists": True,
            "callable": True,
            "signature": signature,
            "result": result,
            "error": None,
        }

    except Exception as exc:

        return {
            "exists": True,
            "callable": True,
            "signature": signature,
            "result": None,
            "error": (
                f"{type(exc).__name__}:"
                f"{exc}"
            ),
        }


# =============================================================================
# RESULT SHAPE
# =============================================================================

def describe_result(
    result,
):

    if result is None:

        print(
            "Runtime result : NONE"
        )

        return

    print(
        "Runtime type   : "
        f"{type(result).__name__}"
    )

    if isinstance(
        result,
        Mapping,
    ):

        print(
            "Mapping        : YES"
        )

        print(
            f"Assets/keys    : {len(result)}"
        )

        keys = list(
            result.keys()
        )

        print(
            "Keys sample    : "
            f"{keys[:20]}"
        )

        expected = set(
            EXPECTED_ASSETS
        )

        actual = set(
            str(key).upper()
            for key in keys
        )

        missing = sorted(
            expected - actual
        )

        extra = sorted(
            actual - expected
        )

        print(
            "Expected assets: "
            f"{len(expected)}"
        )

        print(
            "Matched assets : "
            f"{len(expected & actual)}"
        )

        if missing:

            print(
                "Missing assets : "
                f"{missing}"
            )

        else:

            print(
                "Missing assets : NONE"
            )

        if extra:

            print(
                "Extra assets   : "
                f"{extra}"
            )

        else:

            print(
                "Extra assets   : NONE"
            )

        #
        # Inspect first few asset records.
        #

        print()
        print(
            "RUNTIME RECORD SHAPE"
        )

        for key in keys[:5]:

            value = result[key]

            print(
                f"{key!s:<8} "
                f"type={type(value).__name__}"
            )

            if isinstance(
                value,
                Mapping,
            ):

                print(
                    "         keys="
                    f"{list(value.keys())}"
                )

            else:

                print(
                    "         value="
                    f"{value!r}"
                )

    else:

        print(
            "Mapping        : NO"
        )

        print(
            "Value preview  : "
            f"{result!r}"
        )


# =============================================================================
# MODULE ANALYSIS
# =============================================================================

def analyze_module(
    name,
    module,
):

    section(
        f"MODULE ANALYSIS : {name}"
    )

    print(
        "Path   : "
        f"{module_path(module)}"
    )

    source, source_error = read_source(
        module
    )

    if source_error:

        print(
            "Source : UNAVAILABLE"
        )

        print(
            f"Error  : {source_error}"
        )

        return {
            "module": name,
            "source": None,
            "functions": [],
            "candidates": [],
        }

    print(
        f"Lines  : {len(source.splitlines())}"
    )

    functions = discover_functions(
        source
    )

    candidates = regime_candidates(
        functions
    )

    print()
    print(
        "PUBLIC / DEFINED FUNCTIONS"
    )

    if not functions:

        print(
            "  NONE"
        )

    else:

        for item in functions:

            print(
                f"  {item['name']:<40}"
                f"LINE {item['line']}"
            )

    print()
    print(
        "REGIME-RELATED CANDIDATES"
    )

    if not candidates:

        print(
            "  NONE"
        )

    else:

        for item in candidates:

            print(
                f"  {item['name']:<40}"
                f"LINE {item['line']}"
            )

    print()
    print(
        "TEXT REFERENCES"
    )

    references = discover_text_references(
        source,
        (
            "market_regime",
            "regime",
            "load_market",
            "load_structural",
            "get_market",
        ),
    )

    if not references:

        print(
            "  NONE"
        )

    else:

        for line_number, text in references[:80]:

            print(
                f"  {line_number:5d} | {text}"
            )

    return {
        "module": name,
        "source": source,
        "functions": functions,
        "candidates": candidates,
    }


# =============================================================================
# EXACT EXPECTED API PROBE
# =============================================================================

def probe_expected_api(
    market_regime,
):

    section(
        "EXPECTED API PROBE"
    )

    print(
        "Expected production API:"
    )

    print(
        "    market_regime.load_market_regime()"
    )

    fn = getattr(
        market_regime,
        "load_market_regime",
        None,
    )

    if not callable(fn):

        print(
            "Status : MISSING"
        )

        return None

    print(
        "Status : FOUND"
    )

    result = runtime_probe(
        market_regime,
        "load_market_regime",
    )

    print(
        f"Signature : {result['signature']}"
    )

    if result["error"]:

        print(
            "Runtime   : BLOCKED"
        )

        print(
            f"Error     : {result['error']}"
        )

        return result

    print(
        "Runtime   : EXECUTED"
    )

    describe_result(
        result["result"]
    )

    return result


# =============================================================================
# CANDIDATE RUNTIME PROBE
# =============================================================================

def probe_candidates(
    analyses,
):

    section(
        "REAL REGIME CANDIDATE RUNTIME PROBES"
    )

    tested = set()

    for analysis in analyses:

        module_name = analysis[
            "module"
        ]

        module = importlib.import_module(
            module_name
        )

        for item in analysis[
            "candidates"
        ]:

            function_name = item[
                "name"
            ]

            identity = (
                module_name,
                function_name,
            )

            if identity in tested:
                continue

            tested.add(
                identity
            )

            print()
            print(
                f"MODULE   : {module_name}"
            )

            print(
                f"FUNCTION : {function_name}"
            )

            print(
                f"LINE     : {item['line']}"
            )

            result = runtime_probe(
                module,
                function_name,
            )

            print(
                f"SIGNATURE: "
                f"{result['signature']}"
            )

            if result["error"]:

                print(
                    "RUNTIME  : NOT RESOLVED"
                )

                print(
                    f"ERROR    : "
                    f"{result['error']}"
                )

                continue

            print(
                "RUNTIME  : SUCCESS"
            )

            describe_result(
                result["result"]
            )


# =============================================================================
# CONTRACT SOURCE CROSS-CHECK
# =============================================================================

def inspect_contract():

    section(
        "MARKET REGIME CONTRACT CROSS-CHECK"
    )

    module, error = resolve_module(
        "market_regime_contract"
    )

    if module is None:

        print(
            "market_regime_contract : IMPORT FAILED"
        )

        print(
            f"Error : {error}"
        )

        return

    print(
        "market_regime_contract : IMPORT OK"
    )

    source, source_error = read_source(
        module
    )

    if source_error:

        print(
            f"Source error : {source_error}"
        )

        return

    references = discover_text_references(
        source,
        (
            "load_market_regime",
            "market_regime",
            "build_market_regime_contract",
        ),
    )

    print()
    print(
        "CONTRACT REFERENCES"
    )

    for line_number, text in references[:80]:

        print(
            f"{line_number:5d} | {text}"
        )

    expected = getattr(
        module,
        "load_market_regime_contract",
        None,
    )

    print()
    print(
        "load_market_regime_contract : "
        f"{'FOUND' if callable(expected) else 'MISSING'}"
    )


# =============================================================================
# IMPORT GRAPH
# =============================================================================

def inspect_imports(
    analyses,
):

    section(
        "REGIME MODULE IMPORT GRAPH"
    )

    for analysis in analyses:

        source = analysis[
            "source"
        ]

        if not source:
            continue

        references = discover_text_references(
            source,
            (
                "import market_",
                "from market_",
            ),
        )

        print()
        print(
            f"[{analysis['module']}]"
        )

        if not references:

            print(
                "  No market_* imports found."
            )

        else:

            for line_number, text in references:

                print(
                    f"  {line_number:5d} | {text}"
                )


# =============================================================================
# FINAL INTERPRETATION
# =============================================================================

def final_interpretation(
    analyses,
    expected_probe,
):

    section(
        "DIAGNOSTIC SUMMARY"
    )

    market_regime_analysis = None

    for analysis in analyses:

        if analysis[
            "module"
        ] == "market_regime":

            market_regime_analysis = analysis

    if expected_probe is not None:

        if (
            expected_probe["error"]
            is None
        ):

            print(
                "EXPECTED API STATUS : RUNTIME SUCCESS"
            )

            print(
                "INTERPRETATION       : "
                "The previously reported API mismatch "
                "is no longer present."
            )

            return

    if market_regime_analysis:

        candidates = (
            market_regime_analysis[
                "candidates"
            ]
        )

        if candidates:

            print(
                "EXPECTED API STATUS : MISSING/BLOCKED"
            )

            print(
                "REAL CANDIDATES      : "
                f"{len(candidates)}"
            )

            print()
            print(
                "IMPORTANT:"
            )

            print(
                "A regime-related implementation exists "
                "inside market_regime.py, but its exact "
                "production suitability must be verified "
                "from the runtime probe before any repair."
            )

        else:

            print(
                "EXPECTED API STATUS : MISSING"
            )

            print(
                "market_regime.py does not expose a "
                "supported regime loader."
            )

            print()
            print(
                "NEXT DIAGNOSTIC TARGET:"
            )

            print(
                "Inspect market_regime_engine / "
                "market_state_engine for the actual "
                "production regime source."
            )

    else:

        print(
            "market_regime.py could not be analyzed."
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
        "M2_REAL_REGIME_SOURCE_LOCATOR_v0.2"
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

        # ---------------------------------------------------------------------
        # MODULE RESOLUTION
        # ---------------------------------------------------------------------

        section(
            "PRODUCTION MODULE RESOLUTION"
        )

        loaded_modules = []
        failed_modules = []

        for name in MODULE_CANDIDATES:

            module, error = resolve_module(
                name
            )

            if module is None:

                failed_modules.append(
                    (
                        name,
                        error,
                    )
                )

                print(
                    f"{name:<30} : "
                    f"IMPORT FAILED"
                )

                print(
                    f"{'':30}   "
                    f"{error}"
                )

            else:

                loaded_modules.append(
                    (
                        name,
                        module,
                    )
                )

                print(
                    f"{name:<30} : "
                    f"IMPORT OK"
                )

                print(
                    f"{'':30}   "
                    f"{module_path(module)}"
                )

        if not loaded_modules:

            fail(
                "BLOCKER:NO_REAL_REGIME_MODULE_AVAILABLE"
            )

        # ---------------------------------------------------------------------
        # MODULE ANALYSIS
        # ---------------------------------------------------------------------

        analyses = []

        for name, module in loaded_modules:

            analyses.append(
                analyze_module(
                    name,
                    module,
                )
            )

        # ---------------------------------------------------------------------
        # CONTRACT
        # ---------------------------------------------------------------------

        inspect_contract()

        # ---------------------------------------------------------------------
        # IMPORT GRAPH
        # ---------------------------------------------------------------------

        inspect_imports(
            analyses
        )

        # ---------------------------------------------------------------------
        # EXPECTED API
        # ---------------------------------------------------------------------

        market_regime_module = None

        for name, module in loaded_modules:

            if name == "market_regime":

                market_regime_module = module
                break

        if market_regime_module is None:

            fail(
                "BLOCKER:MARKET_REGIME_MODULE_NOT_IMPORTED"
            )

        expected_probe = probe_expected_api(
            market_regime_module
        )

        # ---------------------------------------------------------------------
        # CANDIDATES
        # ---------------------------------------------------------------------

        probe_candidates(
            analyses
        )

        # ---------------------------------------------------------------------
        # FINAL
        # ---------------------------------------------------------------------

        final_interpretation(
            analyses,
            expected_probe,
        )

        line("=")

        print(
            "LOCATOR STATUS : COMPLETE"
        )

        print(
            "DATABASE WRITE  : NONE"
        )

        print(
            "PRODUCTION MODIFIED : NO"
        )

        print(
            "SYNTHETIC DATA  : NONE"
        )

        print(
            "REPAIR PERFORMED: NO"
        )

        line("=")

        print()
        print(
            "FINAL STATUS : REAL REGIME SOURCE LOCATED/INSPECTED"
        )

        print(
            "NEXT         : USE THIS OUTPUT TO PERFORM "
            "THE MINIMAL API REPAIR ONLY"
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