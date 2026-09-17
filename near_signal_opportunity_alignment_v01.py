from __future__ import annotations

import json
import math
from collections.abc import Mapping

import opportunity_engine
import signal_validator
import score_producer
import signal_scorer
import decision_engine


TARGET = "NEAR"


def dump(label, value):
    print()
    print("=" * 90)
    print(label)
    print("=" * 90)
    if isinstance(value, Mapping):
        print(json.dumps(dict(value), indent=2, default=str))
    else:
        print(repr(value))


def find_asset(obj, asset):
    if isinstance(obj, Mapping):
        if str(obj.get("asset", "")).upper() == asset:
            return obj

        if str(obj.get("symbol", "")).upper() == asset:
            return obj

        for value in obj.values():
            found = find_asset(value, asset)
            if found is not None:
                return found

    elif isinstance(obj, (list, tuple)):
        for value in obj:
            found = find_asset(value, asset)
            if found is not None:
                return found

    return None


print("=" * 90)
print("ARUNDA NEAR SIGNAL <-> OPPORTUNITY ALIGNMENT FORENSIC v0.1")
print("=" * 90)
print("MODE=READ_ONLY")
print("TARGET=NEAR")
print("DB_WRITES=0")
print("EXECUTION=OFF")
print("ORDER_INTENTS=0")
print()


# -------------------------------------------------------------------------
# 1. OPPORTUNITY
# -------------------------------------------------------------------------

opportunity_snapshot = opportunity_engine.run()

opportunity_near = find_asset(
    opportunity_snapshot,
    TARGET,
)

if opportunity_near is None:
    raise RuntimeError(
        "NEAR opportunity record not found"
    )

dump(
    "NEAR OPPORTUNITY",
    opportunity_near,
)


# -------------------------------------------------------------------------
# 2. VALIDATED SIGNALS
# -------------------------------------------------------------------------

validated_signals = (
    signal_validator.load_validated_signals()
)

if not isinstance(validated_signals, Mapping):
    raise RuntimeError(
        "validated_signals is not a mapping"
    )

signal_near = validated_signals.get(TARGET)

if signal_near is None:
    raise RuntimeError(
        "NEAR validated signal not found"
    )

dump(
    "NEAR VALIDATED SIGNAL",
    signal_near,
)


# -------------------------------------------------------------------------
# 3. REAL SCORE
# -------------------------------------------------------------------------

scores = score_producer.run(
    validated_signals
)

score_near = scores.get(TARGET)

if score_near is None:
    raise RuntimeError(
        "NEAR score not found"
    )

dump(
    "NEAR REAL SCORE",
    score_near,
)


# -------------------------------------------------------------------------
# 4. SCORER ALIGNMENT
# -------------------------------------------------------------------------

aligned_scores = signal_scorer.run(
    validated_signals,
    scores,
)

aligned_near = aligned_scores.get(TARGET)

if aligned_near is None:
    raise RuntimeError(
        "NEAR aligned score not found"
    )

dump(
    "NEAR ALIGNED SCORE",
    aligned_near,
)


# -------------------------------------------------------------------------
# 5. DECISION
# -------------------------------------------------------------------------

decision_snapshot = decision_engine.run(
    validated_signals,
    aligned_scores,
)

decision_near = decision_snapshot.get(TARGET)

if decision_near is None:
    raise RuntimeError(
        "NEAR decision not found"
    )

dump(
    "NEAR DECISION",
    decision_near,
)


# -------------------------------------------------------------------------
# 6. DIRECT COMPARISON
# -------------------------------------------------------------------------

signal_state = signal_near.get("signal_state")
signal_direction = signal_near.get("direction")

score_state = score_near.get("signal_state")
score_direction = score_near.get("direction")

aligned_state = aligned_near.get("signal_state")
aligned_direction = aligned_near.get("direction")

decision_state = decision_near.get("state")
decision_direction = decision_near.get("direction")

opp_status = opportunity_near.get(
    "status",
    opportunity_near.get("opportunity_status"),
)

opp_direction = opportunity_near.get(
    "direction"
)

opp_score = opportunity_near.get(
    "score"
)

opp_confidence = opportunity_near.get(
    "confidence"
)

print()
print("=" * 90)
print("NEAR ALIGNMENT MATRIX")
print("=" * 90)

print(
    f"SIGNAL        : state={signal_state} "
    f"direction={signal_direction}"
)

print(
    f"SCORE         : state={score_state} "
    f"direction={score_direction} "
    f"score={score_near.get('score')}"
)

print(
    f"ALIGNED SCORE : state={aligned_state} "
    f"direction={aligned_direction}"
)

print(
    f"DECISION      : state={decision_state} "
    f"direction={decision_direction}"
)

print(
    f"OPPORTUNITY   : status={opp_status} "
    f"direction={opp_direction} "
    f"score={opp_score} "
    f"confidence={opp_confidence}"
)


# -------------------------------------------------------------------------
# 7. SEMANTIC TESTS
# -------------------------------------------------------------------------

print()
print("=" * 90)
print("BOUNDARY TESTS")
print("=" * 90)

tests = {
    "SIGNAL_SCORE_STATE_MATCH":
        signal_state == score_state,

    "SIGNAL_SCORE_DIRECTION_MATCH":
        signal_direction == score_direction,

    "SCORE_DECISION_STATE_COMPATIBLE":
        (
            (score_state == "NEUTRAL" and decision_state == "HOLD")
            or
            (score_state == "ACTIVE" and decision_state == "ACTIONABLE")
        ),

    "SCORE_DECISION_DIRECTION_MATCH":
        (
            (
                score_direction == "NONE"
                and decision_direction == "NONE"
            )
            or
            (
                score_direction in ("LONG", "SHORT")
                and decision_direction == score_direction
            )
        ),

    "OPPORTUNITY_DIRECTION_MATCH":
        opp_direction == decision_direction,

    "OPPORTUNITY_DIRECTION_MATCH_SIGNAL":
        opp_direction == signal_direction,

    "OPPORTUNITY_STATE_COMPATIBLE":
        (
            (
                signal_state == "ACTIVE"
                and opp_direction in ("LONG", "SHORT")
            )
            or
            (
                signal_state == "NEUTRAL"
                and opp_direction in ("NONE", None)
            )
        ),
}

for name, result in tests.items():
    print(
        f"{name:<42} = "
        f"{'PASS' if result else 'FAIL'}"
    )


# -------------------------------------------------------------------------
# 8. FINAL DIAGNOSIS
# -------------------------------------------------------------------------

failed = [
    name
    for name, result in tests.items()
    if not result
]

print()
print("=" * 90)

if failed:
    print("ALIGNMENT_STATUS=FAIL")
    print(
        "FIRST_BOUNDARY_FAILURE="
        + failed[0]
    )
else:
    print("ALIGNMENT_STATUS=PASS")
    print(
        "SIGNAL_OPPORTUNITY_BOUNDARY="
        "SEMANTICALLY_ALIGNED"
    )

print("=" * 90)

print()
print("DB_WRITES=0")
print("EXECUTION=OFF")
print("ORDER_INTENTS=0")
print("STATUS=FORENSIC_COMPLETE")
