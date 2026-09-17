import math
import score_producer
import signal_validator

vs = signal_validator.load_validated_signals()

fs = score_producer.load_features()
ss = score_producer.load_structural_states()
rg = score_producer.load_regimes()

print("=== SCORE COMPONENT FORENSIC ===")
print()

original = score_producer.calculate_score


def trace(direction, features, structural_state, regime_data):

    asset = current_asset[0]

    values = {}

    for name in score_producer.REQUIRED_FEATURES:
        values[name] = score_producer.get_feature(
            features,
            name,
        )

    rc = (
        values["return_20"]
        * score_producer.WEIGHTS["return_20"]
    )

    mc = (
        values["momentum_20"]
        * score_producer.WEIGHTS["momentum_20"]
    )

    tc = (
        values["trend_slope_20"]
        * score_producer.WEIGHTS["trend_slope_20"]
    )

    ac = (
        values["acceleration"]
        * score_producer.WEIGHTS["acceleration"]
    )

    pc = (
        values["position_20"]
        * score_producer.WEIGHTS["position_20"]
    )

    rgc = (
        score_producer.clamp(
            values["range_20"]
        )
        * score_producer.WEIGHTS["range_20"]
    )

    vp = (
        score_producer.clamp(
            values["volatility_20"]
        )
        * 0.25
    )

    if direction == "LONG":

        directional = (
            rc
            + mc
            + tc
            + ac
            + pc
            + rgc
        )

    else:

        directional = (
            -rc
            -mc
            -tc
            -ac
            -pc
            +rgc
        )

    raw = directional - vp

    print("-" * 90)
    print("ASSET:", asset)
    print("DIRECTION:", direction)
    print("FEATURES:", values)
    print()
    print("RETURN COMPONENT:", rc)
    print("MOMENTUM COMPONENT:", mc)
    print("TREND COMPONENT:", tc)
    print("ACCELERATION COMPONENT:", ac)
    print("POSITION COMPONENT:", pc)
    print("RANGE COMPONENT:", rgc)
    print("VOLATILITY PENALTY:", vp)
    print()
    print("DIRECTIONAL SCORE:", directional)
    print("RAW SCORE:", raw)
    print("FINITE:", math.isfinite(raw))
    print("IN [-1,+1]:", -1.0 <= raw <= 1.0)
    print()

    return original(
        direction,
        features,
        structural_state,
        regime_data,
    )


current_asset = ["UNKNOWN"]

original_extract = score_producer.extract_features


def extract(snapshot, asset):

    current_asset[0] = asset

    return original_extract(
        snapshot,
        asset,
    )


score_producer.calculate_score = trace
score_producer.extract_features = extract

try:

    score_producer.run(vs)

except Exception as exc:

    print("=" * 90)
    print("FORENSIC EXCEPTION")
    print("TYPE:", type(exc).__name__)
    print("ERROR:", exc)