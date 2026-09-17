from __future__ import annotations

import ast
import importlib.util
import inspect
import math
import pathlib
import sys
from dataclasses import is_dataclass
from typing import Any


BASE_DIR = pathlib.Path(__file__).resolve().parent
ENGINE_FILE = BASE_DIR / "market_regime_engine.py"

ENGINE_NAME = "MARKET_REGIME_ENGINE_v0.1"


# ============================================================================
# REQUIRED PUBLIC CONTRACT
# ============================================================================

REQUIRED_FUNCTIONS = (
    "validate_regime_bar",
    "validate_regime_bars",
    "calculate_market_regime_records",
    "validate_regime_record",
    "validate_regime_collection",
    "lookahead_audit",
    "determinism_audit",
    "self_test",
)

REQUIRED_CLASSES = (
    "RegimeBar",
    "MarketRegimeRecord",
)


# ============================================================================
# SOURCE
# ============================================================================

def read_source() -> str:

    if not ENGINE_FILE.exists():
        raise AssertionError(
            f"Market Regime Engine not found: {ENGINE_FILE}"
        )

    raw = ENGINE_FILE.read_bytes()

    if raw.startswith(b"\xef\xbb\xbf"):
        raise AssertionError(
            "Market Regime Engine contains UTF-8 BOM."
        )

    source = raw.decode("utf-8")

    if "\ufeff" in source:
        raise AssertionError(
            "Market Regime Engine contains U+FEFF."
        )

    return source


def parse_ast(source: str) -> ast.AST:

    try:
        return ast.parse(
            source,
            filename=str(ENGINE_FILE),
        )

    except SyntaxError as exc:
        raise AssertionError(
            f"AST parse failed: {exc}"
        ) from exc


def function_inventory(tree: ast.AST) -> list[str]:

    result = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            result.append(node.name)

        elif isinstance(node, ast.ClassDef):

            for child in node.body:

                if isinstance(
                    child,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):
                    result.append(child.name)

    return sorted(set(result))


def class_inventory(tree: ast.AST) -> list[str]:

    return sorted(
        {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        }
    )


# ============================================================================
# SOURCE SAFETY
# ============================================================================

def source_mutation_audit(tree: ast.AST) -> None:

    forbidden_calls = {
        "execute",
        "executemany",
        "executescript",
        "commit",
        "rollback",
        "connect",
        "create_engine",
    }

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Name):

            if node.func.id in forbidden_calls:
                raise AssertionError(
                    "Forbidden database / mutation call: "
                    f"{node.func.id}"
                )

        elif isinstance(node.func, ast.Attribute):

            if node.func.attr in forbidden_calls:
                raise AssertionError(
                    "Forbidden database / mutation call: "
                    f"{node.func.attr}"
                )


def database_independence_audit(tree: ast.AST) -> None:

    forbidden_imports = {
        "sqlite3",
        "sqlalchemy",
        "pymysql",
        "psycopg2",
        "duckdb",
    }

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                root = alias.name.split(".")[0]

                if root in forbidden_imports:
                    raise AssertionError(
                        "Database library detected: "
                        f"{root}"
                    )

        elif isinstance(node, ast.ImportFrom):

            if node.module:

                root = node.module.split(".")[0]

                if root in forbidden_imports:
                    raise AssertionError(
                        "Database library detected: "
                        f"{root}"
                    )


def decision_isolation_audit(
    tree: ast.AST,
    source: str,
) -> None:

    forbidden_fields = {
        "buy",
        "sell",
        "signal",
        "decision",
        "long",
        "short",
        "entry",
        "exit",
    }

    for cls in ast.walk(tree):

        if not isinstance(cls, ast.ClassDef):
            continue

        if cls.name not in {
            "MarketRegimeRecord",
            "RegimeBar",
        }:
            continue

        for node in ast.walk(cls):

            if isinstance(node, ast.AnnAssign):

                target = node.target

                if isinstance(target, ast.Name):

                    if target.id.lower() in forbidden_fields:
                        raise AssertionError(
                            "Decision field detected: "
                            f"{target.id}"
                        )

            elif isinstance(node, ast.Assign):

                for target in node.targets:

                    if isinstance(target, ast.Name):

                        if target.id.lower() in forbidden_fields:
                            raise AssertionError(
                                "Decision field detected: "
                                f"{target.id}"
                            )

    source_lower = source.lower()

    for forbidden in (
        "buy_signal",
        "sell_signal",
        "trading_decision",
    ):

        if forbidden in source_lower:
            raise AssertionError(
                "Trading decision token detected: "
                f"{forbidden}"
            )


# ============================================================================
# IMPORT ENGINE
# ============================================================================

def import_engine():

    if str(BASE_DIR) not in sys.path:
        sys.path.insert(
            0,
            str(BASE_DIR),
        )

    module_name = (
        "_arunda_market_regime_engine_behavioral_target"
    )

    spec = importlib.util.spec_from_file_location(
        module_name,
        ENGINE_FILE,
    )

    if spec is None:
        raise AssertionError(
            "Unable to create module specification."
        )

    if spec.loader is None:
        raise AssertionError(
            "Unable to create module loader."
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[module_name] = module

    try:

        spec.loader.exec_module(module)

    except Exception:

        sys.modules.pop(
            module_name,
            None,
        )

        raise

    return module


# ============================================================================
# PUBLIC CONTRACT
# ============================================================================

def required_functions_audit(engine: Any) -> None:

    for name in REQUIRED_FUNCTIONS:

        value = getattr(
            engine,
            name,
            None,
        )

        if value is None:
            raise AssertionError(
                f"Missing required function: {name}"
            )

        if not callable(value):
            raise AssertionError(
                f"Required function is not callable: {name}"
            )


def required_classes_audit(engine: Any) -> None:

    for name in REQUIRED_CLASSES:

        value = getattr(
            engine,
            name,
            None,
        )

        if value is None:
            raise AssertionError(
                f"Missing required class: {name}"
            )

        if not isinstance(value, type):
            raise AssertionError(
                f"Required class invalid: {name}"
            )


def signature_audit(engine: Any) -> None:

    expected = {
        "validate_regime_bar": 1,
        "validate_regime_bars": 1,
        "calculate_market_regime_records": 1,
        "validate_regime_record": 1,
        "validate_regime_collection": 1,
        "lookahead_audit": 1,
        "determinism_audit": 1,
        "self_test": 0,
    }

    for name, expected_min in expected.items():

        fn = getattr(
            engine,
            name,
        )

        signature = inspect.signature(fn)

        required_positional = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            and parameter.default
            is inspect.Parameter.empty
        ]

        if len(required_positional) < expected_min:
            raise AssertionError(
                f"Invalid public signature: {name}"
            )


# ============================================================================
# DATACLASS SCHEMA
# ============================================================================

def dataclass_schema_audit(engine: Any) -> None:

    for name in REQUIRED_CLASSES:

        cls = getattr(
            engine,
            name,
        )

        if not is_dataclass(cls):
            raise AssertionError(
                f"{name} must be a dataclass."
            )

    regime_bar = engine.RegimeBar
    regime_record = engine.MarketRegimeRecord

    bar_fields = set(
        regime_bar.__dataclass_fields__
    )

    record_fields = set(
        regime_record.__dataclass_fields__
    )

    required_bar_fields = {
        "timestamp",
        "high",
        "low",
        "close",
    }

    required_record_fields = {
        "index",
        "timestamp",
    }

    missing_bar = (
        required_bar_fields
        - bar_fields
    )

    missing_record = (
        required_record_fields
        - record_fields
    )

    if missing_bar:
        raise AssertionError(
            "RegimeBar missing fields: "
            f"{sorted(missing_bar)}"
        )

    if missing_record:
        raise AssertionError(
            "MarketRegimeRecord missing fields: "
            f"{sorted(missing_record)}"
        )


# ============================================================================
# TEST BAR FACTORIES
# ============================================================================

def make_bar(
    engine: Any,
    *,
    timestamp: Any,
    high: float,
    low: float,
    close: float,
    open_value: float | None = None,
    volume: float | None = None,
    cmc_id: int | None = 1,
    symbol: str | None = "TEST",
):

    kwargs = {
        "timestamp": timestamp,
        "high": high,
        "low": low,
        "close": close,
    }

    fields = engine.RegimeBar.__dataclass_fields__

    if "open" in fields:

        kwargs["open"] = (
            close
            if open_value is None
            else open_value
        )

    if "volume" in fields:

        kwargs["volume"] = (
            1000.0
            if volume is None
            else volume
        )

    if "cmc_id" in fields:
        kwargs["cmc_id"] = cmc_id

    if "symbol" in fields:
        kwargs["symbol"] = symbol

    return engine.RegimeBar(**kwargs)


def make_series(
    engine: Any,
    length: int = 100,
    *,
    start: float = 100.0,
    slope: float = 0.5,
    volume: float = 1000.0,
    cmc_id: int = 1,
    symbol: str = "TEST",
):

    bars = []

    for i in range(length):

        close = start + (
            slope * i
        )

        high = close + 1.0
        low = close - 1.0
        open_value = close - 0.25

        bars.append(
            make_bar(
                engine,
                timestamp=i,
                high=high,
                low=low,
                close=close,
                open_value=open_value,
                volume=volume,
                cmc_id=cmc_id,
                symbol=symbol,
            )
        )

    return bars


# ============================================================================
# BASIC RUNTIME AUDIT
# ============================================================================

def runtime_output_audit(engine: Any) -> None:

    result = engine.self_test()

    if result is not True:
        raise AssertionError(
            "self_test() did not return True."
        )

    bars = make_series(
        engine,
        length=60,
    )

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    if not isinstance(records, list):
        raise AssertionError(
            "Runtime output must be a list."
        )

    if len(records) != len(bars):
        raise AssertionError(
            "Runtime output length mismatch."
        )

    for i, record in enumerate(records):

        if record.index != i:
            raise AssertionError(
                "Runtime index propagation failed."
            )

        if record.timestamp != bars[i].timestamp:
            raise AssertionError(
                "Timestamp propagation failed."
            )

        if hasattr(record, "cmc_id"):

            if record.cmc_id != bars[i].cmc_id:
                raise AssertionError(
                    "CMC_ID propagation failed."
                )

        if hasattr(record, "symbol"):

            if record.symbol != bars[i].symbol:
                raise AssertionError(
                    "Symbol propagation failed."
                )


# ============================================================================
# IDENTITY
# ============================================================================

def identity_audit(engine: Any) -> None:

    bars = []

    for i in range(30):

        bars.append(
            make_bar(
                engine,
                timestamp=f"T{i}",
                high=101.0 + i,
                low=99.0 + i,
                close=100.0 + i,
                open_value=100.0 + i,
                volume=1000.0,
                cmc_id=1000 + i,
                symbol=f"SYM{i}",
            )
        )

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    for i, record in enumerate(records):

        assert record.index == i

        assert (
            record.timestamp
            == bars[i].timestamp
        )

        if hasattr(record, "cmc_id"):

            assert (
                record.cmc_id
                == bars[i].cmc_id
            )

        if hasattr(record, "symbol"):

            assert (
                record.symbol
                == bars[i].symbol
            )


# ============================================================================
# INPUT ORDER
# ============================================================================

def order_preservation_audit(engine: Any) -> None:

    bars = []

    for i in range(30):

        bars.append(
            make_bar(
                engine,
                timestamp=100 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.0 + i,
                open_value=100.0 + i,
                volume=1000.0,
                cmc_id=500 + i,
                symbol=f"S{i}",
            )
        )

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    actual = [
        record.index
        for record in records
    ]

    expected = list(
        range(len(bars))
    )

    if actual != expected:
        raise AssertionError(
            "Input order was not preserved."
        )


# ============================================================================
# WARM-UP
# ============================================================================

def warmup_audit(engine: Any) -> None:

    bars = make_series(
        engine,
        length=10,
    )

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    if len(records) != len(bars):
        raise AssertionError(
            "Warm-up output length mismatch."
        )

    forbidden = {
        "BUY",
        "SELL",
        "LONG",
        "SHORT",
    }

    for record in records:

        for field in (
            "regime",
            "market_regime",
            "regime_state",
        ):

            if not hasattr(record, field):
                continue

            value = getattr(
                record,
                field,
            )

            if isinstance(value, str):

                if value.upper() in forbidden:
                    raise AssertionError(
                        "Decision output detected during warm-up."
                    )


# ============================================================================
# NUMERIC SAFETY
# ============================================================================

def numeric_safety_audit(engine: Any) -> None:

    bars = make_series(
        engine,
        length=100,
    )

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    for record in records:

        for field in record.__dataclass_fields__:

            value = getattr(
                record,
                field,
            )

            if isinstance(value, bool):
                continue

            if isinstance(value, (int, float)):

                if not math.isfinite(
                    float(value)
                ):
                    raise AssertionError(
                        "Non-finite runtime output: "
                        f"{field}"
                    )


# ============================================================================
# INPUT SAFETY
# ============================================================================

def input_safety_audit(engine: Any) -> None:

    invalid_ohlc = [
        make_bar(
            engine,
            timestamp=0,
            high=10.0,
            low=20.0,
            close=15.0,
        )
    ]

    try:

        engine.validate_regime_bars(
            invalid_ohlc
        )

    except (
        ValueError,
        TypeError,
    ):
        pass

    else:
        raise AssertionError(
            "Invalid OHLC was not rejected."
        )

    invalid_volume = [
        make_bar(
            engine,
            timestamp=0,
            high=10.0,
            low=5.0,
            close=8.0,
            volume=-1.0,
        )
    ]

    try:

        engine.validate_regime_bars(
            invalid_volume
        )

    except (
        ValueError,
        TypeError,
    ):
        pass

    else:
        raise AssertionError(
            "Negative volume was not rejected."
        )


# ============================================================================
# LOOK-AHEAD STRUCTURAL AUDIT
# ============================================================================

def lookahead_contract_audit(engine: Any) -> None:

    signature = inspect.signature(
        engine.lookahead_audit
    )

    if len(signature.parameters) < 1:
        raise AssertionError(
            "lookahead_audit must accept input data."
        )

    source = inspect.getsource(
        engine.lookahead_audit
    )

    source_lower = source.lower()

    forbidden_future_patterns = (
        "[-i]",
        "[i+1:]",
        "[i + 1:]",
        "[i+1]",
        "[i + 1]",
        "look_ahead_data",
        "next_bar",
        "future_bar",
    )

    for pattern in forbidden_future_patterns:

        if pattern in source_lower:
            raise AssertionError(
                "Potential future-data access detected: "
                f"{pattern}"
            )


# ============================================================================
# DETERMINISM
# ============================================================================

def determinism_contract_audit(engine: Any) -> None:

    bars = make_series(
        engine,
        length=100,
    )

    first = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    second = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    if first != second:
        raise AssertionError(
            "Regime output is not deterministic."
        )

    audit = engine.determinism_audit(
        bars
    )

    if audit is not True:
        raise AssertionError(
            "determinism_audit() failed."
        )


# ============================================================================
# BEHAVIORAL HELPERS
# ============================================================================

def public_record_values(
    record: Any,
) -> dict[str, Any]:

    return {
        field: getattr(record, field)
        for field in record.__dataclass_fields__
    }


def numeric_fields(
    record: Any,
) -> dict[str, float]:

    result = {}

    for field in record.__dataclass_fields__:

        value = getattr(
            record,
            field,
        )

        if isinstance(value, bool):
            continue

        if isinstance(value, (int, float)):

            result[field] = float(value)

    return result


def non_identity_fields(
    record: Any,
) -> dict[str, Any]:

    identity = {
        "index",
        "timestamp",
        "cmc_id",
        "symbol",
    }

    return {
        field: getattr(record, field)
        for field in record.__dataclass_fields__
        if field not in identity
    }


# ============================================================================
# BEHAVIORAL AUDIT 1
# OUTPUT LENGTH
# ============================================================================

def behavioral_length_audit(
    engine: Any,
) -> None:

    # IMPORTANT:
    # The current Engine contract rejects an empty collection.
    # Therefore zero-length input is NOT tested here.
    #
    # Empty-input contract is tested separately below and expects
    # explicit ValueError / TypeError rejection.

    for length in (
        1,
        2,
        5,
        10,
        30,
        60,
        100,
    ):

        bars = make_series(
            engine,
            length=length,
        )

        records = (
            engine.calculate_market_regime_records(
                bars
            )
        )

        if not isinstance(records, list):

            raise AssertionError(
                f"Output is not list for length={length}"
            )

        if len(records) != length:

            raise AssertionError(
                "Output length mismatch: "
                f"input={length}, output={len(records)}"
            )


# ============================================================================
# BEHAVIORAL AUDIT 2
# SINGLE BAR
# ============================================================================

def behavioral_single_bar_audit(
    engine: Any,
) -> None:

    bars = make_series(
        engine,
        length=1,
    )

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    if len(records) != 1:

        raise AssertionError(
            "Single-bar input must produce one record."
        )

    record = records[0]

    if record.index != 0:

        raise AssertionError(
            "Single-bar index must be zero."
        )

    if record.timestamp != bars[0].timestamp:

        raise AssertionError(
            "Single-bar timestamp mismatch."
        )


# ============================================================================
# BEHAVIORAL AUDIT 3
# PREFIX CAUSALITY
#
# Adding future bars must not modify already-existing historical records.
# ============================================================================

def behavioral_prefix_causality_audit(
    engine: Any,
) -> None:

    base = make_series(
        engine,
        length=80,
        slope=0.4,
    )

    extended = list(base)

    for i in range(80, 120):

        close = 100.0 + (
            0.4 * i
        )

        extended.append(
            make_bar(
                engine,
                timestamp=i,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                open_value=close - 0.25,
                volume=1000.0,
                cmc_id=1,
                symbol="TEST",
            )
        )

    base_records = (
        engine.calculate_market_regime_records(
            base
        )
    )

    extended_records = (
        engine.calculate_market_regime_records(
            extended
        )
    )

    if len(extended_records) != 120:

        raise AssertionError(
            "Extended behavioral output length mismatch."
        )

    for i in range(80):

        left = public_record_values(
            base_records[i]
        )

        right = public_record_values(
            extended_records[i]
        )

        if left != right:

            raise AssertionError(
                "Prefix causality violated at index "
                f"{i}."
            )


# ============================================================================
# BEHAVIORAL AUDIT 4
# INPUT VALUE SENSITIVITY
# ============================================================================

def behavioral_input_sensitivity_audit(
    engine: Any,
) -> None:

    normal = make_series(
        engine,
        length=100,
        slope=0.25,
    )

    altered = list(normal)

    altered[70] = make_bar(
        engine,
        timestamp=70,
        high=180.0,
        low=160.0,
        close=170.0,
        open_value=165.0,
        volume=5000.0,
        cmc_id=1,
        symbol="TEST",
    )

    normal_records = (
        engine.calculate_market_regime_records(
            normal
        )
    )

    altered_records = (
        engine.calculate_market_regime_records(
            altered
        )
    )

    changed = False

    for i in range(70, 100):

        left = non_identity_fields(
            normal_records[i]
        )

        right = non_identity_fields(
            altered_records[i]
        )

        if left != right:

            changed = True
            break

    if not changed:

        raise AssertionError(
            "Meaningful input perturbation produced "
            "no downstream behavioral change."
        )


# ============================================================================
# BEHAVIORAL AUDIT 5
# IDENTITY MUTATION MUST NOT ALTER DESCRIPTIVE CALCULATIONS
# ============================================================================

def behavioral_identity_isolation_audit(
    engine: Any,
) -> None:

    first = make_series(
        engine,
        length=80,
        slope=0.3,
        cmc_id=1,
        symbol="AAA",
    )

    second = []

    for bar in first:

        kwargs = {
            "timestamp": bar.timestamp,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "open_value": getattr(
                bar,
                "open",
                bar.close,
            ),
            "volume": getattr(
                bar,
                "volume",
                1000.0,
            ),
            "cmc_id": 999999,
            "symbol": "BBB",
        }

        second.append(
            make_bar(
                engine,
                **kwargs,
            )
        )

    records_a = (
        engine.calculate_market_regime_records(
            first
        )
    )

    records_b = (
        engine.calculate_market_regime_records(
            second
        )
    )

    for i in range(len(first)):

        values_a = non_identity_fields(
            records_a[i]
        )

        values_b = non_identity_fields(
            records_b[i]
        )

        if values_a != values_b:

            raise AssertionError(
                "Identity metadata affected descriptive "
                f"regime calculation at index {i}."
            )


# ============================================================================
# BEHAVIORAL AUDIT 6
# CONSTANT SERIES STABILITY
# ============================================================================

def behavioral_constant_series_audit(
    engine: Any,
) -> None:

    bars = []

    for i in range(100):

        bars.append(
            make_bar(
                engine,
                timestamp=i,
                high=101.0,
                low=99.0,
                close=100.0,
                open_value=100.0,
                volume=1000.0,
                cmc_id=1,
                symbol="FLAT",
            )
        )

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    if len(records) != 100:

        raise AssertionError(
            "Constant-series output length mismatch."
        )

    for record in records:

        for field, value in numeric_fields(
            record
        ).items():

            if not math.isfinite(value):

                raise AssertionError(
                    "Constant-series produced "
                    f"non-finite value: {field}"
                )


# ============================================================================
# BEHAVIORAL AUDIT 7
# MONOTONIC UP / DOWN SERIES
# ============================================================================

def behavioral_directional_series_audit(
    engine: Any,
) -> None:

    up = make_series(
        engine,
        length=120,
        start=100.0,
        slope=0.5,
    )

    down = make_series(
        engine,
        length=120,
        start=160.0,
        slope=-0.5,
    )

    up_records = (
        engine.calculate_market_regime_records(
            up
        )
    )

    down_records = (
        engine.calculate_market_regime_records(
            down
        )
    )

    if len(up_records) != len(up):

        raise AssertionError(
            "Up-series output length mismatch."
        )

    if len(down_records) != len(down):

        raise AssertionError(
            "Down-series output length mismatch."
        )

    for records in (
        up_records,
        down_records,
    ):

        for record in records:

            for field, value in numeric_fields(
                record
            ).items():

                if not math.isfinite(value):

                    raise AssertionError(
                        "Directional series produced "
                        f"non-finite field: {field}"
                    )


# ============================================================================
# BEHAVIORAL AUDIT 8
# SHOCK RESPONSE
# ============================================================================

def behavioral_shock_audit(
    engine: Any,
) -> None:

    bars = make_series(
        engine,
        length=120,
        slope=0.1,
    )

    shocked = list(bars)

    shocked[90] = make_bar(
        engine,
        timestamp=90,
        high=250.0,
        low=50.0,
        close=200.0,
        open_value=100.0,
        volume=10000.0,
        cmc_id=1,
        symbol="TEST",
    )

    normal_records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    shocked_records = (
        engine.calculate_market_regime_records(
            shocked
        )
    )

    changed = False

    for i in range(90, 120):

        if (
            non_identity_fields(
                normal_records[i]
            )
            !=
            non_identity_fields(
                shocked_records[i]
            )
        ):

            changed = True
            break

    if not changed:

        raise AssertionError(
            "Large OHLCV shock produced no "
            "descriptive behavioral response."
        )


# ============================================================================
# BEHAVIORAL AUDIT 9
# DUPLICATE INPUT DETERMINISM
# ============================================================================

def behavioral_repeatability_audit(
    engine: Any,
) -> None:

    bars = make_series(
        engine,
        length=120,
        slope=0.2,
    )

    outputs = []

    for _ in range(3):

        outputs.append(
            engine.calculate_market_regime_records(
                bars
            )
        )

    if outputs[0] != outputs[1]:

        raise AssertionError(
            "Repeated calculation #1 differs."
        )

    if outputs[1] != outputs[2]:

        raise AssertionError(
            "Repeated calculation #2 differs."
        )


# ============================================================================
# BEHAVIORAL AUDIT 10
# PUBLIC VALIDATORS
#
# IMPORTANT:
# Validators are tested according to behavior, not a hard-coded return
# convention.
#
# Accepted successful contracts:
#   - True
#   - None
#   - validated object / collection
#
# Rejected:
#   - False
#   - exception for valid input
#   - malformed collection result
# ============================================================================

def behavioral_validator_audit(
    engine: Any,
) -> None:

    bars = make_series(
        engine,
        length=60,
    )

    # ------------------------------------------------------------------------
    # validate_regime_bars()
    # ------------------------------------------------------------------------

    try:

        bar_validation_result = (
            engine.validate_regime_bars(
                bars
            )
        )

    except Exception as exc:

        raise AssertionError(
            "validate_regime_bars() raised an exception "
            "for valid input: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    if isinstance(
        bar_validation_result,
        bool,
    ):

        if bar_validation_result is not True:

            raise AssertionError(
                "validate_regime_bars() explicitly "
                "rejected valid input."
            )

    elif bar_validation_result is None:

        pass

    else:

        try:

            if len(
                bar_validation_result
            ) != len(bars):

                raise AssertionError(
                    "validate_regime_bars() returned a "
                    "collection with invalid length."
                )

        except TypeError as exc:

            raise AssertionError(
                "validate_regime_bars() returned an "
                "unexpected non-boolean, non-collection result."
            ) from exc

    # ------------------------------------------------------------------------
    # calculate_market_regime_records()
    # ------------------------------------------------------------------------

    try:

        records = (
            engine.calculate_market_regime_records(
                bars
            )
        )

    except Exception as exc:

        raise AssertionError(
            "calculate_market_regime_records() raised "
            "an exception for valid input: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    if not isinstance(
        records,
        list,
    ):

        raise AssertionError(
            "calculate_market_regime_records() "
            "must return a list."
        )

    if len(records) != len(bars):

        raise AssertionError(
            "calculate_market_regime_records() "
            "returned an invalid number of records."
        )

    # ------------------------------------------------------------------------
    # validate_regime_collection()
    # ------------------------------------------------------------------------

    try:

        record_validation_result = (
            engine.validate_regime_collection(
                records
            )
        )

    except Exception as exc:

        raise AssertionError(
            "validate_regime_collection() raised an "
            "exception for valid output: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    if isinstance(
        record_validation_result,
        bool,
    ):

        if record_validation_result is not True:

            raise AssertionError(
                "validate_regime_collection() explicitly "
                "rejected valid output."
            )

    elif record_validation_result is None:

        pass

    else:

        try:

            if len(
                record_validation_result
            ) != len(records):

                raise AssertionError(
                    "validate_regime_collection() returned "
                    "a collection with invalid length."
                )

        except TypeError as exc:

            raise AssertionError(
                "validate_regime_collection() returned an "
                "unexpected non-boolean, non-collection result."
            ) from exc

    # ------------------------------------------------------------------------
    # validate_regime_bar()
    # ------------------------------------------------------------------------

    for bar in bars:

        try:

            result = (
                engine.validate_regime_bar(
                    bar
                )
            )

        except Exception as exc:

            raise AssertionError(
                "validate_regime_bar() raised an exception "
                "for a valid bar: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        if result is False:

            raise AssertionError(
                "validate_regime_bar() explicitly "
                "rejected a valid bar."
            )

    # ------------------------------------------------------------------------
    # validate_regime_record()
    # ------------------------------------------------------------------------

    for record in records:

        try:

            result = (
                engine.validate_regime_record(
                    record
                )
            )

        except Exception as exc:

            raise AssertionError(
                "validate_regime_record() raised an exception "
                "for a valid record: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        if result is False:

            raise AssertionError(
                "validate_regime_record() explicitly "
                "rejected a valid record."
            )


# ============================================================================
# BEHAVIORAL AUDIT 11
# EMPTY INPUT
#
# Current Engine contract explicitly rejects an empty RegimeBar collection.
# Therefore this audit verifies rejection rather than requiring [] output.
# ============================================================================

def behavioral_empty_input_audit(
    engine: Any,
) -> None:

    try:

        engine.calculate_market_regime_records(
            []
        )

    except (
        ValueError,
        TypeError,
    ):

        return

    except Exception as exc:

        raise AssertionError(
            "Empty input was rejected with an unexpected "
            f"exception type: {type(exc).__name__}: {exc}"
        ) from exc

    else:

        raise AssertionError(
            "Current contract requires empty RegimeBar "
            "collection to be rejected."
        )


# ============================================================================
# BEHAVIORAL AUDIT 12
# NO DECISION VOCABULARY
# ============================================================================

def behavioral_decision_isolation_audit(
    engine: Any,
) -> None:

    bars = make_series(
        engine,
        length=120,
    )

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    forbidden = {
        "BUY",
        "SELL",
        "LONG",
        "SHORT",
        "ENTRY",
        "EXIT",
    }

    for record in records:

        values = public_record_values(
            record
        )

        for field, value in values.items():

            if isinstance(value, str):

                if value.upper() in forbidden:

                    raise AssertionError(
                        "Decision vocabulary detected: "
                        f"{field}={value}"
                    )


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER — DEV-06 — STEP 14B"
    )
    print(
        "MARKET REGIME ENGINE BEHAVIORAL AUDIT"
    )
    print("=" * 100)

    print()
    print("-" * 100)
    print("MODE")
    print("-" * 100)

    print(
        "Database mutation                                  : NONE"
    )

    print(
        "Production write                                   : NONE"
    )

    print(
        "Audit mode                                         : READ ONLY"
    )

    print(
        "Database usage                                     : NOT REQUIRED"
    )

    try:

        # ====================================================================
        # SOURCE
        # ====================================================================

        source = read_source()
        tree = parse_ast(source)

        print()
        print("-" * 100)
        print("FILE VALIDATION")
        print("-" * 100)

        print(
            "Market Regime Engine                               : PASS"
        )

        print(
            "AST Parse                                           : PASS"
        )

        # ====================================================================
        # SOURCE SAFETY
        # ====================================================================

        source_mutation_audit(tree)
        database_independence_audit(tree)
        decision_isolation_audit(
            tree,
            source,
        )

        print()
        print("-" * 100)
        print("SOURCE SAFETY")
        print("-" * 100)

        print(
            "Source mutation statements                         : PASS"
        )

        print(
            "Database independence                              : PASS"
        )

        print(
            "Decision isolation                                 : PASS"
        )

        # ====================================================================
        # INVENTORY
        # ====================================================================

        functions = function_inventory(tree)
        classes = class_inventory(tree)

        missing_functions = (
            set(REQUIRED_FUNCTIONS)
            - set(functions)
        )

        missing_classes = (
            set(REQUIRED_CLASSES)
            - set(classes)
        )

        if missing_functions:

            raise AssertionError(
                "Missing required functions: "
                f"{sorted(missing_functions)}"
            )

        if missing_classes:

            raise AssertionError(
                "Missing required classes: "
                f"{sorted(missing_classes)}"
            )

        # ====================================================================
        # IMPORT
        # ====================================================================

        engine = import_engine()

        required_functions_audit(engine)
        required_classes_audit(engine)
        signature_audit(engine)
        dataclass_schema_audit(engine)

        print()
        print("-" * 100)
        print("STATIC CONTRACT")
        print("-" * 100)

        print(
            "Required functions                                 : PASS"
        )

        print(
            "Required classes                                   : PASS"
        )

        print(
            "Public API signatures                              : PASS"
        )

        print(
            "Dataclass schema                                   : PASS"
        )

        # ====================================================================
        # BASE RUNTIME
        # ====================================================================

        runtime_output_audit(engine)
        identity_audit(engine)
        order_preservation_audit(engine)
        warmup_audit(engine)
        numeric_safety_audit(engine)
        input_safety_audit(engine)
        lookahead_contract_audit(engine)
        determinism_contract_audit(engine)

        print()
        print("-" * 100)
        print("BASE RUNTIME CONTRACT")
        print("-" * 100)

        print(
            "Runtime output                                      : PASS"
        )

        print(
            "Identity propagation                               : PASS"
        )

        print(
            "Input order preservation                           : PASS"
        )

        print(
            "Warm-up semantics                                  : PASS"
        )

        print(
            "Numeric safety                                     : PASS"
        )

        print(
            "Input validation                                   : PASS"
        )

        print(
            "Look-ahead structural safety                       : PASS"
        )

        print(
            "Deterministic output                               : PASS"
        )

        # ====================================================================
        # BEHAVIORAL TESTS
        # ====================================================================

        behavioral_empty_input_audit(engine)

        print(
            "Empty input rejection                              : PASS"
        )

        behavioral_length_audit(engine)

        print(
            "Variable-length behavior                           : PASS"
        )

        behavioral_single_bar_audit(engine)

        print(
            "Single-bar behavior                                : PASS"
        )

        behavioral_prefix_causality_audit(engine)

        print(
            "Prefix causality                                   : PASS"
        )

        behavioral_input_sensitivity_audit(engine)

        print(
            "Input sensitivity                                  : PASS"
        )

        behavioral_identity_isolation_audit(engine)

        print(
            "Identity isolation                                 : PASS"
        )

        behavioral_constant_series_audit(engine)

        print(
            "Constant-series stability                          : PASS"
        )

        behavioral_directional_series_audit(engine)

        print(
            "Directional-series stability                      : PASS"
        )

        behavioral_shock_audit(engine)

        print(
            "Shock response                                     : PASS"
        )

        behavioral_repeatability_audit(engine)

        print(
            "Repeated-output stability                          : PASS"
        )

        behavioral_validator_audit(engine)

        print(
            "Public validator behavior                          : PASS"
        )

        behavioral_decision_isolation_audit(engine)

        print(
            "Decision-output isolation                          : PASS"
        )

        # ====================================================================
        # ENGINE SELF TEST
        # ====================================================================

        if engine.self_test() is not True:

            raise AssertionError(
                "Market Regime Engine self_test failed."
            )

        print()
        print("-" * 100)
        print("ENGINE SELF TEST")
        print("-" * 100)

        print(
            "self_test                                          : PASS"
        )

        # ====================================================================
        # FINAL CONTRACT
        # ====================================================================

        print()
        print("-" * 100)
        print(
            "STEP 14B BEHAVIORAL CONTRACT"
        )
        print("-" * 100)

        summary = (
            "Empty input rejection",
            "Variable-length behavior",
            "Single-bar behavior",
            "Prefix causality",
            "Input sensitivity",
            "Identity isolation",
            "Constant-series stability",
            "Directional-series stability",
            "Shock response",
            "Repeated-output determinism",
            "Public validator behavior",
            "Decision-output isolation",
        )

        for item in summary:

            print(
                f"{item:<52} : PASS"
            )

        # ====================================================================
        # VERDICT
        # ====================================================================

        print()
        print("=" * 100)
        print(
            "STEP 14B VERDICT"
        )
        print("=" * 100)

        print(
            "RESULT : MARKET REGIME ENGINE BEHAVIORAL AUDIT PASS"
        )

        print(
            "STATUS : READY FOR NEXT CONTRACT STEP"
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

    except Exception as exc:

        print()
        print("=" * 100)
        print(
            "STEP 14B VERDICT"
        )
        print("=" * 100)

        print(
            "RESULT : MARKET REGIME ENGINE BEHAVIORAL AUDIT FAIL"
        )

        print(
            "ERROR  : "
            f"{type(exc).__name__}: {exc}"
        )

        raise


if __name__ == "__main__":
    main()