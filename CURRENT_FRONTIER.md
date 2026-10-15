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

# CURRENT GOVERNANCE OVERRIDE — 2026-10-12

> **THIS SECTION IS THE ACTIVE STATE.** Historical sections below are preserved as evidence/history and must not override this state.

## VERIFIED MANAGEMENT POSITION
- One-time REAL_PRODUCTION phase-entry mandate: **AUTHORIZED — 2026-10-12**.
- Provider: TOOBIT. Markets in scope: SPOT and FUTURES.
- Standing mandate: no per-trade management approval.
- Zero initial exchange balance is an allowed starting environmental state; provider responses/outcomes must be genuine.
- Authoritative decision record: `MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md`.

## CURRENT TECHNICAL FRONTIER
**FINAL REAL-ORDER GATE — OPEN / NOT VERIFIED.**
Management phase-entry authorization is recorded, but it does not authorize a live submission by itself. The standing mandate does not require an invented issuance timestamp or expiry duration. The operational Toobit adapter remains submission-disabled; provider client-order-ID constraints and ambiguous POST/recovery semantics remain unresolved. Outcome capture/reconciliation is offline-tested on isolated PR #38 only and is not operationally wired; no real outcome evidence exists.

## PR #38 candidate evidence — 2026-10-15 (isolated; not operational promotion)
- Candidate branch: `feature/execution-outcome-evidence-contract-20261015`; CI-tested code/test/workflow revision: `ed34ec0f5c31a82809ec7e1237bb239a6bd33196`; subsequent commits only synchronized documentation, and the adapter, recovery module, recovery tests, and workflow blob hashes remain unchanged.; PR #38 targets `operational-main-20261007` and remains open/unmerged.
- Built on this candidate: append-only outcome capture, fail-closed ambiguous-submission classification, exact client-ID read-only lookup for Spot `GET /api/v1/spot/order` and Futures `GET /api/v2/futures/order`, exact client-ID/symbol validation, and a bridge that persists only an exact provider row. A failed lookup or missing row never makes retry safe.
- Focused GitHub Actions CI passed **51 tests** on this candidate (run [38721082194](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38721082194); duplicate event run [38721075314](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38721075314)). These are fake-transport/offline tests, not live Toobit verification.
- **Still BLOCKED / NOT VERIFIED:** operational branch's provider adapter remains submission-disabled; the standing mandate has no evidenced timezone-aware `issued_at` and `expires_at`; official docs do not establish client-ID length/charset, reuse/uniqueness after terminal orders, duplicate-POST semantics, or lookup consistency/retention/exhaustiveness; the candidate recovery path is not wired to production runtime and no live outcome evidence exists.
- Safety remains unchanged: no production runtime, provider write, order, cancellation, withdrawal, or database mutation. Keep `safe_to_retry=false`; do not merge PR #38 or claim real-order readiness from this CI.

## GLOBAL SELECTION QUALITY LOOP — 2026-10-12
- **Code state: BUILT / FOCUSED CI PASS (16 tests; run 38266864429, commit `9af0c20ec4b46891ead075a11b4e1a83401ecb73`).** The normal pipeline emits provider-neutral selection anchors, follows later real-market observations, and reports aggregated quality metrics; independent of Toobit listing and order submission.
- Append-only evidence: `runtime_observations/global_selection_outcomes.jsonl`. It records canonical decision identity, selection time, direction, reference price/source, subsequent observed prices, 1h/4h/24h horizon status, directional return, favorable/adverse excursion, and hindsight-only counterfactual movement for missed-opportunity review.
- The aggregate report groups by asset and direction and reports observed/pending counts, scored/unscored counts, wins/losses/flat outcomes, win rate, mean and median directional return at 1h/4h/24h. Pending horizons are excluded from win-rate denominators; direction `NONE` is not scored directionally. The pipeline logs these metrics as `GLOBAL_SELECTION_QUALITY`, `GLOBAL_SELECTION_QUALITY_BY_ASSET`, and `GLOBAL_SELECTION_QUALITY_BY_DIRECTION` each normal cycle.
- Read-only report CLI `global_selection_quality_report_v0_1.py` now builds per-asset rankings for 1h/4h/24h only when the configured minimum sample size is met (default 5), and reports mean/median directional returns, win rate and mean favorable/adverse excursions. It never fetches data, changes decisions, writes the DB or treats pending observations as losses.
- The repository currently has no committed `runtime_observations/global_selection_outcomes.jsonl`; therefore there is no production evidence stream available to rank yet. No real-market quality conclusion is claimed until the operational runtime records genuine observations.
- Missing observations remain pending or are reported as skipped; no synthetic data or inferred outcome is created. The tracker does not write the production database and does not change decisions or execution flags.
- **Production evidence accumulation and calibration effectiveness: NOT VERIFIED** because no production runtime was executed for this code change. This loop does not clear the final real-order gate or authorize an order.

## SAFETY — ACTIVE
- `EXECUTION AUTHORIZATION = FALSE` until the technical boundary validates a current ready request against a valid standing-mandate observation.
- `ORDER WRITE = FORBIDDEN` while any required gate evidence is missing.
- `PROVIDER WRITE = FORBIDDEN` while any required gate evidence is missing.
- `DATABASE WRITE = FORBIDDEN`.
- `arunda_pipeline.py` is wired to the provider-neutral Global Selection Quality Loop after authoritative Decision birth and before Dynamic Risk; this does not activate order execution or provider writes.
- PR #31 remains Draft and unmerged; its base is the candidate branch `fix/stable-client-order-id-contract-20261012`, not the operational branch, so it is not eligible for direct promotion to production. Offline CI run 38237269560 passed 88 tests, but official Toobit client-ID and ambiguous-recovery guarantees remain unresolved.
- No production runtime, live order, cancel, withdrawal, or live provider write as part of this verification.

## ALLOWED NOW
- Static contract and code-path verification.
- Offline focused tests and CI evidence review.
- Read-only provider evidence only where explicitly permitted by existing scope.
- Resolve technical blockers without weakening safety, idempotency, provenance, or fail-closed behavior.
- Keep the canonical four governance documents synchronized.

## ADVANCEMENT RULE
Continue from this frontier without re-auditing closed stages. The standing management mandate eliminates per-trade management approvals, but each candidate still must independently pass the existing Decision → Risk → Trade Gate → readiness → technical authorization → adapter/provider contracts. Do not submit a live order until every current technical/provider precondition is evidenced and the adapter genuinely supports the required operation.

---

# ARUNDA TRADER — CURRENT FRONTIER

## STATUS
CURRENT FRONTIER — PROVIDER-NEUTRAL EXECUTION PATH COMPLETION

## EXCHANGE-AGNOSTIC ADAPTER CONTRACT
Status: VERIFIED / REPLACEABLE

The execution boundary now has an explicit provider-neutral adapter contract. The Core does not name Toobit and can target another exchange adapter implementing the same contract.

Toobit remains only the currently selected concrete execution environment. Its capabilities are advertised separately and its order submission/cancellation are still disabled.

Next: complete the provider-neutral handoff from canonical order request through the selected adapter without binding Core to any exchange. A later real order attempt, once the real-production phase has been explicitly entered, does not require a new management approval; it uses the active standing mandate through the technical authorization boundary.


CURRENT FRONTIER — EXECUTION PATH COMPLETION / DYNAMIC ASSET BOUNDARY

## CP DYNAMIC EXECUTION ASSET UNIVERSE
Status: VERIFIED / PROVIDER-DRIVEN / ASSET-AGNOSTIC

Implemented on `operational-main-20261007`:
- Toobit adapter discovers current `TRADING` assets directly from authoritative exchange metadata.
- Spot discovery is dynamic over live USDT base assets.
- Futures discovery is dynamic over live contract underlyings.
- Exact instrument resolution remains separate and fail-closed.
- No hardcoded BTC/ETH/SOL production universe exists.
- Multi-asset tests verify ETH/SOL/XRP independently of BTC.

Commits: `91ffc7e`, `0e3f59e8`, `3b55141a`.

The remaining goal is completion of the provider handoff toward a valid Order Request. Provider rejection is an environment outcome, not a reason to hardcode or redesign Core. Execution authorization remains FALSE.

CURRENT FRONTIER — FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST

## CURRENT STATE
Project Completion is CLOSED / VERIFIED and Toobit Binding is CLOSED / VERIFIED at the adapter contract boundary. The active gate is now the final real-market exchange integration / controlled test.

The Core remains provider-neutral and exchange-agnostic. Toobit remains outside Core through the replaceable adapter boundary.

## AUTHORITATIVE ROUTE
MCP-01 HANDOFF → MAIN → SELECTIVE, EVIDENCE-BACKED INTEGRATION → PROVIDER READINESS → PROJECT COMPLETION (CLOSED / VERIFIED) → TOOBIT BINDING → FINAL REAL-MARKET CONTROLLED TEST → EXECUTION AUTHORIZATION → FIRST REAL ORDER → FIRST REAL FILL → REAL OUTCOME → OBSERVATION → CALIBRATION

## PROJECT COMPLETION EVIDENCE
- exchange_execution_contract.py provides the canonical exchange-neutral order/result contract and execution-off safety contract.
- pre_execution_readiness_v0_1.py produces PRE_EXECUTION_READY with provider_binding=DEFERRED.
- execution_ready_package_v0_1.py preserves provider_binding=DEFERRED and execution_authorized=False.
- Provider-readiness modules remain separate from the Core.
- arunda_pipeline.py does not bind Toobit or call the provider-preflight chain.
- exchange_execution_boundary.py is now present on MAIN and restores the required exchange-agnostic fail-closed boundary.
- The restored boundary validates the canonical request and returns EXECUTION_DISABLED while execution is off; it performs no network/API/order/DB action and does not transform quantity.
- Static syntax verification passed for the restored boundary.

## ARCHITECTURAL VERDICT
CORE → EXCHANGE-AGNOSTIC EXECUTION BOUNDARY → REPLACEABLE EXCHANGE ADAPTER → TOOBIT

Toobit is not a Core dependency. It is not wired into arunda_pipeline.py at Project Completion.

## CURRENT FRONTIER — FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST
Status:
CURRENT FRONTIER / OPEN / NOT EXECUTED

Verified read-only evidence:
- Full Read-Only Provider Preflight = PASS on live Toobit.
- Authoritative Futures instrument = BTC-SWAP-USDT (TRADING, USDT, PERPETUAL).
- ExchangeInfo, Futures balance, leverage, positions, open orders, history orders, and server time returned HTTP 200.
- Provider preflight evidence constructed successfully.
- Account/order/contract/timestamp evidence was known and valid; no open/recent order IDs were present.
- GET-only transport; no write endpoint invoked.
- CP46-D test contract = 21/21 PASS across the Toobit adapter and CP46-D provider-preflight suites.
- git diff --check = PASS.
- targeted py_compile = PASS.
- evidence-alignment commit = f80fa83.

Controlled-test readiness boundary:
1. preserve Core → exchange-agnostic boundary → Toobit adapter architecture;
2. verify the controlled-test contract before any execution permission;
3. use real market/provider evidence only;
4. keep EXECUTION AUTHORIZATION = FALSE;
5. no order/cancel/withdraw, DB mutation, or arunda_pipeline.py wiring;
6. no additional provider API calls unless separately authorized for the controlled-test evidence set.

NEXT ACTION:
Perform controlled-test contract/readiness inspection only.

## CP46-D / CP46-A6 CHECKPOINT STATE

CP46-D test contract:
VERIFIED

Evidence:
- 21/21 focused tests passed.
- py_compile PASS.
- git diff --check PASS.
- Futures routing, authoritative instrument resolution, contract evidence, provider-native margin state, leverage state, position state, and order state are covered.
- The focused tests explicitly verify that the Futures path reaches A6 and fails closed on missing exposure authorization.

CP46-A6:
BLOCKED

Exclusive blocker:
exposure_allowed has no established provider-native Futures authorization evidence.

This is not a margin, leverage, position, contract, instrument, translation, or routing blocker. Those surfaces are verified. The blocker is specifically the absence of a direct authoritative provider signal permitting additional Futures exposure.

NEXT ACTION:
Investigate provider-native exposure authorization only. No inference from balance, leverage, margin mode, or empty positions. If direct evidence cannot be established, retain BLOCKED.

## SAFETY
EXECUTION AUTHORIZATION = FALSE
ORDER WRITE = FORBIDDEN
DATABASE WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN
NO REAL TRADE


## TOOBIT BINDING — CLOSED / VERIFIED
Status: CLOSED / VERIFIED / FOCUSED STATIC CONTRACT PASS

The adapter checkpoint is closed. The subsequent controlled-test work has verified the live read-only provider surface.

## FINAL REAL-MARKET CONTROLLED TEST — CURRENT
Status: OPEN / NOT EXECUTED

The full read-only provider preflight has passed against live Toobit. This is evidence for readiness, not execution authorization.

No order, cancellation, withdrawal, exchange write, DB mutation, or execution authorization has occurred.

NEXT ACTION: Perform controlled-test contract/readiness inspection only.


CP46-A6 PROVIDER-NATIVE EXPOSURE INVESTIGATION — CONCLUSION

Investigation result:
- Toobit's documented read-only Futures surfaces expose balance/availableBalance, leverage and marginType, positions, and risk-limit configuration.
- The documented API-key permission model distinguishes read permissions from trade permissions; it does not expose a Futures account Boolean equivalent to exposure_allowed.
- Toobit documents order-time rejection conditions including no-opening-trades, insufficient order margin, and maximum Futures risk-limit exceeded. These are execution-time outcomes/constraints, not a pre-execution provider-native authorization Boolean.
- Therefore no direct authoritative provider-native Futures exposure_allowed signal has been established.

Classification:
DIRECT AUTHORITATIVE exposure_allowed = NOT FOUND
INFERRED exposure_allowed = FORBIDDEN
UNKNOWN exposure_allowed = YES

Management verdict:
CP46-A6 remains BLOCKED exclusively by missing provider-native Futures exposure authorization evidence. Do not convert balance, leverage, marginType, empty positions, risk-limit configuration, API-key trade permission, or hypothetical order acceptance into exposure_allowed=True.

No additional provider API call, order, cancel, withdrawal, DB mutation, execution authorization, or pipeline wiring is authorized by this investigation.

## CP46-A6 — FINAL MANAGEMENT DECISION

The provider-native exposure investigation is CLOSED.

Decision:
CP46-A6 remains BLOCKED / NOT VERIFIABLE because Toobit currently exposes no established read-only provider-native Futures authorization signal equivalent to `exposure_allowed`.

Classification:
- ArundaTrader defect: NO
- Missing implementation surface: NO
- Provider capability/evidence gap: YES

Therefore:
- Do not modify `provider_preflight_v0_1.py` to infer permission.
- Do not treat balance, leverage, marginType, empty positions, risk limits, API-key trade permission, or hypothetical order acceptance as authorization.
- Do not send an order merely to discover whether exposure is accepted.
- Do not activate execution.

CURRENT FRONTIER:
FINAL REAL-MARKET EXECUTION READINESS — BLOCKED BY EXTERNAL PROVIDER EVIDENCE GAP.

NEXT ACTION:
Obtain new authoritative Toobit provider evidence/clarification for Futures exposure authorization. Until then, remain fail-closed.


## CURRENT UPDATE — OUTCOME EVIDENCE FORENSIC PASS — 2026-10-15

- New isolated candidate head: `411395402de8a9aeb78bf8454649c1516a110700`; PR #38 remains open/unmerged against `operational-main-20261007`.
- Static review found and fixed a provenance defect: a local timestamp for a `READ_ONLY_LOOKUP` was being labeled `provider_timestamp_known=true`. The schema now marks provider time known only for an explicitly timestamped `PROVIDER_RESPONSE`; read-only lookup time remains local observation time.
- Recovery now validates the timezone-aware local observation timestamp before making its GET request; naive/invalid values fail closed without transport activity.
- Added tests for timestamp provenance, invalid timestamp rejection before network, malformed lookup rows, and local timestamp generation.
- GitHub Actions run [38721872191](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38721872191) passed **56 tests** (offline/fake transport).
- This closes the current offline contract defect found in this review, but **does not** clear the real-order gate. Management mandate timestamp fields and Toobit live semantics remain unverified; no production wiring, live API request, order, cancellation, withdrawal, or database write occurred. `safe_to_retry=false` remains mandatory.

# END CURRENT FRONTIER

## CURRENT FRONTIER — EXCHANGE-AGNOSTIC ORDER PREPARATION HANDOFF

Status:
CURRENT FRONTIER / BUILT / NOT YET LOCALLY VERIFIED

Management decision:
The project now advances past the Toobit-specific `exposure_allowed` evidence blocker at the Core architecture level. The provider-native exposure gap remains a provider capability issue, but it does not redefine the exchange-neutral completion path.

Target path:
`TRADE READY → ORDER INTENT → PRE-EXECUTION READY → CANONICAL ORDER REQUEST → REPLACEABLE ADAPTER → OPAQUE PROVIDER ORDER REQUEST → [LATER, EXPLICIT AUTHORIZATION] ORDER ATTEMPT`

Built:
- Provider-neutral `AdapterOrderPreparation` contract.
- Provider-neutral preparation boundary.
- Toobit adapter-owned provider translation.
- No Core inspection of provider symbol/payload.
- No order submission, cancellation, DB write, or execution activation.

Important:
- Canonical quantity remains authoritative BASE_ASSET quantity.
- Provider-specific quantity conversion belongs only inside the selected adapter.
- Toobit is the first adapter only and remains replaceable.

Verification:
New focused tests are committed but not yet locally executed in this checkpoint environment.

NEXT ACTION:
Builder runs the focused adapter/preparation tests, `py_compile`, and `git diff --check`. Any failure is fixed only within this checkpoint scope; no Core redesign and no pipeline wiring.
\n\n## CURRENT FRONTIER — PROVIDER-NEUTRAL ORDER ATTEMPT BOUNDARY\n\nStatus: VERIFIED / PASS / EXECUTION-CLOSED\n\nTarget path:\n`CANONICAL ORDER REQUEST → ADAPTER PREPARATION → OPAQUE PROVIDER ORDER REQUEST → EXPLICIT AUTHORIZATION → PROVIDER ORDER ATTEMPT`\n\nVerified evidence:\n- Prepared-order submission contract added to the replaceable adapter boundary.\n- Final order-attempt boundary validates the canonical request and explicit authorization before invoking `submit_prepared_order`.\n- No authorization inference is permitted.\n- Toobit remains a replaceable adapter and returns fail-closed submission while execution is disabled.\n- Focused suite = 22/22 PASS.\n- py_compile = PASS.\n- git diff --check = PASS.\n\nSafety:\n- EXECUTION AUTHORIZATION = FALSE.\n- ORDER WRITE = FORBIDDEN.\n- PROVIDER WRITE = FORBIDDEN.\n- DATABASE WRITE = FORBIDDEN.\n- No pipeline wiring.\n\nManagement verdict:\nThis frontier is VERIFIED. Do not reopen the preparation boundary or redesign Core.\n\nNEXT ACTION:\nBuild/verify the explicit execution-attempt readiness contract that will govern the eventual real provider attempt, still without enabling execution.\n

## CP FINAL EXECUTION ATTEMPT CONTRACT — VERIFIED

Status: VERIFIED / PASS / EXECUTION-CLOSED

Completed path:
`Execution Ready Package → Execution-Attempt Readiness → Explicit Authorization → Adapter Preparation → Provider-Neutral Order Attempt → Replaceable Adapter`

Evidence:
- 28/28 focused tests passed.
- py_compile PASS.
- git diff --check PASS.
- Fast-forward to commit `448806f` completed successfully.
- Invalid readiness/package alignment blocks before adapter submission.
- Missing explicit authorization blocks before adapter submission.
- Explicit valid authorization reaches the replaceable adapter boundary.
- Toobit remains fail-closed; no real provider write occurs.

Strategic invariants:
- Core remains exchange-agnostic.
- Toobit remains a replaceable execution adapter.
- EXECUTION AUTHORIZATION = FALSE.
- No order/cancel/withdrawal.
- No DB mutation.
- No `arunda_pipeline.py` wiring.
- No authorization inference.

Management verdict:
The final provider-neutral execution-attempt contract is VERIFIED and execution-closed.

NEXT FRONTIER:
Management review of the final real-order-attempt gate under the ONE-TIME STANDING PHASE-ENTRY MANDATE. Verification does not activate execution, and no per-trade management approval exists.


## CURRENT FRONTIER — STANDING REAL-PRODUCTION TRADING MANDATE

Management interpretation: the real trader is intended to trade both Spot and Futures under its existing verified contracts. Management authorization is required to enter the real-production phase, not to approve every individual trade.

Once phase-entry is authorized:
- no per-trade management permission is required;
- zero exchange capital is permitted as the starting state;
- Toobit/provider response is authoritative for acceptance or rejection;
- real rejection is captured as evidence rather than treated as a reason to weaken the contract;
- capital is added progressively only after real-market quality/outcome evidence supports it;
- 24-hour operation is a later maturity target, not a prerequisite for starting the feedback loop.

NEXT ACTION: verify the standing mandate package and obtain the single explicit phase-entry management decision. Do not execute before that decision.


## NON-NEGOTIABLE OPERATING INVARIANT — DO NOT REPEAT THIS DECISION

The management model is a ONE-TIME PHASE-ENTRY MANDATE, not per-trade approval.

After explicit phase-entry authorization:
- Spot and Futures are both in scope.
- The trader operates autonomously under the already-verified Decision/Risk/Trade Gate/Execution contracts.
- No management approval request is generated for each trade.
- Zero exchange balance is not a local blocker; the provider is authoritative for acceptance/rejection.
- Real rejection is evidence and must not trigger contract weakening.
- Capital is scaled progressively only after real-market outcome/quality evidence and management review.
- 24-hour operation/analysis is a later maturity stage, not a prerequisite for starting the real feedback loop.

Any future Builder must treat REAL_PRODUCTION_PHASE_ENTRY_REVIEW.md and this section as active governance constraints. Historical text that conflicts with this invariant is historical residue and MUST NOT reopen the per-trade authorization model.
