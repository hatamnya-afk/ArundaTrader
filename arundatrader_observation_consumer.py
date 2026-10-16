"""CP69 canonical observation reader owned by ArundaTrader's native UI.

Read-only: validates the producer contract and never imports AroondaAI,
Trader runtime modules, exchange clients, or database code.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import json

CP69_SCHEMA = "arunda.runtime_observation"
CP69_SCHEMA_VERSION = "1.0"
_REQUIRED = (
    "schema", "schema_version", "source_system", "environment_id",
    "adapter_id", "observation_id", "emitted_at", "provenance",
    "state", "execution_state",
)


@dataclass(frozen=True)
class CanonicalRuntimeObservation:
    schema: str
    schema_version: str
    source_system: str
    environment_id: str
    adapter_id: str
    observation_id: str
    emitted_at: str
    knowledge_cutoff: str | None
    provenance: dict[str, Any]
    state: dict[str, Any]
    execution_state: dict[str, Any]

    def __post_init__(self) -> None:
        for name in ("schema", "schema_version", "source_system", "environment_id",
                     "adapter_id", "observation_id", "emitted_at"):
            _require_text(name, getattr(self, name))
        if self.knowledge_cutoff is not None:
            _require_text("knowledge_cutoff", self.knowledge_cutoff)
        _require_dict("provenance", self.provenance)
        _require_dict("state", self.state)
        _require_dict("execution_state", self.execution_state)
        if self.schema != CP69_SCHEMA or self.schema_version != CP69_SCHEMA_VERSION:
            raise ValueError("unsupported CP69 schema/version")
        if self.source_system != "ArundaTrader":
            raise ValueError("canonical source system mismatch")
        if self.environment_id != "arundatrader":
            raise ValueError("canonical environment identity mismatch")
        if self.adapter_id != "arundatrader_adapter":
            raise ValueError("canonical adapter identity mismatch")
        _require_text("provenance.source", self.provenance.get("source"))
        _require_text("provenance.runtime_snapshot_id",
                      self.provenance.get("runtime_snapshot_id"))
        if self.execution_state.get("EXECUTION") != "OFF":
            raise ValueError("unexpected execution state: EXECUTION")
        if self.execution_state.get("REAL_ORDER") is not False:
            raise ValueError("unexpected execution state: REAL_ORDER")
        if self.execution_state.get("REAL_TRADE") is not False:
            raise ValueError("unexpected execution state: REAL_TRADE")
        db_writes = self.execution_state.get("DB_WRITES")
        if not isinstance(db_writes, int) or isinstance(db_writes, bool) or db_writes < 0:
            raise ValueError("invalid execution state: DB_WRITES")
        boundary = self.provenance.get("db_write_boundary")
        if db_writes > 0 and boundary != "CP49_AUTHORITATIVE_BIRTH_PERSISTENCE":
            raise ValueError("unauthorized production DB write boundary")
        if db_writes == 0 and boundary is not None:
            raise ValueError("DB write boundary present with zero writes")
        emitted = datetime.fromisoformat(self.emitted_at.replace("Z", "+00:00"))
        if emitted.tzinfo is None:
            raise ValueError("emitted_at must include timezone")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CanonicalRuntimeObservation":
        if not isinstance(payload, dict):
            raise TypeError("observation payload must be an object")
        missing = [key for key in _REQUIRED if key not in payload]
        if missing:
            raise ValueError(f"missing required observation fields: {missing}")
        return cls(
            schema=payload["schema"], schema_version=payload["schema_version"],
            source_system=payload["source_system"], environment_id=payload["environment_id"],
            adapter_id=payload["adapter_id"], observation_id=payload["observation_id"],
            emitted_at=payload["emitted_at"], knowledge_cutoff=payload.get("knowledge_cutoff"),
            provenance=payload["provenance"], state=payload["state"],
            execution_state=payload["execution_state"],
        )


def read_latest_observation(path: Path) -> CanonicalRuntimeObservation:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"CP69 stream not found: {path}")
    latest: tuple[int, str] | None = None
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                latest = (line_number, line)
    if latest is None:
        raise ValueError("CP69 stream has no observations")
    line_number, raw = latest
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"latest CP69 record is invalid JSON at line {line_number}") from exc
    return CanonicalRuntimeObservation.from_dict(payload)


def _require_text(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_dict(name: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a dict")
