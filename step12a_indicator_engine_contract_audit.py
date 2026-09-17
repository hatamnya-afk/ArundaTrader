"""
ARUNDA TRADER — DEV-06
STEP 12A — INDICATOR ENGINE CONTRACT AUDIT

Purpose
-------
Static + runtime contract audit for the real Indicator Engine v0.1.

Architecture
------------
- READ ONLY
- Database independent
- No SQL
- No database writes
- No trading decisions
- No BUY / SELL output
- Look-ahead protection required
- Deterministic output required
- CMC_ID / symbol identity preserved

This audit is intentionally based on the ACTUAL public API of
indicator_engine.py.
"""

from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence


# ============================================================================
# CONFIGURATION
# ============================================================================

ENGINE_MODULE_NAME = "indicator_engine"
ENGINE_FILE_NAME = "indicator_engine.py"

ENGINE_NAME = "INDICATOR_ENGINE_v0.1"


REQUIRED_FUNCTIONS = (
    "calculate_sma",
    "calculate_ema",
    "calculate_wma",
    "calculate_rsi",
    "calculate_macd",
    "calculate_atr",
    "calculate_bollinger_bands",
    "calculate_stochastic",
    "calculate_adx",
    "calculate_vwap",
    "calculate_volume_change_ratio",
    "calculate_ichimoku",
    "calculate_indicator_records",
    "validate_indicator_record",
    "validate_indicator_collection",
    "lookahead_audit",
    "determinism_audit",
    "self_test",
)


REQUIRED_CLASSES = (
    "IndicatorBar",
    "IndicatorRecord",
)


INDICATOR_RECORD_FIELDS = (
    "index",
    "timestamp",
    "cmc_id",
    "symbol",
    "close",

    "sma",
    "ema",
    "wma",

    "rsi",

    "macd",
    "macd_signal",
    "macd_histogram",

    "atr",

    "bb_middle",
    "bb_upper",
    "bb_lower",
    "bb_width",
    "bb_position",

    "stochastic_k",
    "stochastic_d",

    "adx",
    "plus_di",
    "minus_di",

    "vwap",
    "volume_change_ratio",

    "ichimoku_tenkan",
    "ichimoku_kijun",
    "ichimoku_senkou_a",
    "ichimoku_senkou_b",
    "ichimoku_chikou",
)


DECISION_TERMS = (
    "BUY",
    "SELL",
    "LONG",
    "SHORT",
)


SQL_MUTATION_TERMS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "REPLACE",
    "TRUNCATE",
)


# ============================================================================
# OUTPUT HELPERS
# ============================================================================

def section(title: str) -> None:
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def result_line(
    label: str,
    value: Any,
    width: int = 48,
) -> None:

    print(
        f"{label:<{width}} : {value}"
    )


# ============================================================================
# PATH / SOURCE
# ============================================================================

def locate_engine_file() -> Path:

    current_dir = Path(__file__).resolve().parent

    engine_path = (
        current_dir
        / ENGINE_FILE_NAME
    )

    if not engine_path.exists():

        raise FileNotFoundError(
            f"Cannot locate {ENGINE_FILE_NAME} "
            f"next to audit file."
        )

    return engine_path


def read_engine_source(
    engine_path: Path,
) -> str:

    return engine_path.read_text(
        encoding="utf-8"
    )


# ============================================================================
# AST
# ============================================================================

def parse_source(
    source: str,
) -> ast.AST:

    return ast.parse(
        source,
        filename=ENGINE_FILE_NAME,
    )


def collect_ast_functions(
    tree: ast.AST,
) -> List[str]:

    functions: List[str] = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            functions.append(
                node.name
            )

    return sorted(
        set(functions)
    )


def collect_ast_classes(
    tree: ast.AST,
) -> List[str]:

    classes: List[str] = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.ClassDef,
        ):

            classes.append(
                node.name
            )

    return sorted(
        set(classes)
    )


# ============================================================================
# SOURCE SAFETY
# ============================================================================

def source_contains_sql_mutation(
    source: str,
) -> bool:

    upper = source.upper()

    return any(
        term in upper
        for term in SQL_MUTATION_TERMS
    )


def source_has_database_dependency(
    tree: ast.AST,
) -> bool:

    forbidden_modules = {
        "sqlite3",
        "sqlalchemy",
        "pymysql",
        "psycopg2",
        "psycopg",
        "mysql",
    }

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                root = alias.name.split(".")[0]

                if root in forbidden_modules:
                    return True

        elif isinstance(node, ast.ImportFrom):

            if node.module:

                root = node.module.split(".")[0]

                if root in forbidden_modules:
                    return True

    return False


# ============================================================================
# IMPORT ENGINE
# ============================================================================

def import_engine():

    import importlib

    module = importlib.import_module(
        ENGINE_MODULE_NAME
    )

    return module


# ============================================================================
# API INVENTORY
# ============================================================================

def audit_required_functions(
    engine,
) -> bool:

    missing = []

    for name in REQUIRED_FUNCTIONS:

        if not hasattr(engine, name):

            missing.append(name)

    if missing:

        print(
            "Missing required functions:"
        )

        for name in missing:
            print(f" - {name}")

        return False

    return True


def audit_required_classes(
    engine,
) -> bool:

    missing = []

    for name in REQUIRED_CLASSES:

        if not hasattr(engine, name):

            missing.append(name)

    if missing:

        print(
            "Missing required classes:"
        )

        for name in missing:
            print(f" - {name}")

        return False

    return True


# ============================================================================
# SIGNATURE AUDIT
# ============================================================================

EXPECTED_PARAMETERS = {
    "calculate_sma": (
        "closes",
        "period",
    ),

    "calculate_ema": (
        "closes",
        "period",
    ),

    "calculate_wma": (
        "closes",
        "period",
    ),

    "calculate_rsi": (
        "closes",
        "period",
    ),

    "calculate_macd": (
        "closes",
        "fast_period",
        "slow_period",
        "signal_period",
    ),

    "calculate_atr": (
        "bars",
        "period",
    ),

    "calculate_bollinger_bands": (
        "closes",
        "period",
        "stddev_multiplier",
    ),

    "calculate_stochastic": (
        "bars",
        "period",
        "smooth_k",
        "smooth_d",
    ),

    "calculate_adx": (
        "bars",
        "period",
    ),

    "calculate_vwap": (
        "bars",
    ),

    "calculate_volume_change_ratio": (
        "bars",
    ),

    "calculate_ichimoku": (
        "bars",
        "tenkan_period",
        "kijun_period",
        "senkou_b_period",
        "displacement",
    ),

    "calculate_indicator_records": (
        "bars",
        "sma_period",
        "ema_period",
        "wma_period",
        "rsi_period",
        "macd_fast",
        "macd_slow",
        "macd_signal",
        "atr_period",
        "bb_period",
        "bb_stddev",
        "stochastic_period",
        "stochastic_smooth_k",
        "stochastic_smooth_d",
        "adx_period",
        "ichimoku_tenkan",
        "ichimoku_kijun",
        "ichimoku_senkou_b",
        "ichimoku_displacement",
    ),

    "validate_indicator_record": (
        "record",
    ),

    "validate_indicator_collection": (
        "records",
    ),

    "lookahead_audit": (
        "bars",
    ),

    "determinism_audit": (
        "bars",
    ),

    "self_test": (),
}


def audit_public_signatures(
    engine,
) -> bool:

    for function_name, expected in EXPECTED_PARAMETERS.items():

        function = getattr(
            engine,
            function_name,
        )

        signature = inspect.signature(
            function
        )

        actual = tuple(
            signature.parameters.keys()
        )

        if actual != expected:

            print(
                f"SIGNATURE MISMATCH | "
                f"{function_name} | "
                f"expected={expected} | "
                f"actual={actual}"
            )

            return False

    return True


# ============================================================================
# DATACLASS CONTRACT
# ============================================================================

def audit_indicator_record_schema(
    engine,
) -> bool:

    IndicatorRecord = engine.IndicatorRecord

    actual_fields = tuple(
        IndicatorRecord.__dataclass_fields__.keys()
    )

    if actual_fields != INDICATOR_RECORD_FIELDS:

        print(
            "IndicatorRecord schema mismatch."
        )

        print(
            f"Expected : {INDICATOR_RECORD_FIELDS}"
        )

        print(
            f"Actual   : {actual_fields}"
        )

        return False

    return True


def audit_indicator_bar_schema(
    engine,
) -> bool:

    IndicatorBar = engine.IndicatorBar

    expected = (
        "timestamp",
        "high",
        "low",
        "close",
        "open",
        "volume",
        "cmc_id",
        "symbol",
    )

    actual = tuple(
        IndicatorBar.__dataclass_fields__.keys()
    )

    if actual != expected:

        print(
            "IndicatorBar schema mismatch."
        )

        print(
            f"Expected : {expected}"
        )

        print(
            f"Actual   : {actual}"
        )

        return False

    return True


# ============================================================================
# SYNTHETIC DATA
# ============================================================================

def build_test_bars(
    engine,
    count: int = 80,
):

    bars = []

    IndicatorBar = engine.IndicatorBar

    for i in range(count):

        close = (
            100.0
            + i
            + (1.0 if i % 3 == 0 else 0.0)
        )

        bars.append(
            IndicatorBar(
                timestamp=i,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                open=close,
                volume=1000.0 + i * 10.0,
                cmc_id=777,
                symbol="AUDIT_TEST",
            )
        )

    return bars


# ============================================================================
# RUNTIME OUTPUT CONTRACT
# ============================================================================

def audit_runtime_output(
    engine,
    bars,
) -> bool:

    records = engine.calculate_indicator_records(
        bars
    )

    if not isinstance(
        records,
        list,
    ):

        print(
            "calculate_indicator_records "
            "did not return list."
        )

        return False

    if len(records) != len(bars):

        print(
            "Record count mismatch."
        )

        return False

    for i, record in enumerate(records):

        if not isinstance(
            record,
            engine.IndicatorRecord,
        ):

            print(
                f"Invalid record type at index {i}"
            )

            return False

        if record.index != i:

            print(
                f"Index mismatch at {i}"
            )

            return False

        if record.timestamp != bars[i].timestamp:

            print(
                f"Timestamp propagation mismatch at {i}"
            )

            return False

        if record.cmc_id != bars[i].cmc_id:

            print(
                f"CMC_ID propagation mismatch at {i}"
            )

            return False

        if record.symbol != bars[i].symbol:

            print(
                f"Symbol propagation mismatch at {i}"
            )

            return False

        if record.close != bars[i].close:

            print(
                f"Close propagation mismatch at {i}"
            )

            return False

        engine.validate_indicator_record(
            record
        )

    return engine.validate_indicator_collection(
        records
    )


# ============================================================================
# INDICATOR FAMILY CONTRACT
# ============================================================================

def audit_indicator_families(
    engine,
    bars,
) -> bool:

    closes = [
        bar.close
        for bar in bars
    ]

    trend = (
        engine.calculate_sma(closes),
        engine.calculate_ema(closes),
        engine.calculate_wma(closes),
        engine.calculate_macd(closes),
    )

    if len(trend) != 4:
        return False

    momentum = (
        engine.calculate_rsi(closes),
        engine.calculate_stochastic(bars),
    )

    if len(momentum) != 2:
        return False

    volatility = (
        engine.calculate_atr(bars),
        engine.calculate_bollinger_bands(closes),
    )

    if len(volatility) != 2:
        return False

    strength = engine.calculate_adx(bars)

    if len(strength) != 3:
        return False

    price_volume = (
        engine.calculate_vwap(bars),
        engine.calculate_volume_change_ratio(bars),
    )

    if len(price_volume) != 2:
        return False

    cloud = engine.calculate_ichimoku(bars)

    if len(cloud) != 5:
        return False

    return True


# ============================================================================
# WARM-UP CONTRACT
# ============================================================================

def audit_warmup_contract(
    engine,
    bars,
) -> bool:

    records = engine.calculate_indicator_records(
        bars
    )

    first = records[0]

    required_none_fields = (
        "sma",
        "ema",
        "wma",
        "rsi",
        "macd",
        "macd_signal",
        "macd_histogram",
        "atr",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "bb_position",
        "stochastic_k",
        "stochastic_d",
        "adx",
        "plus_di",
        "minus_di",
        "ichimoku_tenkan",
        "ichimoku_kijun",
        "ichimoku_senkou_b",
    )

    for field in required_none_fields:

        if getattr(first, field) is not None:

            print(
                f"Warm-up violation | "
                f"field={field} | "
                f"value={getattr(first, field)}"
            )

            return False

    return True


# ============================================================================
# NUMERIC CONTRACT
# ============================================================================

def audit_numeric_contract(
    engine,
    bars,
) -> bool:

    records = engine.calculate_indicator_records(
        bars
    )

    numeric_fields = (
        "close",
        "sma",
        "ema",
        "wma",
        "rsi",
        "macd",
        "macd_signal",
        "macd_histogram",
        "atr",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "bb_position",
        "stochastic_k",
        "stochastic_d",
        "adx",
        "plus_di",
        "minus_di",
        "vwap",
        "volume_change_ratio",
        "ichimoku_tenkan",
        "ichimoku_kijun",
        "ichimoku_senkou_a",
        "ichimoku_senkou_b",
        "ichimoku_chikou",
    )

    for record in records:

        for field in numeric_fields:

            value = getattr(
                record,
                field,
            )

            if value is not None:

                if not engine._finite(value):

                    print(
                        f"Non-finite runtime value | "
                        f"index={record.index} | "
                        f"field={field}"
                    )

                    return False

    return True


# ============================================================================
# IDENTITY CONTRACT
# ============================================================================

def audit_identity_contract(
    engine,
) -> bool:

    IndicatorBar = engine.IndicatorBar

    bars = [
        IndicatorBar(
            timestamp=100,
            high=110,
            low=90,
            close=100,
            volume=1000,
            cmc_id=12345,
            symbol="BTC_USDT",
        ),

        IndicatorBar(
            timestamp=101,
            high=111,
            low=91,
            close=101,
            volume=1100,
            cmc_id=12345,
            symbol="BTC_USDT",
        ),

        IndicatorBar(
            timestamp=102,
            high=112,
            low=92,
            close=102,
            volume=1200,
            cmc_id=12345,
            symbol="BTC_USDT",
        ),
    ]

    records = engine.calculate_indicator_records(
        bars
    )

    for i, record in enumerate(records):

        if record.timestamp != bars[i].timestamp:
            return False

        if record.cmc_id != 12345:
            return False

        if record.symbol != "BTC_USDT":
            return False

    return True


# ============================================================================
# INPUT SAFETY
# ============================================================================

def audit_input_safety(
    engine,
) -> bool:

    IndicatorBar = engine.IndicatorBar

    invalid_ohlc = [
        IndicatorBar(
            timestamp=0,
            high=10,
            low=20,
            close=15,
        )
    ]

    try:

        engine.validate_bars(
            invalid_ohlc
        )

    except ValueError:
        pass

    else:

        print(
            "Invalid OHLC was accepted."
        )

        return False

    invalid_volume = [
        IndicatorBar(
            timestamp=0,
            high=10,
            low=5,
            close=8,
            volume=-1,
        )
    ]

    try:

        engine.validate_bars(
            invalid_volume
        )

    except ValueError:
        pass

    else:

        print(
            "Negative volume was accepted."
        )

        return False

    invalid_nan = [
        IndicatorBar(
            timestamp=0,
            high=float("nan"),
            low=5,
            close=8,
        )
    ]

    try:

        engine.validate_bars(
            invalid_nan
        )

    except ValueError:
        pass

    else:

        print(
            "NaN OHLC was accepted."
        )

        return False

    return True


# ============================================================================
# LOOK-AHEAD CONTRACT
# ============================================================================

def audit_lookahead_contract(
    engine,
    bars,
) -> bool:

    result = engine.lookahead_audit(
        bars
    )

    if result is not True:

        print(
            "lookahead_audit returned failure."
        )

        return False

    return True


# ============================================================================
# DETERMINISM CONTRACT
# ============================================================================

def audit_determinism_contract(
    engine,
    bars,
) -> bool:

    result = engine.determinism_audit(
        bars
    )

    if result is not True:

        print(
            "determinism_audit returned failure."
        )

        return False

    first = engine.calculate_indicator_records(
        bars
    )

    second = engine.calculate_indicator_records(
        bars
    )

    if first != second:

        print(
            "Repeated calculation is not deterministic."
        )

        return False

    return True


# ============================================================================
# DECISION ISOLATION
# ============================================================================

def audit_decision_isolation(
    source: str,
) -> bool:

    upper = source.upper()

    forbidden_patterns = (
        "BUY",
        "SELL",
        "LONG",
        "SHORT",
    )

    for term in forbidden_patterns:

        # Allow documentation describing forbidden outputs.
        # We reject actual decision-like executable identifiers.
        for node in ast.walk(
            ast.parse(
                source,
                filename=ENGINE_FILE_NAME,
            )
        ):

            if isinstance(
                node,
                ast.Name,
            ):

                if node.id.upper() == term:

                    print(
                        f"Decision identifier found: {term}"
                    )

                    return False

            if isinstance(
                node,
                ast.Attribute,
            ):

                if node.attr.upper() == term:

                    print(
                        f"Decision attribute found: {term}"
                    )

                    return False

    return True


# ============================================================================
# SOURCE ORDER / ARCHITECTURE
# ============================================================================

def audit_architecture_contract(
    source: str,
    tree: ast.AST,
) -> bool:

    if "sqlite3" in source.lower():

        print(
            "Database dependency detected."
        )

        return False

    if source_has_database_dependency(tree):

        print(
            "Database module dependency detected."
        )

        return False

    if source_contains_sql_mutation(source):

        print(
            "SQL mutation keyword detected."
        )

        return False

    return True


# ============================================================================
# SELF TEST CONTRACT
# ============================================================================

def audit_self_test(
    engine,
) -> bool:

    result = engine.self_test()

    if result is not True:

        print(
            f"self_test returned {result!r}"
        )

        return False

    return True


# ============================================================================
# MAIN AUDIT
# ============================================================================

def run_audit() -> bool:

    print("=" * 100)
    print(
        "ARUNDA TRADER — DEV-06 — STEP 12A"
    )
    print(
        "INDICATOR ENGINE CONTRACT AUDIT"
    )
    print("=" * 100)

    # ------------------------------------------------------------------------
    # Locate source
    # ------------------------------------------------------------------------

    section("MODE")

    result_line(
        "Database mutation",
        "NONE",
    )

    result_line(
        "Production write",
        "NONE",
    )

    result_line(
        "Audit mode",
        "READ ONLY",
    )

    result_line(
        "Database usage",
        "NOT REQUIRED",
    )

    engine_path = locate_engine_file()

    source = read_engine_source(
        engine_path
    )

    # ------------------------------------------------------------------------
    # AST
    # ------------------------------------------------------------------------

    section("FILE VALIDATION")

    try:

        tree = parse_source(
            source
        )

        result_line(
            "Indicator Engine",
            "PASS",
        )

        result_line(
            "AST Parse",
            "PASS",
        )

    except Exception as exc:

        result_line(
            "Indicator Engine",
            "FAIL",
        )

        result_line(
            "AST Parse",
            f"FAIL — {exc}",
        )

        return False

    # ------------------------------------------------------------------------
    # Source safety
    # ------------------------------------------------------------------------

    section("SOURCE SAFETY")

    sql_safe = not source_contains_sql_mutation(
        source
    )

    db_safe = not source_has_database_dependency(
        tree
    )

    result_line(
        "SQL mutation statements",
        "PASS" if sql_safe else "FAIL",
    )

    result_line(
        "Database independence",
        "PASS" if db_safe else "FAIL",
    )

    if not sql_safe or not db_safe:
        return False

    # ------------------------------------------------------------------------
    # Function inventory
    # ------------------------------------------------------------------------

    section(
        "INDICATOR ENGINE FUNCTION INVENTORY"
    )

    functions = collect_ast_functions(
        tree
    )

    for function_name in functions:

        print(
            f" - {function_name}"
        )

    # ------------------------------------------------------------------------
    # Required functions
    # ------------------------------------------------------------------------

    section(
        "REQUIRED INDICATOR ENGINE FUNCTIONS"
    )

    required_functions_pass = audit_required_functions(
        import_engine()
    )

    result_line(
        "Required functions",
        "PASS"
        if required_functions_pass
        else "FAIL",
    )

    if not required_functions_pass:
        return False

    # ------------------------------------------------------------------------
    # Classes
    # ------------------------------------------------------------------------

    engine = import_engine()

    result_line(
        "Required classes",
        "PASS"
        if audit_required_classes(engine)
        else "FAIL",
    )

    if not audit_required_classes(engine):
        return False

    # ------------------------------------------------------------------------
    # Signatures
    # ------------------------------------------------------------------------

    section(
        "PUBLIC API SIGNATURE AUDIT"
    )

    signature_pass = audit_public_signatures(
        engine
    )

    result_line(
        "Public API signatures",
        "PASS"
        if signature_pass
        else "FAIL",
    )

    if not signature_pass:
        return False

    # ------------------------------------------------------------------------
    # Dataclass schemas
    # ------------------------------------------------------------------------

    section(
        "OUTPUT SCHEMA CONTRACT"
    )

    record_schema_pass = (
        audit_indicator_record_schema(
            engine
        )
    )

    bar_schema_pass = (
        audit_indicator_bar_schema(
            engine
        )
    )

    result_line(
        "IndicatorBar schema",
        "PASS"
        if bar_schema_pass
        else "FAIL",
    )

    result_line(
        "IndicatorRecord schema",
        "PASS"
        if record_schema_pass
        else "FAIL",
    )

    if not record_schema_pass or not bar_schema_pass:
        return False

    # ------------------------------------------------------------------------
    # Build runtime data
    # ------------------------------------------------------------------------

    bars = build_test_bars(
        engine
    )

    # ------------------------------------------------------------------------
    # Runtime output
    # ------------------------------------------------------------------------

    section(
        "RUNTIME OUTPUT CONTRACT"
    )

    runtime_output_pass = audit_runtime_output(
        engine,
        bars,
    )

    result_line(
        "Indicator records runtime",
        "PASS"
        if runtime_output_pass
        else "FAIL",
    )

    if not runtime_output_pass:
        return False

    # ------------------------------------------------------------------------
    # Indicator families
    # ------------------------------------------------------------------------

    section(
        "INDICATOR FAMILY CONTRACT"
    )

    family_pass = audit_indicator_families(
        engine,
        bars,
    )

    result_line(
        "Trend indicators",
        "PASS" if family_pass else "FAIL",
    )

    result_line(
        "Momentum indicators",
        "PASS" if family_pass else "FAIL",
    )

    result_line(
        "Volatility indicators",
        "PASS" if family_pass else "FAIL",
    )

    result_line(
        "Trend strength indicators",
        "PASS" if family_pass else "FAIL",
    )

    result_line(
        "Price / Volume indicators",
        "PASS" if family_pass else "FAIL",
    )

    result_line(
        "Cloud indicators",
        "PASS" if family_pass else "FAIL",
    )

    if not family_pass:
        return False

    # ------------------------------------------------------------------------
    # Warm-up
    # ------------------------------------------------------------------------

    section(
        "WARM-UP / INSUFFICIENT HISTORY CONTRACT"
    )

    warmup_pass = audit_warmup_contract(
        engine,
        bars,
    )

    result_line(
        "Warm-up semantics",
        "PASS" if warmup_pass else "FAIL",
    )

    if not warmup_pass:
        return False

    # ------------------------------------------------------------------------
    # Numeric
    # ------------------------------------------------------------------------

    section(
        "NUMERIC SAFETY CONTRACT"
    )

    numeric_pass = audit_numeric_contract(
        engine,
        bars,
    )

    result_line(
        "Finite indicator values",
        "PASS" if numeric_pass else "FAIL",
    )

    if not numeric_pass:
        return False

    # ------------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------------

    section(
        "CMC_ID / SYMBOL / TIMESTAMP IDENTITY CONTRACT"
    )

    identity_pass = audit_identity_contract(
        engine
    )

    result_line(
        "CMC_ID identity",
        "PASS" if identity_pass else "FAIL",
    )

    result_line(
        "Symbol identity",
        "PASS" if identity_pass else "FAIL",
    )

    result_line(
        "Timestamp propagation",
        "PASS" if identity_pass else "FAIL",
    )

    result_line(
        "Input order preservation",
        "PASS" if identity_pass else "FAIL",
    )

    if not identity_pass:
        return False

    # ------------------------------------------------------------------------
    # Input safety
    # ------------------------------------------------------------------------

    section(
        "BOUNDARY / INPUT SAFETY"
    )

    input_safety_pass = audit_input_safety(
        engine
    )

    result_line(
        "Invalid OHLC rejection",
        "PASS" if input_safety_pass else "FAIL",
    )

    result_line(
        "Negative volume rejection",
        "PASS" if input_safety_pass else "FAIL",
    )

    result_line(
        "Non-finite rejection",
        "PASS" if input_safety_pass else "FAIL",
    )

    if not input_safety_pass:
        return False

    # ------------------------------------------------------------------------
    # Self test
    # ------------------------------------------------------------------------

    section(
        "ENGINE SELF TEST"
    )

    self_test_pass = audit_self_test(
        engine
    )

    result_line(
        "self_test",
        "PASS" if self_test_pass else "FAIL",
    )

    if not self_test_pass:
        return False

    # ------------------------------------------------------------------------
    # Look-ahead
    # ------------------------------------------------------------------------

    section(
        "LOOK-AHEAD / FUTURE DATA CONTRACT"
    )

    lookahead_pass = audit_lookahead_contract(
        engine,
        bars,
    )

    result_line(
        "Look-ahead audit",
        "PASS" if lookahead_pass else "FAIL",
    )

    result_line(
        "Future-data protection",
        "PASS" if lookahead_pass else "FAIL",
    )

    if not lookahead_pass:
        return False

    # ------------------------------------------------------------------------
    # Determinism
    # ------------------------------------------------------------------------

    section(
        "DETERMINISM CONTRACT"
    )

    determinism_pass = audit_determinism_contract(
        engine,
        bars,
    )

    result_line(
        "Deterministic output",
        "PASS" if determinism_pass else "FAIL",
    )

    if not determinism_pass:
        return False

    # ------------------------------------------------------------------------
    # Decision isolation
    # ------------------------------------------------------------------------

    section(
        "DECISION OUTPUT ISOLATION"
    )

    decision_isolation_pass = audit_decision_isolation(
        source
    )

    result_line(
        "Trading decision output",
        "PASS"
        if decision_isolation_pass
        else "FAIL",
    )

    result_line(
        "BUY / SELL output",
        "NONE"
        if decision_isolation_pass
        else "FAIL",
    )

    if not decision_isolation_pass:
        return False

    # ------------------------------------------------------------------------
    # Architecture
    # ------------------------------------------------------------------------

    section(
        "ARCHITECTURE CONTRACT"
    )

    architecture_pass = audit_architecture_contract(
        source,
        tree,
    )

    result_line(
        "Analysis-layer isolation",
        "PASS"
        if architecture_pass
        else "FAIL",
    )

    result_line(
        "Database independence",
        "PASS"
        if architecture_pass
        else "FAIL",
    )

    result_line(
        "Production writes",
        "NONE"
        if architecture_pass
        else "FAIL",
    )

    if not architecture_pass:
        return False

    # ------------------------------------------------------------------------
    # Required contract summary
    # ------------------------------------------------------------------------

    section(
        "REQUIRED INDICATOR ENGINE CONTRACT"
    )

    contract_items = (
        (
            "Source mutation safety",
            sql_safe and db_safe,
        ),
        (
            "Database independence",
            db_safe,
        ),
        (
            "Required functions",
            required_functions_pass,
        ),
        (
            "Required classes",
            audit_required_classes(engine),
        ),
        (
            "Public API signatures",
            signature_pass,
        ),
        (
            "IndicatorBar schema",
            bar_schema_pass,
        ),
        (
            "IndicatorRecord schema",
            record_schema_pass,
        ),
        (
            "Runtime output",
            runtime_output_pass,
        ),
        (
            "Indicator family contract",
            family_pass,
        ),
        (
            "Warm-up semantics",
            warmup_pass,
        ),
        (
            "Numeric safety",
            numeric_pass,
        ),
        (
            "CMC_ID / symbol identity",
            identity_pass,
        ),
        (
            "Boundary semantics",
            input_safety_pass,
        ),
        (
            "Engine self-test",
            self_test_pass,
        ),
        (
            "Look-ahead protection",
            lookahead_pass,
        ),
        (
            "Deterministic output",
            determinism_pass,
        ),
        (
            "Decision isolation",
            decision_isolation_pass,
        ),
        (
            "Architecture preservation",
            architecture_pass,
        ),
    )

    all_pass = True

    for label, passed in contract_items:

        result_line(
            label,
            "PASS" if passed else "FAIL",
        )

        if not passed:
            all_pass = False

    # ------------------------------------------------------------------------
    # Final verdict
    # ------------------------------------------------------------------------

    print("=" * 100)
    print(
        "STEP 12A VERDICT"
    )
    print("=" * 100)

    if all_pass:

        print(
            "RESULT : INDICATOR ENGINE CONTRACT AUDIT PASS"
        )

        print(
            "STATUS : READY FOR STEP 12B"
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
            "Look-Ahead   : PROTECTED"
        )

        print(
            "Decision     : NONE"
        )

        return True

    print(
        "RESULT : INDICATOR ENGINE CONTRACT AUDIT FAIL"
    )

    print(
        "STATUS : NOT READY FOR STEP 12B"
    )

    return False


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    try:

        success = run_audit()

        if not success:

            raise SystemExit(1)

    except Exception as exc:

        print()
        print(
            "STEP 12A AUDIT ERROR : "
            f"{type(exc).__name__}: {exc}"
        )

        raise