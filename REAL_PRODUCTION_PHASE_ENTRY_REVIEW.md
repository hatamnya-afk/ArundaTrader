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

# REAL-PRODUCTION PHASE ENTRY REVIEW — v0.1

## Purpose
This is the final management review package for entering the first real-production trading phase.

It is a governance/readiness artifact. It does not itself authorize a provider write.

## Standing operational mandate
Once management explicitly authorizes phase entry:
- ArundaTrader may operate autonomously.
- SPOT and FUTURES are in scope.
- No per-trade management approval is required.
- Decision, risk, sizing, invalidation, and Trade Gate remain inside the existing trader contracts.
- Provider acceptance/rejection is authoritative.
- Zero exchange balance is allowed as the starting environmental state and is not a local pre-submit blocker.
- Real provider rejection is recorded as feedback; contracts are not weakened to avoid rejection.
- Capital is added progressively only after management review of real outcome evidence and demonstrated quality.
- 24-hour operation/analysis is a later maturity target, not a prerequisite for starting the real feedback loop.

## Evidence required before phase-entry decision
1. Canonical order path verified.
2. Execution-attempt contract verified.
3. Decision → Risk → Trade Gate path verified.
4. Authoritative provider read-only evidence verified.
5. Exact provider/instrument routing is verified for the attempted market.
6. Fail-closed safety interlocks remain intact.
7. No pipeline/DB mutation is required for the review.
8. Evidence capture path exists for provider response, fill/not-filled state, rejection reason, and outcome.
9. No per-trade management approval dependency exists.
10. Capital policy explicitly permits zero initial exchange balance.

## First-phase operating model
REAL MARKET
→ Dynamic Universe
→ Opportunity
→ Signal / Validation / Fusion / Score
→ Decision
→ Risk / Trade Gate
→ Order Attempt
→ Provider ACCEPT / REJECT
→ FILL / NOT FILLED
→ REAL OUTCOME
→ OBSERVATION
→ CALIBRATION
→ MANAGEMENT CAPITAL REVIEW

## Management decision
Current state: **AUTHORIZED — 2026-10-12**.

Authoritative decision record: `MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md`.
The project owner explicitly authorized entry into the real-production trading phase on 2026-10-12.

This is a one-time standing phase-entry mandate covering SPOT and FUTURES. It must not be converted into repeated per-trade approval requests.

**Important:** the management decision is granted; this does not waive the listed technical/provider preconditions for an actual order attempt. The current active authorization observation and all order-attempt evidence must still validate at the technical gate.

## Safety before authorization
Until phase entry is explicitly authorized:
- EXECUTION AUTHORIZATION = FALSE
- provider write = forbidden
- order = forbidden
- cancellation = forbidden
- withdrawal = forbidden
- database mutation = forbidden
- automatic pipeline wiring = forbidden

## After phase-entry authorization
The standing mandate becomes operational. The trader does not request management approval for each trade.

A later management restriction, halt, or capital-scaling decision is a separate management event.

## Non-negotiable architectural invariant
The provider is the authority for whether an otherwise valid request is accepted or rejected. ArundaTrader must not manufacture a local acceptance/rejection outcome from balance absence, assumptions, or inferred provider behavior.

## Review verdict
**MANAGEMENT PHASE ENTRY: AUTHORIZED.**
**TECHNICAL REAL-ORDER READINESS: NOT YET VERIFIED.**

Continue by verifying each outstanding precondition against current repository/runtime evidence. Do not infer a successful live path from offline tests, and do not activate order execution until the exact technical gate is verified.

## GLOBAL SELECTION QUALITY LOOP — 2026-10-12
- Code integrated on `operational-main-20261007`; focused GitHub Actions contract/wiring tests: **11 passed**.
- The normal pipeline now records canonical decision/selection anchors and later real-market observations independently of Toobit listing and order submission.
- Append-only evidence stream: `runtime_observations/global_selection_outcomes.jsonl`; outcome summaries include observed 1h/4h/24h horizons, directional return, favorable/adverse excursion, and hindsight-only counterfactual movement for review of possible missed opportunities.
- No production DB write, live order, provider write, or production runtime was performed. Actual production observation accumulation and calibration effectiveness remain **NOT VERIFIED**.
- This tracking loop does not satisfy the separate real-order gate. Toobit order submission remains disabled/unverified, and trade/provider outcome capture remains NOT VERIFIED.


## STATIC TECHNICAL GATE AUDIT — 2026-10-12

Scope: source inspection only. No production runtime, live order, provider write, database access/mutation, or pipeline activation was performed.

### Confirmed
1. Management phase-entry decision is recorded as AUTHORIZED in `MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md`.
2. `management_execution_authorization_v0_1.py` emits a structured authorization observation. Precise `issued_at` is optional audit metadata; `expires_at` is optional for a standing mandate unless management explicitly chooses a timed mandate.
3. `execution_authorization_boundary_v0_1.py` validates the active mandate, expiry, REAL_PRODUCTION environment, SPOT/FUTURES scope, and request venue. It does not itself submit orders.
4. `execution_attempt_readiness_contract_v0_1.py` requires a valid canonical request and a validated execution-ready package, while preserving `execution_authorized=False` and `provider_binding=DEFERRED`.
5. `exchange_execution_order_attempt_boundary_v0_1.py` would call `adapter.submit_prepared_order` after its gates pass. That makes adapter capability and the active gate evidence material prerequisites.
6. `toobit_exchange_adapter_v0_1.py` currently advertises `order_submission=False`, `order_cancellation=False`, and its class documentation describes a read-only adapter. No supported live submit operation was verified in this adapter.
7. PR #31 remains Draft/unmerged. Its CI evidence (88 tests) is offline/mock/isolated-SQLite evidence only, not live-provider verification.

### Blocking evidence before any real order attempt
- **ACTIVE MANDATE INSTANCE:** The management code requires `issued_at` and `expires_at`, and the technical boundary rejects expired/missing expiry. The policy/repository does not establish a mandate duration. Do not invent one or manufacture an active observation from a decision record alone.
- **PROVIDER SUBMISSION CAPABILITY:** Current Toobit adapter is read-only and declares submission disabled; no actual provider submit path has been verified.
- **ORDER-ID / AMBIGUOUS RECOVERY:** Toobit client-order-ID charset/maximum length, reuse scope, duplicate POST semantics, lookup consistency/retention, and exhaustive recovery remain unverified in PR #31. The fail-closed block must remain.
- **END-TO-END EVIDENCE:** A current real request flowing through Decision → Risk → Trade Gate → readiness → authorization → provider result → fill/not-filled → real outcome/observation has not been evidenced by this static audit.
- **TEST EXECUTION:** The four governance updates and current branch code were not run in a local test environment by this audit. No new test-pass claim is made.

### Verdict
**MANAGEMENT PHASE ENTRY: AUTHORIZED.**
**TECHNICAL REAL-ORDER READINESS: BLOCKED / NOT VERIFIED.**
**EXECUTION AUTHORIZATION: FALSE.**
**LIVE ORDER / PROVIDER WRITE / DATABASE WRITE / PIPELINE ACTIVATION: NOT PERFORMED AND NOT CLEARED.**

Next work is to resolve the active-mandate expiry policy and provider execution/recovery contract, then add/run focused tests and re-evaluate the final gate. This is not a request for per-trade approval.


## CURRENT UPDATE — PR #38 OUTCOME CAPTURE / AMBIGUOUS RECOVERY — 2026-10-15

Candidate branch: \`feature/execution-outcome-evidence-contract-20261015\`; reviewed commit \`ed34ec0f5c31a82809ec7e1237bb239a6bd33196\`; PR #38 remains open and unmerged against \`operational-main-20261007\`.

### Candidate work now built and offline-verified
- Corrected the Futures history read endpoint to \`GET /api/v2/futures/history-orders\`.
- Added exact-client-ID read-only recovery for Spot \`GET /api/v1/spot/order\` and Futures \`GET /api/v2/futures/order\`.
- Validates both returned \`clientOrderId\` and provider symbol before outcome capture.
- Provider lookup errors, missing rows, malformed observations, and identity conflicts remain non-retryable; no POST retry or inferred fill is introduced.
- Focused CI passed **51 tests** on the candidate commit: [run 38721082194](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38721082194) and [run 38721075314](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38721075314). These are fake-transport/offline tests only.

### Remaining blockers — final gate still open
1. The operational Toobit adapter remains submission-disabled; candidate code has not been promoted or wired to production.
2. The authorized management decision lacks the timezone-aware \`issued_at\` and \`expires_at\` required by the mandate validator. No timestamp or expiry duration has been invented.
3. Official Toobit docs do not establish client-ID maximum length/allowed charset, reuse/uniqueness after terminal orders, duplicate-POST replay semantics, or lookup consistency/retention/exhaustive recovery.
4. No live provider observation or end-to-end production outcome has been captured; no live Toobit API request was made during this work.

**Current verdict:** MANAGEMENT PHASE ENTRY = AUTHORIZED; CANDIDATE OUTCOME/RECOVERY CONTRACT = OFFLINE CI PASS; TECHNICAL REAL-ORDER READINESS = BLOCKED / NOT VERIFIED; EXECUTION AUTHORIZATION = FALSE. PR #38 remains unmerged. No production runtime, order, cancellation, withdrawal, provider write, or database mutation was performed. Keep \`safe_to_retry=false\` for every ambiguous submission.



## CURRENT UPDATE — OUTCOME EVIDENCE FORENSIC PASS — 2026-10-15

- New isolated candidate head: `411395402de8a9aeb78bf8454649c1516a110700`; PR #38 remains open/unmerged against `operational-main-20261007`.
- Static review found and fixed a provenance defect: a local timestamp for a `READ_ONLY_LOOKUP` was being labeled `provider_timestamp_known=true`. The schema now marks provider time known only for an explicitly timestamped `PROVIDER_RESPONSE`; read-only lookup time remains local observation time.
- Recovery now validates the timezone-aware local observation timestamp before making its GET request; naive/invalid values fail closed without transport activity.
- Added tests for timestamp provenance, invalid timestamp rejection before network, malformed lookup rows, and local timestamp generation.
- GitHub Actions run [38721872191](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38721872191) passed **56 tests** (offline/fake transport).
- This closes the current offline contract defect found in this review, but **does not** clear the real-order gate. Management mandate timestamp fields and Toobit live semantics remain unverified; no production wiring, live API request, order, cancellation, withdrawal, or database write occurred. `safe_to_retry=false` remains mandatory.

# END
