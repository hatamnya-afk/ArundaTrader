# =============================================================================
# ARUNDA PRODUCTION SIGNAL ENGINE + FUSION BINDING v0.3
#
# ARCHITECTURE:
#
# MARKET ARM
#     |
#     v
# EXISTING SIGNAL ENGINE v0.8
#     |
#     v
# EXISTING SIGNAL VALIDATOR v0.4
#     |
#     |
# NEWS ARM --------\
#                   > INTELLIGENCE INPUT
# SOCIAL ARM ------/
#                   |
#                   v
#              FUSION ENGINE v0.6
#                   |
#                   v
#             PRODUCTION FUSION
#
# READ ONLY
# MEMORY ONLY
# NO PRODUCTION DB
# NO DATABASE WRITE
# NO LEGACY MARKET_TECHNICAL
# NO SYNTHETIC DATA
# NO INTERPOLATION
# NO FILL
# NO BACKFILL
# NO PADDING
# SCORE OFF
# DECISION OFF
# ORDER INTENT OFF
# EXECUTION OFF
# =============================================================================

from pathlib import Path
import sqlite3
import importlib
import math


# =============================================================================
# PROJECT
# =============================================================================

PROJECT_ROOT = Path(
    r"C:\Users\ASUS\ArundaTrader"
)

FABRIC_DB = (
    PROJECT_ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

LAUNCH_TIMESTAMP = (
    "2026-08-31T00:00:00+00:00"
)

TIMEFRAME = "1h"
MIN_CONTEXT = 21


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


# =============================================================================
# EXISTING MODULES
# =============================================================================

signal_engine = importlib.import_module(
    "signal_engine"
)

signal_validator = importlib.import_module(
    "signal_validator"
)

adapter = importlib.import_module(
    "rolling_context_adapter_v0_1"
)

news_arm = importlib.import_module(
    "news_arm_v0_1"
)

social_arm = importlib.import_module(
    "social_arm_v0_1"
)

information_contract = importlib.import_module(
    "information_contract_v0_1"
)

fusion_engine = importlib.import_module(
    "fusion_engine"
)


# =============================================================================
# LAUNCH BOUNDARY
# =============================================================================

def launch_epoch():

    from datetime import datetime

    return int(
        datetime.fromisoformat(
            LAUNCH_TIMESTAMP
        ).timestamp()
    )


LAUNCH_EPOCH = launch_epoch()


# =============================================================================
# FABRIC READ
# =============================================================================

def load_fabric_rows():

    if not FABRIC_DB.exists():

        raise RuntimeError(
            "Fabric DB not found: "
            + str(FABRIC_DB)
        )

    conn = sqlite3.connect(
        str(FABRIC_DB)
    )

    conn.row_factory = sqlite3.Row

    try:

        return conn.execute(
            """
            SELECT
                asset,
                symbol,
                timestamp,
                timeframe,
                open,
                high,
                low,
                close,
                volume,
                source_id,
                source_type,
                source_timestamp,
                retrieved_at
            FROM canonical_ohlcv
            WHERE timeframe = ?
              AND timestamp IS NOT NULL
              AND timestamp > 0
              AND timestamp >= ?
            ORDER BY
                asset,
                symbol,
                source_id,
                timestamp
            """,
            (
                TIMEFRAME,
                LAUNCH_EPOCH,
            ),
        ).fetchall()

    finally:

        conn.close()


# =============================================================================
# MARKET IDENTITY
# =============================================================================

def market_key(row):

    return (
        str(
            row["asset"]
        ).upper(),

        str(
            row["symbol"]
        ),

        str(
            row["source_id"]
        ),

        str(
            row["timeframe"]
        ),
    )


def group_markets(rows):

    grouped = {}

    for row in rows:

        asset = str(
            row["asset"]
        ).upper()

        if asset not in EXPECTED_ASSETS:
            continue

        key = market_key(
            row
        )

        grouped.setdefault(
            key,
            []
        ).append(row)

    return grouped


# =============================================================================
# CONTIGUOUS RUN
# =============================================================================

def current_contiguous_run(rows):

    ordered = sorted(
        rows,
        key=lambda r: int(
            r["timestamp"]
        ),
    )

    if not ordered:
        return []

    run = [
        ordered[-1]
    ]

    for index in range(
        len(ordered) - 1,
        0,
        -1,
    ):

        newer = int(
            ordered[index]["timestamp"]
        )

        older = int(
            ordered[index - 1]["timestamp"]
        )

        if newer - older != 3600:
            break

        run.append(
            ordered[index - 1]
        )

    run.reverse()

    return run


# =============================================================================
# PROVENANCE
# =============================================================================

def validate_production_rows(rows):

    for row in rows:

        if row["timeframe"] != TIMEFRAME:
            return False

        if not row["source_id"]:
            return False

        if not row["source_type"]:
            return False

        if not row["source_timestamp"]:
            return False

        if int(
            row["timestamp"]
        ) < LAUNCH_EPOCH:
            return False

        if int(
            row["timestamp"]
        ) <= 0:
            return False

    return True


# =============================================================================
# MARKET BARS
# =============================================================================

def build_market_bars(rows):

    return [
        adapter.row_to_market_bar(
            row
        )
        for row in rows
    ]


# =============================================================================
# FEATURE PIPELINE
# =============================================================================

def build_feature_record(
    asset,
    rows,
):

    if len(rows) < MIN_CONTEXT:
        return None

    market_bars = build_market_bars(
        rows
    )

    indicator_bars = [
        adapter.market_bar_to_indicator_bar(
            bar
        )
        for bar in market_bars
    ]

    indicators = (
        adapter.calculate_indicator_records(
            indicator_bars
        )
    )

    structure_result = (
        adapter.analyze_market_structure(
            market_bars
        )
    )

    structures = (
        adapter.align_structure_points(
            market_bars,
            structure_result
        )
    )

    feature_bars = [
        adapter.market_bar_to_feature_bar(
            bar
        )
        for bar in market_bars
    ]

    features = (
        adapter.calculate_feature_records(
            feature_bars,
            indicators,
            structures,
        )
    )

    if not features:
        return None

    return features[-1]


# =============================================================================
# FEATURE RECORD -> EXISTING SIGNAL INPUT
# =============================================================================

def feature_record_to_signal_input(
    asset,
    record,
    points,
):

    if record is None:

        raise RuntimeError(
            "Missing FeatureRecord: "
            + asset
        )

    def get(name):

        value = getattr(
            record,
            name,
            None,
        )

        if isinstance(
            value,
            float,
        ):

            if not math.isfinite(
                value
            ):
                return None

        return value

    return {

        "asset":
            asset,

        "points":
            int(points),

        "structure_direction":
            get(
                "structure_direction"
            ),

        "structure_strength":
            get(
                "structure_strength"
            ),

        "structure_confidence":
            get(
                "structure_confidence"
            ),

        "structure_point_type":
            get(
                "structure_point_type"
            ),

        "trend":
            None,

        "momentum":
            None,

        "acceleration":
            None,

        "position":
            None,

        "volatility":
            get(
                "volatility_regime"
            ),
    }


# =============================================================================
# NEWS ARM
# =============================================================================

def load_news():

    result = news_arm.run()

    if not isinstance(
        result,
        dict,
    ):

        raise RuntimeError(
            "NEWS_ARM_RUNTIME_INVALID"
        )

    items = result.get(
        "items",
        [],
    )

    if not isinstance(
        items,
        list,
    ):

        raise RuntimeError(
            "NEWS_ARM_ITEMS_INVALID"
        )

    valid = []

    for item in items:

        if information_contract.validate_news(
            item
        ):

            valid.append(
                item
            )

    return {

        "items":
            valid,

        "count":
            len(valid),

        "invalid":
            len(items) - len(valid),
    }


# =============================================================================
# SOCIAL ARM
# =============================================================================

def load_social():

    result = social_arm.run()

    if not isinstance(
        result,
        dict,
    ):

        raise RuntimeError(
            "SOCIAL_ARM_RUNTIME_INVALID"
        )

    items = result.get(
        "items",
        [],
    )

    if not isinstance(
        items,
        list,
    ):

        raise RuntimeError(
            "SOCIAL_ARM_ITEMS_INVALID"
        )

    valid = []

    for item in items:

        if information_contract.validate_social(
            item
        ):

            valid.append(
                item
            )

    return {

        "items":
            valid,

        "count":
            len(valid),

        "invalid":
            len(items) - len(valid),
    }


# =============================================================================
# ASSET INTELLIGENCE
# =============================================================================

def intelligence_for_asset(
    asset,
    news_items,
    social_items,
):

    news = [
        item
        for item in news_items
        if str(
            item.get(
                "asset",
                "",
            )
        ).upper() == asset
    ]

    social = [
        item
        for item in social_items
        if str(
            item.get(
                "asset",
                "",
            )
        ).upper() == asset
    ]

    return {

        "asset":
            asset,

        "market_available":
            False,

        "news_available":
            len(news) > 0,

        "social_available":
            len(social) > 0,

        "news_signals":
            news,

        "social_signals":
            social,
    }


# =============================================================================
# MARKET SIGNAL
# =============================================================================

def process_market(
    asset,
    rows,
):

    result = {

        "asset":
            asset,

        "input_ready":
            False,

        "signal":
            None,

        "valid":
            False,

        "validation":
            None,

        "context_violation":
            False,

        "provenance_valid":
            False,

        "continuity_valid":
            False,

        "market_points":
            0,
    }

    if not rows:

        result["validation"] = (
            "NO_ROWS"
        )

        return result

    if not validate_production_rows(
        rows
    ):

        result["validation"] = (
            "PROVENANCE_INVALID"
        )

        return result

    run = current_contiguous_run(
        rows
    )

    result["market_points"] = (
        len(run)
    )

    if len(run) < MIN_CONTEXT:

        result["validation"] = (
            "INSUFFICIENT_CURRENT_RUN"
        )

        return result

    result["input_ready"] = True
    result["provenance_valid"] = True
    result["continuity_valid"] = True

    feature_record = build_feature_record(
        asset,
        run,
    )

    if feature_record is None:

        result["validation"] = (
            "FEATURE_RECORD_UNAVAILABLE"
        )

        return result

    signal_input = (
        feature_record_to_signal_input(
            asset,
            feature_record,
            len(run),
        )
    )

    # -------------------------------------------------------------------------
    # EXISTING SIGNAL ENGINE v0.8
    # -------------------------------------------------------------------------

    engine_record = (
        signal_engine.build_signal(
            asset,
            signal_input,
        )
    )

    if not isinstance(
        engine_record,
        dict,
    ):

        result["validation"] = (
            "ENGINE_RECORD_INVALID"
        )

        return result

    signal = engine_record.get(
        "signal"
    )

    if not isinstance(
        signal,
        dict,
    ):

        result["validation"] = (
            "SIGNAL_OBJECT_INVALID"
        )

        return result

    # -------------------------------------------------------------------------
    # EXISTING SIGNAL VALIDATOR v0.4
    # -------------------------------------------------------------------------

    valid, reason = (
        signal_validator.validate_one_signal(
            asset,
            signal,
        )
    )

    result["signal"] = signal
    result["valid"] = bool(valid)
    result["validation"] = reason

    return result


# =============================================================================
# MARKET SIGNAL -> FUSION INPUT
# =============================================================================

def build_fusion_market_signals(
    results,
):

    market_signals = {}

    for asset in EXPECTED_ASSETS:

        market_result = results[
            asset
        ]["market"]

        signal = market_result.get(
            "signal"
        )

        if not isinstance(
            signal,
            dict,
        ):

            continue

        if not market_result.get(
            "valid"
        ):

            continue

        # ---------------------------------------------------------------------
        # Preserve the exact existing Signal Engine output.
        #
        # Fusion v0.6 is responsible for interpreting:
        #
        # LONG  -> positive market direction
        # SHORT -> negative market direction
        # NONE/FLAT/NEUTRAL -> neutral
        #
        # No synthetic market score is generated here.
        # ---------------------------------------------------------------------

        market_signals[
            asset
        ] = dict(signal)

    return market_signals


# =============================================================================
# FUSION
# =============================================================================

def run_fusion(
    results,
    news_items,
    social_items,
):

    market_signals = (
        build_fusion_market_signals(
            results
        )
    )

    # -------------------------------------------------------------------------
    # REAL PRODUCTION ARMS -> FUSION v0.6
    # -------------------------------------------------------------------------

    fusion_output = (
        fusion_engine.run(
            market_signals=market_signals,
            news_items=news_items,
            social_items=social_items,
        )
    )

    if not isinstance(
        fusion_output,
        dict,
    ):

        raise RuntimeError(
            "FUSION_RUNTIME_OUTPUT_INVALID"
        )

    if fusion_output.get(
        "engine_version"
    ) != "FUSION_v0.6":

        raise RuntimeError(
            "FUSION_ENGINE_VERSION_MISMATCH"
        )

    if fusion_output.get(
        "db_writes"
    ) != 0:

        raise RuntimeError(
            "FUSION_DB_WRITE_VIOLATION"
        )

    if fusion_output.get(
        "legacy_used"
    ) is not False:

        raise RuntimeError(
            "FUSION_LEGACY_USAGE_VIOLATION"
        )

    if fusion_output.get(
        "production_only"
    ) is not True:

        raise RuntimeError(
            "FUSION_PRODUCTION_BOUNDARY_VIOLATION"
        )

    return fusion_output


# =============================================================================
# FUSION VALIDATION
# =============================================================================

def validate_fusion_output(
    fusion_output,
):

    results = fusion_output.get(
        "results",
        []
    )

    if not isinstance(
        results,
        list,
    ):

        return False, (
            "FUSION_RESULTS_INVALID"
        )

    if len(results) != len(
        EXPECTED_ASSETS
    ):

        return False, (
            "FUSION_ASSET_COUNT_INVALID"
        )

    seen = set()

    for result in results:

        if not isinstance(
            result,
            dict,
        ):

            return False, (
                "FUSION_RESULT_NOT_DICT"
            )

        asset = str(
            result.get(
                "asset",
                "",
            )
        ).upper()

        if asset not in EXPECTED_ASSETS:

            return False, (
                "FUSION_UNKNOWN_ASSET"
            )

        if asset in seen:

            return False, (
                "FUSION_DUPLICATE_ASSET"
            )

        seen.add(
            asset
        )

        if result.get(
            "engine_version"
        ) != "FUSION_v0.6":

            return False, (
                "FUSION_ENGINE_VERSION_INVALID"
            )

        if result.get(
            "contract_version"
        ) != "INFORMATION_CONTRACT_v0.1":

            return False, (
                "FUSION_CONTRACT_VERSION_INVALID"
            )

        if result.get(
            "provenance_valid"
        ) is not True:

            return False, (
                "FUSION_PROVENANCE_INVALID"
            )

    if seen != set(
        EXPECTED_ASSETS
    ):

        return False, (
            "FUSION_ASSET_SET_INVALID"
        )

    return True, "FUSION_VALID"


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 94)

    print(
        "ARUNDA PRODUCTION SIGNAL ENGINE + FUSION BINDING v0.3"
    )

    print("=" * 94)

    print(
        "LAUNCH_TIMESTAMP        :",
        LAUNCH_TIMESTAMP
    )

    print(
        "TIMEFRAME               :",
        TIMEFRAME
    )

    print(
        "MIN_CONTEXT             :",
        MIN_CONTEXT
    )

    print(
        "MARKET_ARM              : ACTIVE"
    )

    print(
        "SIGNAL_ENGINE           : EXISTING v0.8"
    )

    print(
        "SIGNAL_VALIDATOR        : EXISTING v0.4"
    )

    print(
        "NEWS_ARM                : ACTIVE"
    )

    print(
        "SOCIAL_ARM              : ACTIVE"
    )

    print(
        "FUSION_ENGINE           : v0.6"
    )

    print(
        "LEGACY_MARKET_TECHNICAL : FORBIDDEN"
    )

    print(
        "CMC_SNAPSHOT            : FORBIDDEN"
    )

    print(
        "COINALYZE               : FORBIDDEN"
    )

    print(
        "PRODUCTION DB           : NOT TOUCHED"
    )

    print(
        "FUSION                  : ACTIVE"
    )

    print(
        "SCORE                   : OFF"
    )

    print(
        "DECISION                : OFF"
    )

    print(
        "ORDER INTENTS           : 0"
    )

    print(
        "EXECUTION               : OFF"
    )

    print()

    # =========================================================================
    # REAL MARKET DATA
    # =========================================================================

    rows = load_fabric_rows()

    grouped = group_markets(
        rows
    )

    # =========================================================================
    # REAL NEWS
    # =========================================================================

    news_runtime = load_news()

    news_items = news_runtime[
        "items"
    ]

    # =========================================================================
    # REAL SOCIAL
    # =========================================================================

    social_runtime = load_social()

    social_items = social_runtime[
        "items"
    ]

    # =========================================================================
    # MARKET + INTELLIGENCE
    # =========================================================================

    results = {}

    for asset in EXPECTED_ASSETS:

        candidates = []

        for key, market_rows in (
            grouped.items()
        ):

            if key[0] != asset:
                continue

            source_id = str(
                key[2]
            )

            if not source_id.startswith(
                "KUCOIN"
            ):

                continue

            candidates.append(
                (
                    key,
                    market_rows,
                )
            )

        if not candidates:

            market_result = {

                "asset":
                    asset,

                "input_ready":
                    False,

                "valid":
                    False,

                "validation":
                    "NO_PRODUCTION_MARKET",

                "signal":
                    None,

                "provenance_valid":
                    False,

                "continuity_valid":
                    False,

                "context_violation":
                    False,

                "market_points":
                    0,
            }

        else:

            candidates.sort(
                key=lambda item:
                    len(item[1]),
                reverse=True,
            )

            selected_key, selected_rows = (
                candidates[0]
            )

            _ = selected_key

            market_result = (
                process_market(
                    asset,
                    selected_rows,
                )
            )

        intelligence = (
            intelligence_for_asset(
                asset,
                news_items,
                social_items,
            )
        )

        intelligence[
            "market_available"
        ] = (
            market_result.get(
                "signal"
            ) is not None
        )

        results[
            asset
        ] = {

            "market":
                market_result,

            "intelligence":
                intelligence,
        }

    # =========================================================================
    # MARKET COUNTS
    # =========================================================================

    market_signals = sum(
        1
        for item in results.values()
        if item["market"].get(
            "signal"
        ) is not None
    )

    validated_signals = sum(
        1
        for item in results.values()
        if item["market"].get(
            "valid"
        ) is True
    )

    market_ready = sum(
        1
        for item in results.values()
        if item["market"].get(
            "input_ready"
        ) is True
    )

    # =========================================================================
    # INFORMATION COUNTS
    # =========================================================================

    news_assets = sum(
        1
        for item in results.values()
        if item["intelligence"].get(
            "news_available"
        )
    )

    social_assets = sum(
        1
        for item in results.values()
        if item["intelligence"].get(
            "social_available"
        )
    )

    # =========================================================================
    # MARKET PROVENANCE / CONTINUITY
    # =========================================================================

    provenance_valid = (
        market_ready == len(
            EXPECTED_ASSETS
        )
        and all(
            item["market"].get(
                "provenance_valid"
            )
            for item in results.values()
            if item["market"].get(
                "input_ready"
            )
        )
    )

    continuity_valid = (
        market_ready == len(
            EXPECTED_ASSETS
        )
        and all(
            item["market"].get(
                "continuity_valid"
            )
            for item in results.values()
            if item["market"].get(
                "input_ready"
            )
        )
    )

    # =========================================================================
    # LEGACY
    # =========================================================================

    legacy_data_used = False

    # =========================================================================
    # INFORMATION CONTRACT
    # =========================================================================

    contract_valid = (
        news_runtime[
            "invalid"
        ] == 0

        and social_runtime[
            "invalid"
        ] == 0
    )

    # =========================================================================
    # FUSION
    # =========================================================================

    fusion_output = None

    fusion_valid = False

    fusion_validation = (
        "NOT_RUN"
    )

    fusion_runtime_error = None

    try:

        fusion_output = run_fusion(
            results,
            news_items,
            social_items,
        )

        (
            fusion_valid,
            fusion_validation,
        ) = validate_fusion_output(
            fusion_output
        )

    except Exception as exc:

        fusion_runtime_error = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    # =========================================================================
    # FUSION COUNTS
    # =========================================================================

    fusion_results = []

    if isinstance(
        fusion_output,
        dict,
    ):

        fusion_results = fusion_output.get(
            "results",
            []
        )

    fusion_outputs = len(
        fusion_results
    )

    fusion_available = sum(
        1
        for item in fusion_results
        if item.get(
            "fused_score"
        ) is not None
    )

    fusion_validated = sum(
        1
        for item in fusion_results
        if item.get(
            "provenance_valid"
        ) is True
    )

    # =========================================================================
    # FINAL BINDING PASS
    # =========================================================================

    binding_pass = (

        # Existing production signal path
        market_ready
        == len(EXPECTED_ASSETS)

        and market_signals
        == len(EXPECTED_ASSETS)

        and validated_signals
        == len(EXPECTED_ASSETS)

        # Market production guarantees
        and provenance_valid
        and continuity_valid

        # Information contracts
        and contract_valid

        # No legacy
        and not legacy_data_used

        # Fusion
        and fusion_outputs
        == len(EXPECTED_ASSETS)

        and fusion_validated
        == len(EXPECTED_ASSETS)

        and fusion_valid

        # Hard runtime boundaries
        and (
            fusion_output is not None
        )

        and (
            fusion_output.get(
                "db_writes"
            ) == 0
        )

        and (
            fusion_output.get(
                "production_only"
            ) is True
        )

        and (
            fusion_output.get(
                "legacy_used"
            ) is False
        )
    )

    if binding_pass:

        status = (
            "PRODUCTION_FUSION_BINDING_PASS"
        )

    else:

        status = (
            "PRODUCTION_FUSION_BINDING_BLOCKED"
        )

    # =========================================================================
    # OUTPUT
    # =========================================================================

    print("=" * 94)

    print(
        "PRODUCTION FUSION BINDING RESULT"
    )

    print("=" * 94)

    print(
        "MARKETS=",
        len(EXPECTED_ASSETS)
    )

    print(
        "MARKET_SIGNAL_OUTPUTS=",
        market_signals
    )

    print(
        "VALIDATED_MARKET_SIGNALS=",
        validated_signals
    )

    print(
        "NEWS_ITEMS=",
        news_runtime["count"]
    )

    print(
        "NEWS_ASSETS=",
        news_assets
    )

    print(
        "NEWS_CONTRACT_INVALID=",
        news_runtime["invalid"]
    )

    print(
        "SOCIAL_ITEMS=",
        social_runtime["count"]
    )

    print(
        "SOCIAL_ASSETS=",
        social_assets
    )

    print(
        "SOCIAL_CONTRACT_INVALID=",
        social_runtime["invalid"]
    )

    print(
        "FUSION_OUTPUTS=",
        fusion_outputs
    )

    print(
        "FUSION_AVAILABLE=",
        fusion_available
    )

    print(
        "FUSION_VALIDATED=",
        fusion_validated
    )

    print(
        "FUSION_VALIDATION=",
        fusion_validation
    )

    print(
        "PROVENANCE_VALID=",
        provenance_valid
    )

    print(
        "CONTINUITY_VALID=",
        continuity_valid
    )

    print(
        "PRODUCTION_DATA_ONLY=TRUE"
    )

    print(
        "LEGACY_DATA_USED=",
        legacy_data_used
    )

    print(
        "LAUNCH_BOUNDARY=",
        LAUNCH_TIMESTAMP
    )

    print(
        "PRODUCTION_DB_TOUCHED=FALSE"
    )

    print(
        "DB_WRITES=0"
    )

    print(
        "FUSION=ACTIVE"
    )

    print(
        "SCORE=OFF"
    )

    print(
        "DECISION=OFF"
    )

    print(
        "ORDER_INTENTS=0"
    )

    print(
        "EXECUTION=OFF"
    )

    if fusion_runtime_error:

        print(
            "FUSION_RUNTIME_ERROR=",
            fusion_runtime_error
        )

    print(
        "STATUS=",
        status
    )

    print()

    # =========================================================================
    # PER-ASSET PRODUCTION CHAIN
    # =========================================================================

    print("=" * 94)

    print(
        "PRODUCTION MARKET -> SIGNAL -> NEWS -> SOCIAL -> FUSION"
    )

    print("=" * 94)

    for asset in EXPECTED_ASSETS:

        item = results[
            asset
        ]

        market = item[
            "market"
        ]

        intelligence = item[
            "intelligence"
        ]

        signal = market.get(
            "signal"
        )

        news_count = len(
            intelligence[
                "news_signals"
            ]
        )

        social_count = len(
            intelligence[
                "social_signals"
            ]
        )

        fusion_result = None

        for candidate in fusion_results:

            if candidate.get(
                "asset"
            ) == asset:

                fusion_result = candidate
                break

        if signal is not None:

            signal_state = signal.get(
                "signal_state"
            )

            signal_direction = signal.get(
                "direction"
            )

        else:

            signal_state = (
                "NO_SIGNAL"
            )

            signal_direction = (
                "NONE"
            )

        if fusion_result is not None:

            fused_score = fusion_result.get(
                "fused_score"
            )

            fused_confidence = (
                fusion_result.get(
                    "confidence"
                )
            )

            fused_direction = (
                fusion_result.get(
                    "direction"
                )
            )

            regime = fusion_result.get(
                "regime"
            )

            quality = fusion_result.get(
                "data_quality"
            )

        else:

            fused_score = None
            fused_confidence = None
            fused_direction = "NONE"
            regime = "UNAVAILABLE"
            quality = "UNAVAILABLE"

        print(
            "{} | "
            "MARKET={} | "
            "SIGNAL={} | "
            "NEWS={} | "
            "SOCIAL={} | "
            "FUSED={} | "
            "CONF={} | "
            "DIRECTION={} | "
            "REGIME={} | "
            "QUALITY={}".format(
                asset,
                signal_state,
                signal_direction,
                news_count,
                social_count,
                (
                    f"{fused_score:.2f}"
                    if isinstance(
                        fused_score,
                        (int, float),
                    )
                    else "N/A"
                ),
                (
                    f"{fused_confidence:.3f}"
                    if isinstance(
                        fused_confidence,
                        (int, float),
                    )
                    else "N/A"
                ),
                fused_direction,
                regime,
                quality,
            )
        )

    print()

    # =========================================================================
    # HARD SAFETY SUMMARY
    # =========================================================================

    print("=" * 94)

    print(
        "HARD SAFETY STATE"
    )

    print("=" * 94)

    print(
        "CANONICAL_STORE_WRITE   : 0"
    )

    print(
        "PRODUCTION_DB_WRITE     : 0"
    )

    print(
        "LEGACY_MARKET_TECHNICAL : NOT USED"
    )

    print(
        "CMC_SNAPSHOT            : NOT USED"
    )

    print(
        "COINALYZE               : NOT USED"
    )

    print(
        "SYNTHETIC_DATA          : FORBIDDEN"
    )

    print(
        "INTERPOLATION           : FORBIDDEN"
    )

    print(
        "FILL                    : FORBIDDEN"
    )

    print(
        "BACKFILL                : FORBIDDEN"
    )

    print(
        "PADDING                 : FORBIDDEN"
    )

    print(
        "SCORE                   : OFF"
    )

    print(
        "DECISION                : OFF"
    )

    print(
        "ORDER_INTENTS           : 0"
    )

    print(
        "EXECUTION               : OFF"
    )

    print("=" * 94)

    return (
        0
        if binding_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )