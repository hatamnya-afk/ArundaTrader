from __future__ import annotations

import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

import app as authority


def setup_authority(tmp_path: Path, monkeypatch):
    private = Ed25519PrivateKey.generate()
    seed = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    monkeypatch.setattr(authority, "SOURCE_ID", "test-authority")
    monkeypatch.setattr(authority, "MANDATE_ID", "TEST-MANDATE-1")
    key_path = tmp_path / "private.key"
    key_path.write_text(base64.b64encode(seed).decode("ascii"), encoding="ascii")
    token_path = tmp_path / "admin.token"
    token_path.write_text("test-operator-token", encoding="ascii")
    state_path = tmp_path / "status.json"
    state_path.write_text(json.dumps({"mandate_id": "TEST-MANDATE-1", "status": "REVOKED"}), encoding="utf-8")
    monkeypatch.setattr(authority, "PRIVATE_KEY_FILE", key_path)
    monkeypatch.setattr(authority, "ADMIN_TOKEN_FILE", token_path)
    monkeypatch.setattr(authority, "STATE_FILE", state_path)
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(public).decode("ascii")


def verify_response(payload, public_b64):
    signed = {k: payload[k] for k in ("schema_version", "mandate_id", "status", "observed_at", "source_id")}
    canonical = json.dumps(signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    Ed25519PublicKey.from_public_bytes(base64.b64decode(public_b64)).verify(
        base64.b64decode(payload["signature"]), canonical
    )


def test_status_payload_signature_matches_trader_canonicalization_and_is_not_cached(tmp_path, monkeypatch):
    public_b64 = setup_authority(tmp_path, monkeypatch)
    response = TestClient(authority.app).get("/v1/mandate-status")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    payload = response.json()
    assert set(payload) == {"schema_version", "mandate_id", "status", "observed_at", "source_id", "signature"}
    assert payload["status"] == "REVOKED"
    verify_response(payload, public_b64)


def test_operator_auth_required_and_state_transition_is_signed(tmp_path, monkeypatch):
    public_b64 = setup_authority(tmp_path, monkeypatch)
    client = TestClient(authority.app)
    body = {"status": "ACTIVE", "reason": "Explicit authorized management activation"}
    assert client.put("/v1/mandate-status", json=body).status_code == 401
    assert client.put("/v1/mandate-status", json=body, headers={"Authorization": "Bearer wrong"}).status_code == 403
    changed = client.put(
        "/v1/mandate-status", json=body,
        headers={"Authorization": "Bearer test-operator-token"},
    )
    assert changed.status_code == 200
    assert changed.headers["cache-control"] == "no-store, max-age=0"
    signed = client.get("/v1/mandate-status")
    assert signed.status_code == 200
    payload = signed.json()
    assert payload["status"] == "ACTIVE"
    verify_response(payload, public_b64)
    audit = json.loads((authority.STATE_FILE.with_name("audit.jsonl")).read_text(encoding="utf-8").splitlines()[0])
    assert audit["event"] == "transition_request"
    assert audit["requested_status"] == "ACTIVE"


def test_extra_status_fields_rejected(tmp_path, monkeypatch):
    setup_authority(tmp_path, monkeypatch)
    response = TestClient(authority.app).put(
        "/v1/mandate-status",
        json={"status": "ACTIVE", "reason": "Authorized activation", "unexpected": True},
        headers={"Authorization": "Bearer test-operator-token"},
    )
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store, max-age=0"


def test_malformed_state_fails_closed_without_leaking_details(tmp_path, monkeypatch):
    setup_authority(tmp_path, monkeypatch)
    authority.STATE_FILE.write_text('{"mandate_id":"TEST-MANDATE-1","status":"ACTIVE","extra":true}', encoding="utf-8")
    response = TestClient(authority.app).get("/v1/mandate-status")
    assert response.status_code == 503
    assert response.json() == {"detail": "AUTHORITY_UNAVAILABLE"}
    assert response.headers["cache-control"] == "no-store, max-age=0"


def test_audit_write_failure_does_not_change_state(tmp_path, monkeypatch):
    setup_authority(tmp_path, monkeypatch)
    original_open = Path.open

    def fail_audit_open(path, *args, **kwargs):
        if path.name == "audit.jsonl":
            raise OSError("simulated audit storage failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_audit_open)
    response = TestClient(authority.app).put(
        "/v1/mandate-status",
        json={"status": "ACTIVE", "reason": "Explicit authorized activation"},
        headers={"Authorization": "Bearer test-operator-token"},
    )
    assert response.status_code == 500 or response.status_code == 503
    state = json.loads(authority.STATE_FILE.read_text(encoding="utf-8"))
    assert state["status"] == "REVOKED"


def test_state_write_failure_is_reported_and_audit_request_remains(tmp_path, monkeypatch):
    setup_authority(tmp_path, monkeypatch)

    def fail_state_write(status):
        raise RuntimeError("simulated state persistence failure")

    monkeypatch.setattr(authority, "_atomic_write_state", fail_state_write)
    response = TestClient(authority.app).put(
        "/v1/mandate-status",
        json={"status": "ACTIVE", "reason": "Explicit authorized activation"},
        headers={"Authorization": "Bearer test-operator-token"},
    )
    assert response.status_code == 503
    state = json.loads(authority.STATE_FILE.read_text(encoding="utf-8"))
    assert state["status"] == "REVOKED"
    audit_lines = authority.STATE_FILE.with_name("audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(audit_lines) == 1
    assert json.loads(audit_lines[0])["requested_status"] == "ACTIVE"


def test_invalid_private_key_fails_closed(tmp_path, monkeypatch):
    setup_authority(tmp_path, monkeypatch)
    authority.PRIVATE_KEY_FILE.write_text("not-base64!", encoding="ascii")
    response = TestClient(authority.app).get("/v1/mandate-status")
    assert response.status_code == 503
    assert response.json() == {"detail": "AUTHORITY_UNAVAILABLE"}
    assert response.headers["cache-control"] == "no-store, max-age=0"
