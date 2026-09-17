import os
import inspect
import math
from typing import Any, Mapping


# =============================================================================
# ARUNDA TRADER — M2
# REAL_SIGNAL_TO_PRODUCTION_SCORER_RUNTIME_v0.5
# =============================================================================
#
# PURPOSE
# -------
# Execute REAL production signals through the EXISTING production scorer.
#
# REPAIR
# ------
# v0.4 blocker:
#
#   market_regime_contract.load_market_regime_contract()
#       ->
#   market_regime.py.load_market_regime()
#
# The production contract expects market_regime.load_market_regime(),
# but that API is not exposed by market_regime.py.
#
# THIS RUNTIME DOES NOT MODIFY production source.
#
# Instead, this harness resolves the REAL underlying regime source through
# the already-existing production dependency chain discovered by forensic
# inspection.
#
# IMPORTANT:
# - NO synthetic regime
# - NO synthetic feature
# - NO synthetic structure
# - NO production modification
# - NO database write
# - NO decision
# - NO prediction
# - NO execution
#
# =============================================================================


ENGINE_VERSION = "M2_REAL_SCORER_RUNTIME_v0.5"

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


# =============================================================================
# TERMINAL
# =============================================================================

def line(char="=", length=100):
    print(char * length)


def fail(message):
    raise RuntimeError(message)


# =============================================================================
# MODULE LOADING
# =============================================================================

def load_production_modules():

    try:
        import signal_engine
    except Exception as exc:
        fail(
            "BLOCKER:IMPORT_SIGNAL_ENGINE:"
            f"{type(exc).__name__}:{exc}"
        )

    try:
        import signal_scorer
    except Exception as exc:
        fail(
            "BLOCKER:IMPORT_SIGNAL_SCORER:"
            f"{type(exc).__name__}:{exc}"
        )

    try:
        import market_state_engine
    except Exception as exc:
        fail(
            "BLOCKER:IMPORT_MARKET_STATE_ENGINE:"
            f"{type(exc).__name__}:{exc}"
        )

    try:
        import market_regime_contract
    except Exception as exc:
        fail(
            "BLOCKER:IMPORT_MARKET_REGIME_CONTRACT:"
            f"{type(exc).__name__}:{exc}"
        )

    try:
        import market_regime
    except Exception as exc:
        fail(
            "BLOCKER:IMPORT_MARKET_REGIME:"
            f"{type(exc).__name__}:{exc}"
        )

    return (
        signal_engine,
        signal_scorer,
        market_state_engine,
        market_regime_contract,
        market_regime,
    )


# =============================================================================
# API RESOLUTION
# =============================================================================

def require_callable(
    module,
    name,
):

    fn = getattr(
        module,
        name,
        None,
    )

    if not callable(fn):

        fail(
            "BLOCKER:MISSING_PRODUCTION_API:"
            f"{module.__name__}.{name}"
        )

    return fn


# =============================================================================
# SELF TEST
# =============================================================================

def self_test():

    assert isinstance(
        ENGINE_VERSION,
        str,
    )

    assert len(
        EXPECTED_ASSETS
    ) == 15

    assert len(
        set(EXPECTED_ASSETS)
    ) == 15

    print("SELF TEST : PASS")


# =============================================================================
# REAL SIGNAL
# =============================================================================

def load_real_signals(
    signal_engine,
):

    build_all = require_callable(
        signal_engine,
        "build_all",
    )

    try:

        snapshot = build_all()

    except Exception as exc:

        fail(
            "BLOCKER:REAL_SIGNAL_RUNTIME:"
            f"{type(exc).__name__}:{exc}"
        )

    if not isinstance(
        snapshot,
        Mapping,
    ):

        fail(
            "BLOCKER:REAL_SIGNAL_INVALID_SNAPSHOT:"
            f"{type(snapshot).__name__}"
        )

    return snapshot


def extract_real_signal(
    asset,
    record,
):

    if not isinstance(
        record,
        Mapping,
    ):

        fail(
            f"BLOCKER:REAL_SIGNAL_RECORD_INVALID:{asset}"
        )

    signal = record.get(
        "signal"
    )

    if signal is None:

        fail(
            f"BLOCKER:REAL_SIGNAL_MISSING:{asset}"
        )

    if not isinstance(
        signal,
        Mapping,
    ):

        fail(
            f"BLOCKER:REAL_SIGNAL_NOT_MAPPING:{asset}"
        )

    direction = signal.get(
        "direction"
    )

    state = signal.get(
        "signal_state"
    )

    if state is None:

        state = signal.get(
            "state"
        )

    if direction is None:

        fail(
            f"BLOCKER:REAL_SIGNAL_DIRECTION_MISSING:{asset}"
        )

    if state is None:

        fail(
            f"BLOCKER:REAL_SIGNAL_STATE_MISSING:{asset}"
        )

    direction = str(
        direction
    ).upper()

    state = str(
        state
    ).upper()

    eligible = (
        state == "ACTIVE"
        and direction in {
            "LONG",
            "SHORT",
        }
    )

    return {
        "asset": asset,
        "state": state,
        "direction": direction,
        "eligible": eligible,
        "signal": signal,
    }


# =============================================================================
# REAL STRUCTURE
# =============================================================================

def load_real_structures(
    market_state_engine,
):

    loader = require_callable(
        market_state_engine,
        "load_structural_state",
    )

    try:

        structures = loader()

    except Exception as exc:

        fail(
            "BLOCKER:REAL_STRUCTURE_RUNTIME:"
            f"{type(exc).__name__}:{exc}"
        )

    if not isinstance(
        structures,
        Mapping,
    ):

        fail(
            "BLOCKER:REAL_STRUCTURE_INVALID:"
            f"{type(structures).__name__}"
        )

    return structures


# =============================================================================
# REAL REGIME — REPAIRED RESOLUTION
# =============================================================================
#
# IMPORTANT:
#
# The production contract itself is currently unusable because:
#
#     market_regime_contract.load_market_regime_contract()
#
# internally requires:
#
#     market_regime.load_market_regime()
#
# and that API is missing.
#
# We therefore DO NOT fabricate the regime and DO NOT modify the production
# module.
#
# Instead we inspect market_regime.py for an existing REAL source object/API.
#
# =============================================================================

def resolve_real_regime_source(
    market_regime,
):

    candidates = (
        "load_market_regime",
        "build_market_regime",
        "calculate_market_regime",
        "get_market_regime",
        "load_regime",
        "build_regime",
        "calculate_regime",
        "get_regime",
    )

    for name in candidates:

        candidate = getattr(
            market_regime,
            name,
            None,
        )

        if callable(candidate):

            return (
                f"market_regime.{name}",
                candidate,
            )

    #
    # The forensic locator already established that no public candidate
    # exists. Do not invent an API or synthesize regime data.
    #

    fail(
        "BLOCKER:REAL_REGIME_SOURCE_NOT_EXPOSED:"
        "market_regime.py exposes no supported real regime loader."
    )


def load_real_regime_source(
    market_regime,
):

    source_name, loader = resolve_real_regime_source(
        market_regime
    )

    try:

        signature = inspect.signature(
            loader
        )

    except Exception as exc:

        fail(
            "BLOCKER:REAL_REGIME_SOURCE_SIGNATURE:"
            f"{source_name}:"
            f"{type(exc).__name__}:{exc}"
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

    if required:

        fail(
            "BLOCKER:REAL_REGIME_SOURCE_REQUIRES_UPSTREAM_INPUT:"
            f"{source_name}:"
            f"required={len(required)}"
        )

    try:

        regimes = loader()

    except Exception as exc:

        fail(
            "BLOCKER:REAL_REGIME_SOURCE_RUNTIME:"
            f"{source_name}:"
            f"{type(exc).__name__}:{exc}"
        )

    if not isinstance(
        regimes,
        Mapping,
    ):

        fail(
            "BLOCKER:REAL_REGIME_SOURCE_INVALID:"
            f"{source_name}:"
            f"{type(regimes).__name__}"
        )

    return (
        source_name,
        regimes,
    )


# =============================================================================
# REGIME NORMALIZATION
# =============================================================================

def normalize_regime_contract(
    regimes,
):

    if not isinstance(
        regimes,
        Mapping,
    ):

        fail(
            "BLOCKER:REAL_REGIME_INVALID_MAPPING"
        )

    missing = sorted(
        set(EXPECTED_ASSETS)
        - set(regimes.keys())
    )

    if missing:

        fail(
            "BLOCKER:REAL_REGIME_MISSING_ASSETS:"
            f"{missing}"
        )

    extra = sorted(
        set(regimes.keys())
        - set(EXPECTED_ASSETS)
    )

    if extra:

        fail(
            "BLOCKER:REAL_REGIME_UNEXPECTED_ASSETS:"
            f"{extra}"
        )

    normalized = {}

    for asset in EXPECTED_ASSETS:

        value = regimes[asset]

        if not isinstance(
            value,
            Mapping,
        ):

            fail(
                "BLOCKER:REAL_REGIME_INVALID_ASSET_RECORD:"
                f"{asset}:"
                f"{type(value).__name__}"
            )

        #
        # Preserve the REAL production object.
        #
        normalized[asset] = value

    return normalized


# =============================================================================
# REAL REGIME
# =============================================================================

def load_real_regimes(
    market_regime_contract,
    market_regime,
):

    #
    # First prove the production contract remains the canonical source.
    #

    contract_loader = require_callable(
        market_regime_contract,
        "load_market_regime_contract",
    )

    try:

        contract_result = contract_loader()

        if isinstance(
            contract_result,
            Mapping,
        ):

            return (
                "market_regime_contract.load_market_regime_contract()",
                normalize_regime_contract(
                    contract_result
                ),
            )

    except Exception as contract_exc:

        contract_error = contract_exc

    else:

        contract_error = None

    #
    # Contract is blocked by the confirmed API mismatch.
    #
    # DO NOT fabricate.
    #
    # Resolve only an already-existing real source from market_regime.py.
    #

    try:

        source_name, regimes = load_real_regime_source(
            market_regime
        )

    except Exception as source_exc:

        if contract_error is not None:

            fail(
                "BLOCKER:REAL_REGIME_CONTRACT_AND_SOURCE:"
                f"CONTRACT="
                f"{type(contract_error).__name__}:"
                f"{contract_error};"
                f"SOURCE="
                f"{type(source_exc).__name__}:"
                f"{source_exc}"
            )

        raise

    return (
        source_name,
        normalize_regime_contract(
            regimes
        ),
    )


# =============================================================================
# FEATURE SOURCE
# =============================================================================

def resolve_feature_source(
    signal_scorer,
):

    loader = getattr(
        signal_scorer,
        "load_feature_snapshot",
        None,
    )

    if callable(loader):

        return (
            "signal_scorer.load_feature_snapshot",
            loader,
        )

    try:

        import feature_engine

    except Exception:

        feature_engine = None

    if feature_engine is not None:

        for name in (
            "load_feature_snapshot",
            "calculate_feature_records",
        ):

            candidate = getattr(
                feature_engine,
                name,
                None,
            )

            if callable(candidate):

                return (
                    f"feature_engine.{name}",
                    candidate,
                )

    return (
        None,
        None,
    )


def normalize_feature_snapshot(
    snapshot,
):

    if not isinstance(
        snapshot,
        Mapping,
    ):

        fail(
            "BLOCKER:REAL_FEATURE_SNAPSHOT_INVALID:"
            f"{type(snapshot).__name__}"
        )

    return snapshot


def extract_feature_record(
    signal_scorer,
    asset,
    feature_snapshot,
):

    extractor = require_callable(
        signal_scorer,
        "extract_latest_feature_record",
    )

    if asset not in feature_snapshot:

        fail(
            f"BLOCKER:REAL_FEATURE_MISSING_ASSET:{asset}"
        )

    asset_data = feature_snapshot[
        asset
    ]

    try:

        record = extractor(
            asset,
            asset_data,
        )

    except Exception as exc:

        fail(
            "BLOCKER:REAL_FEATURE_EXTRACTION:"
            f"{asset}:"
            f"{type(exc).__name__}:{exc}"
        )

    if not isinstance(
        record,
        Mapping,
    ):

        fail(
            f"BLOCKER:REAL_FEATURE_RECORD_INVALID:{asset}"
        )

    return record


def load_real_features(
    signal_scorer,
):

    name, loader = resolve_feature_source(
        signal_scorer
    )

    if loader is not None:

        try:

            signature = inspect.signature(
                loader
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

            if len(required) == 0:

                snapshot = loader()

                return (
                    name,
                    normalize_feature_snapshot(
                        snapshot
                    ),
                )

        except Exception as exc:

            fail(
                "BLOCKER:REAL_FEATURE_SOURCE_RUNTIME:"
                f"{name}:"
                f"{type(exc).__name__}:{exc}"
            )

    fail(
        "BLOCKER:REAL_FEATURE_INPUT_PIPELINE_NOT_EXPOSED:"
        "signal_scorer.load_features() requires real "
        "bars_by_asset and indicators_by_asset, but no "
        "zero-input production feature snapshot source "
        "is exposed."
    )


# =============================================================================
# SCORE VALIDATION
# =============================================================================

def validate_real_score(
    asset,
    score,
):

    if isinstance(
        score,
        bool,
    ):

        fail(
            f"BLOCKER:REAL_SCORE_INVALID_TYPE:{asset}:bool"
        )

    try:

        value = float(
            score
        )

    except (
        TypeError,
        ValueError,
    ):

        fail(
            f"BLOCKER:REAL_SCORE_NOT_NUMERIC:{asset}:{score!r}"
        )

    if not math.isfinite(
        value
    ):

        fail(
            f"BLOCKER:REAL_SCORE_NOT_FINITE:{asset}:{value}"
        )

    if value < -1.0 or value > 1.0:

        fail(
            "BLOCKER:REAL_SCORE_OUT_OF_CONTRACT:"
            f"{asset}:{value}"
        )

    return round(
        value,
        6,
    )


# =============================================================================
# REAL SCORER
# =============================================================================

def score_real_signal(
    signal_scorer,
    asset,
    signal_record,
    feature_record,
    structural_state,
    regime_data,
):

    calculate_score = require_callable(
        signal_scorer,
        "calculate_score",
    )

    direction = signal_record[
        "direction"
    ]

    try:

        score = calculate_score(
            direction,
            feature_record,
            structural_state,
            regime_data,
        )

    except Exception as exc:

        fail(
            "BLOCKER:PRODUCTION_SCORER_RUNTIME:"
            f"{asset}:"
            f"{type(exc).__name__}:{exc}"
        )

    return validate_real_score(
        asset,
        score,
    )


# =============================================================================
# ASSET MAPPING
# =============================================================================

def resolve_asset_mapping(
    mapping,
    asset,
    label,
):

    if asset not in mapping:

        fail(
            f"BLOCKER:{label}_MISSING_ASSET:{asset}"
        )

    value = mapping[
        asset
    ]

    if not isinstance(
        value,
        Mapping,
    ):

        fail(
            f"BLOCKER:{label}_INVALID_ASSET_RECORD:"
            f"{asset}:"
            f"{type(value).__name__}"
        )

    return value


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — M2"
    )
    print(
        "REAL_SIGNAL_TO_PRODUCTION_SCORER_RUNTIME_v0.5"
    )
    print("=" * 100)

    print(
        f"PROJECT              : {PROJECT_DIR}"
    )

    print(
        "MODE                 : PRODUCTION RUNTIME READ"
    )

    print(
        "REAL SIGNAL SOURCE   : signal_engine.build_all()"
    )

    print(
        "SCORER               : signal_scorer.calculate_score()"
    )

    print(
        "DATABASE WRITE       : NONE"
    )

    print(
        "SYNTHETIC DATA       : NONE"
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

        (
            signal_engine,
            signal_scorer,
            market_state_engine,
            market_regime_contract,
            market_regime,
        ) = load_production_modules()

        # =====================================================================
        # SCORER
        # =====================================================================

        print()
        line("-", 100)
        print(
            "PRODUCTION SCORER"
        )
        line("-", 100)

        scorer = require_callable(
            signal_scorer,
            "calculate_score",
        )

        print(
            "Module       : signal_scorer"
        )

        print(
            "Function     : calculate_score"
        )

        print(
            f"Signature    : {inspect.signature(scorer)}"
        )

        print(
            "Resolution   : DETERMINISTIC"
        )

        print(
            "Status       : PRODUCTION SCORER RESOLVED"
        )

        # =====================================================================
        # REAL SIGNALS
        # =====================================================================

        print()
        line("-", 100)
        print(
            "REAL SIGNAL SOURCE"
        )
        line("-", 100)

        signals_snapshot = load_real_signals(
            signal_engine
        )

        print(
            "Source       : signal_engine.build_all()"
        )

        print(
            f"Assets       : {len(signals_snapshot)}"
        )

        print(
            "Signal source: build_all()[asset]['signal']"
        )

        real_signals = {}

        for asset in sorted(
            signals_snapshot.keys()
        ):

            real_signals[
                asset
            ] = extract_real_signal(
                asset,
                signals_snapshot[asset],
            )

        print()
        print(
            "REAL SIGNALS"
        )
        line("-", 100)

        for asset in sorted(
            real_signals.keys()
        ):

            record = real_signals[
                asset
            ]

            print(
                f"{asset:<8}"
                f"STATE={record['state']:<12}"
                f"DIRECTION={record['direction']:<7}"
                f"SCORER_ELIGIBLE={record['eligible']}"
            )

        eligible_assets = [

            asset

            for asset, record
            in real_signals.items()

            if record["eligible"]
        ]

        if not eligible_assets:

            fail(
                "BLOCKER:NO_REAL_ELIGIBLE_SIGNAL"
            )

        print()
        print(
            f"Eligible real signals : {len(eligible_assets)}"
        )

        # =====================================================================
        # STRUCTURE
        # =====================================================================

        print()
        line("-", 100)
        print(
            "REAL STRUCTURAL STATE"
        )
        line("-", 100)

        structures = load_real_structures(
            market_state_engine
        )

        print(
            "Source       : "
            "market_state_engine.load_structural_state()"
        )

        print(
            f"Assets       : {len(structures)}"
        )

        # =====================================================================
        # REGIME
        # =====================================================================

        print()
        line("-", 100)
        print(
            "REAL REGIME DATA"
        )
        line("-", 100)

        regime_source_name, regimes = load_real_regimes(
            market_regime_contract,
            market_regime,
        )

        print(
            f"Source       : {regime_source_name}"
        )

        print(
            f"Assets       : {len(regimes)}"
        )

        # =====================================================================
        # FEATURES
        # =====================================================================

        print()
        line("-", 100)
        print(
            "REAL FEATURE SOURCE"
        )
        line("-", 100)

        (
            feature_source_name,
            feature_snapshot,
        ) = load_real_features(
            signal_scorer
        )

        print(
            f"Source       : {feature_source_name}"
        )

        print(
            f"Assets       : {len(feature_snapshot)}"
        )

        # =====================================================================
        # REAL SIGNAL → SCORER
        # =====================================================================

        print()
        line("-", 100)
        print(
            "REAL SIGNAL → PRODUCTION SCORER"
        )
        line("-", 100)

        print(
            f"{'ASSET':<8}"
            f"{'DIRECTION':<12}"
            f"{'FEATURE':<12}"
            f"{'STRUCTURE':<12}"
            f"{'REGIME':<12}"
            f"{'SCORE':>10}"
            f"{'VALID':>9}"
        )

        print(
            "-" * 100
        )

        results = {}

        for asset in sorted(
            eligible_assets
        ):

            signal_record = real_signals[
                asset
            ]

            feature_record = extract_feature_record(
                signal_scorer,
                asset,
                feature_snapshot,
            )

            structural_state = resolve_asset_mapping(
                structures,
                asset,
                "REAL_STRUCTURE",
            )

            regime_data = resolve_asset_mapping(
                regimes,
                asset,
                "REAL_REGIME",
            )

            score = score_real_signal(
                signal_scorer,
                asset,
                signal_record,
                feature_record,
                structural_state,
                regime_data,
            )

            results[
                asset
            ] = {
                "direction": signal_record[
                    "direction"
                ],
                "score": score,
                "feature_index": feature_record.get(
                    "index"
                ),
                "feature_timestamp": feature_record.get(
                    "timestamp"
                ),
            }

            print(
                f"{asset:<8}"
                f"{signal_record['direction']:<12}"
                f"{'REAL':<12}"
                f"{'REAL':<12}"
                f"{'REAL':<12}"
                f"{score:>10.6f}"
                f"{'PASS':>9}"
            )

        # =====================================================================
        # FINAL VALIDATION
        # =====================================================================

        if len(results) != len(
            eligible_assets
        ):

            fail(
                "BLOCKER:REAL_SCORE_COVERAGE_MISMATCH:"
                f"{len(results)}!={len(eligible_assets)}"
            )

        if not results:

            fail(
                "BLOCKER:NO_REAL_VALID_SCORE"
            )

        print()
        line("=", 100)

        print(
            "M2 RESULT"
        )

        line("=", 100)

        print(
            f"Real Signals         : {len(real_signals)}"
        )

        print(
            f"Eligible Signals     : {len(eligible_assets)}"
        )

        print(
            f"Valid Scores         : {len(results)}"
        )

        print(
            f"Regime Source        : {regime_source_name}"
        )

        print(
            "Synthetic Data       : NONE"
        )

        print(
            "Database Write       : NONE"
        )

        print(
            "Decision             : NOT USED"
        )

        print(
            "Prediction           : NOT USED"
        )

        print(
            "Execution            : NOT USED"
        )

        line("=", 100)

        print()
        print(
            "FINAL STATUS : REAL VALID SCORE"
        )

        print(
            "M2 STATUS    : VERIFIED"
        )

        print(
            "NEXT         : PROCEED TO NEXT ROADMAP INTEGRATION"
        )

        return 0

    except KeyboardInterrupt:

        print()
        print(
            "M2 RUNTIME INTERRUPTED"
        )

        return 130

    except Exception as exc:

        print()
        line("=", 100)

        print(
            "M2 STATUS : BLOCKED"
        )

        print(
            f"ERROR     : {type(exc).__name__}: {exc}"
        )

        line("=", 100)

        return 1


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )