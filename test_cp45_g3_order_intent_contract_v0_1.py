
import ast
from pathlib import Path

import arunda_pipeline as pipeline


PIPELINE = Path("arunda_pipeline.py")
FORBIDDEN = {
    "order_id",
    "exchange",
    "exchange_order_id",
    "adapter",
    "api_request",
    "signature",
    "submitted",
    "executed_quantity",
    "executed_price",
    "trade_id",
    "execution_authorization",
    "future_outcome",
    "realized_return",
    "pnl",
    "exit_price",
}


def test_cp45_required_order_intent_contract_is_exactly_eleven_fields():
    expected = {
        "asset",
        "direction",
        "entry_price",
        "quantity",
        "quantity_unit",
        "quantity_source",
        "confidence",
        "regime",
        "timestamp",
        "snapshot_id",
        "intent_id",
    }
    assert set(pipeline.CURRENT_ORDER_INTENT_REQUIRED_FIELDS) == expected
    assert len(pipeline.CURRENT_ORDER_INTENT_REQUIRED_FIELDS) == 11


def test_cp45_direction_contract_is_long_short_only():
    assert set(pipeline.VALID_DIRECTIONS) == {"LONG", "SHORT"}


def test_cp45_runtime_order_intent_contains_exact_contract():
    intent = pipeline.RuntimeOrderIntent(
        asset="BTC/USDT",
        direction="LONG",
        entry_price=100,
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="POSITION_SIZING.position_size",
        confidence=0.9,
        regime="TEST",
        timestamp="2026-01-01T00:00:00",
        snapshot_id="SNAPSHOT-1",
        intent_id="OI-SNAPSHOT-1-BTC/USDT",
    )
    assert set(intent.keys()) == set(pipeline.CURRENT_ORDER_INTENT_REQUIRED_FIELDS)


def test_cp45_quantity_is_not_recomputed_by_canonical_request_builder():
    import inspect
    import exchange_execution_contract

    sig = inspect.signature(exchange_execution_contract.build_order_request)
    assert "quantity" not in sig.parameters

    source = inspect.getsource(exchange_execution_contract.build_order_request)
    assert 'quantity = risk["position_quantity"]' in source


def test_cp45_bridge_does_not_pass_quantity_argument_or_infer_reference_price():
    tree = ast.parse(PIPELINE.read_text(encoding="utf-8-sig"))

    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr == "build_order_request":
                names = {kw.arg for kw in node.keywords if kw.arg is not None}
                if "risk" in names and "intent_id" in names and "snapshot_id" in names:
                    found = True
                    assert "quantity" not in names
                    ref = next(
                        kw for kw in node.keywords if kw.arg == "reference_price"
                    )
                    assert isinstance(ref.value, ast.Constant)
                    assert ref.value.value is None

    assert found


def test_cp45_forbidden_execution_fields_are_absent_from_order_intent_contract():
    fields = set(pipeline.CURRENT_ORDER_INTENT_REQUIRED_FIELDS)
    assert not fields.intersection(FORBIDDEN)


def test_cp45_order_intent_contract_is_exchange_agnostic():
    source = "\n".join(
        f"{Path(path).name}\n{Path(path).read_text(encoding='utf-8')}"
        for path in [
            "arunda_pipeline.py",
        ]
    )
    forbidden_exchange_terms = {
        "exchange_order_id",
        "api_request",
        "signature",
        "submitted",
        "executed_quantity",
        "executed_price",
        "trade_id",
    }
    contract_start = source.find("CURRENT_ORDER_INTENT_REQUIRED_FIELDS")
    assert contract_start >= 0
    contract_slice = source[contract_start:source.find(")", contract_start) + 1]
    assert not any(term in contract_slice for term in forbidden_exchange_terms)


def test_cp45_arbitrary_cardinality_has_no_fixed_order_intent_count():
    source = PIPELINE.read_text(encoding="utf-8-sig")
    assert "len(intents) == 15" not in source
    assert "len(order_intents) == 15" not in source
    assert "== 15" not in source
    assert "== 6" not in source
    assert "== 10" not in source

 
def test_cp45_canonical_request_quantity_is_exactly_risk_quantity():
    import exchange_execution_contract

    risk_quantity = 7.25
    request = exchange_execution_contract.build_order_request(
        asset="BTC/USDT",
        direction="LONG",
        order_type="MARKET",
        risk={"position_quantity": risk_quantity},
        entry_price=100,
        reference_price=None,
        intent_id="OI-S1-BTC/USDT",
        snapshot_id="S1",
        timestamp="2026-01-01T00:00:00",
    )

    assert request.quantity == risk_quantity
    assert request.quantity_unit == "BASE_ASSET"
    assert request.quantity_source == "RISK.position_quantity"


def test_cp45_canonical_request_rejects_missing_quantity_provenance():
    import exchange_execution_contract
    import pytest

    with pytest.raises(ValueError, match="QUANTITY_PROVENANCE_MISSING"):
        exchange_execution_contract.build_order_request(
            asset="BTC/USDT",
            direction="LONG",
            order_type="MARKET",
            risk={},
            entry_price=100,
            reference_price=None,
            intent_id="OI-S1-BTC/USDT",
            snapshot_id="S1",
            timestamp="2026-01-01T00:00:00",
        )


def test_cp45_canonical_request_rejects_unavailable_quantity():
    import exchange_execution_contract
    import pytest

    with pytest.raises(ValueError, match="QUANTITY_UNAVAILABLE"):
        exchange_execution_contract.build_order_request(
            asset="BTC/USDT",
            direction="LONG",
            order_type="MARKET",
            risk={"position_quantity": None},
            entry_price=100,
            reference_price=None,
            intent_id="OI-S1-BTC/USDT",
            snapshot_id="S1",
            timestamp="2026-01-01T00:00:00",
        )


def test_cp45_bridge_preserves_identity_fields_without_replacement():
    source = PIPELINE.read_text(encoding="utf-8-sig")
    start = source.find("def build_canonical_order_requests(")
    assert start >= 0
    section = source[start:source.find("\ndef ", start + 5)]

    assert 'intent["direction"]' in section
    assert 'intent["entry_price"]' in section
    assert 'intent["intent_id"]' in section
    assert "snapshot_id=snapshot_id" in section


def test_cp45_bridge_does_not_recalculate_or_rescale_quantity():
    source = PIPELINE.read_text(encoding="utf-8-sig")
    start = source.find("def build_canonical_order_requests(")
    assert start >= 0
    section = source[start:source.find("\ndef ", start + 5)]

    forbidden_quantity_transforms = (
        "round(quantity",
        "quantity *",
        "quantity /",
        "quantity +",
        "quantity -",
        "min(quantity",
        "max(quantity",
        "abs(quantity",
        "float(quantity",
        "int(quantity",
    )

    assert not any(token in section for token in forbidden_quantity_transforms)


def test_cp45_bridge_keeps_order_intent_distinct_from_canonical_request():
    source = PIPELINE.read_text(encoding="utf-8-sig")

    intent_start = source.find("CURRENT_ORDER_INTENT_REQUIRED_FIELDS")
    request_start = source.find("def build_canonical_order_requests(")

    assert intent_start >= 0
    assert request_start >= 0

    intent_contract = source[intent_start:request_start]

    assert "order_type" not in intent_contract
    assert "reference_price" not in intent_contract
    assert "exchange_order_id" not in intent_contract
    assert "api_request" not in intent_contract


def test_cp45_bridge_is_fail_closed_on_quantity_mismatch():
    source = PIPELINE.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "build_canonical_order_requests"
    )
    section = ast.get_source_segment(source, function)
    assert section is not None

    assert 'position_quantity' in section
    assert 'getattr(' in section
    assert '"quantity"' in section
    assert 'Canonical quantity mismatch' in section
    assert "fail(" in section


def test_cp45_no_silent_reference_price_inference():
    source = PIPELINE.read_text(encoding="utf-8-sig")
    start = source.find("def build_canonical_order_requests(")
    assert start >= 0
    section = source[start:source.find("\ndef ", start + 5)]

    assert "reference_price=None" in section
    assert "reference_price=entry_price" not in section
    assert "reference_price=quantity" not in section


def test_cp45_no_fixed_runtime_cardinality_in_bridge():
    source = PIPELINE.read_text(encoding="utf-8-sig")
    start = source.find("def build_canonical_order_requests(")
    assert start >= 0
    section = source[start:source.find("\ndef ", start + 5)]

    for fixed_count in ("15", "10", "6", "4"):
        assert f"== {fixed_count}" not in section
        assert f"len(order_intents) == {fixed_count}" not in section
        assert f"len(intents) == {fixed_count}" not in section




