"""Offline tests for explicit runtime dependency wiring and DB isolation."""

from pathlib import Path

import pytest

from execution_dependency_runtime_factory_v0_1 import load_execution_dependencies


def test_factory_requires_both_explicit_opt_in_switches(monkeypatch, tmp_path):
    monkeypatch.delenv("ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT", raising=False)
    monkeypatch.delenv("ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION", raising=False)
    with pytest.raises(ValueError, match="NOT_EXPLICITLY_ENABLED"):
        load_execution_dependencies(production_database_path=tmp_path / "arunda.db")


def test_factory_rejects_claim_store_path_equal_to_production_db(monkeypatch, tmp_path):
    production = tmp_path / "arunda.db"
    production.touch()
    monkeypatch.setenv("ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT", "1")
    monkeypatch.setenv("ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION", "1")
    monkeypatch.setenv("ARUNDA_EXECUTION_CLAIM_DB", str(production))
    monkeypatch.setenv("TOOBIT_API_KEY", "fixture-key")
    monkeypatch.setenv("TOOBIT_API_SECRET", "fixture-secret")
    with pytest.raises(ValueError, match="MUST_NOT_USE_PRODUCTION_DATABASE"):
        load_execution_dependencies(production_database_path=production)


def test_factory_injects_adapter_and_separate_durable_claim_store(monkeypatch, tmp_path):
    production = tmp_path / "arunda.db"
    production.touch()
    claim_path = tmp_path / "execution" / "claims.sqlite3"
    claim_path.parent.mkdir()
    monkeypatch.setenv("ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT", "1")
    monkeypatch.setenv("ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION", "1")
    monkeypatch.setenv("ARUNDA_EXECUTION_CLAIM_DB", str(claim_path))
    monkeypatch.setenv("TOOBIT_API_KEY", "fixture-key")
    monkeypatch.setenv("TOOBIT_API_SECRET", "fixture-secret")

    adapter, store = load_execution_dependencies(production_database_path=production)
    assert adapter.adapter_name == "TOOBIT"
    assert adapter.capabilities().order_submission is True
    assert Path(store.path).resolve() == claim_path.resolve()
    assert Path(store.path).resolve() != production.resolve()
    assert claim_path.exists()
