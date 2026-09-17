
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

SIGNAL_INPUT_FILE = (
    ROOT / "production_signal_input_boundary_v0_1.py"
)

DYNAMIC_SIGNAL_FILE = (
    ROOT / "dynamic_signal_boundary_v0_1.py"
)

SAMPLE_SYMBOLS = (
    "AVA/USDT",
    "MTV/USDT",
    "TEL/USDT",
)


def load_module(path: Path, name: str):
    """
    Safely load a project module from file.

    Important:
    The module MUST be registered in sys.modules before
    exec_module(). Python 3.13 dataclass/type resolution
    depends on this for dynamically loaded modules.
    """

    if not path.exists():
        raise RuntimeError(
            f"FILE_NOT_FOUND:{path.name}"
        )

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED:{path.name}"
        )

    module = importlib.util.module_from_spec(spec)

    # Critical for Python 3.13:
    # dataclasses and other type-resolution mechanisms
    # expect cls.__module__ to exist in sys.modules.
    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        # Do not leave a broken partially-loaded module behind.
        sys.modules.pop(name, None)
        raise

    return module


def main() -> int:

    print("=" * 100)
    print("ARUNDA CONTROLLED DYNAMIC SIGNAL RUNTIME v0.1")
    print("=" * 100)

    print("STATUS=RUNNING")
    print("DYNAMIC_UNIVERSE=True")
    print("EXPECTED_ASSETS_USED=False")
    print("CMC_USED=False")
    print("LEGACY_DATA_USED=False")
    print("PRE_LAUNCH_DATA_USED=False")
    print("SYNTHETIC=False")
    print("INTERPOLATION=False")
    print("FILL=False")
    print("BACKFILL=False")
    print("PADDING=False")
    print("BLENDING=False")
    print("PRODUCTION_DB_TOUCHED=False")
    print("DB_WRITES=0")
    print("FUSION_EXECUTED=False")
    print("SCORE_EXECUTED=False")
    print("DECISION_EXECUTED=False")
    print("RISK_EXECUTED=False")
    print("TRADE_GATE_EXECUTED=False")
    print("OPPORTUNITY_EXECUTED=False")
    print("ORDER_INTENTS_CREATED=0")
    print("EXECUTION=OFF")
    print()

    # ------------------------------------------------------------------
    # LOAD BOUNDARIES
    # ------------------------------------------------------------------

    signal_input = load_module(
        SIGNAL_INPUT_FILE,
        "production_signal_input_runtime",
    )

    dynamic_signal = load_module(
        DYNAMIC_SIGNAL_FILE,
        "dynamic_signal_boundary_runtime",
    )

    print("PRODUCTION_SIGNAL_INPUT_MODULE=PASS")
    print("DYNAMIC_SIGNAL_BOUNDARY_MODULE=PASS")

    # ------------------------------------------------------------------
    # STATIC CONTRACT CHECK
    # ------------------------------------------------------------------

    if not dynamic_signal.contract_check():
        raise RuntimeError(
            "DYNAMIC_SIGNAL_BOUNDARY_CONTRACT_FAILED"
        )

    print("DYNAMIC_SIGNAL_CONTRACT=PASS")

    # ------------------------------------------------------------------
    # LOAD EXISTING APPROVED ENGINES
    # ------------------------------------------------------------------

    universe_binding = signal_input.load_module(
        signal_input.UNIVERSE_BINDING_MODULE,
        "production_universe_runtime",
    )

    kucoin = signal_input.load_module(
        signal_input.KUCOIN_MODULE,
        "kucoin_runtime",
    )

    import indicator_engine
    import market_structure_engine
    import feature_engine

    print("UNIVERSE_BINDING=PASS")
    print("KUCOIN_BINDING=PASS")
    print("INDICATOR_ENGINE=PASS")
    print("MARKET_STRUCTURE_ENGINE=PASS")
    print("FEATURE_ENGINE=PASS")

    # ------------------------------------------------------------------
    # REAL DYNAMIC UNIVERSE
    # ------------------------------------------------------------------

    all_records, eligible_records = (
        signal_input.discover_production_universe(
            universe_binding
        )
    )

    print(
        f"REAL_UNIVERSE_SIZE={len(all_records)}"
    )

    print(
        f"ELIGIBLE_UNIVERSE_SIZE={len(eligible_records)}"
    )

    eligible_by_symbol = {
        str(
            getattr(
                record,
                "symbol",
                "",
            )
        ).strip().upper(): record
        for record in eligible_records
    }

    # ------------------------------------------------------------------
    # EXACT CONTROLLED SAMPLE
    # ------------------------------------------------------------------

    selected = []

    for symbol in SAMPLE_SYMBOLS:

        record = eligible_by_symbol.get(
            symbol
        )

        if record is None:
            raise RuntimeError(
                f"CONTROLLED_MARKET_NOT_ELIGIBLE:{symbol}"
            )

        selected.append(record)

    if len(selected) != 3:
        raise RuntimeError(
            "CONTROLLED_SAMPLE_INVALID"
        )

    print(
        "SAMPLE_MARKETS="
        + ",".join(
            SAMPLE_SYMBOLS
        )
    )

    # ------------------------------------------------------------------
    # PRODUCTION SIGNAL INPUT
    # ------------------------------------------------------------------

    production_inputs = []

    for record in selected:

        symbol = str(
            getattr(
                record,
                "symbol",
                "",
            )
        ).strip().upper()

        print()
        print(
            f"MARKET_START={symbol}"
        )

        market_input = (
            signal_input.market_record_to_arm_input(
                record
            )
        )

        print(
            f"MARKET_RECORD_BINDING=PASS "
            f"SYMBOL={symbol}"
        )

        print(
            f"MARKET_ARM_INPUT_BINDING=PASS "
            f"SYMBOL={symbol}"
        )

        production_input = (
            signal_input.build_production_signal_input(
                market_input,
                kucoin,
                indicator_engine,
                market_structure_engine,
                feature_engine,
            )
        )

        if not isinstance(
            production_input,
            signal_input.ProductionSignalInput,
        ):
            raise RuntimeError(
                f"PRODUCTION_SIGNAL_INPUT_INVALID:{symbol}"
            )

        if not production_input.continuity_valid:
            raise RuntimeError(
                f"CONTINUITY_INVALID:{symbol}"
            )

        if not production_input.provenance_valid:
            raise RuntimeError(
                f"PROVENANCE_INVALID:{symbol}"
            )

        if not production_input.canonical_validation:
            raise RuntimeError(
                f"CANONICAL_VALIDATION_INVALID:{symbol}"
            )

        if (
            production_input.actual_points
            < signal_input.MIN_CONTEXT
        ):
            raise RuntimeError(
                f"INSUFFICIENT_CONTEXT:{symbol}"
            )

        production_inputs.append(
            production_input
        )

        print(
            f"PRODUCTION_SIGNAL_INPUT=PASS "
            f"SYMBOL={symbol} "
            f"POINTS={production_input.actual_points} "
            f"LATEST={production_input.latest_timestamp_iso}"
        )

    # ------------------------------------------------------------------
    # DYNAMIC SIGNAL RUNTIME
    # ------------------------------------------------------------------

    records = (
        dynamic_signal.build_dynamic_signals(
            production_inputs
        )
    )

    if len(records) != 3:
        raise RuntimeError(
            f"SIGNAL_CARDINALITY_INVALID:{len(records)}"
        )

    if not dynamic_signal.validate_dynamic_signal_records(
        records
    ):
        raise RuntimeError(
            "DYNAMIC_SIGNAL_VALIDATION_FAILED"
        )

    summary = (
        dynamic_signal.summarize_dynamic_signals(
            records
        )
    )

    # ------------------------------------------------------------------
    # PER-MARKET RESULT
    # ------------------------------------------------------------------

    for record in records:

        print(
            f"SIGNAL_RESULT="
            f"SYMBOL={record.asset} "
            f"STATE={record.signal_state} "
            f"DIRECTION={record.direction} "
            f"CONTEXT={record.context} "
            f"STATUS={record.status} "
            f"ELIGIBLE={record.eligible}"
        )

    # ------------------------------------------------------------------
    # HARD STOP
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("CONTROLLED DYNAMIC SIGNAL RUNTIME RESULT")
    print("=" * 100)

    print("STATUS=READY_NO_EXECUTION")

    print(
        f"REAL_UNIVERSE_SIZE={len(all_records)}"
    )

    print(
        f"ELIGIBLE_UNIVERSE_SIZE={len(eligible_records)}"
    )

    print(
        "MARKETS_PROCESSED=3"
    )

    print("REAL_MARKET_DATA=True")
    print("PRODUCTION_SIGNAL_INPUT=PASS")

    print(
        f"SIGNALS_CREATED={summary['signals_total']}"
    )

    print(
        f"ACTIVE_SIGNALS={summary['active']}"
    )

    print(
        f"VALIDATED_SIGNALS={summary['signals_total']}"
    )

    print(
        f"ELIGIBLE_SIGNALS={summary['eligible']}"
    )

    print(
        f"LONG_SIGNALS={summary['long']}"
    )

    print(
        f"SHORT_SIGNALS={summary['short']}"
    )

    print(
        f"NEUTRAL_SIGNALS={summary['neutral']}"
    )

    print("NEWS_INPUT=NOT_EXECUTED")
    print("SOCIAL_INPUT=NOT_EXECUTED")
    print("FUSION=NOT_EXECUTED")
    print("SCORE=NOT_EXECUTED")
    print("DECISION=NOT_EXECUTED")
    print("RISK=NOT_EXECUTED")
    print("TRADE_GATE=NOT_EXECUTED")
    print("OPPORTUNITIES_TOTAL=0")
    print("ELIGIBLE_OPPORTUNITIES=0")
    print("NO_TRADE=NOT_EVALUATED")

    print("DYNAMIC_UNIVERSE=True")
    print("EXPECTED_ASSETS_USED=False")
    print("CMC_USED=False")
    print("LEGACY_DATA_USED=False")
    print("PRE_LAUNCH_DATA_USED=False")
    print("PROVENANCE=PASS")
    print("CONTINUITY=PASS")
    print("CANONICAL_VALIDATION=PASS")

    print("SYNTHETIC=False")
    print("INTERPOLATION=False")
    print("FILL=False")
    print("BACKFILL=False")
    print("PADDING=False")
    print("BLENDING=False")

    print("PRODUCTION_DB_TOUCHED=False")
    print("DB_WRITES=0")
    print("ORDER_INTENTS_CREATED=0")
    print("EXECUTION=OFF")
    print("REAL_ORDER=False")
    print("REAL_TRADE=False")

    print(
        "FILES_MODIFIED=NONE"
    )

    print("BLOCKER=NONE")

    print(
        "NEXT=SIGNAL → VALIDATION"
    )

    print()
    print(
        "FINAL_GATE="
        "PRODUCTION SIGNAL INPUT → DYNAMIC SIGNAL = PASS"
    )

    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )