"""Independent Ed25519 management mandate authority.

The signing private key and operator token are read only from mounted secret files.
This service is deployed separately from ArundaTrader. Never mount its secrets in
the trading runtime or commit secret files to source control.
"""
from __future__ import annotations

import hmac
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

SCHEMA_VERSION = "1"
SOURCE_ID = os.environ.get("ARUNDA_AUTHORITY_SOURCE_ID", "").strip()
MANDATE_ID = os.environ.get("ARUNDA_AUTHORITY_MANDATE_ID", "").strip()
STATE_FILE = Path(os.environ.get("ARUNDA_AUTHORITY_STATE_FILE", "/var/lib/arunda-authority/status.json"))
PRIVATE_KEY_FILE = Path(os.environ.get("ARUNDA_AUTHORITY_PRIVATE_KEY_FILE", "/run/secrets/ed25519_private_key_b64"))
ADMIN_TOKEN_FILE = Path(os.environ.get("ARUNDA_AUTHORITY_ADMIN_TOKEN_FILE", "/run/secrets/authority_admin_token"))
_LOCK = threading.RLock()
app = FastAPI(title="Arunda Management Mandate Authority", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def prevent_response_caching(request: Request, call_next):
    """Never let clients or intermediaries cache time-sensitive authority responses."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["ACTIVE", "REVOKED"]
    reason: str = Field(min_length=8, max_length=500)


def _read_secret(path: Path) -> bytes:
    try:
        data = path.read_bytes().strip()
    except OSError as exc:
        raise RuntimeError("AUTHORITY_SECRET_UNAVAILABLE") from exc
    if not data:
        raise RuntimeError("AUTHORITY_SECRET_EMPTY")
    return data


def _private_key() -> Ed25519PrivateKey:
    import base64
    import binascii

    raw_text = _read_secret(PRIVATE_KEY_FILE)
    try:
        raw = base64.b64decode(raw_text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("AUTHORITY_PRIVATE_KEY_INVALID") from exc
    if len(raw) != 32:
        raise RuntimeError("AUTHORITY_PRIVATE_KEY_INVALID")
    return Ed25519PrivateKey.from_private_bytes(raw)


def _state() -> dict[str, str]:
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("AUTHORITY_STATE_UNAVAILABLE") from exc
    if not isinstance(value, dict) or set(value) != {"mandate_id", "status"}:
        raise RuntimeError("AUTHORITY_STATE_INVALID")
    if value["mandate_id"] != MANDATE_ID or value["status"] not in ("ACTIVE", "REVOKED"):
        raise RuntimeError("AUTHORITY_STATE_INVALID")
    return value


def _signed_response() -> dict[str, str]:
    if not SOURCE_ID or not MANDATE_ID:
        raise RuntimeError("AUTHORITY_IDENTITY_NOT_CONFIGURED")
    state = _state()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "mandate_id": state["mandate_id"],
        "status": state["status"],
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_id": SOURCE_ID,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    import base64

    payload["signature"] = base64.b64encode(_private_key().sign(canonical)).decode("ascii")
    return payload


def _require_operator(authorization: str | None) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    supplied = authorization[7:].encode("utf-8")
    try:
        expected = _read_secret(ADMIN_TOKEN_FILE)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="AUTHORITY_UNAVAILABLE") from exc
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="AUTHENTICATION_FAILED")


def _fsync_directory(path: Path) -> None:
    """Persist directory-entry changes where supported by the deployment OS."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_fd = os.open(str(path), flags)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _atomic_write_state(status: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps({"mandate_id": MANDATE_ID, "status": status}, sort_keys=True) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=".status-", dir=str(STATE_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, STATE_FILE)
        _fsync_directory(STATE_FILE.parent)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


@app.get("/v1/mandate-status")
def get_mandate_status() -> dict[str, str]:
    """Public read-only endpoint; payload authenticity comes from Ed25519 + HTTPS."""
    try:
        with _LOCK:
            return _signed_response()
    except (RuntimeError, OSError) as exc:
        # Do not leak file paths, secret material, or cryptographic details.
        raise HTTPException(status_code=503, detail="AUTHORITY_UNAVAILABLE") from exc


@app.get("/readyz")
def readiness() -> dict[str, str]:
    """Deployment readiness, distinct from process liveness and mandate activation."""
    try:
        with _LOCK:
            if not SOURCE_ID or not MANDATE_ID:
                raise RuntimeError("AUTHORITY_IDENTITY_NOT_CONFIGURED")
            _state()
            _private_key()
        return {"service": "arunda-management-authority", "ready": "true"}
    except (RuntimeError, OSError) as exc:
        raise HTTPException(status_code=503, detail="AUTHORITY_NOT_READY") from exc


@app.put("/v1/mandate-status")
def update_mandate_status(
    update: StatusUpdate,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    """Authenticated management-only status transition; audit reason is not returned."""
    _require_operator(authorization)
    if not MANDATE_ID or not SOURCE_ID:
        raise HTTPException(status_code=503, detail="AUTHORITY_NOT_CONFIGURED")
    try:
        with _LOCK:
            current = _state()
            audit_path = STATE_FILE.with_name("audit.jsonl")
            audit = {
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": "transition_request",
                "mandate_id": MANDATE_ID,
                "from": current["status"],
                "requested_status": update.status,
                "reason": update.reason,
            }
            # Audit the request before mutating state. If audit persistence fails,
            # the requested transition is not applied.
            with audit_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(audit, sort_keys=True, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            _atomic_write_state(update.status)
            return {"mandate_id": MANDATE_ID, "status": update.status, "result": "RECORDED"}
    except (RuntimeError, OSError) as exc:
        raise HTTPException(status_code=503, detail="AUTHORITY_UNAVAILABLE") from exc


@app.get("/healthz")
def health() -> dict[str, str]:
    # Liveness only; intentionally does not reveal mandate status or secret health.
    return {"service": "arunda-management-authority", "status": "ok"}
