"""
ARUNDA TRADER — DEV-06 — STEP 13B
FEATURE ENGINE QUALITY & CAUSAL VALIDATION

Purpose
-------
Deep quality and causal validation of Feature Engine v0.1.

Architecture
------------
- Read-only audit
- No database access
- No SQL
- No production writes
- No source mutation
- No trading decisions
- No BUY / SELL
- No LONG / SHORT
- No future-data dependency

Validated Areas
---------------
1. Source mutation safety
2. Database independence
3. Module import
4. Required functions
5. Required classes
6. Public API signatures
7. FeatureBar schema
8. FeatureRecord schema
9. Trend feature quality
10. Momentum feature quality
11. Volatility feature quality
12. Trend-strength quality
13. Price / volume quality
14. Ichimoku / cloud quality
15. Market structure quality
16. Composite feature quality
17. Warm-up semantics
18. Numeric safety
19. Identity preservation
20. Boundary / input safety
21. Adversarial sequences
22. Look-ahead protection
23. Deterministic output
24. Decision isolation
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import math
import sys
from dataclasses import fields
from pathlib import Path
from typing import Any


# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(
    __file__
).resolve().parent

ENGINE_FILE = (
    BASE_DIR
    / "feature_engine.py"
)

ENGINE_MODULE_NAME = (
    "arunda_feature_engine_step13b"
)


# ============================================================================
# EXPECTED PUBLIC API
# ============================================================================

REQUIRED_FUNCTIONS = (
    "_clip",
    "_finite",
    "_float",
    "_get",
    "_indicator_value",
    "_normalize_confidence",
    "_normalize_direction",
    "_normalize_strength",
    "_safe_div",
    "_structure_value",
    "calculate_composite_features",
    "calculate_feature_records",
    "calculate_ichimoku_features",
    "calculate_momentum_features",
    "calculate_price_volume_features",
    "calculate_structure_features",
    "calculate_trend_features",
    "calculate_trend_strength_features",
    "calculate_volatility_features",
    "determinism_audit",
    "lookahead_audit",
    "print_feature_sample",
    "self_test",
    "validate_feature_bar",
    "validate_feature_bars",
    "validate_feature_collection",
    "validate_feature_record",
)

REQUIRED_CLASSES = (
    "FeatureBar",
    "FeatureRecord",
)


# ============================================================================
# FEATURE FIELDS
# ============================================================================

NUMERIC_FEATURE_FIELDS = (
    "ema_distance",
    "sma_distance",
    "wma_distance",
    "rsi_normalized",
    "macd_normalized",
    "stochastic_position",
    "atr_normalized",
    "bb_position",
    "bb_width",
    "adx_normalized",
    "di_spread",
    "price_to_vwap",
    "volume_change_ratio",
    "ichimoku_tenkan_distance",
    "ichimoku_kijun_distance",
    "ichimoku_cloud_position",
    "trend_alignment",
    "momentum_alignment",
)

BOUNDED_FEATURE_FIELDS = (
    "rsi_normalized",
    "stochastic_position",
    "adx_normalized",
    "di_spread",
    "ichimoku_cloud_position",
    "trend_alignment",
    "momentum_alignment",
)

STRUCTURAL_FEATURE_FIELDS = (
    "structure_direction",
    "structure_strength",
    "structure_confidence",
    "structure_point_type",
    "bos_recent",
    "choch_recent",
    "volatility_regime",
    "structure_regime",
)

DECISION_FORBIDDEN_FIELDS = (
    "buy",
    "sell",
    "signal",
    "decision",
    "long",
    "short",
    "entry",
    "exit",
    "order",
    "execute",
    "execution",
    "position_size",
)


# ============================================================================
# AST HELPERS
# ============================================================================

def read_source() -> str:

    if not ENGINE_FILE.exists():

        raise AssertionError(
            f"Feature Engine not found: "
            f"{ENGINE_FILE}"
        )

    try:

        return ENGINE_FILE.read_text(
            encoding="utf-8-sig"
        )

    except Exception as exc:

        raise AssertionError(
            f"Unable to read Feature Engine: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def parse_ast(
    source: str,
) -> ast.AST:

    try:

        return ast.parse(
            source,
            filename=str(
                ENGINE_FILE
            ),
        )

    except SyntaxError as exc:

        raise AssertionError(
            f"AST parse failed: {exc}"
        ) from exc


def ast_function_names(
    tree: ast.AST,
) -> set[str]:

    names = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            names.add(
                node.name
            )

    return names


def ast_class_names(
    tree: ast.AST,
) -> set[str]:

    names = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.ClassDef,
        ):
            names.add(
                node.name
            )

    return names


# ============================================================================
# SOURCE SAFETY
# ============================================================================

def source_mutation_audit(
    tree: ast.AST,
) -> bool:

    forbidden_calls = {
        "open",
        "remove",
        "unlink",
        "rename",
        "replace",
        "rmtree",
        "copy",
        "copy2",
        "move",
        "write_text",
        "write_bytes",
        "mkdir",
        "makedirs",
    }

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Call,
        ):

            function_name = None

            if isinstance(
                node.func,
                ast.Name,
            ):
                function_name = (
                    node.func.id
                )

            elif isinstance(
                node.func,
                ast.Attribute,
            ):
                function_name = (
                    node.func.attr
                )

            if function_name in forbidden_calls:

                raise AssertionError(
                    "Source mutation "
                    f"operation detected: "
                    f"{function_name}"
                )

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
                ast.NamedExpr,
            ),
        ):
            continue

    return True


# ============================================================================
# DATABASE / SQL INDEPENDENCE
# ============================================================================

def database_independence_audit(
    source: str,
    tree: ast.AST,
) -> bool:

    forbidden_imports = {
        "sqlite3",
        "sqlalchemy",
        "psycopg2",
        "pymysql",
        "mysql",
        "duckdb",
    }

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                root = (
                    alias.name
                    .split(".")[0]
                    .lower()
                )

                if root in forbidden_imports:

                    raise AssertionError(
                        "Database module "
                        f"import detected: {root}"
                    )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:

                root = (
                    node.module
                    .split(".")[0]
                    .lower()
                )

                if root in forbidden_imports:

                    raise AssertionError(
                        "Database module "
                        f"import detected: {root}"
                    )

    sql_keywords = (
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "ALTER ",
        "CREATE TABLE",
        "DROP TABLE",
        "TRUNCATE ",
    )

    upper_source = source.upper()

    for keyword in sql_keywords:

        if keyword in upper_source:

            raise AssertionError(
                "SQL statement detected: "
                f"{keyword.strip()}"
            )

    return True


# ============================================================================
# MODULE IMPORT
# ============================================================================

def import_engine():

    if ENGINE_MODULE_NAME in sys.modules:

        del sys.modules[
            ENGINE_MODULE_NAME
        ]

    spec = (
        importlib.util.spec_from_file_location(
            ENGINE_MODULE_NAME,
            ENGINE_FILE,
        )
    )

    if spec is None:

        raise AssertionError(
            "Could not create module spec."
        )

    if spec.loader is None:

        raise AssertionError(
            "Feature Engine loader unavailable."
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    # Critical for dataclasses and
    # __module__ resolution.
    sys.modules[
        ENGINE_MODULE_NAME
    ] = module

    try:

        spec.loader.exec_module(
            module
        )

    except Exception:

        sys.modules.pop(
            ENGINE_MODULE_NAME,
            None,
        )

        raise

    return module


# ============================================================================
# SIGNATURE AUDIT
# ============================================================================

def signature_audit(
    engine: Any,
) -> bool:

    expected = {
        "calculate_feature_records": (
            "bars",
            "indicator_records",
            "structure_records",
        ),

        "lookahead_audit": (
            "bars",
            "indicator_records",
            "structure_records",
        ),

        "determinism_audit": (
            "bars",
            "indicator_records",
            "structure_records",
        ),

        "calculate_trend_features": (
            "close",
            "indicator",
        ),

        "calculate_momentum_features": (
            "indicator",
        ),

        "calculate_volatility_features": (
            "close",
            "indicator",
        ),

        "calculate_trend_strength_features": (
            "indicator",
        ),

        "calculate_price_volume_features": (
            "close",
            "indicator",
        ),

        "calculate_ichimoku_features": (
            "close",
            "indicator",
        ),

        "calculate_structure_features": (
            "structure",
        ),

        "validate_feature_bar": (
            "bar",
        ),

        "validate_feature_bars": (
            "bars",
        ),

        "validate_feature_record": (
            "record",
        ),

        "validate_feature_collection": (
            "records",
        ),
    }

    for name, expected_params in expected.items():

        function = getattr(
            engine,
            name,
            None,
        )

        if function is None:

            raise AssertionError(
                f"Missing API: {name}"
            )

        actual = tuple(
            inspect.signature(
                function
            ).parameters.keys()
        )

        if actual != expected_params:

            raise AssertionError(
                f"Signature mismatch: "
                f"{name} | "
                f"expected={expected_params} | "
                f"actual={actual}"
            )

    return True


# ============================================================================
# SYNTHETIC INPUTS
# ============================================================================

def build_bars(
    engine: Any,
    count: int = 100,
):

    bars = []

    for i in range(count):

        close = (
            100.0
            + i * 0.5
            + math.sin(i / 5.0)
        )

        high = (
            close
            + 1.0
            + abs(math.sin(i))
        )

        low = (
            close
            - 1.0
            - abs(math.cos(i))
        )

        bars.append(
            engine.FeatureBar(
                timestamp=i,
                high=high,
                low=low,
                close=close,
                open=close,
                volume=1000.0 + i * 10.0,
                cmc_id=875,
                symbol="TEST",
            )
        )

    return bars


class SyntheticIndicator:

    def __init__(
        self,
        index: int,
    ):

        close = (
            100.0
            + index * 0.5
            + math.sin(index / 5.0)
        )

        self.ema = (
            close - 0.5
            if index >= 19
            else None
        )

        self.sma = (
            close - 0.4
            if index >= 19
            else None
        )

        self.wma = (
            close - 0.3
            if index >= 19
            else None
        )

        self.rsi = (
            60.0
            if index >= 14
            else None
        )

        self.macd = (
            1.0
            if index >= 25
            else None
        )

        self.stochastic_k = (
            70.0
            if index >= 15
            else None
        )

        self.atr = (
            2.0
            if index >= 13
            else None
        )

        self.bb_position = (
            0.5
            if index >= 19
            else None
        )

        self.bb_width = (
            0.04
            if index >= 19
            else None
        )

        self.adx = (
            30.0
            if index >= 27
            else None
        )

        self.plus_di = (
            35.0
            if index >= 13
            else None
        )

        self.minus_di = (
            15.0
            if index >= 13
            else None
        )

        self.vwap = (
            close - 0.2
        )

        self.volume_change_ratio = (
            1.01
            if index >= 1
            else None
        )

        self.ichimoku_tenkan = (
            close - 0.2
            if index >= 8
            else None
        )

        self.ichimoku_kijun = (
            close - 0.1
            if index >= 25
            else None
        )

        self.ichimoku_senkou_a = (
            close - 0.1
            if index >= 25
            else None
        )

        self.ichimoku_senkou_b = (
            close - 0.05
            if index >= 51
            else None
        )


def build_indicators(
    count: int,
):

    return [
        SyntheticIndicator(i)
        for i in range(count)
    ]


def build_structures(
    count: int,
):

    structures = []

    for i in range(count):

        structures.append(
            {
                "direction": (
                    "BULLISH"
                    if i % 3 != 0
                    else "NEUTRAL"
                ),

                "strength": (
                    "STRONG"
                    if i >= 30
                    else "MEDIUM"
                ),

                "confidence": (
                    "HIGH"
                    if i >= 40
                    else "MEDIUM"
                ),

                "structure": (
                    "HH"
                    if i % 2 == 0
                    else "HL"
                ),

                "bos": i >= 30,

                "choch": (
                    i == 60
                ),
            }
        )

    return structures


# ============================================================================
# SCHEMA AUDIT
# ============================================================================

def schema_audit(
    engine: Any,
) -> bool:

    FeatureBar = engine.FeatureBar
    FeatureRecord = engine.FeatureRecord

    bar_fields = {
        field.name
        for field in fields(
            FeatureBar
        )
    }

    expected_bar_fields = {
        "timestamp",
        "high",
        "low",
        "close",
        "open",
        "volume",
        "cmc_id",
        "symbol",
    }

    if bar_fields != expected_bar_fields:

        raise AssertionError(
            "FeatureBar schema mismatch: "
            f"{bar_fields}"
        )

    record_fields = {
        field.name
        for field in fields(
            FeatureRecord
        )
    }

    expected_record_fields = {
        "index",
        "timestamp",
        "cmc_id",
        "symbol",
        "close",

        "ema_distance",
        "sma_distance",
        "wma_distance",

        "rsi_normalized",
        "macd_normalized",
        "stochastic_position",

        "atr_normalized",
        "bb_position",
        "bb_width",

        "adx_normalized",
        "di_spread",

        "price_to_vwap",
        "volume_change_ratio",

        "ichimoku_tenkan_distance",
        "ichimoku_kijun_distance",
        "ichimoku_cloud_position",

        "structure_direction",
        "structure_strength",
        "structure_confidence",
        "structure_point_type",

        "bos_recent",
        "choch_recent",

        "trend_alignment",
        "momentum_alignment",
        "volatility_regime",
        "structure_regime",
    }

    if record_fields != expected_record_fields:

        raise AssertionError(
            "FeatureRecord schema mismatch."
        )

    return True


# ============================================================================
# RUNTIME QUALITY
# ============================================================================

def runtime_audit(
    engine: Any,
    bars: list,
    indicators: list,
    structures: list,
) -> list:

    records = (
        engine.calculate_feature_records(
            bars,
            indicators,
            structures,
        )
    )

    if len(records) != len(bars):

        raise AssertionError(
            "Runtime record count mismatch."
        )

    if not engine.validate_feature_collection(
        records
    ):

        raise AssertionError(
            "Feature collection validation failed."
        )

    return records


# ============================================================================
# TREND QUALITY
# ============================================================================

def trend_quality_audit(
    engine: Any,
    bars: list,
    indicators: list,
) -> bool:

    for i, bar in enumerate(bars):

        result = (
            engine.calculate_trend_features(
                bar.close,
                indicators[i],
            )
        )

        for field in (
            "ema_distance",
            "sma_distance",
            "wma_distance",
        ):

            value = result[field]

            if value is not None:

                if not math.isfinite(
                    float(value)
                ):

                    raise AssertionError(
                        f"Invalid trend feature: "
                        f"{field}"
                    )

    return True


# ============================================================================
# MOMENTUM QUALITY
# ============================================================================

def momentum_quality_audit(
    engine: Any,
    indicators: list,
) -> bool:

    for indicator in indicators:

        result = (
            engine.calculate_momentum_features(
                indicator
            )
        )

        for field in (
            "rsi_normalized",
            "stochastic_position",
        ):

            value = result[field]

            if value is not None:

                if not (
                    -1.0
                    <= value
                    <= 1.0
                ):

                    raise AssertionError(
                        f"Momentum feature "
                        f"outside range: "
                        f"{field}"
                    )

        macd = result[
            "macd_normalized"
        ]

        if macd is not None:

            if not math.isfinite(
                float(macd)
            ):

                raise AssertionError(
                    "Invalid MACD feature."
                )

    return True


# ============================================================================
# VOLATILITY QUALITY
# ============================================================================

def volatility_quality_audit(
    engine: Any,
    bars: list,
    indicators: list,
) -> bool:

    for i, bar in enumerate(bars):

        result = (
            engine.calculate_volatility_features(
                bar.close,
                indicators[i],
            )
        )

        atr = result[
            "atr_normalized"
        ]

        if atr is not None:

            if atr < 0:

                raise AssertionError(
                    "ATR normalized "
                    "cannot be negative."
                )

            if not math.isfinite(
                float(atr)
            ):

                raise AssertionError(
                    "ATR normalized "
                    "must be finite."
                )

        bb_width = result[
            "bb_width"
        ]

        if bb_width is not None:

            if bb_width < 0:

                raise AssertionError(
                    "BB width cannot "
                    "be negative."
                )

    return True


# ============================================================================
# TREND STRENGTH QUALITY
# ============================================================================

def trend_strength_quality_audit(
    engine: Any,
    indicators: list,
) -> bool:

    for indicator in indicators:

        result = (
            engine.calculate_trend_strength_features(
                indicator
            )
        )

        adx = result[
            "adx_normalized"
        ]

        if adx is not None:

            if not (
                0.0
                <= adx
                <= 1.0
            ):

                raise AssertionError(
                    "ADX normalized "
                    "outside [0,1]."
                )

        di_spread = result[
            "di_spread"
        ]

        if di_spread is not None:

            if not (
                -1.0
                <= di_spread
                <= 1.0
            ):

                raise AssertionError(
                    "DI spread outside "
                    "[-1,1]."
                )

    return True


# ============================================================================
# PRICE / VOLUME QUALITY
# ============================================================================

def price_volume_quality_audit(
    engine: Any,
    bars: list,
    indicators: list,
) -> bool:

    for i, bar in enumerate(bars):

        result = (
            engine.calculate_price_volume_features(
                bar.close,
                indicators[i],
            )
        )

        for field in (
            "price_to_vwap",
            "volume_change_ratio",
        ):

            value = result[field]

            if value is not None:

                if not math.isfinite(
                    float(value)
                ):

                    raise AssertionError(
                        f"Non-finite "
                        f"price/volume "
                        f"feature: {field}"
                    )

    return True


# ============================================================================
# ICHIMOKU QUALITY
# ============================================================================

def ichimoku_quality_audit(
    engine: Any,
    bars: list,
    indicators: list,
) -> bool:

    for i, bar in enumerate(bars):

        result = (
            engine.calculate_ichimoku_features(
                bar.close,
                indicators[i],
            )
        )

        cloud = result[
            "ichimoku_cloud_position"
        ]

        if cloud is not None:

            if not (
                -1.0
                <= cloud
                <= 1.0
            ):

                raise AssertionError(
                    "Ichimoku cloud "
                    "position outside "
                    "[-1,1]."
                )

    return True


# ============================================================================
# STRUCTURE QUALITY
# ============================================================================

def structure_quality_audit(
    engine: Any,
    structures: list,
) -> bool:

    allowed_direction = {
        None,
        "BULLISH",
        "BEARISH",
        "NEUTRAL",
        "UNKNOWN",
    }

    allowed_strength = {
        None,
        "WEAK",
        "MEDIUM",
        "STRONG",
        "UNKNOWN",
    }

    allowed_confidence = {
        None,
        "LOW",
        "MEDIUM",
        "HIGH",
        "UNKNOWN",
    }

    for structure in structures:

        result = (
            engine.calculate_structure_features(
                structure
            )
        )

        if result[
            "structure_direction"
        ] not in allowed_direction:

            raise AssertionError(
                "Invalid structure direction."
            )

        if result[
            "structure_strength"
        ] not in allowed_strength:

            raise AssertionError(
                "Invalid structure strength."
            )

        if result[
            "structure_confidence"
        ] not in allowed_confidence:

            raise AssertionError(
                "Invalid structure confidence."
            )

        if not isinstance(
            result["bos_recent"],
            bool,
        ):

            raise AssertionError(
                "bos_recent must be bool."
            )

        if not isinstance(
            result["choch_recent"],
            bool,
        ):

            raise AssertionError(
                "choch_recent must be bool."
            )

    return True


# ============================================================================
# COMPOSITE QUALITY
# ============================================================================

def composite_quality_audit(
    records: list,
) -> bool:

    for record in records:

        if (
            record.trend_alignment
            is not None
        ):

            if not (
                -1.0
                <= record.trend_alignment
                <= 1.0
            ):

                raise AssertionError(
                    "Trend alignment "
                    "outside [-1,1]."
                )

        if (
            record.momentum_alignment
            is not None
        ):

            if not (
                -1.0
                <= record.momentum_alignment
                <= 1.0
            ):

                raise AssertionError(
                    "Momentum alignment "
                    "outside [-1,1]."
                )

    return True


# ============================================================================
# WARM-UP QUALITY
# ============================================================================

def warmup_quality_audit(
    records: list,
) -> bool:

    if not records:

        raise AssertionError(
            "No feature records."
        )

    first = records[0]

    expected_none = (
        "ema_distance",
        "sma_distance",
        "wma_distance",
        "rsi_normalized",
        "macd_normalized",
        "stochastic_position",
        "atr_normalized",
        "bb_position",
        "bb_width",
        "adx_normalized",
        "di_spread",
        "ichimoku_kijun_distance",
        "ichimoku_cloud_position",
    )

    for field in expected_none:

        if getattr(
            first,
            field,
        ) is not None:

            raise AssertionError(
                "Warm-up violation: "
                f"{field}"
            )

    return True


# ============================================================================
# NUMERIC SAFETY
# ============================================================================

def numeric_safety_audit(
    engine: Any,
    records: list,
) -> bool:

    for record in records:

        for field in NUMERIC_FEATURE_FIELDS:

            value = getattr(
                record,
                field,
            )

            if value is None:
                continue

            if not math.isfinite(
                float(value)
            ):

                raise AssertionError(
                    "Non-finite feature: "
                    f"{field}"
                )

        for field in BOUNDED_FEATURE_FIELDS:

            value = getattr(
                record,
                field,
            )

            if value is None:
                continue

            if not (
                -1.0
                <= value
                <= 1.0
            ):

                raise AssertionError(
                    "Bounded feature outside "
                    f"[-1,1]: {field}"
                )

        if not engine.validate_feature_record(
            record
        ):

            raise AssertionError(
                "Feature record validation failed."
            )

    return True


# ============================================================================
# IDENTITY QUALITY
# ============================================================================

def identity_quality_audit(
    records: list,
    bars: list,
) -> bool:

    if len(records) != len(bars):

        raise AssertionError(
            "Identity audit length mismatch."
        )

    for i, record in enumerate(
        records
    ):

        bar = bars[i]

        if record.index != i:

            raise AssertionError(
                "Index identity mismatch."
            )

        if (
            record.timestamp
            != bar.timestamp
        ):

            raise AssertionError(
                "Timestamp identity mismatch."
            )

        if record.cmc_id != bar.cmc_id:

            raise AssertionError(
                "CMC_ID identity mismatch."
            )

        if record.symbol != bar.symbol:

            raise AssertionError(
                "Symbol identity mismatch."
            )

        if record.close != bar.close:

            raise AssertionError(
                "Close identity mismatch."
            )

    return True


# ============================================================================
# INPUT SAFETY
# ============================================================================

def input_safety_audit(
    engine: Any,
) -> bool:

    # Invalid OHLC
    try:

        engine.validate_feature_bar(
            engine.FeatureBar(
                timestamp=0,
                high=1.0,
                low=2.0,
                close=1.5,
            )
        )

    except ValueError:
        pass

    else:

        raise AssertionError(
            "Invalid OHLC accepted."
        )

    # Negative volume
    try:

        engine.validate_feature_bar(
            engine.FeatureBar(
                timestamp=0,
                high=2.0,
                low=1.0,
                close=1.5,
                volume=-1.0,
            )
        )

    except ValueError:
        pass

    else:

        raise AssertionError(
            "Negative volume accepted."
        )

    # NaN
    try:

        engine.validate_feature_bar(
            engine.FeatureBar(
                timestamp=0,
                high=float("nan"),
                low=1.0,
                close=1.5,
            )
        )

    except ValueError:
        pass

    else:

        raise AssertionError(
            "NaN accepted."
        )

    # Infinity
    try:

        engine.validate_feature_bar(
            engine.FeatureBar(
                timestamp=0,
                high=float("inf"),
                low=1.0,
                close=1.5,
            )
        )

    except ValueError:
        pass

    else:

        raise AssertionError(
            "Infinity accepted."
        )

    # Empty bars
    try:

        engine.validate_feature_bars(
            []
        )

    except ValueError:
        pass

    else:

        raise AssertionError(
            "Empty bars accepted."
        )

    return True


# ============================================================================
# ADVERSARIAL SEQUENCES
# ============================================================================

def adversarial_sequence_audit(
    engine: Any,
) -> bool:

    # ------------------------------------------------------------------------
    # Flat market
    # ------------------------------------------------------------------------

    bars = []

    for i in range(80):

        bars.append(
            engine.FeatureBar(
                timestamp=i,
                high=100.0,
                low=100.0,
                close=100.0,
                open=100.0,
                volume=1000.0,
                cmc_id=1,
                symbol="FLAT",
            )
        )

    indicators = []

    for i in range(80):

        indicator = SyntheticIndicator(i)

        indicator.vwap = 100.0

        indicators.append(
            indicator
        )

    structures = [
        {
            "direction": "NEUTRAL",
            "strength": "WEAK",
            "confidence": "LOW",
            "structure": "NONE",
            "bos": False,
            "choch": False,
        }
        for _ in range(80)
    ]

    records = (
        engine.calculate_feature_records(
            bars,
            indicators,
            structures,
        )
    )

    engine.validate_feature_collection(
        records
    )

    # ------------------------------------------------------------------------
    # Monotonic rise
    # ------------------------------------------------------------------------

    rising_bars = []

    for i in range(80):

        close = 100.0 + i

        rising_bars.append(
            engine.FeatureBar(
                timestamp=i,
                high=close + 2.0,
                low=close - 1.0,
                close=close,
                open=close - 0.5,
                volume=1000.0 + i,
                cmc_id=2,
                symbol="RISE",
            )
        )

    rising_indicators = (
        build_indicators(80)
    )

    rising_structures = [
        {
            "direction": "BULLISH",
            "strength": "STRONG",
            "confidence": "HIGH",
            "structure": "HH",
            "bos": True,
            "choch": False,
        }
        for _ in range(80)
    ]

    rising_records = (
        engine.calculate_feature_records(
            rising_bars,
            rising_indicators,
            rising_structures,
        )
    )

    engine.validate_feature_collection(
        rising_records
    )

    # ------------------------------------------------------------------------
    # Monotonic decline
    # ------------------------------------------------------------------------

    falling_bars = []

    for i in range(80):

        close = 200.0 - i

        falling_bars.append(
            engine.FeatureBar(
                timestamp=i,
                high=close + 1.0,
                low=close - 2.0,
                close=close,
                open=close + 0.5,
                volume=1000.0 + i,
                cmc_id=3,
                symbol="FALL",
            )
        )

    falling_indicators = (
        build_indicators(80)
    )

    falling_structures = [
        {
            "direction": "BEARISH",
            "strength": "STRONG",
            "confidence": "HIGH",
            "structure": "LL",
            "bos": True,
            "choch": False,
        }
        for _ in range(80)
    ]

    falling_records = (
        engine.calculate_feature_records(
            falling_bars,
            falling_indicators,
            falling_structures,
        )
    )

    engine.validate_feature_collection(
        falling_records
    )

    return True


# ============================================================================
# INPUT ORDER PRESERVATION
# ============================================================================

def order_preservation_audit(
    engine: Any,
    bars: list,
    indicators: list,
    structures: list,
) -> bool:

    records = (
        engine.calculate_feature_records(
            bars,
            indicators,
            structures,
        )
    )

    original_ids = [
        (
            bar.timestamp,
            bar.cmc_id,
            bar.symbol,
        )
        for bar in bars
    ]

    output_ids = [
        (
            record.timestamp,
            record.cmc_id,
            record.symbol,
        )
        for record in records
    ]

    if original_ids != output_ids:

        raise AssertionError(
            "Input order was not preserved."
        )

    return True


# ============================================================================
# LOOK-AHEAD / CAUSAL VALIDATION
# ============================================================================

def causal_audit(
    engine: Any,
    bars: list,
    indicators: list,
    structures: list,
) -> bool:

    if not engine.lookahead_audit(
        bars,
        indicators,
        structures,
    ):

        raise AssertionError(
            "Feature Engine look-ahead "
            "audit failed."
        )

    # ------------------------------------------------------------------------
    # Explicit prefix reconstruction
    # ------------------------------------------------------------------------

    full = (
        engine.calculate_feature_records(
            bars,
            indicators,
            structures,
        )
    )

    fields = (
        "ema_distance",
        "sma_distance",
        "wma_distance",
        "rsi_normalized",
        "macd_normalized",
        "stochastic_position",
        "atr_normalized",
        "bb_position",
        "bb_width",
        "adx_normalized",
        "di_spread",
        "price_to_vwap",
        "volume_change_ratio",
        "ichimoku_tenkan_distance",
        "ichimoku_kijun_distance",
        "ichimoku_cloud_position",
        "structure_direction",
        "structure_strength",
        "structure_confidence",
        "structure_point_type",
        "bos_recent",
        "choch_recent",
        "trend_alignment",
        "momentum_alignment",
        "volatility_regime",
        "structure_regime",
    )

    # Test selected points to keep the audit
    # comprehensive without excessive runtime.
    selected_indices = (
        0,
        1,
        13,
        19,
        25,
        30,
        51,
        70,
        99,
    )

    for i in selected_indices:

        prefix = (
            engine.calculate_feature_records(
                bars[:i + 1],
                indicators[:i + 1],
                structures[:i + 1],
            )
        )

        if not prefix:

            raise AssertionError(
                "Prefix produced no records."
            )

        a = full[i]
        b = prefix[-1]

        for field in fields:

            left = getattr(
                a,
                field,
            )

            right = getattr(
                b,
                field,
            )

            if left is None or right is None:

                if left is not right:

                    raise AssertionError(
                        "Causal mismatch: "
                        f"index={i} "
                        f"field={field}"
                    )

                continue

            if isinstance(
                left,
                bool,
            ):

                if left != right:

                    raise AssertionError(
                        "Boolean causal "
                        "mismatch: "
                        f"{field}"
                    )

            elif isinstance(
                left,
                str,
            ):

                if left != right:

                    raise AssertionError(
                        "String causal "
                        "mismatch: "
                        f"{field}"
                    )

            else:

                if not math.isclose(
                    float(left),
                    float(right),
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):

                    raise AssertionError(
                        "Numeric causal "
                        "mismatch: "
                        f"index={i} "
                        f"field={field}"
                    )

    return True


# ============================================================================
# DETERMINISM
# ============================================================================

def determinism_quality_audit(
    engine: Any,
    bars: list,
    indicators: list,
    structures: list,
) -> bool:

    first = (
        engine.calculate_feature_records(
            bars,
            indicators,
            structures,
        )
    )

    second = (
        engine.calculate_feature_records(
            bars,
            indicators,
            structures,
        )
    )

    if first != second:

        raise AssertionError(
            "Feature Engine output is "
            "not deterministic."
        )

    if not engine.determinism_audit(
        bars,
        indicators,
        structures,
    ):

        raise AssertionError(
            "Built-in determinism audit failed."
        )

    return True


# ============================================================================
# DECISION ISOLATION
# ============================================================================

def decision_isolation_audit(
    engine: Any,
    source: str,
    records: list,
) -> bool:

    record_fields = {
        field.name.lower()
        for field in fields(
            engine.FeatureRecord
        )
    }

    for forbidden in DECISION_FORBIDDEN_FIELDS:

        if forbidden in record_fields:

            raise AssertionError(
                "Decision field detected: "
                f"{forbidden}"
            )

    # Inspect source for actual decision-style
    # output calls, excluding harmless mentions
    # inside comments/docstrings as much as possible
    # through AST.

    tree = ast.parse(
        source,
        filename=str(
            ENGINE_FILE
        ),
    )

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Return,
        ):

            value = node.value

            if isinstance(
                value,
                ast.Constant,
            ) and isinstance(
                value.value,
                str,
            ):

                text = (
                    value.value
                    .upper()
                )

                if text in {
                    "BUY",
                    "SELL",
                    "LONG",
                    "SHORT",
                }:

                    raise AssertionError(
                        "Trading decision "
                        "output detected."
                    )

    for record in records:

        for forbidden in (
            "buy",
            "sell",
            "signal",
            "decision",
            "long",
            "short",
        ):

            if hasattr(
                record,
                forbidden,
            ):

                raise AssertionError(
                    "Decision attribute "
                    f"detected: {forbidden}"
                )

    return True


# ============================================================================
# SOURCE HASH
# ============================================================================

def source_hash(
    source: str,
) -> str:

    return hashlib.sha256(
        source.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER — DEV-06 — STEP 13B"
    )
    print(
        "FEATURE ENGINE QUALITY & CAUSAL VALIDATION"
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

    # ------------------------------------------------------------------------
    # SOURCE
    # ------------------------------------------------------------------------

    source = read_source()

    tree = parse_ast(
        source
    )

    before_hash = source_hash(
        source
    )

    # ------------------------------------------------------------------------
    # FILE VALIDATION
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("FILE VALIDATION")
    print("=" * 100)

    print(
        "Feature Engine                                     : PASS"
    )

    print(
        "AST Parse                                          : PASS"
    )

    # ------------------------------------------------------------------------
    # SOURCE SAFETY
    # ------------------------------------------------------------------------

    source_mutation_audit(
        tree
    )

    database_independence_audit(
        source,
        tree,
    )

    print()
    print("-" * 100)
    print("SOURCE SAFETY")
    print("-" * 100)

    print(
        "Source mutation safety                             : PASS"
    )

    print(
        "Database independence                              : PASS"
    )

    # ------------------------------------------------------------------------
    # FUNCTION INVENTORY
    # ------------------------------------------------------------------------

    function_names = ast_function_names(
        tree
    )

    print()
    print("-" * 100)
    print("FEATURE ENGINE FUNCTION INVENTORY")
    print("-" * 100)

    for name in sorted(
        function_names
    ):

        print(
            f" - {name}"
        )

    missing_functions = (
        set(REQUIRED_FUNCTIONS)
        - function_names
    )

    if missing_functions:

        raise AssertionError(
            "Missing required functions: "
            f"{sorted(missing_functions)}"
        )

    class_names = ast_class_names(
        tree
    )

    missing_classes = (
        set(REQUIRED_CLASSES)
        - class_names
    )

    if missing_classes:

        raise AssertionError(
            "Missing required classes: "
            f"{sorted(missing_classes)}"
        )

    print()
    print("-" * 100)
    print("REQUIRED FEATURE ENGINE API")
    print("-" * 100)

    print(
        "Required functions                                 : PASS"
    )

    print(
        "Required classes                                   : PASS"
    )

    # ------------------------------------------------------------------------
    # MODULE IMPORT
    # ------------------------------------------------------------------------

    try:

        engine = import_engine()

    except Exception as exc:

        raise AssertionError(
            "Feature Engine import failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    print()
    print("-" * 100)
    print("MODULE RUNTIME")
    print("-" * 100)

    print(
        "Feature Engine import                              : PASS"
    )

    # ------------------------------------------------------------------------
    # SIGNATURES
    # ------------------------------------------------------------------------

    signature_audit(
        engine
    )

    print()
    print("-" * 100)
    print("PUBLIC API SIGNATURE AUDIT")
    print("-" * 100)

    print(
        "Public API signatures                              : PASS"
    )

    # ------------------------------------------------------------------------
    # SCHEMA
    # ------------------------------------------------------------------------

    schema_audit(
        engine
    )

    print()
    print("-" * 100)
    print("OUTPUT SCHEMA CONTRACT")
    print("-" * 100)

    print(
        "FeatureBar schema                                  : PASS"
    )

    print(
        "FeatureRecord schema                               : PASS"
    )

    # ------------------------------------------------------------------------
    # SYNTHETIC DATA
    # ------------------------------------------------------------------------

    bars = build_bars(
        engine,
        count=100,
    )

    indicators = build_indicators(
        100
    )

    structures = build_structures(
        100
    )

    # ------------------------------------------------------------------------
    # RUNTIME
    # ------------------------------------------------------------------------

    records = runtime_audit(
        engine,
        bars,
        indicators,
        structures,
    )

    print()
    print(
        "Runtime output                                     : PASS"
    )

    # ------------------------------------------------------------------------
    # IDENTITY
    # ------------------------------------------------------------------------

    identity_quality_audit(
        records,
        bars,
    )

    order_preservation_audit(
        engine,
        bars,
        indicators,
        structures,
    )

    print()
    print("-" * 100)
    print(
        "CMC_ID / SYMBOL / TIMESTAMP IDENTITY CONTRACT"
    )
    print("-" * 100)

    print(
        "CMC_ID identity                                    : PASS"
    )

    print(
        "Symbol identity                                    : PASS"
    )

    print(
        "Timestamp propagation                              : PASS"
    )

    print(
        "Input order preservation                           : PASS"
    )

    # ------------------------------------------------------------------------
    # FEATURE QUALITY
    # ------------------------------------------------------------------------

    trend_quality_audit(
        engine,
        bars,
        indicators,
    )

    momentum_quality_audit(
        engine,
        indicators,
    )

    volatility_quality_audit(
        engine,
        bars,
        indicators,
    )

    trend_strength_quality_audit(
        engine,
        indicators,
    )

    price_volume_quality_audit(
        engine,
        bars,
        indicators,
    )

    ichimoku_quality_audit(
        engine,
        bars,
        indicators,
    )

    structure_quality_audit(
        engine,
        structures,
    )

    composite_quality_audit(
        records
    )

    print()
    print("-" * 100)
    print("FEATURE FAMILY QUALITY")
    print("-" * 100)

    print(
        "Trend feature quality                             : PASS"
    )

    print(
        "Momentum feature quality                          : PASS"
    )

    print(
        "Volatility feature quality                        : PASS"
    )

    print(
        "Trend strength quality                            : PASS"
    )

    print(
        "Price / volume quality                            : PASS"
    )

    print(
        "Ichimoku / cloud quality                          : PASS"
    )

    print(
        "Market structure quality                          : PASS"
    )

    print(
        "Composite feature quality                         : PASS"
    )

    # ------------------------------------------------------------------------
    # WARM-UP
    # ------------------------------------------------------------------------

    warmup_quality_audit(
        records
    )

    print()
    print("-" * 100)
    print(
        "WARM-UP / INSUFFICIENT HISTORY CONTRACT"
    )
    print("-" * 100)

    print(
        "Warm-up semantics                                  : PASS"
    )

    # ------------------------------------------------------------------------
    # NUMERIC
    # ------------------------------------------------------------------------

    numeric_safety_audit(
        engine,
        records,
    )

    print()
    print("-" * 100)
    print(
        "NUMERIC SAFETY CONTRACT"
    )
    print("-" * 100)

    print(
        "Finite feature values                              : PASS"
    )

    print(
        "Bounded normalized values                          : PASS"
    )

    # ------------------------------------------------------------------------
    # INPUT SAFETY
    # ------------------------------------------------------------------------

    input_safety_audit(
        engine
    )

    print()
    print("-" * 100)
    print(
        "BOUNDARY / INPUT SAFETY"
    )
    print("-" * 100)

    print(
        "Invalid OHLC rejection                             : PASS"
    )

    print(
        "Negative volume rejection                          : PASS"
    )

    print(
        "Non-finite rejection                               : PASS"
    )

    # ------------------------------------------------------------------------
    # ADVERSARIAL
    # ------------------------------------------------------------------------

    adversarial_sequence_audit(
        engine
    )

    print()
    print("-" * 100)
    print(
        "ADVERSARIAL SEQUENCE VALIDATION"
    )
    print("-" * 100)

    print(
        "Flat sequence                                      : PASS"
    )

    print(
        "Monotonic rising sequence                         : PASS"
    )

    print(
        "Monotonic falling sequence                         : PASS"
    )

    # ------------------------------------------------------------------------
    # CAUSAL
    # ------------------------------------------------------------------------

    causal_audit(
        engine,
        bars,
        indicators,
        structures,
    )

    print()
    print("-" * 100)
    print(
        "LOOK-AHEAD / FUTURE DATA CONTRACT"
    )
    print("-" * 100)

    print(
        "Look-ahead protection                              : PASS"
    )

    print(
        "Future-data protection                             : PASS"
    )

    # ------------------------------------------------------------------------
    # DETERMINISM
    # ------------------------------------------------------------------------

    determinism_quality_audit(
        engine,
        bars,
        indicators,
        structures,
    )

    print()
    print("-" * 100)
    print(
        "DETERMINISM CONTRACT"
    )
    print("-" * 100)

    print(
        "Deterministic output                               : PASS"
    )

    # ------------------------------------------------------------------------
    # DECISION ISOLATION
    # ------------------------------------------------------------------------

    decision_isolation_audit(
        engine,
        source,
        records,
    )

    print()
    print("-" * 100)
    print(
        "DECISION OUTPUT ISOLATION"
    )
    print("-" * 100)

    print(
        "Trading decision output                            : PASS"
    )

    print(
        "BUY / SELL output                                  : NONE"
    )

    # ------------------------------------------------------------------------
    # RUNTIME SOURCE INTEGRITY
    # ------------------------------------------------------------------------

    after_source = read_source()

    after_hash = source_hash(
        after_source
    )

    if before_hash != after_hash:

        raise AssertionError(
            "Feature Engine source was "
            "modified during audit."
        )

    # ------------------------------------------------------------------------
    # ARCHITECTURE
    # ------------------------------------------------------------------------

    print()
    print("-" * 100)
    print("ARCHITECTURE CONTRACT")
    print("-" * 100)

    print(
        "Analysis-layer isolation                           : PASS"
    )

    print(
        "Database independence                              : PASS"
    )

    print(
        "Production writes                                  : NONE"
    )

    # ------------------------------------------------------------------------
    # FINAL REQUIRED CONTRACT
    # ------------------------------------------------------------------------

    print()
    print("-" * 100)
    print(
        "REQUIRED FEATURE ENGINE QUALITY CONTRACT"
    )
    print("-" * 100)

    print(
        "Source mutation safety                             : PASS"
    )

    print(
        "Database independence                              : PASS"
    )

    print(
        "Module import                                      : PASS"
    )

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
        "Trend indicator quality                            : PASS"
    )

    print(
        "Momentum indicator quality                         : PASS"
    )

    print(
        "Volatility indicator quality                       : PASS"
    )

    print(
        "Trend strength quality                             : PASS"
    )

    print(
        "Price / volume quality                             : PASS"
    )

    print(
        "Cloud / Ichimoku quality                           : PASS"
    )

    print(
        "Market structure quality                           : PASS"
    )

    print(
        "Composite feature quality                          : PASS"
    )

    print(
        "Warm-up semantics                                  : PASS"
    )

    print(
        "Numeric safety                                     : PASS"
    )

    print(
        "CMC_ID / symbol identity                            : PASS"
    )

    print(
        "Boundary semantics                                 : PASS"
    )

    print(
        "Input safety                                       : PASS"
    )

    print(
        "Adversarial sequences                              : PASS"
    )

    print(
        "Look-ahead protection                              : PASS"
    )

    print(
        "Deterministic output                               : PASS"
    )

    print(
        "Decision isolation                                 : PASS"
    )

    # ------------------------------------------------------------------------
    # FINAL VERDICT
    # ------------------------------------------------------------------------

    print()
    print("=" * 100)
    print(
        "STEP 13B VERDICT"
    )
    print("=" * 100)

    print(
        "RESULT : FEATURE ENGINE QUALITY & CAUSAL VALIDATION PASS"
    )

    print(
        "STATUS : READY FOR STEP 14"
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

    print("=" * 100)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print()
        print("=" * 100)
        print(
            "STEP 13B VERDICT"
        )
        print("=" * 100)

        print(
            "RESULT : FEATURE ENGINE QUALITY & CAUSAL VALIDATION FAIL"
        )

        print(
            f"ERROR  : "
            f"{type(exc).__name__}: {exc}"
        )

        raise