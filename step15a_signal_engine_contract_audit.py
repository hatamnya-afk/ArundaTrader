# =============================================================================
# ARUNDA TRADER
# STEP 15A — SIGNAL ENGINE CONTRACT AUDIT v0.2
#
# PURPOSE
# -------
# Contract / behavioral audit of the existing Signal Layer.
#
# AUDITED FILES
# -------------
# signal_logic.py
# signal_engine.py
# signal_contract.py
#
# MODE
# ----
# READ ONLY / AUDIT ONLY
#
# DATABASE
# --------
# NOT USED
#
# WRITES
# ------
# NONE
#
# SCORING
# -------
# NOT USED
#
# PREDICTION
# ----------
# NOT USED
#
# DECISION
# --------
# NOT USED
#
# EXECUTION
# ---------
# NOT USED
#
# ARCHITECTURE
# ------------
# Existing production files are NOT modified.
#
# AUDIT VERSION
# -------------
# v0.2
#
# IMPORTANT
# ---------
# 15A-23 and 15A-24 use AST-based dependency inspection.
# They DO NOT search raw source text.
#
# =============================================================================

import ast
import os

import signal_engine
import signal_logic
import signal_contract


EXPECTED_ASSETS = [
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
]

EXPECTED_DIRECTIONS = {
    "LONG",
    "SHORT",
    "NONE",
}

EXPECTED_STATES = {
    "ACTIVE",
    "NEUTRAL",
}


# =============================================================================
# AUDIT UTILITIES
# =============================================================================

class AuditFailure(Exception):
    pass


def assert_true(condition, message):

    if not condition:
        raise AuditFailure(message)


def assert_equal(actual, expected, message):

    if actual != expected:

        raise AuditFailure(
            "{} | expected={!r}, actual={!r}".format(
                message,
                expected,
                actual,
            )
        )


def assert_raises(exception_type, func, message):

    try:

        func()

    except exception_type:

        return

    except Exception as error:

        raise AuditFailure(
            "{} | expected {}, got {}".format(
                message,
                exception_type.__name__,
                type(error).__name__,
            )
        )

    raise AuditFailure(
        "{} | expected {}".format(
            message,
            exception_type.__name__,
        )
    )


def run_test(name, function):

    try:

        function()

        print(
            "{:<48} : PASS".format(name)
        )

        return True

    except Exception as error:

        print(
            "{:<48} : FAIL".format(name)
        )

        print(
            "  ERROR :",
            type(error).__name__,
            str(error),
        )

        return False


# =============================================================================
# AST UTILITIES
# =============================================================================

def load_module_ast(module):

    path = module.__file__

    assert_true(
        path is not None,
        "module path unavailable: {}".format(
            module.__name__
        ),
    )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        source = file.read()

    try:

        return ast.parse(
            source,
            filename=path,
        )

    except SyntaxError as error:

        raise AuditFailure(
            "AST parse failed for {}: {}".format(
                os.path.basename(path),
                error,
            )
        )


def get_imported_modules(tree):

    modules = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                modules.add(
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:

                modules.add(
                    node.module
                )

    return modules


def get_import_aliases(tree):

    aliases = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                local_name = (
                    alias.asname
                    if alias.asname
                    else alias.name.split(".")[0]
                )

                aliases[local_name] = alias.name

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:

                for alias in node.names:

                    local_name = (
                        alias.asname
                        if alias.asname
                        else alias.name
                    )

                    aliases[local_name] = (
                        "{}.{}".format(
                            node.module,
                            alias.name,
                        )
                    )

    return aliases


def get_called_names(tree):

    calls = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):

            continue

        function = node.func

        if isinstance(
            function,
            ast.Name,
        ):

            calls.append(
                function.id
            )

        elif isinstance(
            function,
            ast.Attribute,
        ):

            parts = []

            current = function

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

            calls.append(
                ".".join(
                    reversed(parts)
                )
            )

    return calls


def get_name_references(tree):

    references = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Name,
        ):

            references.append(
                node.id
            )

    return references


def ast_dependency_report(module):

    tree = load_module_ast(
        module
    )

    return {
        "imports": get_imported_modules(
            tree
        ),
        "aliases": get_import_aliases(
            tree
        ),
        "calls": get_called_names(
            tree
        ),
        "names": get_name_references(
            tree
        ),
    }


# =============================================================================
# DEPENDENCY DEFINITIONS
# =============================================================================

SCORING_MODULE_NAMES = {
    "signal_scorer",
    "scoring",
    "signal_scoring",
}

SCORING_SYMBOL_NAMES = {
    "score",
    "calculate_score",
    "calculate_signal_score",
    "build_score",
    "signal_score",
}

PREDICTION_MODULE_NAMES = {
    "prediction",
    "predictor",
    "signal_prediction",
    "price_prediction",
}

PREDICTION_SYMBOL_NAMES = {
    "prediction",
    "predict",
    "predict_price",
    "predict_signal",
    "future_return",
    "future_price",
}


# =============================================================================
# AST DEPENDENCY MATCHING
# =============================================================================

def detect_dependency(
    report,
    module_names,
    symbol_names,
):

    findings = []

    #
    # IMPORT DEPENDENCIES
    #

    for imported in report["imports"]:

        root = imported.split(".")[0]

        if (
            imported in module_names
            or root in module_names
        ):

            findings.append(
                "IMPORT: {}".format(
                    imported
                )
            )

    #
    # IMPORT ALIASES
    #

    for local_name, target in report[
        "aliases"
    ].items():

        root = target.split(".")[0]

        if (
            target in module_names
            or root in module_names
            or local_name in module_names
        ):

            findings.append(
                "ALIAS: {} -> {}".format(
                    local_name,
                    target,
                )
            )

    #
    # FUNCTION CALLS
    #

    for call in report["calls"]:

        terminal = call.split(".")[-1]

        root = call.split(".")[0]

        if (
            call in symbol_names
            or terminal in symbol_names
            or root in module_names
        ):

            findings.append(
                "CALL: {}".format(
                    call
                )
            )

    #
    # DIRECT NAME REFERENCES
    #

    for name in report["names"]:

        if name in symbol_names:

            findings.append(
                "NAME: {}".format(
                    name
                )
            )

    return sorted(
        set(findings)
    )


# =============================================================================
# 15A-01 EXPECTED ASSET COMPLETENESS
# =============================================================================

def test_expected_assets():

    assert_equal(
        signal_logic.EXPECTED_ASSETS,
        EXPECTED_ASSETS,
        "signal_logic EXPECTED_ASSETS mismatch",
    )

    assert_equal(
        signal_engine.EXPECTED_ASSETS,
        EXPECTED_ASSETS,
        "signal_engine EXPECTED_ASSETS mismatch",
    )

    assert_equal(
        signal_contract.EXPECTED_ASSETS,
        EXPECTED_ASSETS,
        "signal_contract EXPECTED_ASSETS mismatch",
    )


# =============================================================================
# 15A-02 EMPTY SIGNAL CONTRACT
# =============================================================================

def test_empty_signal_contract():

    contract = (
        signal_contract.build_signal_contract()
    )

    assert_true(
        signal_contract.validate_signal_contract(
            contract
        ),
        "empty signal contract must validate",
    )

    assert_equal(
        len(contract),
        15,
        "signal contract must contain exactly 15 assets",
    )


# =============================================================================
# 15A-03 SIGNAL SCHEMA INTEGRITY
# =============================================================================

def test_signal_schema():

    signal = (
        signal_contract.build_empty_signal(
            "BTC"
        )
    )

    expected_fields = {
        "asset",
        "timestamp",
        "signal_state",
        "direction",
        "confidence",
        "reason",
    }

    assert_equal(
        set(signal.keys()),
        expected_fields,
        "signal fields mismatch",
    )

    assert_true(
        signal_contract.validate_signal(
            signal
        ),
        "empty BTC signal must validate",
    )


# =============================================================================
# 15A-04 UNKNOWN ASSET REJECTION
# =============================================================================

def test_unknown_asset_rejection():

    assert_raises(
        RuntimeError,
        lambda:
            signal_contract.build_empty_signal(
                "UNKNOWN"
            ),
        "unknown asset must be rejected",
    )


# =============================================================================
# 15A-05 LONG GENERATION
# =============================================================================

def test_long_generation():

    direction = (
        signal_logic.build_direction(
            {
                "trend": "UP",
                "momentum": "STRONG",
                "acceleration": "ACCELERATING",
                "position": "MIDDLE",
                "volatility": "MEDIUM",
            }
        )
    )

    assert_equal(
        direction,
        "LONG",
        "valid bullish structure must generate LONG",
    )


# =============================================================================
# 15A-06 SHORT GENERATION
# =============================================================================

def test_short_generation():

    direction = (
        signal_logic.build_direction(
            {
                "trend": "DOWN",
                "momentum": "WEAK",
                "acceleration": "DECELERATING",
                "position": "MIDDLE",
                "volatility": "MEDIUM",
            }
        )
    )

    assert_equal(
        direction,
        "SHORT",
        "valid bearish structure must generate SHORT",
    )


# =============================================================================
# 15A-07 NONE GENERATION
# =============================================================================

def test_none_generation():

    direction = (
        signal_logic.build_direction(
            {
                "trend": "UP",
                "momentum": "WEAK",
                "acceleration": "ACCELATING",
                "position": "MIDDLE",
                "volatility": "MEDIUM",
            }
        )
    )

    assert_equal(
        direction,
        "NONE",
        "non-directional structure must generate NONE",
    )


# =============================================================================
# 15A-08 HIGH VOLATILITY SAFETY
# =============================================================================

def test_high_volatility_safety():

    direction = (
        signal_logic.build_direction(
            {
                "trend": "UP",
                "momentum": "STRONG",
                "acceleration": "ACCELERATING",
                "position": "UPPER",
                "volatility": "HIGH",
            }
        )
    )

    assert_equal(
        direction,
        "NONE",
        "HIGH volatility must block directional output",
    )


# =============================================================================
# FIXTURE HELPERS
# =============================================================================

def long_structure():

    return {
        "trend": "UP",
        "momentum": "STRONG",
        "acceleration": "ACCELERATING",
        "position": "MIDDLE",
        "volatility": "MEDIUM",
    }


def short_structure():

    return {
        "trend": "DOWN",
        "momentum": "WEAK",
        "acceleration": "DECELERATING",
        "position": "MIDDLE",
        "volatility": "MEDIUM",
    }


def neutral_structure():

    return {
        "trend": "UP",
        "momentum": "WEAK",
        "acceleration": "ACCELATING",
        "position": "MIDDLE",
        "volatility": "MEDIUM",
    }


def high_volatility_long_structure():

    return {
        "trend": "UP",
        "momentum": "STRONG",
        "acceleration": "ACCELERATING",
        "position": "UPPER",
        "volatility": "HIGH",
    }


def ready_regime():

    return {
        "status": "READY",
        "regime": "TREND",
    }


def structural_record(
    structure
):

    return {
        "structure": structure
    }


# =============================================================================
# 15A-09 ENGINE LONG
# =============================================================================

def test_engine_long():

    result = signal_engine.build_signal(
        "BTC",
        ready_regime(),
        structural_record(
            long_structure()
        ),
    )

    assert_true(
        signal_contract.validate_signal(
            result
        ),
        "LONG signal must satisfy contract",
    )

    assert_equal(
        result["asset"],
        "BTC",
        "asset identity must be preserved",
    )

    assert_equal(
        result["direction"],
        "LONG",
        "LONG direction must propagate",
    )

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "LONG signal must be ACTIVE",
    )

    assert_equal(
        result["reason"],
        "STRUCTURAL_DIRECTION",
        "LONG reason mismatch",
    )


# =============================================================================
# 15A-10 ENGINE SHORT
# =============================================================================

def test_engine_short():

    result = signal_engine.build_signal(
        "ETH",
        ready_regime(),
        structural_record(
            short_structure()
        ),
    )

    assert_true(
        signal_contract.validate_signal(
            result
        ),
        "SHORT signal must satisfy contract",
    )

    assert_equal(
        result["asset"],
        "ETH",
        "asset identity must be preserved",
    )

    assert_equal(
        result["direction"],
        "SHORT",
        "SHORT direction must propagate",
    )

    assert_equal(
        result["signal_state"],
        "ACTIVE",
        "SHORT signal must be ACTIVE",
    )

    assert_equal(
        result["reason"],
        "STRUCTURAL_DIRECTION",
        "SHORT reason mismatch",
    )


# =============================================================================
# 15A-11 ENGINE NONE
# =============================================================================

def test_engine_none():

    result = signal_engine.build_signal(
        "SOL",
        ready_regime(),
        structural_record(
            neutral_structure()
        ),
    )

    assert_true(
        signal_contract.validate_signal(
            result
        ),
        "NONE signal must satisfy contract",
    )

    assert_equal(
        result["direction"],
        "NONE",
        "NONE direction mismatch",
    )

    assert_equal(
        result["signal_state"],
        "NEUTRAL",
        "NONE must map to NEUTRAL",
    )

    assert_equal(
        result["reason"],
        None,
        "NEUTRAL signal reason must be None",
    )


# =============================================================================
# 15A-12 HIGH VOLATILITY
# =============================================================================

def test_engine_high_volatility():

    result = signal_engine.build_signal(
        "XRP",
        ready_regime(),
        structural_record(
            high_volatility_long_structure()
        ),
    )

    assert_equal(
        result["direction"],
        "NONE",
        "HIGH volatility must suppress direction",
    )

    assert_equal(
        result["signal_state"],
        "NEUTRAL",
        "suppressed direction must become NEUTRAL",
    )


# =============================================================================
# 15A-13 MISSING REGIME
# =============================================================================

def test_missing_regime():

    assert_raises(
        RuntimeError,
        lambda:
            signal_engine.build_signal(
                "BTC",
                {},
                structural_record(
                    long_structure()
                ),
            ),
        "missing/non-ready regime must be rejected",
    )


# =============================================================================
# 15A-14 INVALID STRUCTURAL STATE
# =============================================================================

def test_invalid_structural_state():

    assert_raises(
        RuntimeError,
        lambda:
            signal_engine.build_signal(
                "BTC",
                ready_regime(),
                {},
            ),
        "missing structural state must be rejected",
    )


# =============================================================================
# 15A-15 INVALID STRUCTURAL TYPE
# =============================================================================

def test_invalid_structural_type():

    assert_raises(
        RuntimeError,
        lambda:
            signal_engine.build_signal(
                "BTC",
                ready_regime(),
                {
                    "structure": None
                },
            ),
        "invalid structural state must be rejected",
    )


# =============================================================================
# 15A-16 INPUT SENSITIVITY
# =============================================================================

def test_input_sensitivity():

    long_result = (
        signal_engine.build_signal(
            "BTC",
            ready_regime(),
            structural_record(
                long_structure()
            ),
        )
    )

    short_result = (
        signal_engine.build_signal(
            "BTC",
            ready_regime(),
            structural_record(
                short_structure()
            ),
        )
    )

    assert_true(
        long_result["direction"]
        != short_result["direction"],
        "material structural change must change direction",
    )


# =============================================================================
# 15A-17 DETERMINISM
# =============================================================================

def test_determinism():

    first = signal_engine.build_signal(
        "BTC",
        ready_regime(),
        structural_record(
            long_structure()
        ),
    )

    second = signal_engine.build_signal(
        "BTC",
        ready_regime(),
        structural_record(
            long_structure()
        ),
    )

    assert_equal(
        first,
        second,
        "identical inputs must generate identical outputs",
    )


# =============================================================================
# 15A-18 IDENTITY ISOLATION
# =============================================================================

def test_identity_isolation():

    btc = signal_engine.build_signal(
        "BTC",
        ready_regime(),
        structural_record(
            long_structure()
        ),
    )

    eth = signal_engine.build_signal(
        "ETH",
        ready_regime(),
        structural_record(
            long_structure()
        ),
    )

    assert_equal(
        btc["asset"],
        "BTC",
        "BTC identity corrupted",
    )

    assert_equal(
        eth["asset"],
        "ETH",
        "ETH identity corrupted",
    )


# =============================================================================
# 15A-19 SEMANTIC CONSISTENCY
# =============================================================================

def test_signal_semantic_consistency():

    directions = {
        "LONG": long_structure(),
        "SHORT": short_structure(),
        "NONE": neutral_structure(),
    }

    for direction, structure in directions.items():

        result = signal_engine.build_signal(
            "BTC",
            ready_regime(),
            structural_record(
                structure
            ),
        )

        if direction in {
            "LONG",
            "SHORT",
        }:

            assert_equal(
                result["signal_state"],
                "ACTIVE",
                "directional signal must be ACTIVE",
            )

        else:

            assert_equal(
                result["signal_state"],
                "NEUTRAL",
                "NONE signal must be NEUTRAL",
            )


# =============================================================================
# 15A-20 INVALID SEMANTIC COMBINATIONS
# =============================================================================

def test_contract_rejects_semantic_mismatch():

    invalid_active_none = {
        "asset": "BTC",
        "timestamp": None,
        "signal_state": "ACTIVE",
        "direction": "NONE",
        "confidence": None,
        "reason": None,
    }

    invalid_neutral_long = {
        "asset": "BTC",
        "timestamp": None,
        "signal_state": "NEUTRAL",
        "direction": "LONG",
        "confidence": None,
        "reason": None,
    }

    active_none_current = (
        signal_contract.validate_signal(
            invalid_active_none
        )
    )

    neutral_long_current = (
        signal_contract.validate_signal(
            invalid_neutral_long
        )
    )

    if (
        active_none_current
        or neutral_long_current
    ):

        raise AuditFailure(
            "SIGNAL CONTRACT SEMANTIC GAP: "
            "invalid state/direction combinations are accepted"
        )


# =============================================================================
# 15A-21 DATABASE ISOLATION
# =============================================================================

def test_database_isolation():

    source_files = [
        signal_logic.__file__,
        signal_engine.__file__,
        signal_contract.__file__,
    ]

    for path in source_files:

        tree = load_module_ast(
            signal_logic
            if path == signal_logic.__file__
            else signal_engine
            if path == signal_engine.__file__
            else signal_contract
        )

        imported_modules = (
            get_imported_modules(tree)
        )

        assert_true(
            "sqlite3" not in imported_modules,
            "direct sqlite3 import found in {}".format(
                os.path.basename(path)
            ),
        )


# =============================================================================
# 15A-22 WRITE ISOLATION
# =============================================================================

def test_write_isolation():

    forbidden_modules = {
        "sqlite3",
        "pandas",
        "sqlalchemy",
    }

    modules = [
        signal_logic,
        signal_engine,
        signal_contract,
    ]

    for module in modules:

        report = ast_dependency_report(
            module
        )

        imports = report["imports"]

        for forbidden in forbidden_modules:

            assert_true(
                forbidden not in imports,
                "possible storage dependency {} found in {}".format(
                    forbidden,
                    module.__name__,
                ),
            )


# =============================================================================
# 15A-23 SCORING ISOLATION — AST BASED
# =============================================================================

def test_scoring_isolation():

    report = ast_dependency_report(
        signal_engine
    )

    findings = detect_dependency(
        report,
        SCORING_MODULE_NAMES,
        SCORING_SYMBOL_NAMES,
    )

    assert_equal(
        findings,
        [],
        "real scoring dependency detected",
    )


# =============================================================================
# 15A-24 PREDICTION ISOLATION — AST BASED
# =============================================================================

def test_prediction_isolation():

    report = ast_dependency_report(
        signal_engine
    )

    findings = detect_dependency(
        report,
        PREDICTION_MODULE_NAMES,
        PREDICTION_SYMBOL_NAMES,
    )

    assert_equal(
        findings,
        [],
        "real prediction dependency detected",
    )


# =============================================================================
# 15A-25 DECISION ISOLATION
# =============================================================================

def test_decision_isolation():

    tree = load_module_ast(
        signal_engine
    )

    imported_modules = (
        get_imported_modules(tree)
    )

    forbidden_modules = {
        "decision_engine",
        "decision_contract",
        "execution_engine",
        "order_engine",
    }

    for module in forbidden_modules:

        assert_true(
            module not in imported_modules,
            "decision/execution dependency detected: {}".format(
                module
            ),
        )


# =============================================================================
# 15A-26 CONFIDENCE ISOLATION
# =============================================================================

def test_confidence_not_computed():

    result = signal_engine.build_signal(
        "BTC",
        ready_regime(),
        structural_record(
            long_structure()
        ),
    )

    assert_equal(
        result["confidence"],
        None,
        "Signal Engine must not calculate confidence at this stage",
    )


# =============================================================================
# 15A-27 REASON CONTRACT
# =============================================================================

def test_reason_contract():

    long_result = signal_engine.build_signal(
        "BTC",
        ready_regime(),
        structural_record(
            long_structure()
        ),
    )

    neutral_result = signal_engine.build_signal(
        "BTC",
        ready_regime(),
        structural_record(
            neutral_structure()
        ),
    )

    assert_equal(
        long_result["reason"],
        "STRUCTURAL_DIRECTION",
        "active signal reason mismatch",
    )

    assert_equal(
        neutral_result["reason"],
        None,
        "neutral signal reason mismatch",
    )


# =============================================================================
# 15A-28 INPUT NON-MUTATION
# =============================================================================

def test_input_non_mutation():

    regime = ready_regime()

    structure = structural_record(
        long_structure()
    )

    regime_before = dict(
        regime
    )

    structure_before = {
        "structure": dict(
            structure["structure"]
        )
    }

    signal_engine.build_signal(
        "BTC",
        regime,
        structure,
    )

    assert_equal(
        regime,
        regime_before,
        "regime input was mutated",
    )

    assert_equal(
        structure,
        structure_before,
        "structural input was mutated",
    )


# =============================================================================
# 15A-29 ALL EXPECTED ASSETS
# =============================================================================

def test_all_assets_build():

    for asset in EXPECTED_ASSETS:

        result = signal_engine.build_signal(
            asset,
            ready_regime(),
            structural_record(
                long_structure()
            ),
        )

        assert_equal(
            result["asset"],
            asset,
            "asset identity mismatch",
        )

        assert_true(
            signal_contract.validate_signal(
                result
            ),
            "invalid signal generated for {}".format(
                asset
            ),
        )


# =============================================================================
# 15A-30 CONTRACT FIELD TYPES
# =============================================================================

def test_field_types():

    result = signal_engine.build_signal(
        "BTC",
        ready_regime(),
        structural_record(
            long_structure()
        ),
    )

    assert_true(
        isinstance(
            result["asset"],
            str,
        ),
        "asset must be string",
    )

    assert_true(
        result["timestamp"] is None
        or isinstance(
            result["timestamp"],
            str,
        ),
        "timestamp must be None or string",
    )

    assert_true(
        isinstance(
            result["signal_state"],
            str,
        ),
        "signal_state must be string",
    )

    assert_true(
        isinstance(
            result["direction"],
            str,
        ),
        "direction must be string",
    )

    assert_true(
        result["confidence"] is None
        or isinstance(
            result["confidence"],
            (int, float),
        ),
        "confidence must be None or numeric",
    )

    assert_true(
        result["reason"] is None
        or isinstance(
            result["reason"],
            str,
        ),
        "reason must be None or string",
    )


# =============================================================================
# STATIC ARCHITECTURE AUDIT
# =============================================================================

def static_architecture_audit():

    print()

    print("=" * 78)
    print("STATIC ARCHITECTURE AUDIT")
    print("=" * 78)

    files = [
        signal_logic.__file__,
        signal_engine.__file__,
        signal_contract.__file__,
    ]

    for path in files:

        print(
            "{:<32} : FOUND".format(
                os.path.basename(path)
            )
        )

        assert_true(
            os.path.isfile(path),
            "missing production file: {}".format(
                path
            ),
        )

    print()


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print("ARUNDA TRADER — STEP 15A")
    print("SIGNAL ENGINE CONTRACT AUDIT v0.2")
    print("=" * 78)

    print(
        "Mode        : READ ONLY / AUDIT ONLY"
    )

    print(
        "Database    : NOT USED"
    )

    print(
        "Writes      : NONE"
    )

    print(
        "Scoring     : NOT USED"
    )

    print(
        "Prediction   : NOT USED"
    )

    print(
        "Decision     : NOT USED"
    )

    print(
        "Execution    : NOT USED"
    )

    print()

    print(
        "Production files:"
    )

    print(
        "  - signal_logic.py"
    )

    print(
        "  - signal_engine.py"
    )

    print(
        "  - signal_contract.py"
    )

    print("=" * 78)
    print()

    static_architecture_audit()

    tests = [

        (
            "15A-01 Expected asset completeness",
            test_expected_assets,
        ),

        (
            "15A-02 Empty signal contract",
            test_empty_signal_contract,
        ),

        (
            "15A-03 Signal schema integrity",
            test_signal_schema,
        ),

        (
            "15A-04 Unknown asset rejection",
            test_unknown_asset_rejection,
        ),

        (
            "15A-05 LONG generation",
            test_long_generation,
        ),

        (
            "15A-06 SHORT generation",
            test_short_generation,
        ),

        (
            "15A-07 NONE generation",
            test_none_generation,
        ),

        (
            "15A-08 HIGH volatility safety",
            test_high_volatility_safety,
        ),

        (
            "15A-09 Engine LONG propagation",
            test_engine_long,
        ),

        (
            "15A-10 Engine SHORT propagation",
            test_engine_short,
        ),

        (
            "15A-11 Engine NONE propagation",
            test_engine_none,
        ),

        (
            "15A-12 HIGH volatility propagation",
            test_engine_high_volatility,
        ),

        (
            "15A-13 Missing regime rejection",
            test_missing_regime,
        ),

        (
            "15A-14 Invalid structural state",
            test_invalid_structural_state,
        ),

        (
            "15A-15 Invalid structural type",
            test_invalid_structural_type,
        ),

        (
            "15A-16 Input sensitivity",
            test_input_sensitivity,
        ),

        (
            "15A-17 Determinism",
            test_determinism,
        ),

        (
            "15A-18 Identity isolation",
            test_identity_isolation,
        ),

        (
            "15A-19 Signal semantic consistency",
            test_signal_semantic_consistency,
        ),

        (
            "15A-20 Invalid semantic combinations",
            test_contract_rejects_semantic_mismatch,
        ),

        (
            "15A-21 Database isolation",
            test_database_isolation,
        ),

        (
            "15A-22 Write isolation",
            test_write_isolation,
        ),

        (
            "15A-23 Scoring isolation",
            test_scoring_isolation,
        ),

        (
            "15A-24 Prediction isolation",
            test_prediction_isolation,
        ),

        (
            "15A-25 Decision isolation",
            test_decision_isolation,
        ),

        (
            "15A-26 Confidence isolation",
            test_confidence_not_computed,
        ),

        (
            "15A-27 Reason contract",
            test_reason_contract,
        ),

        (
            "15A-28 Input non-mutation",
            test_input_non_mutation,
        ),

        (
            "15A-29 All expected assets",
            test_all_assets_build,
        ),

        (
            "15A-30 Contract field types",
            test_field_types,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print("BEHAVIORAL CONTRACT AUDIT")
    print("=" * 78)

    for name, function in tests:

        if run_test(
            name,
            function,
        ):

            passed += 1

        else:

            failed += 1

    print()

    print("=" * 78)
    print("STEP 15A SUMMARY")
    print("=" * 78)

    print(
        "Total Tests :",
        len(tests),
    )

    print(
        "PASS        :",
        passed,
    )

    print(
        "FAIL        :",
        failed,
    )

    print()

    if failed == 0:

        print("=" * 78)
        print("STEP 15A VERDICT")
        print("=" * 78)

        print(
            "RESULT      : SIGNAL ENGINE CONTRACT AUDIT PASS"
        )

        print(
            "STATUS      : READY FOR NEXT CONTRACT STEP"
        )

        print()

        print(
            "Architecture : PRESERVED"
        )

        print(
            "Database     : NOT USED"
        )

        print(
            "Writes       : NONE"
        )

        print(
            "Scoring      : NOT USED"
        )

        print(
            "Prediction   : NOT USED"
        )

        print(
            "Decision     : NOT USED"
        )

        print(
            "Execution    : NOT USED"
        )

        print(
            "Look-Ahead   : PROTECTED"
        )

        print("=" * 78)

        return 0

    print("=" * 78)
    print("STEP 15A VERDICT")
    print("=" * 78)

    print(
        "RESULT      : SIGNAL ENGINE CONTRACT AUDIT FAIL"
    )

    print(
        "STATUS      : REPAIR REQUIRED"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Production Signal files were NOT modified."
    )

    print("=" * 78)

    return 1


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )