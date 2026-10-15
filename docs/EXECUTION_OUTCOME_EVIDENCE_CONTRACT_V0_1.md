# Execution Outcome Evidence Contract v0.1

Status: additive contract candidate; not wired to production execution.

## Purpose

Represent a provider response or read-only lookup as append-only outcome evidence tied to the authoritative Decision, intent, attempt, and client-order identities. This is separate from market-performance outcomes and does not create a trade or submit an order.

## Safety and interpretation

- The caller must supply an explicit evidence stream path; there is no implicit production path.
- The module makes no network calls and does not call Toobit.
- OPEN/NEW/ACCEPTED never implies a fill.
- FILLED and PARTIALLY_FILLED require explicit positive execution quantity and price; incomplete records remain explicitly incomplete.
- CANCELED/CANCELLED/EXPIRED without execution quantity remain unreconciled; terminal status alone does not prove zero fills.
- Unknown provider statuses remain UNKNOWN.
- Every record has `fill_inferred=false`.
- Event identity is bound to provider + trade event + source kind + provider observation ID. Reusing that source identity with a different payload fails closed.
- Persistence is append-only and idempotent for one process. It is **not** a cross-process lock, durable order claim, or exactly-once guarantee.

## Explicitly not completed

- No live provider response has been captured by this contract.
- No adapter integration, production pipeline wiring, authorization change, order write, cancellation, database write, or runtime was performed.
- Provider-specific status mapping and live outcome semantics still require adapter-backed evidence.
- This contract does not clear the final real-order gate.
