# MANAGEMENT DIRECTIVE — CP-07 PROVISIONAL ACCEPTANCE / CP-08 ENTRY — 2026-10-29

## Decision and sequencing override

- **CP-07: PROVISIONALLY ACCEPTED for its completed initial review/preparation scope; NOT CLOSED / NOT FULLY VERIFIED.** The real-data stream/report, coverage and timestamp limitations, horizon status, and elapsed-time contract were reviewed. No specific reproducible calculation defect was identified in the inspected evidence.
- The separate 24-hour observation window is **DEFERRED until the currently planned product work is completed**. It has not started. Do not launch it now, and do not describe CP-07's full real-data quality acceptance as complete. This directive supersedes earlier wording that prohibited entering CP-08 before the 24-hour window; all uncompleted CP-07 quality claims remain gated on that later review.
- **CP-08 is now the single CURRENT FRONTIER.** CP-07 is a provisionally accepted prior checkpoint with its 24-hour follow-up explicitly deferred; no parallel current frontier is created.
- **CP-08 scope:** complete/reuse the existing UI / Control Center quality presentation. Surface the existing evidence with overall, per-asset, per-direction, and per-horizon views; show sample counts and distinguish observed/scored, pending, and unscorable/missing-evidence outcomes. Preserve traceability and limitations. Use the existing UI/dashboard components and existing evidence source; exactly two existing UIs, no third UI or parallel dashboard.
- CP-08 is a presentation/integration checkpoint, **not** approval to claim signal profitability, customer-publishable eligibility, or subscription readiness. Missing evidence stays missing; immature horizons stay pending. No backfill, synthetic data, interpolation, forward-fill, or fabricated metrics.
- First action: read-only inventory of existing UI/Control Center and already available quality-report/dashboard components; compare them against the CP-08 display contract; identify the smallest evidence-backed gap. Do not re-audit closed CP-05/CP-06 or rebuild existing components.
- Preserve the active local worktree and branch constraints. This documentation update is only on remote branch `operational-main-20261007`; it does not alter the local worktree or imply the remote branch is identical to local `operational-main-20261007-reconcile`.
- **Safety unchanged:** `EXECUTION=OFF`, `REAL_ORDER=FALSE`, `REAL_TRADE=FALSE`. No orders, exchange/provider writes, production DB mutations, or execution enablement. Do not modify protected `arunda_pipeline.py`, Decision, Risk, or Trade Gate without a concrete reproducible defect and explicit scope.

---

# MANAGEMENT ADDENDUM — CP-07 READINESS PREPARATION / START HOLD — 2026-10-29

## CP-07 readiness preparation — 2026-10-29

- Chosen operating mode: option 3 — continue controlled single-cycle observations while preparing a genuine 24-hour observation window. The 24-hour window has NOT started; do not wait for completion of the entire product.
- Preparation review is accepted: existing genuine stream/report and coverage/timestamp/horizon limitations have been examined; no specific reproducible `elapsed_ms` computation defect was identified.
- Runtime path is not yet verified for continuous observation. `track_cycle` is wired into the main pipeline cycle; inspected launchers start UI scripts only; a point-in-time process/task check found no active Arunda runtime or observation/pipeline task (backup tasks only). This is consistent with prior single-cycle runs and is not, by itself, a regression.
- 24-hour start is ON HOLD until the exact known-good single-cycle invocation is identified, its execution/write safety boundaries are confirmed, and the start timestamp plus interruption/recovery/end-review procedure are recorded.
- No parallel collector/scheduler; no speculative code changes; do not modify protected `arunda_pipeline.py`, Decision, Risk, or Trade Gate without a specific reproducible defect and explicit scope.
- CP-07 remains CURRENT / IN PROGRESS / NOT CLOSED. CP-05 remains CLOSED; CP-06 initial gate remains APPROVED; CP-08 is not activated. No backfill or synthetic data; immature horizons remain pending; no profitability/customer eligibility claim. Execution remains OFF.

---

# MANAGEMENT ADDENDUM — INITIAL PROJECT APPROVAL / CP-07 CONTINUES — 2026-10-29

**Management status:** INITIAL PROJECT APPROVAL = APPROVED for continuing the existing project and incremental real-data signal-quality evaluation.

- CP-05 = CLOSED; do not reopen without direct reproducible regression.
- CP-06 initial implementation/test gate = APPROVED for progression; the separate real-data quality review does not automatically reopen CP-06.
- CP-07 = CURRENT / IN PROGRESS / NOT CLOSED. The existing local stream review found 6,445 selection anchors; 4,956 with market observations; 1,489 without observations. Observation gaps: median 60 minutes, p90 22 hours. Runtime capture timestamp missing from 14,253 observations; no inspected elapsed_ms mismatches.
- Interpretation: descriptive observation coverage/timing only. No profitability, predictive-quality, or customer-eligibility claim is established by these counts.
- Next action: keep the existing observation process running and allow genuine data to accumulate; perform a concise targeted review only when a meaningful new evidence window exists or a concrete reproducible defect is found.
- No repeated broad audit, speculative edits, backfill, synthetic data, parallel implementation, or modifications to protected pipeline/Decision/Risk/Trade Gate absent an evidence-backed authorized need.
- Execution remains OFF; no orders, exchange writes, production DB mutations, or live trading.

---

## PRODUCT PATH AUDIT — 2026-10-18

- CP65 is VERIFIED / CLOSED / CANONICAL in Aroonda `PROJECT_STATE.md`; no reopening is implied.
- CP69 source wiring is present in canonical `arunda_pipeline.py`; current observation is written through the CP69 producer. Static wiring is not fresh-runtime verification.
- Aroonda CP72 read-only CLI is merged with passing contract CI. ArundaTrader PR #54 (quality dashboard) and PR #55 (optional Aroonda projection in native UI) are merged with focused CI evidence.
- Real signal-quality evaluation remains BLOCKED / NOT VERIFIED: the canonical repository snapshot contains no `runtime_observations/global_selection_outcomes.jsonl` artifact. Inspect the genuine local stream before judging quality.
- Subscription/access/payment remains downstream of complete quality evidence and explicit eligible-signal selection.
- Detailed evidence ledger: `PRODUCT_PATH_AUDIT_2026-10-18.md`.

---

# CURRENT PRODUCT GOVERNANCE OVERRIDE — 2026-10-17

> **Active management direction.** This override records the product mission approved on 2026-10-16. It supersedes older statements below only where they conflict about the *current project priority/frontier*. It does not rewrite historical evidence, reopen closed checkpoints, change technical execution contracts, or grant execution authority.

## Product mission and boundary

ArundaTrader remains the existing market/signal engine; Aroonda AI remains a separate local intelligence system. The immediate commercial objective is a customer-facing signal-software product with selected eligible signals and monthly subscriptions. This product must remain usable while order execution is disabled.

The intended customer experience includes, where evidence exists: asset, signal time, status, quality, supporting evidence, history/outcomes, and Aroonda analysis within the existing permitted observation/environment boundary. Customer access control and the monthly plan lifecycle (validity, expiry, renewal/cancellation, entitlements, payment integration, and audit events) are product requirements, **not claims of already-built functionality**.

## Status discipline

- **Existing foundations:** preserve the established market/signal chain, existing UI assets, and read-only observation/analysis boundaries. Reuse existing code and proposals; do not create a parallel dashboard or duplicate integration.
- **OPEN / NOT VERIFIED:** UI/Control Center completeness and its actual data connections; CP65/CP69 integration status for the intended product path; Aroonda observations/analysis surfaced safely in UI; reproducible signal-quality evaluation; criteria for selecting customer-publishable signals; customer access, payment, subscription, entitlement, expiry, and audit lifecycle.
- An existing proposal, PR #37 (“Add local read-only selection quality dashboard”, branch `feature/local-selection-quality-dashboard-20261015`), is not merged into `operational-main-20261007`. Review/reuse it before proposing equivalent work. Its historical selection outcomes are not, by themselves, proof that signals are ready to sell.
- Do not describe the product as launched, subscriptions as connected, signals as validated for customers, or runtime behavior as verified without direct evidence on the relevant branch.

## Current project frontier — product path

1. Audit the existing UI / Control Center and actual CP65, CP69, bridge, observation-consumer, and read-only runtime-analysis code on the canonical branch.
2. Record what is BUILT, VERIFIED, OPEN, BLOCKED, and missing, with file/commit/test evidence; do not infer missing implementation from inconclusive search alone.
3. Produce a minimal, evidence-backed implementation plan that reuses existing components and avoids duplicate paths.
4. Then proceed in order: safe UI/observation integration → real-data signal-quality evaluation → explicit eligible-signal selection → customer access and monthly subscription product.
5. Consider capital entry/live trading only later, after signal quality is reviewed and approved, under a separate explicit decision and the existing technical safety gates.

## Unchanged safety and governance

- `EXECUTION AUTHORIZATION = FALSE`; product work does not activate trading.
- No real/test order, provider/exchange write, cancellation, withdrawal, production runtime, production DB mutation, or execution-switch activation is part of this documentation/product-frontier change.
- Do not wire or modify protected `arunda_pipeline.py` as part of this task.
- Use genuine valid post-launch observations only. No synthetic data, interpolation, forward-fill, backfill, padding, fabrication, or silent source blending.
- Do not reopen CLOSED / VERIFIED checkpoints without direct regression evidence. BUILT is not VERIFIED.
- The technical real-order readiness gate may remain BLOCKED / NOT VERIFIED independently; it is not the immediate product frontier and must not displace the approved signal-product sequence.

---
> ## CURRENT ADDENDUM — 2026-10-15 — SIGNED POST + FUTURES SETTLEMENT ALIGNMENT
>
> - Signed Toobit POST parameters now travel in the documented `application/x-www-form-urlencoded` body, while GET query parameters remain in the URL. A mocked transport test verifies body, signature field, content type, and no query-string submission.
> - Futures account-state and duplicate-order reads now use the selected execution instrument's settlement category (`USDT` or `USDC`) rather than hardcoding `USDT`; unknown categories fail closed. Added USDC fixture tests for account state and duplicate checks.
> - **Focused Execution Contract CI: PASS** ([run 38805534608](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38805534608)): 101 passed, 2 subtests passed. **Phase-entry verification: PASS** ([run 38805534537](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38805534537)): 60 tests passed.
> - No live provider calls, orders, cancellations, production runtime, production DB writes, or execution switch changes occurred. Production order path remains BLOCKED / NOT VERIFIED pending authorized runtime wiring, current-run authoritative execution instrument/context, and a genuine Futures exposure-permission source.
>
> ---
>
> ## CURRENT ADDENDUM — 2026-10-15 — SIGNED POST TRANSPORT FIX
>
> - Static review found the HTTPS transport was placing signed Toobit POST parameters in the URL query. Official Toobit signing examples send signed POST parameters in an `application/x-www-form-urlencoded` request body. The transport now keeps GET parameters in the URL and sends POST parameters in the form body; no retry or redirect behavior was added.
> - Added an offline mocked-HTTP test asserting the POST URL contains no query parameters, the form body carries the client ID/signature, and the form content type is present.
> - **Focused Execution Contract CI: PASS** ([run 38805062214](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38805062214)): 99 passed, 2 subtests passed. **Phase-entry verification: PASS** ([run 38805061865](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38805061865)): 60 tests passed.
> - No live API call, order, cancellation, production runtime, production DB write, or execution switch change occurred. The normal pipeline remains fail-closed; live order readiness is still BLOCKED / NOT VERIFIED.
>
> ---
>
> ## CURRENT ADDENDUM — 2026-10-15 — RECONCILIATION TRANSPORT TESTS
>
> - The Toobit HTTPS transport allowlist now includes the read-only Spot order query route `/api/v1/spot/order` and Futures order query route `/api/v2/futures/order`. The existing POST allowlist is unchanged.
> - Added mocked-transport tests for both GET routes; no network call is made by these tests.
> - Focused CI on commit `42f70801901ff81740cf883565758929e5276526`: 98 passed, 2 subtests passed ([run](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38804457253)). Phase-entry focused CI: 59 tests OK ([run](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38804457237)).
> - These are offline results only. `EXECUTION_ENABLED = False`; no production runtime, provider order, cancellation, or production DB write occurred. Live execution readiness remains BLOCKED / NOT VERIFIED.
>
> ---
>
> ## CURRENT ADDENDUM — 2026-10-15 — FUTURES RECONCILIATION ROUTE + EXPANDED OFFLINE VERIFICATION
>
> - Static review found the read-only Futures reconciliation query was still using the legacy `/api/v1/futures/order` route while the adapter's current Futures order submission contract uses v2. Updated the query route to documented `GET /api/v2/futures/order`, preserving the exact `origClientOrderId` and settlement category inputs. Official Toobit v2 docs list the GET route and client-order-ID query parameter: https://api-docs.toobit.com/api/usdt-m-api-v2.
> - Updated the adapter contract test to assert the v2 route and expanded `.github/workflows/focused-execution-contract.yml` so the canonical reconciliation coordinator, compatibility wrapper, isolated dependency factory, offline final-attempt E2E, fail-closed pipeline integration test, Toobit adapter and HTTPS transport suites run in the same focused workflow.
> - **CI VERIFIED / PASS:** [Focused Execution Contract Tests](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38804251519), commit `73ba2582f892208a1742338f0fa220ecdda2e33a`, result **97 passed in 1.19s**.
> - Scope is offline contract testing only. No live Toobit order/query, provider write, cancellation, production runtime, production DB write, execution switch change, or pipeline submission wiring was performed.
> - Current state remains **TECHNICAL REAL-ORDER READINESS: BLOCKED / NOT VERIFIED**. The normal pipeline's execution boundary remains fail-closed and `EXECUTION_ENABLED = False`; the isolated claim/evidence store and reconciliation contract are not activated as an authorized production order path. Live provider acceptance/fill/outcome capture and authoritative Futures exposure permission remain unverified. Do not mark the live gate PASS based on offline CI.
>
> ---
>
> ## CURRENT ADDENDUM — 2026-10-15 — ORDER RECONCILIATION CONTRACT
>
> - Added `execution_order_reconciliation_v0_1.py`: only already-fenced ambiguous claims may be reconciled; exact client-ID and symbol identity must match; no order submit/cancel/retry is performed.
> - Added durable normalized reconciliation evidence to the isolated `SQLiteIntentClaimStore`: client ID, venue/symbol, provider order ID/status, executed quantity/price, provider timestamp, detail code and observation timestamp. Evidence ID reuse with conflicting contents fails closed.
> - Corrected Toobit Futures lookup to documented `GET /api/v1/futures/order`. Official docs: [Spot Query Order](https://api-docs.toobit.com/api/spot-account-and-trading.html) and [Futures Query Order](https://api-docs.toobit.com/api/usdt-m-account-and-trading.html) both document `origClientOrderId`; Futures also documents category and order status fields.
> - Client ID is deterministic (`A` + 31 SHA-256 hex chars of canonical intent ID). Toobit documents Spot client IDs as unique among open orders, not globally unique forever. Therefore the safety invariant is Arunda's permanent unique constraint in the durable claim store; collision means block before submission. This guarantee is not a production guarantee until that store is durably configured and wired into the authorized runtime.
> - **Offline verification:** [Focused Execution Contract Tests](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38802980657) — 58 passed; [Phase-entry focused verification](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38802986919) — 58 tests, OK. Scope is offline contract tests only.
> - A negative/failed/malformed lookup is **not** proof of non-execution. It records `UNRESOLVED_KEEP_QUARANTINED` / `RECONCILIATION_REQUIRED`; no resubmit is allowed. This resolves the ambiguity safely by policy, not by assuming an undocumented provider guarantee.
> - **Operational status remains BLOCKED / NOT VERIFIED:** the durable claim/evidence store and reconciliation helper are not wired into `arunda_pipeline.py` or an authorized production runtime. No provider write, order, cancellation, production runtime, or production DB write was performed; submission switches remain OFF.
>
> ---
>
> ## CURRENT ADDENDUM — 2026-10-15 — AMBIGUOUS ORDER RECONCILIATION CONTRACT
>
> - Added `exchange_execution_order_reconciliation_v0_1.py`: takes an existing durable intent claim, queries the exact provider client ID through the adapter's read-only query, validates identity, persists immutable reconciliation evidence in the explicitly supplied claim/evidence store, and transitions the claim to `PROVIDER_ACCEPTED` / `PROVIDER_REJECTED` only for a positive identity-matched order result.
> - Lookup error, missing order, malformed response, or identity mismatch persists `UNRESOLVED_KEEP_QUARANTINED` and transitions a nonterminal claim to `RECONCILIATION_REQUIRED`. It never releases/reopens the claim, never resubmits, and never infers non-execution from a negative lookup. Evidence-write failures are reported explicitly and do not authorize another POST.
> - CI on commit `2d37c36726b5542b8e79c8f4e4eefdb4c3bc2cad`: Phase-entry focused verification PASS, **57 tests**; Focused Execution Contract Tests PASS, **56 tests**. Both are offline/focused contract verification, not live exchange verification.
> - Provider identity constraint: Toobit's Spot documentation says `newClientOrderId` must be unique among open orders; it does not establish lifetime uniqueness or guarantee that a negative single-order lookup proves no prior execution. The durable Core claim store enforces non-reuse within its provider namespace for all intents represented in that store. That guarantee applies only when the configured isolated durable store is actually used; do not generalize it to external actors or unrecorded history.
> - Official references: [Toobit Spot Account/Trade — Query Order and All Orders](https://api-docs.toobit.com/api/spot-account-and-trading.html); [Toobit Futures v2 — Get one regular order and History regular orders](https://api-docs.toobit.com/api/usdt-m-api-v2).
> - **Management verdict remains BLOCKED for live production:** adapter submission is still disabled; no production pipeline wiring, provider write request, cancellation, real order, production runtime, or production DB write occurred. Futures exposure permission is not inferred from balances, leverage, margin mode, or positions. Do not mark the production order gate PASS based on these offline tests.
>
> ---
>
> ## CURRENT ADDENDUM — 2026-10-15 — STANDING-MANDATE EXPIRY POLICY
>
> - The active phase-entry mandate is revocation-controlled with **no calendar expiry**; do not require or fabricate `issued_at`/`expires_at` merely to create a standing mandate. If an explicit expiry is supplied, it must be timezone-aware, future-dated, and consistent with issuance.
> - Code changes are committed on `operational-main-20261007`: management producer `bdc61f8`; technical authorization boundary `fdcd9de`; management tests `4a02fc5`; final-attempt tests `507ab01` and corrective test-fixture commit `eca7b35`.
> - The final-attempt test fixture was corrected to use only an in-memory claim-store double and a fake adapter stable client ID, and to assert the boundary's specific fail-closed errors. This is offline test scaffolding only; it does not contact Toobit.
> - **Focused verification: VERIFIED / PASS for the scoped tests only.** GitHub Actions run `38801470736` on commit `29f36d33c188ce917d78dfbfde1c0517cbb20b47` completed successfully: `20 passed in 0.05s` across `test_management_execution_authorization_v0_1.py` and `test_final_execution_attempt_contract_v0_1.py`. This does not verify the full suite, Toobit live submission, provider recovery guarantees, or production pipeline integration.
> - This change does **not** authorize a live attempt. Toobit submission remains disabled/unverified; provider client-order-ID and ambiguous-recovery guarantees and outcome capture remain blockers. No pipeline wiring, runtime, live order, provider write, cancellation, or production DB write is authorized by this addendum.
>
> This dated addendum supersedes older statements below that claim the mandate must have calendar expiry fields; those older entries remain historical evidence.
>
> ---
>
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
The management decision does not itself authorize a live submission. Static inspection has found unresolved technical prerequisites: the current Toobit adapter advertises order submission as disabled and has no verified submit path; the active mandate needs an explicit valid expiry; Toobit client-order-ID constraints and ambiguous recovery semantics remain unverified on Draft PR #31. **Trade/order outcome capture remains NOT VERIFIED.**

## GLOBAL SELECTION QUALITY LOOP — 2026-10-12
- **Code state: BUILT / FOCUSED CI PASS (16 tests; run 38266864429, commit `9af0c20ec4b46891ead075a11b4e1a83401ecb73`).** The normal pipeline emits provider-neutral selection anchors, follows later real-market observations, and reports aggregated quality metrics; independent of Toobit listing and order submission.
- Append-only evidence: `runtime_observations/global_selection_outcomes.jsonl`. It records canonical decision identity, selection time, direction, reference price/source, subsequent observed prices, 1h/4h/24h horizon status, directional return, favorable/adverse excursion, and hindsight-only counterfactual movement for missed-opportunity review.
- The aggregate report groups by asset and direction and reports observed/pending counts, scored/unscored counts, wins/losses/flat outcomes, win rate, mean and median directional return at 1h/4h/24h. Pending horizons are excluded from win-rate denominators; direction `NONE` is not scored directionally. The pipeline logs these metrics as `GLOBAL_SELECTION_QUALITY`, `GLOBAL_SELECTION_QUALITY_BY_ASSET`, and `GLOBAL_SELECTION_QUALITY_BY_DIRECTION` each normal cycle.
- Read-only report CLI `global_selection_quality_report_v0_1.py` builds per-asset rankings for 1h/4h/24h only when the configured minimum sample size is met (default 5), and reports mean/median directional returns, win rate and mean favorable/adverse excursions. It never fetches data, changes decisions, writes the DB or treats pending observations as losses.
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

# ARUNDA TRADER — PROJECT STATE

## PURPOSE
Canonical repository-level source of truth for ArundaTrader. Chat memory is not authoritative when these documents are available.

## PROJECT IDENTITY
ArundaTrader is a modular, layered, real-market analysis and trading-decision system. The Core remains exchange-agnostic until project completion is explicitly closed.

Toobit is the execution exchange/environment and is kept outside Core through a replaceable adapter boundary.
KuCoin, Bybit, Gate, and other authorized providers belong to the Market Information Arm. They are market-information sources, not the execution exchange. Their observations are normalized/provider-neutral before entering Core.
News and Social are established information arms and are not current work unless direct, provable regression is identified.

## FINAL OBJECTIVE
Reach the first real trade through a controlled lifecycle, then capture the real fill, real outcome, observation, and empirical calibration.

The intended intelligence objective is maximum validated profit-opportunity capture through intelligent capital allocation and disciplined invalidation/exposure control. Capital allocation is an output of validated opportunity and constraints, not a universal hardcoded ceiling.

## MASTER LIFECYCLE
1. REAL WORLD INFORMATION
2. MARKET INFORMATION ARM — KuCoin / Bybit / Gate / other providers
3. NEWS ARM
4. SOCIAL ARM
5. NORMALIZED / PROVIDER-NEUTRAL MARKET & INFORMATION OBSERVATIONS
6. DATA FABRIC / PRODUCTION BOUNDARY
7. DYNAMIC UNIVERSE
8. OPPORTUNITY
9. SIGNAL
10. VALIDATION
11. FUSION
12. SCORE
13. DECISION
14. ENTRY / INVALIDATION
15. SMART RISK / CAPITAL ALLOCATION / POSITION SIZING
16. TRADE GATE
17. TRADE READY
18. ORDER INTENT
19. EXCHANGE CONSTRAINTS
20. PRE-EXECUTION READY
21. EXCHANGE-AGNOSTIC BOUNDARY
22. PROJECT COMPLETION GATE
23. TOOBIT EXCHANGE BINDING
24. FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST
25. EXPLICIT EXECUTION AUTHORIZATION
26. FIRST REAL ORDER
27. FIRST REAL FILL
28. REAL OUTCOME
29. OBSERVATION
30. CALIBRATION

## PRODUCTION BOUNDARY
LAUNCH_TIMESTAMP = 2026-08-31T00:00:00+00:00
Production analysis uses real post-launch data only.

## DATA / CARDINALITY RULES
- Real data only.
- No synthetic data, interpolation, forward-fill, back-fill, padding, fabrication, or silent source blending.
- One candle/observation = one attributable source; provenance is mandatory.
- Fail closed when required real data cannot be verified.
- Production flow is dynamic: `ELIGIBLE[N] → RISK[N] → TRADE_GATE[N] → TRADE_READY[N]`.
- Legacy `15` is test-era cardinality, not production truth.
- Observed `6` is runtime cardinality only, not a target or fixed universe.
- Global Universe is not the Toobit Universe.

## EXECUTION SAFETY
EXECUTION AUTHORIZATION = FALSE
ORDER WRITE = FORBIDDEN
WITHDRAW = FORBIDDEN
DATABASE WRITE = FORBIDDEN unless explicitly authorized
Credentials and secrets must never be exposed.

## HISTORICAL COMPLETION — CLOSED / VERIFIED
The following are historical truth and must not be reopened or re-audited without direct, provable regression:
- Data Fabric
- Dynamic Universe
- Real Market
- Dynamic Signal
- Opportunity
- Fusion
- Score
- Decision
- Risk
- Trade Gate
- Risk Contracts
- RiskContext
- Trade Lifecycle
- Exit Evidence
- PortfolioRisk Contract
- Account/Balance Producer
- CP37-J — Toobit Position Wiring
- CP37-KA — Toobit Position Reader compatibility
- REAL-ENVIRONMENT CONTROLLED RELEASE TEST v0.1 — PASS
- CP38-A, C, D, E, F, G, H, I, J, K, L, N — CLOSED / VERIFIED / PASS
- CP38-B — DESIGN PASS
- CP39 — CLOSED / VERIFIED / PASS
- CP40 — CLOSED / VERIFIED / PASS
- CP41 — CLOSED / VERIFIED / PASS
- CP43 — CLOSED / VERIFIED / PASS

CP41 evidence: 12 focused tests passed; compile/static and scope/diff verification passed; no order, execution, API write, or production DB write.
CP43 evidence: 77/77 focused tests passed; compile passed; `git diff --check` passed; worktree clean at closure; execution authorization false; no runtime order, execution, API write, or DB mutation.

## CURRENT FRONTIER

### EXCHANGE-AGNOSTIC ADAPTER CONTRACT — VERIFIED
Status = VERIFIED / REPLACEABLE BOUNDARY

A provider-neutral adapter contract is now explicit in `exchange_execution_adapter_contract_v0_1.py`. Core-facing execution uses a replaceable adapter interface; the contract contains no exchange name, provider symbol, transport, credential, or exchange-specific semantics. Toobit is only one concrete adapter implementation.

Verified changes:
- `ExchangeExecutionAdapter` structural contract established.
- Adapter capabilities are provider-neutral.
- Toobit conforms to the replaceable adapter boundary while remaining execution-disabled.
- Order submission/cancellation remain fail-closed.
- No Core dependency on Toobit was introduced.

Evidence commits: `98b75b1`, `3b4f184`, `ded818b`, `ac97549`, `726a6e3`.

This checkpoint does NOT authorize execution and does NOT close the final real-market gate.



### CP DYNAMIC EXECUTION ASSET UNIVERSE — IMPLEMENTED
Status = VERIFIED / DYNAMIC / PROVIDER-DRIVEN

The execution instrument path is asset-agnostic. Toobit adapter now exposes read-only `discover_tradable_assets(venue)` derived from current authoritative exchange metadata and filtered to `TRADING`. Spot discovery uses live USDT base assets; Futures discovery uses live underlying assets. Exact provider symbol selection remains a separate provider-neutral instrument-resolution step.

No static BTC/ETH/SOL universe was introduced. BTC is not privileged. A newly listed/tradable provider asset can enter the execution asset universe without Core code changes.

Evidence commits: 91ffc7e (dynamic provider asset discovery), 0e3f59e (multi-asset discovery tests), 3b55141 (asset-agnostic resolver test).

SAFETY: discovery is read-only; no order, provider write, DB mutation, execution authorization, or arunda_pipeline.py wiring.


### FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST — OPEN

Status = CURRENT FRONTIER / OPEN / NOT EXECUTED

Purpose:
Open and verify the final real-market controlled-test gate after verified Project Completion and verified Toobit Binding. Opening this gate is governance/readiness control only; it does not authorize execution.

Verified real-market read-only evidence:
- Full Read-Only Provider Preflight = PASS against live Toobit.
- Toobit ExchangeInfo returned HTTP 200 and authoritative Futures instrument resolution selected exactly BTC-SWAP-USDT.
- Futures balance, account leverage, positions, open orders, history orders, and server time returned HTTP 200.
- Provider preflight evidence was constructed successfully.
- Provider account state was known with no position conflict; provider order state was known and empty; contract constraints were valid; timestamp state was known.
- Real provider transport was GET-only.
- No order submission, cancellation, withdrawal, exchange write, database mutation, or execution authorization occurred.
- CP46-D focused verification: 12/12 tests passed; git diff --check passed; targeted py_compile passed.
- Evidence-alignment commit: f80fa83 (CP Controlled Test: align Toobit provider evidence with live state).

Controlled-test boundary:
- Core remains exchange-agnostic.
- Toobit remains outside Core through the replaceable adapter boundary.
- arunda_pipeline.py remains unwired to the Toobit provider-preflight chain.
- Execution authorization remains FALSE.

Authorized scope now:
- Inspect and verify the controlled-test contract/readiness boundary.
- Preserve real-data-only and fail-closed rules.
- Preserve execution-off safety.
- No order/cancel/withdraw.
- No DB mutation.
- No execution authorization unless separately and explicitly authorized.
- No modification of closed/verified checkpoints or protected arunda_pipeline.py.

CP46-D / CP46-A6 STATUS

CP46-D test contract = VERIFIED.
Evidence:
- 21/21 focused tests passed across the Toobit adapter and CP46-D provider-preflight test suites.
- py_compile passed for the focused adapter/evidence/test modules.
- git diff --check passed.
- Futures routing, authoritative instrument resolution, contract evidence, provider-native margin state, leverage state, position state, and order state are covered by the focused contract.
- The three Futures PASS expectations were aligned to the strengthened A6 fail-closed contract without weakening production logic.

CP46-A6 = BLOCKED exclusively by missing provider-native Futures exposure authorization evidence.
- exposure_allowed remains UNKNOWN.
- No inference from balance, leverage, margin mode, or absence of positions is permitted.
- No provider-native Toobit Boolean authorizing additional Futures exposure has been established.
- The fail-closed contract correctly returns BLOCK_PORTFOLIO_EXPOSURE when exposure authorization is not directly evidenced.

NEXT ACTION:
Investigate only whether Toobit exposes a direct, authoritative Futures exposure-authorization signal. If no such provider-native evidence exists, keep CP46-A6 BLOCKED. Do not fabricate or infer exposure permission. No additional provider API calls, order/cancel/withdraw, DB mutation, execution authorization, or arunda_pipeline.py wiring. Do not invoke additional provider APIs, submit/cancel orders, mutate the DB, or enable execution unless separately and explicitly authorized.

### PROJECT COMPLETION — CLOSED / VERIFIED
Status = CLOSED / VERIFIED / STATIC CONTRACT PASS

The exchange-agnostic Core is now closed at the Project Completion Gate. The required exchange boundary is present on MAIN and remains fail-closed. Toobit is still outside Core and is not bound.

Evidence:
- exchange_execution_contract.py defines the canonical exchange-neutral request/result and execution-off safety contract.
- pre_execution_readiness_v0_1.py and execution_ready_package_v0_1.py keep provider binding deferred.
- provider-readiness contracts remain separate from Core.
- arunda_pipeline.py does not call the Toobit preflight chain.
- exchange_execution_boundary.py is present on MAIN and provides the required fail-closed execute_order boundary.
- Static syntax verification passed for the restored boundary.

Architecture:
CORE → EXCHANGE-AGNOSTIC EXECUTION BOUNDARY → REPLACEABLE EXCHANGE ADAPTER → TOOBIT

### TOOBIT EXCHANGE BINDING — CLOSED / VERIFIED
Status = CLOSED / VERIFIED / FOCUSED STATIC CONTRACT PASS

Toobit binding is implemented only at the existing replaceable adapter boundary. The provider-specific adapter remains outside Core and arunda_pipeline.py remains unwired.

Safety remains:
EXECUTION AUTHORIZATION = FALSE
ORDER WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN
DATABASE WRITE = FORBIDDEN
NO REAL TRADE
## REPOSITORY GOVERNANCE
Canonical branch = `main`
Canonical base commit = `8945316ae1fec74ecfab40ac33ec9593e6d7ca8b`
Repository consolidation gate = CLOSED / MANAGEMENT-AUTHORIZED

No unauthorized branch or file may become project truth. Branches are permitted only when explicitly authorized for an active roadmap/checkpoint. New files require defined responsibility, active-checkpoint necessity, and recorded scope.

## PROTECTED SURFACES
- `arunda_pipeline.py`
- production database
- execution controls
- order submission/cancellation
- withdrawal
- closed/verified contracts
- backup/quarantine artifacts

## MANDATORY GOVERNANCE SYNCHRONIZATION
At the end of every checkpoint, synchronize:
1. `PROJECT_STATE.md`
2. `CURRENT_FRONTIER.md`
3. `CHECKPOINTS.md`
4. `MANAGEMENT_ROADMAP.md`

Record BUILT, VERIFIED, CLOSED/BLOCKED/NOT VERIFIED, evidence, blocker, CURRENT FRONTIER, NEXT ACTION, and authorized scope. A checkpoint is not governance-complete until these documents are internally consistent.

## SOURCE-OF-TRUTH ORDER
1. Repository state documents
2. Verified contracts and code
3. Git history
4. Chat context

## MANAGEMENT COMMAND
No restart. No redesign. No reopening closed checkpoints without proven regression. No modification of approved information arms without regression. No Fixed-15/Fixed-6 production assumptions. No test capital as production capital. No guessing of Entry/Invalidation/Quantity/Exposure/Authorization. No order/execution before explicit authorization. No extra branches/files.

The roadmap is the only path.


## PHASE B — TOOBIT BINDING CHECKPOINT STATUS
Status = CLOSED / VERIFIED / FOCUSED STATIC CONTRACT PASS

Verified scope on main:
- toobit_exchange_adapter_v0_1.py — replaceable Toobit-specific read-only adapter boundary.
- test_toobit_exchange_adapter_v0_1.py — focused adapter safety/contract tests.
- No arunda_pipeline.py wiring.
- No order/cancel/withdraw implementation; adapter write methods fail closed.
- No runtime/provider connectivity was performed.
- No DB mutation and no execution authorization.

Evidence:
- 6/6 focused adapter tests passed.
- py_compile passed for adapter and focused tests.
- git diff --check passed.
- Provider-authoritative Futures position state is preserved without local inference.
- Fix commits: 2f3a79a2 and 30485cb8.

Checkpoint closure: VERIFIED/CLOSED at the static/read-only adapter contract boundary. Runtime/provider API connectivity remains deferred to the later authorized controlled-test gate.


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

## CP46-A6 — MANAGEMENT DECISION / PROVIDER CAPABILITY BOUNDARY

Decision:
- The provider-native exposure investigation is CLOSED as an investigation.
- CP46-A6 itself remains BLOCKED / NOT VERIFIABLE at the current Toobit read-only provider boundary.
- No code weakening, inference, order-test, or execution workaround is approved.
- This blocker is classified as an external provider-capability dependency, not an ArundaTrader implementation defect.

Operational consequence:
- Final real-market controlled test remains execution-closed.
- EXECUTION AUTHORIZATION remains FALSE.
- The project must not manufacture an exposure authorization signal locally.
- The only valid unblock is new authoritative provider evidence or an explicit future management decision that changes the execution contract after separate approval.

# END PROJECT STATE


## CURRENT FRONTIER — EXCHANGE-AGNOSTIC ORDER PREPARATION HANDOFF

Status = BUILT / STATIC CONTRACT INTEGRATION — NOT EXECUTED

Management decision:
- The Core must complete the provider-neutral execution path without becoming dependent on Toobit.
- Toobit is one replaceable adapter, not the execution architecture.
- The missing Toobit-specific `exposure_allowed` Boolean is NOT allowed to become a permanent Core-completion blocker.
- Provider rejection remains valid environmental evidence once an explicitly authorized real order attempt is eventually opened.
- EXECUTION AUTHORIZATION remains FALSE.

Built:
- `exchange_execution_adapter_contract_v0_1.py` now defines an opaque `AdapterOrderPreparation` boundary.
- `exchange_execution_order_preparation_v0_1.py` validates the canonical request and delegates preparation to the selected adapter without inspecting provider fields.
- Toobit implements adapter-owned preparation, including provider-specific instrument resolution and quantity translation.
- Futures base-asset quantity is translated inside the adapter using provider contract multiplier; Core quantity remains unchanged.
- Spot market BUY translation is kept inside the adapter because Toobit's provider semantics use quote-asset quantity for that request form.
- No order endpoint is called by preparation.

Safety:
- EXECUTION AUTHORIZATION = FALSE
- ORDER WRITE = FORBIDDEN
- PROVIDER WRITE = FORBIDDEN
- DATABASE WRITE = FORBIDDEN
- `arunda_pipeline.py` remains unwired to Toobit.

Verification status:
- Tests were added for the generic adapter contract, exchange-neutral handoff, and Toobit-owned preparation.
- Local execution of the newly added tests has not yet been performed in this checkpoint environment; do not claim runtime PASS until the Builder runs them locally.

NEXT ACTION:
Run the focused local tests and static checks for the new exchange-neutral preparation boundary. If green, synchronize this checkpoint's four governance documents again with the verified evidence, then continue toward provider-order-attempt readiness without enabling execution.
\n\n## CP EXCHANGE-AGNOSTIC ORDER ATTEMPT BOUNDARY — VERIFIED\n\nStatus: VERIFIED / PASS / EXECUTION-CLOSED\n\nBuilt:\n- `exchange_execution_adapter_contract_v0_1.py` now includes the provider-neutral `submit_prepared_order` contract.\n- `exchange_execution_order_attempt_boundary_v0_1.py` establishes the final provider-neutral gate from prepared adapter order to a future provider order attempt.\n- Authorization is evaluated explicitly; readiness, adapter capability, account state, or provider metadata cannot infer authorization.\n- Toobit implements the prepared-submission surface but remains fail-closed with `EXECUTION_DISABLED_ORDER_SUBMISSION_NOT_IMPLEMENTED`.\n\nVerification:\n- Focused suite: 22 passed.\n- py_compile: PASS.\n- git diff --check: PASS.\n\nSafety:\n- EXECUTION AUTHORIZATION = FALSE.\n- No real order/cancel/withdrawal.\n- No DB mutation.\n- `arunda_pipeline.py` remains unwired.\n\nManagement verdict:\nThe provider-neutral order-attempt boundary is VERIFIED. The architecture can now reach a selected replaceable adapter only after explicit authorization, while actual provider submission remains separately disabled.\n\nNEXT ACTION:\nAdvance to the explicit execution-attempt contract/readiness gate without activating real execution.\n

## CP FINAL EXECUTION ATTEMPT CONTRACT — VERIFIED

Status = VERIFIED / PASS / EXECUTION-CLOSED

Built:
- `final_execution_attempt_contract_v0_1.py` composes the provider-neutral final execution-attempt path.
- The composition delegates readiness alignment, explicit authorization, adapter preparation, and adapter attempt to the already-verified boundaries.
- `test_final_execution_attempt_contract_v0_1.py` covers unauthorized blocking, authorized reachability of a replaceable adapter, and readiness/package mismatch blocking.

Verification evidence:
- 28/28 focused tests passed across the final contract, readiness, order-attempt boundary, order preparation, adapter contract, and Toobit adapter suites.
- py_compile passed for all focused implementation/test modules.
- git diff --check passed.
- Fast-forward from 91c82a7 to 448806f completed cleanly.

Safety and architecture:
- EXECUTION AUTHORIZATION = FALSE.
- Toobit remains replaceable and outside Core.
- No real order/cancel/withdrawal.
- No DB mutation.
- `arunda_pipeline.py` remains unwired.
- Toobit submission remains fail-closed.
- No authorization is inferred or created by the final contract.

Management verdict:
The provider-neutral execution-attempt composition is VERIFIED. The system can prove the complete pre-attempt route while real execution remains explicitly disabled.

CURRENT FRONTIER:
Controlled decision for the separately authorized real execution-attempt gate; no automatic activation.


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


## CURRENT STATE OVERRIDE — FINAL ATTEMPT DEPENDENCIES — 2026-10-15

Current operational implementation: opt-in Toobit Spot/Futures submit adapter + allowlisted no-retry HTTPS transport, stable intent-derived client ID, isolated SQLite claim store, pre-submit outcome-unknown fence, and post-response durable acceptance/rejection evidence. `arunda_pipeline.py` now injects these dependencies only when both explicit submission switches are set; defaults remain disabled and do not construct the dependencies.

Verification: offline end-to-end lifecycle test uses a mock provider response and confirms exactly one mock POST plus persisted `PROVIDER_ACCEPTED`; focused CI #52 PASS at https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38780574776, commit `a2c2c0cae8742d36eb1f3f1b005426abe39541ac`.

Current disposition: **CODE VERIFIED; LIVE ATTEMPT BLOCKED / NOT VERIFIED**. The authoritative standing mandate lacks timezone-aware `issued_at` and `expires_at`; do not fabricate timestamps. No production runtime, live provider request/order, cancellation, or production DB write occurred. Historical statements above that the pipeline is unwired or submission is unimplemented are superseded by this section; global execution constants and adapter default remain OFF.


## Addendum — 2026-10-15 — Read-only order reconciliation

- Added the fail-closed reconciliation coordinator and offline tests. Positive identity-matched provider lookup persists immutable evidence and can resolve an existing claim; negative, failed, malformed, or mismatched lookup persists `UNRESOLVED_KEEP_QUARANTINED` and keeps the claim in `RECONCILIATION_REQUIRED`. It never retries or authorizes resubmission.
- CI at commit `2d37c36726b5542b8e79c8f4e4eefdb4c3bc2cad`: phase-entry focused verification PASS (57 tests); focused execution contract PASS (56 tests). Offline scope only.
- Toobit Spot client-order IDs are documented as unique among open orders; lifetime uniqueness is not established. The durable claim store enforces no reuse for intents represented in its provider namespace, but cannot prove the absence of external/unrecorded orders.
- Official references: https://api-docs.toobit.com/api/spot-account-and-trading.html and https://api-docs.toobit.com/api/usdt-m-api-v2
- Production order gate remains BLOCKED / NOT VERIFIED: submission disabled, no pipeline wiring, no provider writes, no live order, no cancellation, no production runtime or production DB write. No Futures exposure permission is inferred.


## CURRENT ADDENDUM — 2026-10-16 — ED25519 LIVE MANAGEMENT-MANDATE REVOCATION GATE

- Added `management_mandate_revocation_runtime_v0_1.py`: every final order-attempt path now requires a fresh signed management status before technical authorization. Ed25519 signature verification uses a trusted 32-byte public key; the private key is not part of ArundaTrader.
- Default source performs a bounded HTTPS GET (3-second timeout, 16 KiB response cap, redirects forbidden). Status must match the configured source ID and the current mandate ID, be exactly `ACTIVE` or `REVOKED`, be no older than 30 seconds, and not be more than 5 seconds in the future. Missing source/configuration, malformed payload, missing public key, invalid signature, identity mismatch, stale/future timestamp, and `REVOKED` all fail closed before adapter submission.
- Required runtime configuration: `ARUNDA_MANDATE_STATUS_URL`, `ARUNDA_MANDATE_STATUS_SOURCE_ID`, and `ARUNDA_MANDATE_STATUS_PUBLIC_KEY_B64`. The actual management-authority endpoint and its trusted public key have **not yet been provisioned/configured**; do not treat the mechanism as connected to a real authority until those values are supplied and a real signed response is verified.
- Added positive/negative tests for valid `ACTIVE`, `REVOKED`, invalid signature, stale status, missing source, mismatched mandate ID, future timestamp, missing trusted key, and unexpected source ID. The final-attempt contract also proves `REVOKED` blocks before adapter submission.
- **Operational branch verification:** `operational-main-20261007`, commit `66fb221e5c7340218fc4bc6be0a6db2a96451409`. Phase-entry focused verification PASS: [run 38864547758](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38864547758). Focused Execution Contract CI PASS: [run 38864547866](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38864547866), **111 passed**. An earlier CI attempt failed due missing CI dependency and two test-fixture defects; those were corrected and the above final runs passed.
- No repair branch was merged. No live exchange API write, order, cancellation, production runtime, production DB write, or execution-switch activation occurred. **Production phase-entry remains BLOCKED / NOT VERIFIED until the real authority endpoint/public key are provisioned and the signed status is verified in the actual runtime.**
