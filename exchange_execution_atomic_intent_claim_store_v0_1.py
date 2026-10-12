"""Durable, provider-neutral per-intent claim store (offline contract only).

This module is deliberately NOT wired into any execution path. The caller must
supply an isolated SQLite file path; never pass the production trading database.
A successful claim is permanent: this contract has no release/delete operation.
Timeouts, crashes, and unknown provider outcomes therefore cannot silently free
an intent for a second submission.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


CLAIMED = "CLAIMED"
SUBMISSION_OUTCOME_UNKNOWN = "SUBMISSION_OUTCOME_UNKNOWN"
RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
PROVIDER_ACCEPTED = "PROVIDER_ACCEPTED"
PROVIDER_REJECTED = "PROVIDER_REJECTED"
_ALLOWED_STATES = {
    CLAIMED,
    SUBMISSION_OUTCOME_UNKNOWN,
    RECONCILIATION_REQUIRED,
    PROVIDER_ACCEPTED,
    PROVIDER_REJECTED,
}


@dataclass(frozen=True)
class ClaimResult:
    outcome: str
    provider_namespace: str
    intent_id: str
    client_order_id: str
    status: Optional[str] = None


@dataclass(frozen=True)
class IntentClaim:
    provider_namespace: str
    intent_id: str
    client_order_id: str
    status: str
    created_at_utc: str
    updated_at_utc: str
    trade_event_id: Optional[str]
    decision_id: Optional[str]
    exchange_order_id: Optional[str]
    provider_status: Optional[str]
    evidence_event_id: Optional[str]
    detail_code: Optional[str]


class SQLiteIntentClaimStore:
    """SQLite UNIQUE-key claim store intended for isolated/offline validation.

    SQLite transactions and constraints are the actual concurrency mechanism;
    no in-memory lock or read-then-append JSONL pattern is used. The caller is
    responsible for selecting a durable path and protecting its filesystem.
    """

    def __init__(self, path: str | Path, *, timeout_seconds: float = 10.0):
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("SQLITE_TIMEOUT_INVALID")
        self.path = str(path)
        if not self.path.strip() or self.path == ":memory:":
            raise ValueError("DURABLE_SQLITE_PATH_REQUIRED")
        self.timeout_seconds = float(timeout_seconds)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path, timeout=self.timeout_seconds, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {int(self.timeout_seconds * 1000)}")
        return connection

    def _initialize(self) -> None:
        parent = Path(self.path).expanduser().resolve().parent
        if not parent.exists():
            raise ValueError("CLAIM_STORE_PARENT_DIRECTORY_MISSING")
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_intent_claim (
                    provider_namespace TEXT NOT NULL,
                    intent_id TEXT NOT NULL,
                    client_order_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    trade_event_id TEXT,
                    decision_id TEXT,
                    exchange_order_id TEXT,
                    provider_status TEXT,
                    evidence_event_id TEXT,
                    detail_code TEXT,
                    PRIMARY KEY (provider_namespace, intent_id),
                    UNIQUE (provider_namespace, client_order_id),
                    CHECK (status IN (
                        'CLAIMED', 'SUBMISSION_OUTCOME_UNKNOWN',
                        'RECONCILIATION_REQUIRED', 'PROVIDER_ACCEPTED',
                        'PROVIDER_REJECTED'
                    ))
                )
                """
            )
        finally:
            connection.close()

    @staticmethod
    def _required(value: str, reason: str) -> str:
        result = value.strip() if isinstance(value, str) else ""
        if not result:
            raise ValueError(reason)
        return result

    def claim(
        self, *, provider_namespace: str, intent_id: str, client_order_id: str
    ) -> ClaimResult:
        """Atomically claim one provider-scoped intent; never reopens a claim."""
        provider = self._required(provider_namespace, "PROVIDER_NAMESPACE_REQUIRED").upper()
        intent = self._required(intent_id, "CANONICAL_INTENT_ID_REQUIRED")
        client_id = self._required(client_order_id, "CLIENT_ORDER_ID_REQUIRED")
        now = datetime.now(timezone.utc).isoformat()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    INSERT INTO execution_intent_claim
                    (provider_namespace, intent_id, client_order_id, status,
                     created_at_utc, updated_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (provider, intent, client_id, CLAIMED, now, now),
                )
                connection.execute("COMMIT")
                return ClaimResult("CLAIMED", provider, intent, client_id, CLAIMED)
            except sqlite3.IntegrityError:
                row = connection.execute(
                    """
                    SELECT client_order_id, status FROM execution_intent_claim
                    WHERE provider_namespace = ? AND intent_id = ?
                    """,
                    (provider, intent),
                ).fetchone()
                if row is not None:
                    connection.execute("ROLLBACK")
                    if row["client_order_id"] == client_id:
                        return ClaimResult("ALREADY_CLAIMED", provider, intent, client_id, row["status"])
                    return ClaimResult("IDENTITY_CONFLICT", provider, intent, client_id, row["status"])
                collision = connection.execute(
                    """
                    SELECT intent_id, status FROM execution_intent_claim
                    WHERE provider_namespace = ? AND client_order_id = ?
                    """,
                    (provider, client_id),
                ).fetchone()
                connection.execute("ROLLBACK")
                return ClaimResult(
                    "CLIENT_ORDER_ID_COLLISION", provider, intent, client_id,
                    collision["status"] if collision is not None else None,
                )
        except sqlite3.Error:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def transition(
        self, *, provider_namespace: str, intent_id: str, status: str,
        trade_event_id: Optional[str] = None,
        decision_id: Optional[str] = None,
        exchange_order_id: Optional[str] = None,
        provider_status: Optional[str] = None,
        evidence_event_id: Optional[str] = None,
        detail_code: Optional[str] = None,
    ) -> IntentClaim:
        """Record evidence/status on an existing claim; never creates or releases one."""
        provider = self._required(provider_namespace, "PROVIDER_NAMESPACE_REQUIRED").upper()
        intent = self._required(intent_id, "CANONICAL_INTENT_ID_REQUIRED")
        if status not in _ALLOWED_STATES:
            raise ValueError("CLAIM_STATUS_INVALID")
        now = datetime.now(timezone.utc).isoformat()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT status FROM execution_intent_claim
                WHERE provider_namespace = ? AND intent_id = ?
                """,
                (provider, intent),
            ).fetchone()
            if row is None:
                connection.execute("ROLLBACK")
                raise KeyError("INTENT_CLAIM_NOT_FOUND")
            old_status = row["status"]
            if old_status in (PROVIDER_ACCEPTED, PROVIDER_REJECTED) and status != old_status:
                connection.execute("ROLLBACK")
                raise ValueError("TERMINAL_CLAIM_STATE_CANNOT_CHANGE")
            allowed_next = {
                CLAIMED: {CLAIMED, SUBMISSION_OUTCOME_UNKNOWN, RECONCILIATION_REQUIRED, PROVIDER_ACCEPTED, PROVIDER_REJECTED},
                SUBMISSION_OUTCOME_UNKNOWN: {SUBMISSION_OUTCOME_UNKNOWN, RECONCILIATION_REQUIRED, PROVIDER_ACCEPTED, PROVIDER_REJECTED},
                RECONCILIATION_REQUIRED: {RECONCILIATION_REQUIRED, PROVIDER_ACCEPTED, PROVIDER_REJECTED},
                PROVIDER_ACCEPTED: {PROVIDER_ACCEPTED},
                PROVIDER_REJECTED: {PROVIDER_REJECTED},
            }
            if status not in allowed_next.get(old_status, set()):
                connection.execute("ROLLBACK")
                raise ValueError("CLAIM_STATE_TRANSITION_INVALID")
            if status == PROVIDER_ACCEPTED and (not exchange_order_id or not provider_status):
                connection.execute("ROLLBACK")
                raise ValueError("ACCEPTED_ORDER_EVIDENCE_REQUIRED")
            if status == PROVIDER_REJECTED and not (provider_status or detail_code):
                connection.execute("ROLLBACK")
                raise ValueError("REJECTION_EVIDENCE_REQUIRED")
            if old_status == RECONCILIATION_REQUIRED and status == CLAIMED:
                connection.execute("ROLLBACK")
                raise ValueError("CLAIM_CANNOT_BE_REOPENED")
            connection.execute(
                """
                UPDATE execution_intent_claim
                SET status = ?, updated_at_utc = ?,
                    trade_event_id = COALESCE(?, trade_event_id),
                    decision_id = COALESCE(?, decision_id),
                    exchange_order_id = COALESCE(?, exchange_order_id),
                    provider_status = COALESCE(?, provider_status),
                    evidence_event_id = COALESCE(?, evidence_event_id),
                    detail_code = COALESCE(?, detail_code)
                WHERE provider_namespace = ? AND intent_id = ?
                """,
                (status, now, trade_event_id, decision_id, exchange_order_id,
                 provider_status, evidence_event_id, detail_code, provider, intent),
            )
            connection.execute("COMMIT")
        except (sqlite3.Error, KeyError, ValueError):
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        result = self.get(provider_namespace=provider, intent_id=intent)
        if result is None:
            raise RuntimeError("CLAIM_DISAPPEARED_AFTER_COMMIT")
        return result

    def get(self, *, provider_namespace: str, intent_id: str) -> Optional[IntentClaim]:
        provider = self._required(provider_namespace, "PROVIDER_NAMESPACE_REQUIRED").upper()
        intent = self._required(intent_id, "CANONICAL_INTENT_ID_REQUIRED")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM execution_intent_claim WHERE provider_namespace = ? AND intent_id = ?",
                (provider, intent),
            ).fetchone()
        finally:
            connection.close()
        return IntentClaim(**dict(row)) if row is not None else None


__all__ = [
    "CLAIMED", "SUBMISSION_OUTCOME_UNKNOWN", "RECONCILIATION_REQUIRED",
    "PROVIDER_ACCEPTED", "PROVIDER_REJECTED", "ClaimResult", "IntentClaim",
    "SQLiteIntentClaimStore",
]
