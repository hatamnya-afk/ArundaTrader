import ast
import copy
import importlib
from pathlib import Path


# =============================================================================
# ARUNDA TRADER — STEP 18 SIGNAL SCORE CONTRACT AUDIT v0.1
# =============================================================================
#
# MODE:
#   READ ONLY / AUDIT
#
# RULES:
#   NO DATABASE
#   NO SQL
#   NO WRITES
#   NO NETWORK
#   NO EXCHANGE
#   NO DECISION
#   NO PREDICTION
#   NO RISK
#   NO EXECUTION
#
# =============================================================================


class AuditFailure(Exception):
    pass


EXPECTED_ASSETS = (
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "DOGE", "SHIB", "LINK", "AVAX", "DOT",
    "LTC", "UNI", "AAVE", "SUI", "NEAR",
)

EXPECTED_COUNT = 15

signal_score_contract = importlib.import_module(
    "signal_score_contract"
)


def assert_true(condition, message):
    if not condition:
        raise AuditFailure(message)


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AuditFailure(
            f"{message} | expected={expected!r} got={actual!r}"
        )


def load_scores():
    if not hasattr(
        signal_score_contract,
        "load_score_snapshot",
    ):
        raise RuntimeError(
            "signal_score_contract.load_score_snapshot() missing"
        )

    data = signal_score_contract.load_score_snapshot()

    if not isinstance(data, dict):
        raise AuditFailure(
            "score snapshot must be dict"
        )

    return data


def validate_snapshot(scores):

    assert_equal(
        len(scores),
        EXPECTED_COUNT,
        "unexpected asset count",
    )

    assert_equal(
        set(scores.keys()),
        set(EXPECTED_ASSETS),
        "asset universe mismatch",
    )

    for asset in EXPECTED_ASSETS:

        record = scores[asset]

        assert_true(
            isinstance(record, dict),
            f"invalid record: {asset}",
        )

        assert_equal(
            record.get("asset"),
            asset,
            f"asset identity mismatch: {asset}",
        )

        assert_true(
            "score" in record,
            f"missing score: {asset}",
        )

        score = record["score"]

        assert_true(
            isinstance(score, (int, float))
            and not isinstance(score, bool),
            f"invalid score type: {asset}",
        )

        assert_true(
            -1.0 <= float(score) <= 1.0,
            f"score outside bounds: {asset}",
        )


def test_01_snapshot_type():
    scores = load_scores()

    assert_true(
        isinstance(scores, dict),
        "snapshot must be dict",
    )


def test_02_asset_count():
    scores = load_scores()

    assert_equal(
        len(scores),
        EXPECTED_COUNT,
        "asset count mismatch",
    )


def test_03_asset_universe():
    scores = load_scores()

    assert_equal(
        set(scores.keys()),
        set(EXPECTED_ASSETS),
        "asset universe mismatch",
    )


def test_04_record_integrity():
    scores = load_scores()

    validate_snapshot(scores)


def test_05_score_type():
    scores = load_scores()

    for asset, record in scores.items():

        score = record["score"]

        assert_true(
            isinstance(score, (int, float))
            and not isinstance(score, bool),
            f"invalid score type: {asset}",
        )


def test_06_lower_bound():
    scores = load_scores()

    for asset, record in scores.items():

        assert_true(
            record["score"] >= -1.0,
            f"lower bound violation: {asset}",
        )


def test_07_upper_bound():
    scores = load_scores()

    for asset, record in scores.items():

        assert_true(
            record["score"] <= 1.0,
            f"upper bound violation: {asset}",
        )


def test_08_direction_contract():
    scores = load_scores()

    for asset, record in scores.items():

        direction = record.get("direction")

        assert_true(
            direction in ("LONG", "SHORT", "NONE"),
            f"invalid direction: {asset}",
        )


def test_09_state_contract():
    scores = load_scores()

    for asset, record in scores.items():

        state = record.get("signal_state")

        assert_true(
            state in ("ACTIVE", "NEUTRAL"),
            f"invalid signal state: {asset}",
        )


def test_10_neutral_zero():
    scores = load_scores()

    for asset, record in scores.items():

        if record.get("direction") == "NONE":

            assert_equal(
                record["score"],
                0.0,
                f"NONE must score zero: {asset}",
            )


def test_11_active_direction():
    scores = load_scores()

    for asset, record in scores.items():

        if record.get("signal_state") == "ACTIVE":

            assert_true(
                record.get("direction")
                in ("LONG", "SHORT"),
                f"ACTIVE/NONE mismatch: {asset}",
            )


def test_12_immutability():
    scores = load_scores()

    before = copy.deepcopy(scores)

    validate_snapshot(scores)

    assert_equal(
        scores,
        before,
        "snapshot was modified",
    )


def test_13_determinism():
    first = load_scores()
    second = load_scores()

    assert_equal(
        first,
        second,
        "repeated snapshot is not deterministic",
    )


def test_14_cross_asset_isolation():
    scores = load_scores()

    before = copy.deepcopy(scores)

    for asset in EXPECTED_ASSETS:

        record = scores[asset]

        assert_equal(
            record["asset"],
            asset,
            f"cross-asset identity violation: {asset}",
        )

    assert_equal(
        scores,
        before,
        "cross-asset validation modified snapshot",
    )


def test_15_no_forbidden_dependencies():

    source = Path("signal_score_contract.py")

    assert_true(
        source.exists(),
        "signal_score_contract.py not found",
    )

    text = source.read_text(
        encoding="utf-8-sig"
    )

    tree = ast.parse(
        text,
        filename=str(source),
    )

    forbidden_modules = {
        "sqlite3",
        "requests",
        "httpx",
        "urllib",
        "urllib3",
        "ccxt",
        "aiohttp",
        "websocket",
    }

    forbidden_symbols = {
        "execute",
        "executemany",
        "commit",
        "rollback",
        "post",
        "put",
        "delete",
        "send_order",
        "create_order",
        "place_order",
        "cancel_order",
    }

    violations = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                if alias.name.split(".")[0] in forbidden_modules:

                    violations.append(
                        f"import:{alias.name}"
                    )

        elif isinstance(node, ast.ImportFrom):

            if node.module:
                if node.module.split(".")[0] in forbidden_modules:

                    violations.append(
                        f"from:{node.module}"
                    )

        elif isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):

                if node.func.id in forbidden_symbols:

                    violations.append(
                        f"call:{node.func.id}"
                    )

            elif isinstance(node.func, ast.Attribute):

                if node.func.attr in forbidden_symbols:

                    violations.append(
                        f"call:{node.func.attr}"
                    )

    assert_true(
        not violations,
        "forbidden dependency detected: "
        + repr(violations),
    )


TESTS = [
    ("18-01 Snapshot type", test_01_snapshot_type),
    ("18-02 Asset count", test_02_asset_count),
    ("18-03 Asset universe", test_03_asset_universe),
    ("18-04 Record integrity", test_04_record_integrity),
    ("18-05 Score type", test_05_score_type),
    ("18-06 Lower bound", test_06_lower_bound),
    ("18-07 Upper bound", test_07_upper_bound),
    ("18-08 Direction contract", test_08_direction_contract),
    ("18-09 State contract", test_09_state_contract),
    ("18-10 NEUTRAL zero", test_10_neutral_zero),
    ("18-11 ACTIVE direction", test_11_active_direction),
    ("18-12 Immutability", test_12_immutability),
    ("18-13 Determinism", test_13_determinism),
    ("18-14 Cross-asset isolation", test_14_cross_asset_isolation),
    ("18-15 Forbidden dependency", test_15_no_forbidden_dependencies),
]


def main():

    print("=" * 78)
    print("ARUNDA TRADER — STEP 18 SIGNAL SCORE CONTRACT AUDIT v0.1")
    print("=" * 78)
    print("Mode        : READ ONLY / AUDIT")
    print("Target      : SIGNAL SCORE CONTRACT")
    print("Database    : NOT USED")
    print("Writes      : NONE")
    print("Network     : NOT USED")
    print("Exchange    : NOT USED")
    print("Prediction  : NOT USED")
    print("Decision    : NOT USED")
    print("Risk        : NOT USED")
    print("Execution   : NOT USED")
    print("=" * 78)
    print()

    passed = 0
    failed = 0

    for name, test in TESTS:

        try:
            test()

            print(
                f"{name:<52} : PASS"
            )

            passed += 1

        except Exception as error:

            print(
                f"{name:<52} : FAIL"
            )

            print(
                f"  ERROR : {type(error).__name__} {error}"
            )

            failed += 1

    print()
    print("=" * 78)
    print("SIGNAL SCORE CONTRACT AUDIT")
    print("=" * 78)
    print("Total Tests :", len(TESTS))
    print("PASS        :", passed)
    print("FAIL        :", failed)
    print()

    if failed == 0:

        print("=" * 78)
        print("STEP 18 VERDICT")
        print("=" * 78)
        print("RESULT      : SIGNAL SCORE CONTRACT AUDIT PASS")
        print("STATUS      : READY FOR NEXT SIGNAL STEP")
        print()
        print("Architecture : PRESERVED")
        print("Database     : NOT USED")
        print("Writes       : NONE")
        print("Network      : NOT USED")
        print("Exchange     : NOT USED")
        print("Prediction   : NOT USED")
        print("Decision     : NOT USED")
        print("Risk         : NOT USED")
        print("Execution    : NOT USED")
        print("=" * 78)

        return 0

    print("=" * 78)
    print("STEP 18 VERDICT")
    print("=" * 78)
    print("RESULT      : SIGNAL SCORE CONTRACT AUDIT FAIL")
    print("STATUS      : REPAIR REQUIRED")
    print()
    print("IMPORTANT:")
    print("No production Signal files were modified.")
    print("=" * 78)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
