## STANDING-MANDATE LIFECYCLE — DURABLE JOURNAL CONTRACT PASS (2026-10-15)

- Standing phase-entry mandate is non-expiring by default; explicit expiry remains optional and is enforced when provided. Per-trade management approval remains forbidden.
- Technical authorization rejects missing/invalid lifecycle history and revoked or superseded mandate identities. The append-only JSONL lifecycle journal supports management ACTIVATE/REVOKE/REPLACE events, validates transitions before append, fsyncs committed rows, and uses an OS lock for append coordination.
- Focused CI: **28 passed in 0.16s** (run [38726220987](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38726220987)); outcome-evidence CI also passed (run [38726221006](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38726221006)).
- **Remaining integration gate:** no production runtime currently reads the durable journal before every execution authorization, and the authoritative journal path/access-control/backup policy has not been configured or verified. Therefore lifecycle revocation/replacement is implemented and offline-tested, but not yet enforced by the operational production path. Keep provider submission disabled, do not merge PR #38, and do not claim real-order readiness.

# Standing Mandate Lifecycle Contract v0.1

## Policy

The REAL_PRODUCTION phase-entry mandate is a one-time standing management decision. It does not expire by default and never requires per-trade management approval. An explicit expiry remains supported only when management has actually selected one.

Revocation and replacement are explicit management lifecycle events, not timeouts.

## Lifecycle events

The pure reducer in `standing_mandate_lifecycle_v0_1.py` accepts an ordered lifecycle history:
- `ACTIVATE`: activates a mandate when no other mandate is active.
- `REVOKE`: revokes the currently active mandate.
- `REPLACE`: supersedes the currently active mandate with a new mandate identity.

Every event must have a unique `event_id` and `authority="MANAGEMENT"`. Invalid transitions, duplicate IDs, untrusted authority, stale/revoked/superseded identities, and missing history fail closed at technical authorization.

## Persistence and authority requirement

The reducer is deliberately pure and does not write a database or filesystem. The caller must supply the authoritative, append-only lifecycle history and preserve it across process restarts. The one-event history emitted at phase-entry is an initial event seed only; it is **not** a durable revocation registry by itself.

Until a durable authoritative event source is connected and its read path is verified, the lifecycle logic is contract-tested but is not production-operational. Do not treat this PR or its offline tests as production authorization, do not enable provider submission, and do not merge based on these tests alone.

## Verification scope

Tests cover non-expiring mandates, optional explicit expiry, readiness/market constraints, revocation, replacement, replacement identity, duplicate lifecycle event IDs, and invalid event authority. All tests are offline. No exchange API, order, cancellation, withdrawal, database write, or production runtime is used.
