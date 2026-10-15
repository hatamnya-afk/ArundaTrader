## SERVICE CONFIGURATION + OPERATIONAL PATH AUDIT — 2026-10-15

- Candidate branch now contains a Windows persistent-journal configuration script (`ops/Configure-ArundaMandateJournal.ps1`), a validated/dry-run-first management activation CLI (`ops/Activate-ArundaStandingMandate.py`), the structured phase-entry observation, and a read-only startup preflight (`standing_mandate_service_preflight_v0_1.py`).
- Configuration defaults to `C:\\ProgramData\\ArundaTrader\\security\\standing_mandate_lifecycle.jsonl`, requires the actual runtime identity as an explicit parameter, applies restrictive ACLs to the directory and existing journal/lock files, and sets machine-level `ARUNDA_MANDATE_LIFECYCLE_PATH`. It does not write or seed the journal. The activation CLI defaults to dry-run and writes ACTIVATE only with explicit `--confirm-activate`.
- Focused CI: standing-mandate + startup/activation preflight **54 passed** ([run 38728746302](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38728746302)); execution-outcome evidence **58 passed** ([run 38728746246](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38728746246)).
- Operational path audit on `operational-main-20261007`: `arunda_pipeline.py` still calls `exchange_execution_boundary.execute_order`; `EXECUTION_ENABLED=False`; the operational Toobit adapter advertises `order_submission=False` and fail-closes submission. The candidate lifecycle-aware attempt boundary is not wired into the operational pipeline.
- **Not deployed / NOT VERIFIED:** this repository-only session cannot inspect the Windows host, identify the actual service/task identity, apply the host ACL/environment, persist the management activation event, restart the process, or run host preflight. Do not represent the journal as configured or the operational path as connected until those host checks pass.
- Safety remains unchanged: no operational branch edits, no merge, no production runtime, no provider/database writes, no order/cancel/withdrawal, and no execution flag activation. PR #38 remains open/unmerged. Provider client-order-ID and ambiguous POST recovery semantics remain unresolved.

## DURABLE MANDATE JOURNAL — CANDIDATE INTEGRATION PASS (2026-10-15)

- Connected the durable lifecycle journal to the isolated provider-neutral order-attempt boundary. Every attempt now requires `ARUNDA_MANDATE_LIFECYCLE_PATH`, rereads authoritative journal history, and overwrites any in-memory lifecycle snapshot before authorization. Missing path/history, corrupt journal, revoked or replaced mandate fail closed before adapter submission.
- Added explicit `record_management_phase_entry(...)` to persist activation from a validated authorized REAL_PRODUCTION phase-entry result. Runtime never silently seeds or repairs the journal.
- Focused standing-mandate CI: **42 passed in 0.17s** ([run 38727000052](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38727000052)); execution-outcome CI passed ([run 38727000334](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38727000334)).
- Scope: feature branch / PR #38 only. Not wired into `operational-main-20261007`; no production path or runtime configuration has been deployed. The journal location, OS permissions, backup/recovery policy, and actual operational wiring still require verification. Keep real submission disabled and PR unmerged; all provider semantics and real-production gates remain unresolved.

## Runtime connection added — 2026-10-15

The final order-attempt boundary rereads the durable journal on every attempt via `ARUNDA_MANDATE_LIFECYCLE_PATH`. It replaces any in-memory lifecycle snapshot with journal contents before technical authorization. Missing configuration, absent/corrupt journal, or a revoked/replaced mandate fails closed before the adapter is called. It never auto-creates or repairs activation history.

The explicit helper `record_management_phase_entry(path, validated_management_result)` persists activation only from a validated `AUTHORIZED` REAL_PRODUCTION standing phase-entry result.

Deployment requirements:
1. Configure `ARUNDA_MANDATE_LIFECYCLE_PATH` to a protected, persistent absolute path.
2. Validate the actual management decision, then explicitly persist it with `record_management_phase_entry` to that path.
3. Verify the active mandate with `require_active_mandate(path, expected_mandate_id=...)`.
4. Append revocation/replacement as `REVOKE` / `REPLACE` events using `append_lifecycle_event`; never delete or edit the journal.
5. Protect the journal and sibling lock file with OS permissions and backups. Missing, unreadable, or corrupt history must block authorization; there is no in-memory fallback.

This is connected to the isolated candidate execution-attempt boundary, but is not deployed or wired into `operational-main-20261007`. It does not authorize live order submission. The PR remains subject to all outstanding provider-semantics and production-phase gates.

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
