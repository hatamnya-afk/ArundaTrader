from account_balance_observation_v0_1 import build_account_balance_observation


class _Result:
    def __init__(self, data, *, allowed=True, status="PASS"):
        self.data = data
        self.allowed = allowed
        self.status = status


class _Adapter:
    def __init__(self, account, balances, *, capabilities=None):
        self._account = account
        self._balances = balances
        self._capabilities = capabilities or {
            "ACCOUNT_READ": True,
            "BALANCE_READ": True,
        }

    def capabilities(self):
        return dict(self._capabilities)

    def get_account(self):
        return self._account

    def get_balances(self):
        return self._balances


def _adapter(rows, account=None):
    account = account or {
        "account_id": "REAL-ACCOUNT-TEST-FIXTURE",
        "account_type": "SPOT",
        "environment": "TEST_FIXTURE_ONLY",
        "source_id": "TEST_SOURCE",
        "source_type": "TEST_FIXTURE_ONLY",
        "source_timestamp": "2026-01-01T00:00:00+00:00",
    }
    return _Adapter(
        _Result(account),
        _Result({"balances": rows}),
    )


def test_valid_single_balance():
    observation = build_account_balance_observation(
        _adapter([{"asset": "USDT", "free": 10, "locked": 0, "total": 10}]),
        retrieved_at="2026-01-01T00:00:01+00:00",
    )
    assert observation.account.account_id == "REAL-ACCOUNT-TEST-FIXTURE"
    assert len(observation.balances) == 1
    assert observation.balances[0].asset == "USDT"


def test_zero_balance_is_representable():
    observation = build_account_balance_observation(
        _adapter([{"asset": "USDT", "free": 0, "locked": 0, "total": 0}]),
        retrieved_at="2026-01-01T00:00:01+00:00",
    )
    assert observation.balances[0].total == 0


def test_multiple_balances_are_dynamic():
    observation = build_account_balance_observation(
        _adapter([
            {"asset": "USDT", "free": 10, "locked": 0, "total": 10},
            {"asset": "BTC", "free": 0.1, "locked": 0.02, "total": 0.12},
        ]),
        retrieved_at="2026-01-01T00:00:01+00:00",
    )
    assert len(observation.balances) == 2


def test_empty_balances_are_representable():
    observation = build_account_balance_observation(
        _adapter([]), retrieved_at="2026-01-01T00:00:01+00:00"
    )
    assert observation.balances == ()


def test_missing_account_identity_is_not_invented():
    observation = build_account_balance_observation(
        _adapter([], account={"account_type": "SPOT"}),
        retrieved_at="2026-01-01T00:00:01+00:00",
    )
    assert observation.account.account_id is None


def test_invalid_account_fails_closed():
    adapter = _adapter([])
    adapter._account = _Result({}, allowed=False, status="UNAVAILABLE")
    try:
        build_account_balance_observation(adapter, retrieved_at="2026-01-01T00:00:01+00:00")
    except RuntimeError:
        return
    raise AssertionError("invalid account must fail closed")


def test_invalid_balance_numeric_fails_closed():
    try:
        build_account_balance_observation(
            _adapter([{"asset": "USDT", "free": -1, "locked": 0, "total": 0}]),
            retrieved_at="2026-01-01T00:00:01+00:00",
        )
    except RuntimeError:
        return
    raise AssertionError("invalid balance numeric value must fail closed")


def test_missing_asset_fails_closed():
    try:
        build_account_balance_observation(
            _adapter([{"free": 1, "locked": 0, "total": 1}]),
            retrieved_at="2026-01-01T00:00:01+00:00",
        )
    except RuntimeError:
        return
    raise AssertionError("missing asset must fail closed")


def test_provenance_preserved_when_available():
    observation = build_account_balance_observation(
        _adapter([
            {
                "asset": "USDT",
                "free": 1,
                "locked": 0,
                "total": 1,
                "source_id": "BALANCE-SOURCE",
                "source_type": "TEST_FIXTURE_ONLY",
                "source_timestamp": "2026-01-01T00:00:00+00:00",
            }
        ]),
        retrieved_at="2026-01-01T00:00:01+00:00",
    )
    row = observation.balances[0]
    assert row.source_id == "BALANCE-SOURCE"
    assert row.source_type == "TEST_FIXTURE_ONLY"
    assert row.source_timestamp == "2026-01-01T00:00:00+00:00"


def test_missing_provenance_is_explicitly_unavailable():
    observation = build_account_balance_observation(
        _adapter(
            [{"asset": "USDT", "free": 1, "locked": 0, "total": 1}],
            account={"account_type": "SPOT"},
        ),
        retrieved_at="2026-01-01T00:00:01+00:00",
    )
    row = observation.balances[0]
    assert row.source_id is None
    assert row.source_type is None
    assert row.source_timestamp is None


def test_invalid_provenance_fails_closed():
    try:
        build_account_balance_observation(
            _adapter([{
                "asset": "USDT",
                "free": 1,
                "locked": 0,
                "total": 1,
                "source_id": 123,
            }]),
            retrieved_at="2026-01-01T00:00:01+00:00",
        )
    except RuntimeError:
        return
    raise AssertionError("invalid provenance must fail closed")


def test_missing_required_capability_fails_closed():
    adapter = _Adapter(
        _Result({}),
        _Result({"balances": []}),
        capabilities={"ACCOUNT_READ": True, "BALANCE_READ": False},
    )
    try:
        build_account_balance_observation(adapter, retrieved_at="2026-01-01T00:00:01+00:00")
    except RuntimeError:
        return
    raise AssertionError("unavailable balance capability must fail closed")


def test_immutable_observation():
    observation = build_account_balance_observation(
        _adapter([]), retrieved_at="2026-01-01T00:00:01+00:00"
    )
    try:
        observation.account = observation.account
    except Exception:
        return
    raise AssertionError("observation must be immutable")


def test_no_fixed_asset_count_assumption():
    rows = [
        {"asset": f"A{i}", "free": 1, "locked": 0, "total": 1}
        for i in range(21)
    ]
    observation = build_account_balance_observation(
        _adapter(rows), retrieved_at="2026-01-01T00:00:01+00:00"
    )
    assert len(observation.balances) == 21


def test_no_portfolio_risk_fields():
    observation = build_account_balance_observation(
        _adapter([]), retrieved_at="2026-01-01T00:00:01+00:00"
    )
    assert not hasattr(observation, "total_risk")
    assert not hasattr(observation, "total_exposure")
    assert not hasattr(observation, "concentration")
    assert not hasattr(observation, "correlation_exposure")
    assert not hasattr(observation, "usable_capital")


def test_deterministic_for_same_inputs_and_retrieval_timestamp():
    adapter = _adapter([
        {"asset": "USDT", "free": 10, "locked": 1, "total": 11},
        {"asset": "BTC", "free": 0.1, "locked": 0, "total": 0.1},
    ])
    retrieved_at = "2026-01-01T00:00:01+00:00"
    first = build_account_balance_observation(adapter, retrieved_at=retrieved_at)
    second = build_account_balance_observation(adapter, retrieved_at=retrieved_at)
    assert first == second


def test_invalid_retrieved_at_fails_closed():
    try:
        build_account_balance_observation(_adapter([]), retrieved_at="")
    except RuntimeError:
        return
    raise AssertionError("invalid retrieved_at must fail closed")
