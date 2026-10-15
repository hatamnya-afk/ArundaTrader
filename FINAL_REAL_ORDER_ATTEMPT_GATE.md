## STANDING-MANDATE LIFECYCLE — DURABLE JOURNAL CONTRACT PASS (2026-10-15)

- Standing phase-entry mandate is non-expiring by default; explicit expiry remains optional and is enforced when provided. Per-trade management approval remains forbidden.
- Technical authorization rejects missing/invalid lifecycle history and revoked or superseded mandate identities. The append-only JSONL lifecycle journal supports management ACTIVATE/REVOKE/REPLACE events, validates transitions before append, fsyncs committed rows, and uses an OS lock for append coordination.
- Focused CI: **28 passed in 0.16s** (run [38726220987](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38726220987)); outcome-evidence CI also passed (run [38726221006](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38726221006)).
- **Remaining integration gate:** no production runtime currently reads the durable journal before every execution authorization, and the authoritative journal path/access-control/backup policy has not been configured or verified. Therefore lifecycle revocation/replacement is implemented and offline-tested, but not yet enforced by the operational production path. Keep provider submission disabled, do not merge PR #38, and do not claim real-order readiness.

## STANDING-MANDATE LIFECYCLE — CANDIDATE CI PASS (2026-10-15)

- Standing mandate is non-expiring by default; explicit expiry remains supported only if management supplies it. No fabricated issuance/expiry timestamps.
- Technical authorization now requires lifecycle history and rejects revoked/superseded mandate identities, duplicate event IDs, invalid transitions, or non-management event authority.
- Focused CI: 24 passed in 0.08s (run [38725859677](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38725859677)); outcome-evidence CI also passed (run [38725859582](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38725859582)).
- **Important unresolved integration gate:** lifecycle reducer is pure/offline. The initial activation event is emitted by the mandate producer, but no durable authoritative append-only lifecycle store or production read integration exists yet. Therefore revocation/replacement is contract-tested, not yet operationally enforceable across restarts. Keep real execution blocked, provider submission disabled, and PR unmerged.

## STANDING-MANDATE POLICY UPDATE — 2026-10-15 (CANDIDATE BRANCH ONLY)

- Management authorization dated 2026-10-12 is a one-time standing phase-entry decision; it does not require per-trade management approval.
- A precise `issued_at` timestamp is optional audit metadata. The validator must not fabricate one when the decision record contains only a date/source.
- `expires_at` is optional. No expiry duration was set by management, so the default is a non-expiring standing mandate. If an expiry is explicitly supplied, it must be timezone-aware, in the future, and later than `issued_at` when that timestamp is present.
- The management validator and technical authorization boundary were updated on the isolated PR #38 feature branch, with focused tests added. This does NOT activate production execution, clear the final real-order gate, wire the candidate into the operational branch, or establish a persistent revocation registry.
- **Still BLOCKED / NOT VERIFIED:** operational Toobit submission remains disabled; client-order-ID constraints, duplicate-POST semantics, lookup consistency/retention/exhaustiveness remain unresolved; candidate recovery is not production-wired and no live outcome evidence exists. Keep `safe_to_retry=false`; do not merge PR #38 or send an order based on this change alone.

# FINAL REAL-ORDER ATTEMPT GATE — MANAGEMENT REVIEW PACKAGE
## ArundaTrader — 2026-10-12

### PURPOSE
Define the exact boundary that must be satisfied before a future real provider order attempt can be made under the already-authorized real-production phase.

This document does NOT authorize execution.

### GOVERNING MANAGEMENT INVARIANT

Management authorization is **ONE-TIME REAL-PRODUCTION PHASE-ENTRY MANDATE**.

The management decision is only:

`AUTHORIZE REAL-PRODUCTION TRADING PHASE`

Once explicitly authorized:
- the trader operates autonomously;
- SPOT and FUTURES are both in scope;
- no per-trade management approval exists;
- no individual order, asset, direction, quantity, order-type, exposure, or `attempt_id` is sent to Management for approval;
- individual trade selection and sizing remain inside Decision → Risk → Trade Gate → Readiness;
- Technical Execution Authorization verifies the current request against the active standing mandate;
- the provider remains authoritative for ACCEPT / REJECT.

### VERIFIED ENTRY
- Provider-neutral execution-attempt contract: VERIFIED / PASS.
- Core remains exchange-agnostic.
- Toobit remains a replaceable adapter.
- The phase-entry decision is now explicitly AUTHORIZED (see MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md). Technical execution authorization remains FALSE until a current request and valid, unexpired standing mandate pass every technical gate.

### OWNERSHIP

| Concept | Canonical owner |
|---|---|
| Management phase entry | `management_execution_authorization_v0_1.py` |
| Management review packaging | `management_review_package_v0_1.py` — review-only; never an authorization producer |
The Management boundary is closed-schema: trade/attempt fields and aliases are rejected, and unclassified fields fail closed.
| Technical execution authorization | `execution_authorization_boundary_v0_1.py` |
| Execution readiness | `execution_attempt_readiness_contract_v0_1.py` |
| Final attempt composition | `final_execution_attempt_contract_v0_1.py` |
| Provider-neutral attempt | `exchange_execution_order_attempt_boundary_v0_1.py` |

**Critical distinction:**
`Management Mandate ≠ Execution Attempt`

An `attempt_id` may exist in the execution-attempt/evidence domain. It must not become a Management authorization input.

### REQUIRED PRECONDITIONS

1. Canonical order request is valid.
2. Execution-ready package and readiness state agree.
3. Selected execution instrument is authoritative and unambiguous.
4. Approved provider read-only evidence is available where required by the existing execution contracts.
5. Provider-specific translation remains entirely inside the adapter.
6. No hidden authorization inference exists.
7. The active Management input is a valid `STANDING_MANDATE`, not an attempt-level approval.
8. The standing mandate covers `REAL_PRODUCTION`, SPOT + FUTURES, provider, capital policy, evidence requirements, and expiry.
9. Safety interlocks remain fail-closed.
10. The execution attempt is observable and produces the existing evidence/outcome record.
11. A provider rejection is real environmental evidence, not permission to weaken contracts.
12. Acceptance and fill remain distinct states.
13. Zero provider balance is not converted into a local architecture blocker.

### EXECUTION PATH

```
ONE-TIME MANAGEMENT DECISION
        │
        ▼
REAL-PRODUCTION PHASE ENTRY
        │
        ▼
STANDING_MANDATE
        │
        ▼
AUTONOMOUS TRADER
        │
        ├── SPOT
        └── FUTURES
              │
              ▼
Decision
   ↓
Risk
   ↓
Trade Gate
   ↓
Readiness
   ↓
Technical Execution Authorization
   ↓
Final Execution Attempt Contract
   ↓
Provider-Neutral Attempt Boundary
   ↓
Provider
   ├── ACCEPT
   └── REJECT
        ↓
    REAL EVIDENCE
```

There is **no** `TRADE → MANAGEMENT APPROVAL → TRADE` path.

### ZERO-BALANCE RULE

A zero account balance is valid environmental state. It must not be converted into a local trade blocker before the provider request.

Zero balance does not imply acceptance. If a valid provider attempt is eventually made under the standing mandate and the provider rejects it because of balance, margin, permissions, instrument constraints, or another provider condition, that rejection is real provider evidence.

No contract weakening, fabricated acceptance, inferred permission, or synthetic evidence is allowed.

### MANAGEMENT SAFETY BOUNDARY

The phase-entry decision is already explicitly authorized by MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md. That management decision does not override unresolved technical gates.

Current technical interlocks remain:
- EXECUTION AUTHORIZATION = FALSE until a current ready request and valid, unexpired standing mandate pass technical validation.
- Provider order submission remains fail-closed in the current Toobit adapter.
- Order submission/cancellation/withdrawal and provider writes remain forbidden until their specific technical contracts are verified.
- Database mutation remains forbidden.
- No production runtime or live order is authorized by this review document.

Once technical gates pass, the standing mandate is the management authorization context. **No new management authorization is requested for individual trades.**

### EVIDENCE REQUIRED FOR FUTURE AUTHORIZED OPERATION

Record existing real evidence without fabrication or backfill:
- decision identity and timestamp/provenance;
- canonical order request;
- execution-ready package identity;
- execution attempt identity where applicable;
- execution instrument;
- provider readiness evidence;
- active standing-mandate identity;
- exact provider request outcome;
- provider order identifier if accepted;
- fill status and fill evidence if any;
- rejection reason if rejected;
- post-attempt account/position/order evidence where authorized;
- complete execution state.

The standing mandate itself is not recreated for each attempt.

### CURRENT MANAGEMENT AND TECHNICAL DISPOSITION

- Management phase-entry decision: **AUTHORIZED — 2026-10-12**.
- Current operational branch: operational-main-20261007.
- Technical real-order gate: **OPEN / BLOCKED / NOT VERIFIED**.
- Current Toobit adapter: order_submission=False; submit entrypoints fail closed with EXECUTION_DISABLED_ORDER_SUBMISSION_NOT_IMPLEMENTED.
- Standing mandate artifact: **incomplete for runtime use** because MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md does not carry the required timezone-aware issued_at and expires_at fields. No expiry has been fabricated; management's authorization remains recorded, while technical validation must reject an incomplete mandate.
- PR #31 (Add atomic per-intent claim store contract) remains Draft and unmerged. Its offline CI run #38237269560 passed 88 tests in 1.28s. This validates only offline contract/recovery fixtures and isolated temporary SQLite, not Toobit API semantics or live execution.
- Official Toobit material reviewed in PR #31 does not establish client-order-ID maximum length/allowed charset, uniqueness/reuse scope after terminal states, duplicate POST replay semantics, lookup consistency/retention, or exhaustive history recovery by client ID. These must be supported by authoritative documentation or written provider confirmation. Do not guess values.
- Global Selection Quality Loop focused CI passed 11 tests on the operational branch; production evidence accumulation and calibration effectiveness remain NOT VERIFIED.

### REQUIRED NEXT ACTIONS — FAIL-CLOSED

1. Complete a formally time-bounded standing-mandate observation without inventing issuance/expiry timestamps or silently choosing a policy.
2. Obtain authoritative Toobit documentation or written support confirmation for the unresolved client-order-ID and ambiguous-recovery semantics.
3. Implement/verify the provider adapter submit path only against verified constraints; keep unknown outcomes blocked and never blindly retry.
4. Run focused CI on the intended operational code lineage and verify commit/branch identity.
5. Verify order-attempt outcome capture and reconciliation contracts before any production runtime.
6. Do not run a production runtime, send an order, cancel, withdraw, enable execution, or write to the provider/database while any gate remains open.

The standing phase-entry mandate means no per-trade management approval is required; it does **not** waive any of the above technical gates.


### CURRENT CANDIDATE UPDATE — 2026-10-15

PR #38, isolated on \`feature/execution-outcome-evidence-contract-20261015\`, now contains an offline-tested outcome-capture/recovery candidate:
- Exact-client-ID read-only order lookup: Spot \`GET /api/v1/spot/order\`; Futures \`GET /api/v2/futures/order\`.
- Futures history lookup uses documented \`GET /api/v2/futures/history-orders\`.
- Exact client-ID and symbol validation before capture; missing/error/conflicting observations remain unresolved and \`safe_to_retry=false\`.
- CI passed 51 fake-transport/offline tests on commit \`ed34ec0f5c31a82809ec7e1237bb239a6bd33196\`: [run 38721082194](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38721082194).

This candidate does **not** clear the gate. It is not merged or wired into production; the operational adapter remains submission-disabled. The active standing mandate still lacks verified timezone-aware \`issued_at\`/\`expires_at\`; Toobit client-ID constraints, duplicate-POST behavior, lookup consistency/retention, and exhaustive recovery semantics remain unverified. No live API request or order was made.



## CURRENT UPDATE — OUTCOME EVIDENCE FORENSIC PASS — 2026-10-15

- New isolated candidate head: `411395402de8a9aeb78bf8454649c1516a110700`; PR #38 remains open/unmerged against `operational-main-20261007`.
- Static review found and fixed a provenance defect: a local timestamp for a `READ_ONLY_LOOKUP` was being labeled `provider_timestamp_known=true`. The schema now marks provider time known only for an explicitly timestamped `PROVIDER_RESPONSE`; read-only lookup time remains local observation time.
- Recovery now validates the timezone-aware local observation timestamp before making its GET request; naive/invalid values fail closed without transport activity.
- Added tests for timestamp provenance, invalid timestamp rejection before network, malformed lookup rows, and local timestamp generation.
- GitHub Actions run [38721872191](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38721872191) passed **56 tests** (offline/fake transport).
- This closes the current offline contract defect found in this review, but **does not** clear the real-order gate. Management mandate timestamp fields and Toobit live semantics remain unverified; no production wiring, live API request, order, cancellation, withdrawal, or database write occurred. `safe_to_retry=false` remains mandatory.

# END
