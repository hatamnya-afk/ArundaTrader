import os
import inspect
import ast


# =============================================================================
# ARUNDA TRADER — M2
# REAL_FEATURE_SOURCE_LOCATOR_v0.1
# =============================================================================

ENGINE_VERSION = "M2_REAL_FEATURE_SOURCE_LOCATOR_v0.1"

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

TARGET_MODULES = (
    "signal_scorer",
    "feature_contract",
    "feature_engine",
    "signal_engine",
)

FEATURE_KEYWORDS = (
    "feature",
    "features",
    "indicator",
    "indicators",
    "bar",
    "bars",
    "snapshot",
    "calculate_feature",
    "load_feature",
    "build_feature",
    "latest_feature",
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


# =============================================================================
# TERMINAL
# =============================================================================

def line(char="-", length=100):
    print(char * length)


def fail(message):
    raise RuntimeError(message)


# =============================================================================
# SELF TEST
# =============================================================================

def self_test():

    assert isinstance(
        ENGINE_VERSION,
        str
    )

    assert len(EXPECTED_ASSETS) == 15

    assert len(set(EXPECTED_ASSETS)) == 15

    print("SELF TEST : PASS")


# =============================================================================
# MODULE LOADING
# =============================================================================

def load_modules():

    modules = {}

    for name in TARGET_MODULES:

        try:
            module = __import__(name)
            modules[name] = module

        except Exception as exc:

            print(
                f"{name:<32} : IMPORT FAILED"
            )

            print(
                f"    {type(exc).__name__}: {exc}"
            )

    return modules


# =============================================================================
# SOURCE FILE
# =============================================================================

def get_source_file(module):

    path = getattr(
        module,
        "__file__",
        None,
    )

    if not path:
        return None

    return os.path.abspath(path)


# =============================================================================
# FUNCTION INVENTORY
# =============================================================================

def list_functions(module):

    functions = []

    for name, obj in inspect.getmembers(
        module,
        inspect.isfunction,
    ):

        functions.append(
            (
                name,
                obj,
            )
        )

    return functions


# =============================================================================
# FEATURE FUNCTION CANDIDATES
# =============================================================================

def is_feature_candidate(name):

    lowered = name.lower()

    return any(
        keyword in lowered
        for keyword in FEATURE_KEYWORDS
    )


def print_function_candidates(
    module_name,
    module,
):

    print()
    print(
        f"MODULE : {module_name}"
    )

    line("-")

    functions = list_functions(
        module
    )

    print(
        f"DEFINED FUNCTIONS : {len(functions)}"
    )

    candidates = []

    for name, obj in functions:

        if is_feature_candidate(name):

            try:
                signature = str(
                    inspect.signature(obj)
                )
            except Exception:
                signature = "(signature unavailable)"

            candidates.append(
                (
                    name,
                    obj,
                    signature,
                )
            )

    if not candidates:

        print(
            "FEATURE CANDIDATES : NONE"
        )

        return []

    print(
        "FEATURE CANDIDATES"
    )

    for name, obj, signature in candidates:

        try:
            line_no = inspect.getsourcelines(
                obj
            )[1]
        except Exception:
            line_no = "?"

        print(
            f"  {name:<40}"
            f"LINE {line_no}"
        )

        print(
            f"      SIGNATURE : {signature}"
        )

    return candidates


# =============================================================================
# TEXT SCAN
# =============================================================================

def scan_source_text(
    module_name,
    module,
):

    path = get_source_file(
        module
    )

    if not path or not os.path.exists(path):
        return

    print()
    print(
        f"SOURCE REFERENCES : {module_name}"
    )

    line("-")

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:

            lines = handle.readlines()

    except Exception as exc:

        print(
            f"READ FAILED : {type(exc).__name__}:{exc}"
        )

        return

    matches = []

    for index, text in enumerate(
        lines,
        start=1,
    ):

        lowered = text.lower()

        if any(
            keyword in lowered
            for keyword in FEATURE_KEYWORDS
        ):

            matches.append(
                (
                    index,
                    text.rstrip(),
                )
            )

    print(
        f"MATCH COUNT : {len(matches)}"
    )

    for index, text in matches[:150]:

        print(
            f"{index:5d} | {text}"
        )


# =============================================================================
# AST CALL GRAPH
# =============================================================================

def scan_ast_calls(
    module_name,
    module,
):

    path = get_source_file(
        module
    )

    if not path or not os.path.exists(path):
        return

    print()
    print(
        f"FEATURE-RELATED CALL GRAPH : {module_name}"
    )

    line("-")

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:

            source = handle.read()

        tree = ast.parse(
            source
        )

    except Exception as exc:

        print(
            f"AST FAILED : {type(exc).__name__}:{exc}"
        )

        return

    results = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.Call,
                ast.FunctionDef,
            ),
        ):
            continue

        if isinstance(
            node,
            ast.Call,
        ):

            target = None

            if isinstance(
                node.func,
                ast.Name,
            ):
                target = node.func.id

            elif isinstance(
                node.func,
                ast.Attribute,
            ):
                target = node.func.attr

            if target and is_feature_candidate(
                target
            ):

                results.append(
                    (
                        getattr(
                            node,
                            "lineno",
                            "?",
                        ),
                        target,
                    )
                )

    if not results:

        print(
            "FEATURE-RELATED CALLS : NONE"
        )

        return

    seen = set()

    for line_no, target in sorted(
        results
    ):

        key = (
            line_no,
            target,
        )

        if key in seen:
            continue

        seen.add(key)

        print(
            f"LINE {line_no:<6} -> {target}"
        )


# =============================================================================
# ZERO-INPUT API PROBE
# =============================================================================

def probe_zero_input_candidates(
    module_name,
    module,
):

    print()
    print(
        f"ZERO-INPUT FEATURE API PROBE : {module_name}"
    )

    line("-")

    candidates = []

    for name, obj in list_functions(
        module
    ):

        if not is_feature_candidate(
            name
        ):
            continue

        try:

            signature = inspect.signature(
                obj
            )

            required = [
                parameter
                for parameter
                in signature.parameters.values()
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

        except Exception:
            continue

        if len(required) == 0:

            candidates.append(
                (
                    name,
                    signature,
                    obj,
                )
            )

    if not candidates:

        print(
            "ZERO-INPUT CANDIDATES : NONE"
        )

        return []

    for name, signature, obj in candidates:

        try:
            line_no = inspect.getsourcelines(
                obj
            )[1]
        except Exception:
            line_no = "?"

        print(
            f"{name:<40}"
            f"LINE {line_no}"
        )

        print(
            f"    SIGNATURE : {signature}"
        )

    return candidates


# =============================================================================
# RUNTIME PROBE
# =============================================================================

def runtime_probe(
    module_name,
    candidates,
):

    if not candidates:
        return

    print()
    print(
        f"RUNTIME PROBE : {module_name}"
    )

    line("-")

    for name, signature, function in candidates:

        print()
        print(
            f"FUNCTION : {name}"
        )

        print(
            f"SIGNATURE: {signature}"
        )

        try:

            result = function()

            print(
                "RUNTIME  : SUCCESS"
            )

            print(
                f"TYPE     : {type(result).__name__}"
            )

            if isinstance(
                result,
                dict,
            ):

                print(
                    "MAPPING  : YES"
                )

                print(
                    f"ASSETS   : {len(result)}"
                )

                keys = list(
                    result.keys()
                )

                print(
                    f"KEY SAMPLE : {keys[:15]}"
                )

                matched = [
                    asset
                    for asset
                    in EXPECTED_ASSETS
                    if asset in result
                ]

                print(
                    f"EXPECTED ASSETS MATCHED : "
                    f"{len(matched)}/15"
                )

                if result:

                    first_key = keys[0]

                    first_value = result[
                        first_key
                    ]

                    print(
                        f"FIRST RECORD : {first_key}"
                    )

                    print(
                        f"RECORD TYPE  : "
                        f"{type(first_value).__name__}"
                    )

                    if isinstance(
                        first_value,
                        dict,
                    ):

                        print(
                            "RECORD KEYS  : "
                            f"{list(first_value.keys())}"
                        )

            else:

                print(
                    "MAPPING  : NO"
                )

        except Exception as exc:

            print(
                "RUNTIME  : BLOCKED"
            )

            print(
                f"ERROR    : "
                f"{type(exc).__name__}:{exc}"
            )


# =============================================================================
# SIGNAL SCORER CONTRACT INSPECTION
# =============================================================================

def inspect_scorer(
    signal_scorer,
):

    print()
    print(
        "SIGNAL SCORER FEATURE CONTRACT"
    )

    line("-")

    for name in (
        "load_features",
        "extract_latest_feature_record",
        "calculate_score",
        "load_scores",
    ):

        function = getattr(
            signal_scorer,
            name,
            None,
        )

        if not callable(function):

            print(
                f"{name:<40} MISSING"
            )

            continue

        try:
            signature = inspect.signature(
                function
            )
        except Exception:
            signature = "?"

        try:
            line_no = inspect.getsourcelines(
                function
            )[1]
        except Exception:
            line_no = "?"

        print(
            f"{name:<40}"
            f"LINE {line_no}"
        )

        print(
            f"    SIGNATURE : {signature}"
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
        "REAL_FEATURE_SOURCE_LOCATOR_v0.1"
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

    print()
    print(
        "Running self-test..."
    )

    self_test()

    modules = load_modules()

    print()
    line("-")
    print(
        "PRODUCTION MODULE RESOLUTION"
    )
    line("-")

    for name, module in modules.items():

        print(
            f"{name:<32} : IMPORT OK"
        )

        print(
            f"{'':32}   "
            f"{get_source_file(module)}"
        )

    # -------------------------------------------------------------------------
    # SCORER CONTRACT
    # -------------------------------------------------------------------------

    if "signal_scorer" in modules:

        inspect_scorer(
            modules[
                "signal_scorer"
            ]
        )

    # -------------------------------------------------------------------------
    # MODULE ANALYSIS
    # -------------------------------------------------------------------------

    all_zero_input = []

    for module_name, module in modules.items():

        print_function_candidates(
            module_name,
            module,
        )

        scan_source_text(
            module_name,
            module,
        )

        scan_ast_calls(
            module_name,
            module,
        )

        candidates = probe_zero_input_candidates(
            module_name,
            module,
        )

        if candidates:

            all_zero_input.extend(
                [
                    (
                        module_name,
                        candidate,
                    )
                    for candidate
                    in candidates
                ]
            )

    # -------------------------------------------------------------------------
    # RUNTIME ZERO-INPUT PROBES
    # -------------------------------------------------------------------------

    print()
    line("=")
    print(
        "ZERO-INPUT REAL FEATURE SOURCE RUNTIME PROBES"
    )
    line("=")

    if not all_zero_input:

        print(
            "ZERO-INPUT REAL FEATURE SOURCE : NONE"
        )

    else:

        grouped = {}

        for module_name, candidate in all_zero_input:

            grouped.setdefault(
                module_name,
                [],
            ).append(
                candidate
            )

        for module_name, candidates in grouped.items():

            runtime_probe(
                module_name,
                candidates,
            )

    # -------------------------------------------------------------------------
    # FINAL DIAGNOSTIC
    # -------------------------------------------------------------------------

    print()
    line("=")
    print(
        "DIAGNOSTIC SUMMARY"
    )
    line("=")

    print(
        f"Modules inspected : {len(modules)}"
    )

    print(
        f"Zero-input feature candidates : "
        f"{len(all_zero_input)}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This locator performs NO repair."
    )

    print(
        "No feature data is fabricated."
    )

    print(
        "No bars are fabricated."
    )

    print(
        "No indicators are fabricated."
    )

    print(
        "No database write is performed."
    )

    print(
        "The purpose is to identify the EXISTING real "
        "production feature source and its exact runtime API."
    )

    print()
    line("=")

    if all_zero_input:

        print(
            "LOCATOR STATUS : REAL FEATURE API CANDIDATE(S) FOUND"
        )

        print(
            "NEXT           : INSPECT RUNTIME PROBE RESULTS"
        )

    else:

        print(
            "LOCATOR STATUS : NO ZERO-INPUT FEATURE API FOUND"
        )

        print(
            "NEXT           : TRACE REAL BARS/INDICATORS INPUT BOUNDARY"
        )

    print(
        "DATABASE WRITE       : NONE"
    )

    print(
        "PRODUCTION MODIFIED  : NO"
    )

    print("=" * 100)

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )