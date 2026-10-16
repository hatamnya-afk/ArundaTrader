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


def test_status_payload_signature_matches_trader_canonicalization(tmp_path, monkeypatch):
    public_b64 = setup_authority(tmp_path, monkeypatch)
    response = TestClient(authority.app).get("/v1/mandate-status")
    assert response.status_code == 200
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
    signed = client.get("/v1/mandate-status")
    assert signed.status_code == 200
    payload = signed.json()
    assert payload["status"] == "ACTIVE"
    verify_response(payload, public_b64)


def test_extra_status_fields_rejected(tmp_path, monkeypatch):
    setup_authority(tmp_path, monkeypatch)
    response = TestClient(authority.app).put(
        "/v1/mandate-status",
        json={"status": "ACTIVE", "reason": "Authorized activation", "unexpected": True},
        headers={"Authorization": "Bearer test-operator-token"},
    )
    assert response.status_code == 422
