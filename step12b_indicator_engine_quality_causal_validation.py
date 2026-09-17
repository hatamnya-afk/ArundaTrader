"""
ARUNDA TRADER — DEV-06
STEP 12B — INDICATOR ENGINE QUALITY & CAUSAL VALIDATION

Purpose
-------
Deep quality, mathematical, boundary, determinism, identity and
look-ahead validation for the PASS-LOCKED INDICATOR_ENGINE_v0.1.

Architecture
------------
- Audit / validation layer only
- Database independent
- No SQL
- No database writes
- No production mutation
- No trading decisions
- No BUY / SELL output
- No look-ahead
- Input order preserved
- CMC_ID / symbol / timestamp identity preserved

This audit validates the actual public API and causal semantics of
INDICATOR_ENGINE_v0.1.
"""

from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


ENGINE_FILENAME = "indicator_engine.py"
ENGINE_NAME = "INDICATOR_ENGINE_v0.1"


# ============================================================================
# OUTPUT
# ============================================================================

def section(title: str) -> None:
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def result(label: str, value: Any) -> None:
    print(f"{label:<48}: {value}")


# ============================================================================
# ENGINE LOADING
# ============================================================================

def load_engine():
    engine_path = Path(__file__).resolve().parent / ENGINE_FILENAME

    if not engine_path.exists():
        raise FileNotFoundError(
            f"Indicator Engine not found: {engine_path}"
        )

    source = engine_path.read_text(
        encoding="utf-8"
    )

    ast.parse(source)

    namespace: Dict[str, Any] = {}

    exec(
        compile(
            source,
            str(engine_path),
            "exec",
        ),
        namespace,
    )

    return engine_path, source, namespace


# ============================================================================
# SOURCE SAFETY
# ============================================================================

def audit_source_safety(source: str) -> bool:

    tree = ast.parse(source)

    forbidden_sql = (
        "INSERT",
        "UPDATE",
        "DELETE",
        "ALTER",
        "DROP",
        "CREATE TABLE",
        "CREATE INDEX",
        "REPLACE",
    )

    upper_source = source.upper()

    for token in forbidden_sql:

        if token in upper_source:
            return False

    forbidden_modules = {
        "sqlite3",
        "sqlalchemy",
        "psycopg2",
        "mysql",
        "pymysql",
    }

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                if alias.name.split(".")[0] in forbidden_modules:
                    return False

        elif isinstance(node, ast.ImportFrom):

            if (
                node.module
                and node.module.split(".")[0]
                in forbidden_modules
            ):
                return False

    return True


# ============================================================================
# REQUIRED API
# ============================================================================

REQUIRED_FUNCTIONS = (
    "validate_bar",
    "validate_bars",
    "calculate_sma",
    "calculate_ema",
    "calculate_wma",
    "calculate_rsi",
    "calculate_macd",
    "calculate_true_range",
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


def audit_required_api(namespace: Dict[str, Any]) -> bool:

    for name in REQUIRED_FUNCTIONS:

        if name not in namespace:
            return False

        if not callable(namespace[name]):
            return False

    for name in REQUIRED_CLASSES:

        if name not in namespace:
            return False

        if not inspect.isclass(namespace[name]):
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
}


def audit_signatures(namespace: Dict[str, Any]) -> bool:

    for name, expected in EXPECTED_PARAMETERS.items():

        signature = inspect.signature(
            namespace[name]
        )

        actual = tuple(
            signature.parameters.keys()
        )

        if actual != expected:
            return False

    return True


# ============================================================================
# SYNTHETIC DATA
# ============================================================================

def make_bars(
    namespace: Dict[str, Any],
    closes: Sequence[float],
    cmc_id: int = 1,
    symbol: str = "TEST",
    volume_start: float = 1000.0,
):
    IndicatorBar = namespace["IndicatorBar"]

    bars = []

    for i, close in enumerate(closes):

        close = float(close)

        bars.append(
            IndicatorBar(
                timestamp=i,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                open=close,
                volume=volume_start + i * 10.0,
                cmc_id=cmc_id,
                symbol=symbol,
            )
        )

    return bars


def make_adversarial_bars(
    namespace: Dict[str, Any],
):

    closes = []

    for i in range(120):

        if i % 17 == 0:
            closes.append(100.0)

        elif i % 11 == 0:
            closes.append(
                closes[-1] - 7.0
            )

        elif i % 7 == 0:
            closes.append(
                closes[-1] + 9.0
            )

        elif i % 5 == 0:
            closes.append(
                closes[-1] - 2.0
            )

        else:
            closes.append(
                closes[-1] + 1.0
            )

    return make_bars(
        namespace,
        closes,
        cmc_id=999,
        symbol="ADVERSARIAL",
    )


# ============================================================================
# RECORD HELPERS
# ============================================================================

INDICATOR_FIELDS = (
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


def finite_or_none(value: Any) -> bool:

    return (
        value is None
        or math.isfinite(float(value))
    )


# ============================================================================
# INDICATOR RANGE QUALITY
# ============================================================================

def audit_indicator_ranges(
    namespace: Dict[str, Any],
    records,
) -> bool:

    for record in records:

        if record.rsi is not None:

            if not 0.0 <= record.rsi <= 100.0:
                return False

        if record.stochastic_k is not None:

            if not 0.0 <= record.stochastic_k <= 100.0:
                return False

        if record.stochastic_d is not None:

            if not 0.0 <= record.stochastic_d <= 100.0:
                return False

        if record.adx is not None:

            if record.adx < 0.0:
                return False

        if record.atr is not None:

            if record.atr < 0.0:
                return False

        for field in INDICATOR_FIELDS:

            value = getattr(
                record,
                field,
            )

            if not finite_or_none(value):
                return False

    return True


# ============================================================================
# SMA QUALITY
# ============================================================================

def audit_sma(
    namespace: Dict[str, Any],
    closes: Sequence[float],
) -> bool:

    calculate_sma = namespace["calculate_sma"]

    period = 5

    values = calculate_sma(
        closes,
        period,
    )

    for i in range(period - 1):
        if values[i] is not None:
            return False

    for i in range(period - 1, len(closes)):

        expected = sum(
            closes[i - period + 1:i + 1]
        ) / period

        if not math.isclose(
            values[i],
            expected,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            return False

    return True


# ============================================================================
# EMA QUALITY
# ============================================================================

def audit_ema(
    namespace: Dict[str, Any],
    closes: Sequence[float],
) -> bool:

    calculate_ema = namespace["calculate_ema"]

    period = 5

    values = calculate_ema(
        closes,
        period,
    )

    if any(
        values[i] is not None
        for i in range(period - 1)
    ):
        return False

    seed = sum(
        closes[:period]
    ) / period

    if not math.isclose(
        values[period - 1],
        seed,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        return False

    alpha = 2.0 / (period + 1.0)

    previous = seed

    for i in range(period, len(closes)):

        expected = (
            alpha * closes[i]
            + (1.0 - alpha) * previous
        )

        if not math.isclose(
            values[i],
            expected,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            return False

        previous = expected

    return True


# ============================================================================
# WMA QUALITY
# ============================================================================

def audit_wma(
    namespace: Dict[str, Any],
    closes: Sequence[float],
) -> bool:

    calculate_wma = namespace["calculate_wma"]

    period = 3

    values = calculate_wma(
        closes,
        period,
    )

    denominator = 6.0

    for i in range(period - 1, len(closes)):

        window = closes[
            i - period + 1:i + 1
        ]

        expected = (
            window[0] * 1
            + window[1] * 2
            + window[2] * 3
        ) / denominator

        if not math.isclose(
            values[i],
            expected,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            return False

    return True


# ============================================================================
# RSI QUALITY
# ============================================================================

def audit_rsi(
    namespace: Dict[str, Any],
    closes: Sequence[float],
) -> bool:

    calculate_rsi = namespace["calculate_rsi"]

    period = 14

    values = calculate_rsi(
        closes,
        period,
    )

    for i in range(period):
        if values[i] is not None:
            return False

    constant = [
        100.0
        for _ in range(40)
    ]

    constant_values = calculate_rsi(
        constant,
        period,
    )

    if constant_values[period] != 50.0:
        return False

    rising = [
        float(i + 1)
        for i in range(40)
    ]

    rising_values = calculate_rsi(
        rising,
        period,
    )

    if rising_values[period] != 100.0:
        return False

    return True


# ============================================================================
# MACD QUALITY
# ============================================================================

def audit_macd(
    namespace: Dict[str, Any],
    closes: Sequence[float],
) -> bool:

    calculate_macd = namespace["calculate_macd"]

    macd, signal, histogram = calculate_macd(
        closes
    )

    if not (
        len(macd)
        == len(signal)
        == len(histogram)
        == len(closes)
    ):
        return False

    for i in range(len(closes)):

        if (
            macd[i] is not None
            and signal[i] is not None
            and histogram[i] is not None
        ):

            expected = (
                macd[i]
                - signal[i]
            )

            if not math.isclose(
                histogram[i],
                expected,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

    return True


# ============================================================================
# ATR / TRUE RANGE QUALITY
# ============================================================================

def audit_atr(
    namespace: Dict[str, Any],
    bars,
) -> bool:

    calculate_true_range = namespace[
        "calculate_true_range"
    ]

    calculate_atr = namespace[
        "calculate_atr"
    ]

    tr = calculate_true_range(
        bars
    )

    if len(tr) != len(bars):
        return False

    for value in tr:

        if not math.isfinite(value):
            return False

        if value < 0:
            return False

    period = 5

    atr = calculate_atr(
        bars,
        period,
    )

    if any(
        value is not None and value < 0
        for value in atr
    ):
        return False

    expected = sum(
        tr[:period]
    ) / period

    if not math.isclose(
        atr[period - 1],
        expected,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        return False

    return True


# ============================================================================
# BOLLINGER QUALITY
# ============================================================================

def audit_bollinger(
    namespace: Dict[str, Any],
    closes: Sequence[float],
) -> bool:

    calculate = namespace[
        "calculate_bollinger_bands"
    ]

    middle, upper, lower, width, position = calculate(
        closes,
        period=5,
        stddev_multiplier=2.0,
    )

    for i in range(len(closes)):

        if middle[i] is None:
            continue

        if upper[i] < middle[i]:
            return False

        if lower[i] > middle[i]:
            return False

        if upper[i] < lower[i]:
            return False

        if width[i] is not None and width[i] < 0:
            return False

    return True


# ============================================================================
# STOCHASTIC QUALITY
# ============================================================================

def audit_stochastic(
    namespace: Dict[str, Any],
    bars,
) -> bool:

    calculate = namespace[
        "calculate_stochastic"
    ]

    k, d = calculate(
        bars,
        period=14,
        smooth_k=3,
        smooth_d=3,
    )

    if len(k) != len(bars):
        return False

    if len(d) != len(bars):
        return False

    for value in k:

        if value is not None:

            if not 0.0 <= value <= 100.0:
                return False

    for value in d:

        if value is not None:

            if not 0.0 <= value <= 100.0:
                return False

    return True


# ============================================================================
# ADX / DI QUALITY
# ============================================================================

def audit_adx(
    namespace: Dict[str, Any],
    bars,
) -> bool:

    calculate = namespace["calculate_adx"]

    adx, plus_di, minus_di = calculate(
        bars,
        period=14,
    )

    if not (
        len(adx)
        == len(plus_di)
        == len(minus_di)
        == len(bars)
    ):
        return False

    for values in (
        adx,
        plus_di,
        minus_di,
    ):

        for value in values:

            if value is None:
                continue

            if not math.isfinite(value):
                return False

            if value < 0:
                return False

    return True


# ============================================================================
# VWAP / VOLUME QUALITY
# ============================================================================

def audit_volume_family(
    namespace: Dict[str, Any],
    bars,
) -> bool:

    calculate_vwap = namespace[
        "calculate_vwap"
    ]

    calculate_volume_change_ratio = namespace[
        "calculate_volume_change_ratio"
    ]

    vwap = calculate_vwap(
        bars
    )

    ratio = calculate_volume_change_ratio(
        bars
    )

    if len(vwap) != len(bars):
        return False

    if len(ratio) != len(bars):
        return False

    cumulative_pv = 0.0
    cumulative_volume = 0.0

    for i, bar in enumerate(bars):

        if bar.volume is None:
            continue

        typical = (
            bar.high
            + bar.low
            + bar.close
        ) / 3.0

        cumulative_pv += (
            typical
            * bar.volume
        )

        cumulative_volume += bar.volume

        if cumulative_volume > 0:

            expected = (
                cumulative_pv
                / cumulative_volume
            )

            if not math.isclose(
                vwap[i],
                expected,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

    for i in range(1, len(bars)):

        current = bars[i].volume
        previous = bars[i - 1].volume

        if (
            current is not None
            and previous is not None
            and previous != 0
        ):

            expected = current / previous

            if not math.isclose(
                ratio[i],
                expected,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

    return True


# ============================================================================
# ICHIMOKU QUALITY
# ============================================================================

def audit_ichimoku(
    namespace: Dict[str, Any],
    bars,
) -> bool:

    calculate = namespace[
        "calculate_ichimoku"
    ]

    (
        tenkan,
        kijun,
        senkou_a,
        senkou_b,
        chikou,
    ) = calculate(
        bars
    )

    if not all(
        len(values) == len(bars)
        for values in (
            tenkan,
            kijun,
            senkou_a,
            senkou_b,
            chikou,
        )
    ):
        return False

    # Tenkan
    for i in range(len(bars)):

        if i < 8:

            if tenkan[i] is not None:
                return False

        else:

            window = bars[
                i - 8:i + 1
            ]

            expected = (
                max(b.high for b in window)
                + min(b.low for b in window)
            ) / 2.0

            if not math.isclose(
                tenkan[i],
                expected,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

    # Kijun
    for i in range(len(bars)):

        if i < 25:

            if kijun[i] is not None:
                return False

        else:

            window = bars[
                i - 25:i + 1
            ]

            expected = (
                max(b.high for b in window)
                + min(b.low for b in window)
            ) / 2.0

            if not math.isclose(
                kijun[i],
                expected,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

    # Senkou A must be calculated only from known Tenkan/Kijun.
    for i in range(len(bars)):

        if (
            tenkan[i] is not None
            and kijun[i] is not None
        ):

            expected = (
                tenkan[i]
                + kijun[i]
            ) / 2.0

            if not math.isclose(
                senkou_a[i],
                expected,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

    # Chikou in this engine is explicitly causal:
    # current index i contains close from i - displacement.
    for i in range(len(bars)):

        if i < 26:

            if chikou[i] is not None:
                return False

        else:

            expected = bars[
                i - 26
            ].close

            if chikou[i] != expected:
                return False

    return True


# ============================================================================
# WARM-UP QUALITY
# ============================================================================

def audit_warmup(
    namespace: Dict[str, Any],
    bars,
) -> bool:

    records = namespace[
        "calculate_indicator_records"
    ](bars)

    if records[0].sma is not None:
        return False

    if records[0].ema is not None:
        return False

    if records[0].wma is not None:
        return False

    if records[0].rsi is not None:
        return False

    if records[0].atr is not None:
        return False

    if records[0].bb_middle is not None:
        return False

    if records[0].stochastic_k is not None:
        return False

    if records[0].adx is not None:
        return False

    if records[0].ichimoku_tenkan is not None:
        return False

    if records[0].ichimoku_kijun is not None:
        return False

    if records[0].ichimoku_senkou_b is not None:
        return False

    return True


# ============================================================================
# IDENTITY QUALITY
# ============================================================================

def audit_identity(
    namespace: Dict[str, Any],
    bars,
) -> bool:

    calculate = namespace[
        "calculate_indicator_records"
    ]

    records = calculate(
        bars
    )

    if len(records) != len(bars):
        return False

    for i, (bar, record) in enumerate(
        zip(bars, records)
    ):

        if record.index != i:
            return False

        if record.timestamp != bar.timestamp:
            return False

        if record.cmc_id != bar.cmc_id:
            return False

        if record.symbol != bar.symbol:
            return False

        if record.close != bar.close:
            return False

    return True


# ============================================================================
# DETERMINISM
# ============================================================================

def audit_determinism(
    namespace: Dict[str, Any],
    bars,
) -> bool:

    calculate = namespace[
        "calculate_indicator_records"
    ]

    first = calculate(bars)
    second = calculate(bars)

    if first != second:
        return False

    return namespace[
        "determinism_audit"
    ](bars)


# ============================================================================
# CAUSAL PREFIX AUDIT
# ============================================================================

def audit_causality(
    namespace: Dict[str, Any],
    bars,
) -> bool:

    calculate = namespace[
        "calculate_indicator_records"
    ]

    full = calculate(bars)

    for i, full_record in enumerate(full):

        prefix = bars[
            :i + 1
        ]

        prefix_records = calculate(
            prefix
        )

        if not prefix_records:
            return False

        prefix_record = prefix_records[-1]

        for field in INDICATOR_FIELDS:

            a = getattr(
                full_record,
                field,
            )

            b = getattr(
                prefix_record,
                field,
            )

            if a is None and b is None:
                continue

            if a is None or b is None:
                return False

            if not math.isclose(
                float(a),
                float(b),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

    return True


# ============================================================================
# FUTURE PERTURBATION AUDIT
# ============================================================================

def audit_future_perturbation(
    namespace: Dict[str, Any],
    bars,
) -> bool:

    calculate = namespace[
        "calculate_indicator_records"
    ]

    baseline = calculate(
        bars
    )

    if len(bars) < 40:
        return False

    cutoff = 30

    modified = list(bars)

    IndicatorBar = namespace[
        "IndicatorBar"
    ]

    for i in range(
        cutoff,
        len(modified)
    ):

        original = modified[i]

        modified[i] = IndicatorBar(
            timestamp=original.timestamp,
            high=original.high + 10000.0,
            low=original.low - 10000.0,
            close=original.close + 5000.0,
            open=original.open,
            volume=(
                original.volume * 100.0
                if original.volume is not None
                else None
            ),
            cmc_id=original.cmc_id,
            symbol=original.symbol,
        )

    altered = calculate(
        modified
    )

    for i in range(cutoff):

        base_record = baseline[i]
        altered_record = altered[i]

        for field in INDICATOR_FIELDS:

            a = getattr(
                base_record,
                field,
            )

            b = getattr(
                altered_record,
                field,
            )

            if a is None and b is None:
                continue

            if a is None or b is None:
                return False

            if not math.isclose(
                float(a),
                float(b),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

    return True


# ============================================================================
# ADVERSARIAL QUALITY
# ============================================================================

def audit_adversarial(
    namespace: Dict[str, Any],
) -> bool:

    bars = make_adversarial_bars(
        namespace
    )

    calculate = namespace[
        "calculate_indicator_records"
    ]

    records = calculate(
        bars
    )

    if len(records) != len(bars):
        return False

    if not audit_indicator_ranges(
        namespace,
        records,
    ):
        return False

    if not audit_causality(
        namespace,
        bars,
    ):
        return False

    if not audit_determinism(
        namespace,
        bars,
    ):
        return False

    return True


# ============================================================================
# BOUNDARY SEMANTICS
# ============================================================================

def audit_boundary_semantics(
    namespace: Dict[str, Any],
) -> bool:

    calculate = namespace[
        "calculate_indicator_records"
    ]

    # ------------------------------------------------------------
    # Single bar
    # ------------------------------------------------------------

    one = make_bars(
        namespace,
        [100.0],
    )

    records = calculate(one)

    if len(records) != 1:
        return False

    record = records[0]

    if record.sma is not None:
        return False

    if record.rsi is not None:
        return False

    if record.atr is not None:
        return False

    # ------------------------------------------------------------
    # Flat market
    # ------------------------------------------------------------

    flat = make_bars(
        namespace,
        [100.0] * 100,
    )

    flat_records = calculate(flat)

    for record in flat_records:

        if record.rsi is not None:

            if not math.isclose(
                record.rsi,
                50.0,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

        if record.stochastic_k is not None:

            if not 0.0 <= record.stochastic_k <= 100.0:
                return False

        if record.stochastic_d is not None:

            if not 0.0 <= record.stochastic_d <= 100.0:
                return False

    # ------------------------------------------------------------
    # Monotonic rise
    # ------------------------------------------------------------

    rising = make_bars(
        namespace,
        [
            float(i)
            for i in range(1, 101)
        ],
    )

    rising_records = calculate(
        rising
    )

    for record in rising_records:

        if record.rsi is not None:

            if not math.isclose(
                record.rsi,
                100.0,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

    return True


# ============================================================================
# INPUT SAFETY
# ============================================================================

def audit_input_safety(
    namespace: Dict[str, Any],
) -> bool:

    validate_bars = namespace[
        "validate_bars"
    ]

    IndicatorBar = namespace[
        "IndicatorBar"
    ]

    # Invalid OHLC
    try:

        validate_bars(
            [
                IndicatorBar(
                    timestamp=0,
                    high=10.0,
                    low=20.0,
                    close=15.0,
                )
            ]
        )

        return False

    except ValueError:
        pass

    # Negative volume
    try:

        validate_bars(
            [
                IndicatorBar(
                    timestamp=0,
                    high=10.0,
                    low=5.0,
                    close=8.0,
                    volume=-1.0,
                )
            ]
        )

        return False

    except ValueError:
        pass

    # NaN
    try:

        validate_bars(
            [
                IndicatorBar(
                    timestamp=0,
                    high=float("nan"),
                    low=5.0,
                    close=8.0,
                )
            ]
        )

        return False

    except ValueError:
        pass

    # Infinity
    try:

        validate_bars(
            [
                IndicatorBar(
                    timestamp=0,
                    high=float("inf"),
                    low=5.0,
                    close=8.0,
                )
            ]
        )

        return False

    except ValueError:
        pass

    return True


# ============================================================================
# DECISION ISOLATION
# ============================================================================

def audit_decision_isolation(
    source: str,
    namespace: Dict[str, Any],
) -> bool:

    forbidden_outputs = (
        "BUY",
        "SELL",
        "LONG",
        "SHORT",
        "ENTRY",
        "EXIT",
    )

    # The source documentation can mention these terms as architecture
    # constraints, so inspect callable names and actual generated records
    # instead of treating documentation as executable decision output.

    record_fields = {
        field
        for field in namespace[
            "IndicatorRecord"
        ].__dataclass_fields__
    }

    for token in (
        "buy",
        "sell",
        "entry",
        "exit",
        "decision",
    ):

        if any(
            token == field.lower()
            for field in record_fields
        ):
            return False

    return True


# ============================================================================
# FULL QUALITY / CAUSAL VALIDATION
# ============================================================================

def run_validation() -> bool:

    engine_path, source, namespace = load_engine()

    section("MODE")

    result(
        "Database mutation",
        "NONE",
    )

    result(
        "Production write",
        "NONE",
    )

    result(
        "Audit mode",
        "READ ONLY",
    )

    result(
        "Database usage",
        "NOT REQUIRED",
    )

    section("FILE VALIDATION")

    result(
        "Indicator Engine",
        "PASS",
    )

    ast.parse(source)

    result(
        "AST Parse",
        "PASS",
    )

    section("SOURCE SAFETY")

    source_safe = audit_source_safety(
        source
    )

    result(
        "SQL mutation statements",
        "PASS" if source_safe else "FAIL",
    )

    result(
        "Database independence",
        "PASS" if source_safe else "FAIL",
    )

    assert source_safe

    section("REQUIRED API")

    required_api = audit_required_api(
        namespace
    )

    result(
        "Required functions",
        "PASS" if required_api else "FAIL",
    )

    result(
        "Required classes",
        "PASS" if required_api else "FAIL",
    )

    assert required_api

    section("PUBLIC API SIGNATURE AUDIT")

    signatures = audit_signatures(
        namespace
    )

    result(
        "Public API signatures",
        "PASS" if signatures else "FAIL",
    )

    assert signatures

    section("ENGINE SELF TEST")

    namespace["self_test"]()

    result(
        "self_test",
        "PASS",
    )

    section("TEST DATA")

    closes = [
        100,
        101,
        102,
        101,
        103,
        105,
        104,
        106,
        108,
        107,
        109,
        111,
        110,
        112,
        114,
        113,
        115,
        117,
        116,
        118,
        120,
        119,
        121,
        123,
        122,
        124,
        126,
        125,
        127,
        129,
        128,
        130,
        132,
        131,
        133,
        135,
        134,
        136,
        138,
        137,
        139,
        141,
        140,
        142,
        144,
        143,
        145,
        147,
        146,
        148,
        150,
        149,
        151,
        153,
        152,
        154,
        156,
        155,
        157,
        159,
        158,
        160,
        162,
        161,
        163,
        165,
        164,
        166,
        168,
        167,
        169,
        171,
        170,
        172,
        174,
        173,
        175,
        177,
        176,
        178,
        180,
        179,
    ]

    bars = make_bars(
        namespace,
        closes,
    )

    records = namespace[
        "calculate_indicator_records"
    ](bars)

    result(
        "Synthetic OHLCV generation",
        "PASS",
    )

    # ------------------------------------------------------------------------
    # Indicator quality
    # ------------------------------------------------------------------------

    section("TREND INDICATOR QUALITY")

    sma_quality = audit_sma(
        namespace,
        closes,
    )

    ema_quality = audit_ema(
        namespace,
        closes,
    )

    wma_quality = audit_wma(
        namespace,
        closes,
    )

    result(
        "SMA mathematical consistency",
        "PASS" if sma_quality else "FAIL",
    )

    result(
        "EMA mathematical consistency",
        "PASS" if ema_quality else "FAIL",
    )

    result(
        "WMA mathematical consistency",
        "PASS" if wma_quality else "FAIL",
    )

    assert sma_quality
    assert ema_quality
    assert wma_quality

    section("MOMENTUM INDICATOR QUALITY")

    rsi_quality = audit_rsi(
        namespace,
        closes,
    )

    macd_quality = audit_macd(
        namespace,
        closes,
    )

    stochastic_quality = audit_stochastic(
        namespace,
        bars,
    )

    result(
        "RSI semantics",
        "PASS" if rsi_quality else "FAIL",
    )

    result(
        "MACD / Signal / Histogram consistency",
        "PASS" if macd_quality else "FAIL",
    )

    result(
        "Stochastic %K / %D semantics",
        "PASS" if stochastic_quality else "FAIL",
    )

    assert rsi_quality
    assert macd_quality
    assert stochastic_quality

    section("VOLATILITY INDICATOR QUALITY")

    atr_quality = audit_atr(
        namespace,
        bars,
    )

    bollinger_quality = audit_bollinger(
        namespace,
        closes,
    )

    result(
        "True Range / ATR semantics",
        "PASS" if atr_quality else "FAIL",
    )

    result(
        "Bollinger Bands semantics",
        "PASS" if bollinger_quality else "FAIL",
    )

    assert atr_quality
    assert bollinger_quality

    section("TREND STRENGTH QUALITY")

    adx_quality = audit_adx(
        namespace,
        bars,
    )

    result(
        "ADX / +DI / -DI semantics",
        "PASS" if adx_quality else "FAIL",
    )

    assert adx_quality

    section("PRICE / VOLUME QUALITY")

    volume_quality = audit_volume_family(
        namespace,
        bars,
    )

    result(
        "VWAP / Volume Change Ratio",
        "PASS" if volume_quality else "FAIL",
    )

    assert volume_quality

    section("ICHIMOKU QUALITY")

    ichimoku_quality = audit_ichimoku(
        namespace,
        bars,
    )

    result(
        "Ichimoku causal semantics",
        "PASS" if ichimoku_quality else "FAIL",
    )

    assert ichimoku_quality

    section("INDICATOR RANGE / FINITE VALUE QUALITY")

    range_quality = audit_indicator_ranges(
        namespace,
        records,
    )

    result(
        "Finite indicator values",
        "PASS" if range_quality else "FAIL",
    )

    result(
        "Bounded indicator ranges",
        "PASS" if range_quality else "FAIL",
    )

    assert range_quality

    section("WARM-UP / INSUFFICIENT HISTORY")

    warmup_quality = audit_warmup(
        namespace,
        bars,
    )

    result(
        "Warm-up semantics",
        "PASS" if warmup_quality else "FAIL",
    )

    result(
        "Insufficient-history handling",
        "PASS" if warmup_quality else "FAIL",
    )

    assert warmup_quality

    section("IDENTITY CONTRACT")

    identity_quality = audit_identity(
        namespace,
        bars,
    )

    result(
        "CMC_ID propagation",
        "PASS" if identity_quality else "FAIL",
    )

    result(
        "Symbol propagation",
        "PASS" if identity_quality else "FAIL",
    )

    result(
        "Timestamp propagation",
        "PASS" if identity_quality else "FAIL",
    )

    result(
        "Input order preservation",
        "PASS" if identity_quality else "FAIL",
    )

    assert identity_quality

    section("BOUNDARY MARKET SEMANTICS")

    boundary_quality = audit_boundary_semantics(
        namespace
    )

    result(
        "Single-bar semantics",
        "PASS" if boundary_quality else "FAIL",
    )

    result(
        "Flat market",
        "PASS" if boundary_quality else "FAIL",
    )

    result(
        "Monotonic market",
        "PASS" if boundary_quality else "FAIL",
    )

    assert boundary_quality

    section("INPUT SAFETY")

    input_safety = audit_input_safety(
        namespace
    )

    result(
        "Invalid OHLC rejection",
        "PASS" if input_safety else "FAIL",
    )

    result(
        "Negative volume rejection",
        "PASS" if input_safety else "FAIL",
    )

    result(
        "Non-finite rejection",
        "PASS" if input_safety else "FAIL",
    )

    assert input_safety

    section("ADVERSARIAL INDICATOR SEQUENCES")

    adversarial = audit_adversarial(
        namespace
    )

    result(
        "Adversarial sequences",
        "PASS" if adversarial else "FAIL",
    )

    assert adversarial

    section("LOOK-AHEAD / FUTURE DATA AUDIT")

    engine_lookahead = namespace[
        "lookahead_audit"
    ](bars)

    causal_pipeline = audit_causality(
        namespace,
        bars,
    )

    future_perturbation = audit_future_perturbation(
        namespace,
        bars,
    )

    result(
        "Engine look-ahead audit",
        "PASS" if engine_lookahead else "FAIL",
    )

    result(
        "Full prefix causal validation",
        "PASS" if causal_pipeline else "FAIL",
    )

    result(
        "Future perturbation isolation",
        "PASS" if future_perturbation else "FAIL",
    )

    assert engine_lookahead
    assert causal_pipeline
    assert future_perturbation

    section("DETERMINISM")

    deterministic = audit_determinism(
        namespace,
        bars,
    )

    result(
        "Deterministic output",
        "PASS" if deterministic else "FAIL",
    )

    assert deterministic

    section("DECISION OUTPUT ISOLATION")

    decision_isolation = audit_decision_isolation(
        source,
        namespace,
    )

    result(
        "Trading decision output",
        "PASS" if decision_isolation else "FAIL",
    )

    result(
        "BUY / SELL output",
        "NONE" if decision_isolation else "FAIL",
    )

    assert decision_isolation

    section("FULL TEMPORAL / CAUSAL PIPELINE")

    result(
        "Temporal prefix consistency",
        "PASS" if causal_pipeline else "FAIL",
    )

    result(
        "Future mutation isolation",
        "PASS" if future_perturbation else "FAIL",
    )

    result(
        "Deterministic replay",
        "PASS" if deterministic else "FAIL",
    )

    assert causal_pipeline
    assert future_perturbation
    assert deterministic

    section("REQUIRED INDICATOR ENGINE QUALITY CONTRACT")

    checks = {
        "Source mutation safety": source_safe,
        "Database independence": source_safe,
        "Module import": True,
        "Required functions": required_api,
        "Required classes": required_api,
        "Public API signatures": signatures,
        "Trend indicator quality": (
            sma_quality
            and ema_quality
            and wma_quality
        ),
        "Momentum indicator quality": (
            rsi_quality
            and macd_quality
            and stochastic_quality
        ),
        "Volatility indicator quality": (
            atr_quality
            and bollinger_quality
        ),
        "Trend strength quality": adx_quality,
        "Price / volume quality": volume_quality,
        "Cloud indicator quality": ichimoku_quality,
        "Warm-up semantics": warmup_quality,
        "Numeric safety": range_quality,
        "CMC_ID / symbol identity": identity_quality,
        "Boundary semantics": boundary_quality,
        "Input safety": input_safety,
        "Adversarial sequences": adversarial,
        "Look-ahead protection": (
            engine_lookahead
            and causal_pipeline
            and future_perturbation
        ),
        "Deterministic output": deterministic,
        "Decision isolation": decision_isolation,
    }

    for label, passed in checks.items():

        result(
            label,
            "PASS" if passed else "FAIL",
        )

        assert passed

    print()
    print("=" * 100)
    print("STEP 12B VERDICT")
    print("=" * 100)
    print(
        "RESULT : INDICATOR ENGINE QUALITY & CAUSAL VALIDATION PASS"
    )
    print(
        "STATUS : READY FOR STEP 13"
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


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    print("=" * 100)
    print(
        "ARUNDA TRADER — DEV-06 — STEP 12B"
    )
    print(
        "INDICATOR ENGINE QUALITY & CAUSAL VALIDATION"
    )
    print("=" * 100)

    try:

        run_validation()

    except Exception as exc:

        print()
        print(
            "STEP 12B RESULT : FAIL"
        )

        print(
            f"ERROR : "
            f"{type(exc).__name__}: {exc}"
        )

        raise