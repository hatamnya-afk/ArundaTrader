"""Canonical Decision Identity boundary for CP49.

Consumes identity already present in the real Decision producer. It never
creates, derives, hashes, or substitutes a decision identifier.
"""
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CanonicalDecisionIdentity:
    decision_id: str
    snapshot_id: str
    asset: str
    decision_timestamp_ms: int


@dataclass(frozen=True)
class CanonicalDecisionIdentityResult:
    status: str
    reason: str
    identity: CanonicalDecisionIdentity | None = None


def build_canonical_decision_identity(data: Mapping[str, Any]) -> CanonicalDecisionIdentityResult:
    if not isinstance(data, Mapping):
        return CanonicalDecisionIdentityResult("BLOCK", "CANONICAL_DECISION_RECORD_INVALID")
    decision_id = data.get("decision_id")
    if not isinstance(decision_id, str) or not decision_id.strip():
        return CanonicalDecisionIdentityResult("BLOCK", "CANONICAL_DECISION_ID_MISSING")
    snapshot_id = data.get("snapshot_id")
    asset = data.get("asset")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        return CanonicalDecisionIdentityResult("BLOCK", "CANONICAL_SNAPSHOT_ID_MISSING")
    if not isinstance(asset, str) or not asset.strip():
        return CanonicalDecisionIdentityResult("BLOCK", "CANONICAL_ASSET_MISSING")
    timestamp = data.get("decision_timestamp_ms")
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp <= 0:
        return CanonicalDecisionIdentityResult("BLOCK", "DECISION_TIMESTAMP_INVALID")
    return CanonicalDecisionIdentityResult(
        "PASS", "CANONICAL_DECISION_IDENTITY_VALID",
        CanonicalDecisionIdentity(decision_id.strip(), snapshot_id.strip(), asset.strip(), timestamp),
    )
