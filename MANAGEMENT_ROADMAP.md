# MANAGEMENT OVERRIDE — CP-05 CLOSED / CP-06 ACTIVE — 2026-10-29

**Decision:** CP-05 APPROVED / CLOSED based on the latest fresh local Runtime evidence supplied by management. This is a management sign-off; it does not claim profitability or that every outcome horizon has matured.

Evidence:
- Runtime observation: `obs:e6017739-e6d8-443f-b404-982b481d78ba`
- Runtime snapshot: `RS-3ee9dbd841ae31954c94f9a9a7fa6df159fcb0edfa5d8bba19ed291b8f091017`
- Universe 814; Signal Ready / Validated / Decision Ready 737; Trade Ready 108.
- MCP01 evidence persisted 845; persistence failures 0; Order Intents created 0.
- Execution remains OFF; REAL_ORDER=FALSE; REAL_TRADE=FALSE.

## MANDATORY PATH PRESERVATION

- Active local worktree reported by management: `operational-main-20261007-reconcile`. The branch was not found on GitHub during this update; do not create a replacement branch or assume another branch is equivalent.
- No new branch, branch switch, merge, rebase, reset, clean, force-push, destructive restore, overwrite, or deletion without explicit written management authorization.
- Preserve all existing tracked modifications and untracked files. One active work path; reuse existing code; no parallel implementation.
- Do not reopen CP-05 or any CLOSED / VERIFIED checkpoint absent direct, reproducible regression evidence.
- Do not modify protected `arunda_pipeline.py`, Decision, Risk, or Trade Gate without a specific evidence-backed CP-06 need.
- No real/test orders, exchange writes, cancellation, withdrawal, production DB mutation, or execution enablement. Execution authorization remains FALSE.
- Use genuine eligible post-launch data only. No synthetic outcomes, fabricated data, backfill, interpolation, forward-fill, padding, or silent blending.

## CURRENT FRONTIER — CP-06

**Status: AUTHORIZED TO ENTER.**

**Objective:** deterministic, auditable outcome scoring for genuine eligible signals, reusing the existing CP-05 evidence stream and code.

Acceptance contract:
1. Make outcome-scoring rules and horizons explicit and deterministic.
2. Keep outcomes PENDING until their applicable horizon matures.
3. On maturity, classify CORRECT, INCORRECT, or UNSCORABLE with explicit reasons.
4. Prevent duplicate evaluations and duplicate outcome records.
5. Maintain traceable links from original prediction/decision to market evidence, horizon, and result.
6. Missing/invalid evidence stays explicitly missing; never fabricate or silently repair it.
7. Add focused reproducible tests and a quality report; do not claim profitability or customer eligibility without sufficient evidence.

**Next action:** inspect existing CP-06 implementation/tests read-only on the existing active worktree; identify the smallest verified gap; implement only that gap and run focused tests. Do not rebuild CP-05 or create a parallel subsystem.

---

## CURRENT PRODUCT PATH AUDIT — 2026-10-18

The existing CP69 producer is wired into the canonical pipeline; the native UI now optionally displays Aroonda CP72 analysis through the separate read-only CLI. PR #54 selectively reused the compatible part of PR #37's quality dashboard without merging the divergent branch. CP65 remains VERIFIED / CLOSED; the product Control Center requirement remains open independently.

Current blocker: the genuine `runtime_observations/global_selection_outcomes.jsonl` stream is not present in the repository snapshot, so no real-data quality verdict or customer-eligible signal selection is claimed. Access/subscription/payment work stays behind that gate.

Evidence: `PRODUCT_PATH_AUDIT_2026-10-18.md`.

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

# ARUNDA TRADER — MASTER MANAGEMENT ROADMAP

## 0. AUTHORITY
This document is the authoritative management route for ArundaTrader from project birth through the first real trade and subsequent observation/calibration.

The roadmap is the only advancement path. Repository state documents are the source of truth; chat memory, personal Builder plans, side branches, temporary files, and unrecorded work do not override them.

At the end of EVERY checkpoint, the four governance documents MUST be synchronized before the checkpoint is considered governance-complete:
1. `PROJECT_STATE.md`
2. `CURRENT_FRONTIER.md`
3. `CHECKPOINTS.md`
4. `MANAGEMENT_ROADMAP.md`

This synchronization rule is permanent.

## 1. FINAL OBJECTIVE
Build ArundaTrader as a real-market, layered, provider-neutral trading-decision system and take it through a controlled path to the first real trade, real outcome, observation, and calibration.

The system is designed to maximize validated profit opportunity capture through intelligent allocation and disciplined invalidation/exposure control — not through gambling, arbitrary risk minimization, or fixed profit/risk ceilings.

## 2. NON-NEGOTIABLE ARCHITECTURE

### Core principle
The ArundaTrader Core remains exchange-agnostic until the exchange-binding gate is explicitly opened after project completion.

### Information arms
The Market Information Arm is part of the project and legitimately uses external market providers. Providers such as:
- KuCoin
- Bybit
- Gate
- other authorized market-information providers

are information sources, not the execution exchange. Their output is normalized into provider-neutral market observations before entering the Core.

News and Social are also established information arms. They were validated before the current runtime frontier and are not current work unless a direct, provable regression is identified.

### Execution exchange
Toobit is the selected execution exchange/environment at the end of the lifecycle. It is connected through the exchange-agnostic adapter boundary and must not be embedded into Core architecture before the binding gate.

### Cardinality
Production flow is dynamic:
`ELIGIBLE[N] → RISK[N] → TRADE_GATE[N] → TRADE_READY[N]`

`15` is legacy/test-era cardinality and is not a production contract.
`6` is an observed runtime cardinality only and is not a target or fixed universe.

### Data integrity
- Real data only.
- No synthetic data.
- No interpolation.
- No forward-fill/back-fill.
- No padding/fabrication.
- No silent source blending.
- One observation/candle has one attributable source.
- Provenance is mandatory.
- Required unverified real data causes fail-closed behavior.
- Production analysis begins at `LAUNCH_TIMESTAMP = 2026-08-31T00:00:00+00:00`.

### Safety
Until explicit Management authorization:
- `EXECUTION AUTHORIZATION = FALSE`
- order submission/cancellation is forbidden
- exchange writes are forbidden
- withdrawals are forbidden
- production DB writes are forbidden
- credentials/secrets must never be exposed
- `arunda_pipeline.py` is protected unless separately authorized

## 3. PROJECT HISTORY — BUILT / VERIFIED / CLOSED

The following historical stages are completed and must not be reopened or re-audited without direct, provable regression.

### FOUNDATION / DATA
- Data Fabric established on real market sources.
- Production boundary established at the launch timestamp.
- Dynamic Universe established; legacy fixed-15 universe retained only as historical/test residue.
- Real Market path established.

### MARKET INTELLIGENCE → OPPORTUNITY
- Dynamic Signal established.
- Opportunity established.
- Market Information Arm established using real provider sources, with provider-neutral normalization.
- News Arm and Social Arm were approved before the runtime frontier.

### DECISION CHAIN
- Validation established.
- Fusion established.
- Score established.
- Dynamic Decision established.
- Decision is explicitly separated from Risk and Execution.

### RISK / TRADE CHAIN
- Risk established.
- Trade Gate established.
- Risk Contracts established.
- RiskContext established.
- Trade Lifecycle established.
- Exit Evidence established.
- PortfolioRisk Contract established.
- Account/Balance Producer established.
- CP37-J — Toobit Position Wiring — CLOSED / VERIFIED.
- CP37-KA — Toobit Position Reader compatibility — CLOSED / VERIFIED.
- REAL-ENVIRONMENT CONTROLLED RELEASE TEST v0.1 — CLOSED / VERIFIED / PASS.

### SMART RISK / PRE-EXECUTION HISTORY
- CP38-A — CLOSED / VERIFIED / PASS.
- CP38-B — DESIGN PASS.
- CP38-C through CP38-L — CLOSED / VERIFIED / PASS.
- CP38-N — CLOSED / VERIFIED / PASS.
- CP39 — PRE-EXECUTION READINESS → DECISION HANDOFF — CLOSED / VERIFIED / PASS.
- CP40 — DECISION IMPLEMENTATION — CLOSED / VERIFIED / PASS.
- CP41 — DECISION → TRADE INTENT BOUNDARY — CLOSED / VERIFIED / PASS.
  - 12 focused tests passed.
  - Compile/static and scope/diff verification passed.
  - No order, execution, API write, or production DB write occurred.
- CP43 — PRE-EXECUTION READY PACKAGE — CLOSED / VERIFIED / PASS.
  - 77/77 focused tests passed.
  - Compile verification passed.
  - `git diff --check` passed.
  - Worktree clean at closure.
  - Execution authorization remained false.
  - No order, execution, API write, or production DB mutation occurred.

## 4. CURRENT FRONTIER — PROVIDER-NEUTRAL EXECUTION PATH COMPLETION

### EXCHANGE-AGNOSTIC ADAPTER CONTRACT — VERIFIED
The execution adapter boundary is now explicit and replaceable.

- Core-facing contract is provider-neutral.
- No exchange-specific name, symbol, transport, credential, or API semantics are required by Core.
- Toobit is one concrete adapter, not an architectural dependency.
- Submission/cancellation remain disabled and fail-closed.
- Adapter conformance is structurally tested without provider calls.

Commits: `98b75b1`, `3b4f184`, `ded818b`, `ac97549`, `726a6e3`.

Management verdict: **Toobit is an interchangeable execution environment.** The completion target is the Arunda execution path and its provider-neutral boundary, not Toobit itself. A future exchange can replace Toobit by implementing the same adapter contract.

### Safety
EXECUTION AUTHORIZATION = FALSE
ORDER SUBMISSION/CANCELLATION = FORBIDDEN
WITHDRAWAL = FORBIDDEN
DATABASE WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN

## 4A. HISTORICAL FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST
 — EXECUTION PATH COMPLETION / DYNAMIC ASSET BOUNDARY

### CP DYNAMIC EXECUTION ASSET UNIVERSE — VERIFIED
The execution side is now explicitly provider-driven rather than BTC-driven.

- Toobit exposes a read-only dynamic asset discovery surface from authoritative `exchangeInfo` metadata.
- Spot discovery selects current `TRADING` USDT base assets.
- Futures discovery selects current `TRADING` contract underlyings.
- No static production coin list is maintained.
- BTC has no special status.
- Exact provider symbol resolution remains a separate fail-closed operation.
- Multi-asset coverage is verified with ETH/SOL/XRP fixtures.

Commits: `91ffc7e`, `0e3f59e8`, `3b55141a9c2cf3b3d42ee1e285d18fb81c598dd1`.

Management verdict: dynamic asset support is a completed contract improvement. The next frontier is completing the provider handoff to a valid Order Request while keeping Core exchange-agnostic. Toobit rejection, if it occurs later under explicit authorization, is treated as provider/environment evidence and does not justify a BTC-specific or hardcoded Core design.

### Safety
EXECUTION AUTHORIZATION = FALSE
ORDER SUBMISSION/CANCELLATION = FORBIDDEN
WITHDRAWAL = FORBIDDEN
DATABASE WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN

## 4A. HISTORICAL FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST

### PROJECT COMPLETION GATE
Status:
CLOSED / VERIFIED / STATIC CONTRACT PASS

Evidence:
- The canonical exchange-neutral execution contract is present.
- Pre-execution readiness and execution-ready package preserve provider binding as DEFERRED.
- Provider-readiness modules remain outside the exchange-agnostic Core.
- arunda_pipeline.py remains free of Toobit preflight binding.
- The required exchange_execution_boundary.py was restored on MAIN as a minimal fail-closed exchange-agnostic boundary.
- Static syntax verification passed for the restored boundary.
- No Runtime, provider API call, order, real trade, or DB mutation was performed.

Architectural verdict:
CORE → EXCHANGE-AGNOSTIC BOUNDARY → REPLACEABLE EXCHANGE ADAPTER → TOOBIT

### CURRENT FRONTIER
FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST

Project Completion and Toobit Binding are CLOSED / VERIFIED.

The active gate is now the final real-market controlled-test gate. The Toobit adapter remains outside Core and arunda_pipeline.py remains unwired.

### SAFETY
EXECUTION AUTHORIZATION = FALSE
ORDER SUBMISSION/CANCELLATION = FORBIDDEN
WITHDRAWAL = FORBIDDEN
DATABASE WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN
## 5. FORWARD ROADMAP — FINAL CONTROLLED TEST

Project Completion is CLOSED / VERIFIED.
Toobit Binding is CLOSED / VERIFIED.

Current route:
`PROJECT COMPLETION → TOOBIT BINDING → FINAL REAL-MARKET CONTROLLED TEST → EXECUTION AUTHORIZATION → FIRST REAL ORDER → FIRST REAL FILL → REAL OUTCOME → OBSERVATION → CALIBRATION`

### Verified read-only evidence
- Full Read-Only Provider Preflight = PASS against live Toobit.
- Authoritative Futures instrument = BTC-SWAP-USDT.
- Live ExchangeInfo, Futures balance, leverage, positions, open orders, history orders, and server time returned HTTP 200.
- Provider preflight evidence constructed successfully.
- Account/order/contract/timestamp evidence was known and valid.
- GET-only transport; no write endpoint invoked.
- CP46-D test contract = 21/21 PASS across the Toobit adapter and CP46-D provider-preflight suites.
- git diff --check = PASS.
- targeted py_compile = PASS.
- evidence-alignment commit = f80fa83.

### Active controlled-test boundary
The evidence above proves read-only provider readiness. It does not authorize execution.

Do not wire Toobit into arunda_pipeline.py.
Do not submit/cancel orders.
Do not withdraw.
Do not mutate the DB.
Do not enable execution.
Do not invoke additional provider APIs unless separately authorized as part of the controlled-test evidence scope.

## CP46-D / CP46-A6 MANAGEMENT STATE

CP46-D test contract = CLOSED / VERIFIED.

Evidence:
- 21/21 focused tests PASS.
- py_compile PASS.
- git diff --check PASS.
- Futures routing, authoritative instrument resolution, contract evidence, provider-native margin state, leverage state, position state, and order state verified by focused contract tests.
- A6 fail-closed behavior is explicitly tested.

CP46-A6 = BLOCKED.

Exclusive blocker:
- No provider-native Toobit Futures signal has been established that directly authorizes additional portfolio exposure.
- exposure_allowed therefore remains UNKNOWN.
- Balance presence, leverage presence, margin mode, or empty positions MUST NOT be converted into exposure_allowed=True.

Management verdict:
The test contract is verified; the execution-readiness gate is correctly blocked. Do not weaken the contract to obtain PASS.

NEXT ACTION:
Investigate only provider-native Futures exposure authorization evidence. If no direct authoritative signal exists, preserve CP46-A6 as BLOCKED and advance no execution boundary.

## 6. MANAGEMENT GATES

A checkpoint is complete only when:
- BUILT is recorded.
- VERIFIED is recorded with evidence.
- CLOSED or BLOCKED/NOT VERIFIED is recorded.
- blocker is recorded if applicable.
- CURRENT FRONTIER is explicit.
- NEXT ACTION is explicit.
- authorized branch/file scope is recorded when relevant.
- all four governance documents are synchronized.

A route/frontier change requires immediate governance synchronization and its reason + Management authorization.

No next checkpoint starts before the previous checkpoint's governance synchronization is complete.

## 7. BRANCH / FILE GOVERNANCE

No personal, experimental, convenience, speculative, or parallel-truth branch is permitted.

A branch may exist only when explicitly authorized for the active roadmap/checkpoint, with purpose, source, target, and relationship to Canonical recorded.

No file may be added outside the explicitly authorized checkpoint scope.

Temporary, generated, backup, quarantine, forensic, review, and unrelated artifacts are not Canonical project truth.

## 8. SOURCE-OF-TRUTH ORDER
1. Repository state documents
2. Verified contracts and code
3. Git history
4. Chat context

If repository documents conflict, stop and escalate rather than inventing a parallel interpretation.

## 9. CURRENT MANAGEMENT COMMAND

Do not restart.
Do not redesign the project.
Do not reopen closed checkpoints without direct, provable regression.
Do not wholesale-merge the divergent MCP source branch.
Do not create extra branches/files.
Do not mutate the production DB.
Do not execute orders or real trades without explicit authorization.
Do not fabricate outcome evidence.
Preserve provenance and fail-closed behavior.

**Current path:**
`MCP-01 HANDOFF → MAIN → SELECTIVE, EVIDENCE-BACKED INTEGRATION → PROVIDER READINESS → PROJECT COMPLETION → TOOBIT BINDING → FINAL REAL-MARKET CONTROLLED TEST → EXECUTION AUTHORIZATION → FIRST REAL ORDER → FIRST REAL FILL → REAL OUTCOME → OBSERVATION → CALIBRATION`

Every completed checkpoint MUST update the four governance documents before the next frontier begins.


## FINAL REAL-MARKET CONTROLLED TEST CHECKPOINT STATUS
Current Frontier: FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST.

Checkpoint state: OPEN / NOT EXECUTED.

Verified readiness evidence:
- Toobit Binding checkpoint is CLOSED / VERIFIED.
- Full Read-Only Provider Preflight = PASS on live Toobit.
- Authoritative Futures instrument resolved to BTC-SWAP-USDT.
- Live signed read-only account/order endpoints returned HTTP 200.
- Provider preflight evidence constructed successfully.
- CP46-D = 12/12 PASS; git diff --check PASS; targeted py_compile PASS.
- Commit f80fa83 records the final provider-evidence compatibility fixes.

The checkpoint is governance-open but execution-closed.

NEXT ACTION:
Provider-native Futures exposure authorization investigation only. No inference, no execution, no DB mutation, no order/cancel/withdraw.


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

## CP46-A6 — MANAGEMENT DECISION: EXTERNAL PROVIDER CAPABILITY BOUNDARY

Management decision:
Stop further speculative implementation/search at the current evidence boundary. The investigation is CLOSED, while the checkpoint remains BLOCKED / NOT VERIFIABLE.

Reason:
No authoritative read-only Toobit Futures signal equivalent to `exposure_allowed` has been established. Existing account/risk fields are evidence of state and constraints, not authorization to increase exposure.

Strategic consequence:
This is now an external provider-capability dependency. ArundaTrader remains correctly fail-closed. No redesign, weakening, order probe, DB mutation, execution activation, or pipeline wiring is justified.

CURRENT FRONTIER:
FINAL REAL-MARKET EXECUTION READINESS — PROVIDER EVIDENCE BLOCKED.

NEXT ACTION:
Seek authoritative provider clarification/new documented or account-native evidence. Resume only if such evidence exists or a separately approved execution-contract decision changes the requirement.

# END MASTER MANAGEMENT ROADMAP


## CURRENT ROADMAP FRONTIER — EXCHANGE-AGNOSTIC ORDER PREPARATION

Management decision:
The execution roadmap proceeds through the replaceable adapter boundary rather than waiting for a Toobit-specific preflight Boolean that the provider does not expose.

Target:
`Canonical Order Request → Exchange-Agnostic Adapter Contract → Adapter-Owned Provider Order Preparation → Explicitly Authorized Order Attempt`

Rules:
- Core remains exchange-agnostic.
- Toobit remains replaceable.
- Provider-specific translation stays inside the adapter.
- Canonical quantity is never mutated by Core.
- No order/cancel/withdrawal is performed in preparation.
- No DB mutation.
- EXECUTION AUTHORIZATION = FALSE.
- `arunda_pipeline.py` remains unwired until the exchange-neutral completion gate is independently verified.

Current checkpoint:
CP EXCHANGE-AGNOSTIC ORDER PREPARATION HANDOFF — BUILT / NOT YET LOCALLY VERIFIED.

Evidence:
- Generic adapter contract extended with opaque preparation envelope.
- Generic preparation boundary added.
- Toobit adapter translates Futures base quantity using provider contract multiplier and constructs provider-specific payload internally.
- Focused tests added.

NEXT ACTION:
Builder runs local focused tests + py_compile + git diff --check. Then governance is synchronized with actual evidence before the next frontier.
\n\n## CURRENT ROADMAP FRONTIER — EXCHANGE-AGNOSTIC ORDER ATTEMPT\n\nStatus: VERIFIED / PASS / EXECUTION-CLOSED\n\nCompleted path:\n`Canonical Order Request → Exchange-Agnostic Adapter Contract → Adapter-Owned Provider Order Preparation → Provider-Neutral Order Attempt Boundary`\n\nEvidence:\n- `submit_prepared_order` is now part of the replaceable adapter contract.\n- Final order-attempt boundary requires valid technical authorization derived from the active standing mandate and delegates only to the selected adapter.\n- Toobit submission remains fail-closed; no real provider write occurs.\n- 22/22 focused tests passed.\n- py_compile passed.\n- git diff --check passed.\n\nStrategic rules remain unchanged:\n- Core is exchange-agnostic.\n- Toobit is replaceable.\n- Provider-specific payload remains inside the adapter.\n- EXECUTION AUTHORIZATION = FALSE until the ONE-TIME REAL-PRODUCTION PHASE-ENTRY MANDATE is explicitly authorized.\n- No DB mutation and no pipeline wiring.\n\nNEXT FRONTIER:\nExecution-attempt readiness and technical authorization verification against the active standing mandate. A future real order attempt, after phase-entry authorization, does not require a new management authorization.\n

## CURRENT ROADMAP FRONTIER — FINAL EXECUTION ATTEMPT CONTRACT

Status: VERIFIED / PASS / EXECUTION-CLOSED

Completed route:
`Execution Ready Package → Execution-Attempt Readiness → Explicit Authorization → Adapter Preparation → Provider-Neutral Order Attempt → Replaceable Exchange Adapter`

Evidence:
- `final_execution_attempt_contract_v0_1.py` composes the final provider-neutral execution-attempt route.
- `test_final_execution_attempt_contract_v0_1.py` verifies the three critical branches.
- 28/28 focused tests passed across the final contract and all directly dependent execution surfaces.
- py_compile PASS.
- git diff --check PASS.
- Fast-forward to `448806f` PASS.

Management rules remain unchanged:
- Core remains exchange-agnostic.
- Toobit remains replaceable.
- EXECUTION AUTHORIZATION = FALSE.
- No order/cancel/withdrawal.
- No DB mutation.
- No pipeline wiring.
- No execution activation is implied by contract verification.
- Provider rejection, if eventually observed under the active standing mandate after phase entry, is environment evidence rather than a reason to redesign Core.

Management verdict:
The provider-neutral execution path is now contract-complete through the adapter-attempt boundary and VERIFIED. The next management gate is the ONE-TIME REAL-PRODUCTION PHASE-ENTRY DECISION; verification itself does not authorize that phase entry. After phase entry, the trader operates autonomously and the technical authorization boundary uses the standing mandate for each request.

NEXT ACTION:
Do not activate execution automatically. Review/approve the explicit real-attempt scope separately before any provider write is permitted.


## CURRENT MANAGEMENT FRONTIER — STANDING REAL-PRODUCTION TRADING MANDATE

Status: MANAGEMENT REVIEW / READY FOR PHASE-ENTRY DECISION

The management authorization is clarified as a one-time phase-entry mandate for the initial real-production trading phase, not a requirement to request management permission for every trade.

### Standing scope
- Market modes: SPOT + FUTURES.
- Trader operation: autonomous within the already-verified decision, risk, Trade Gate, readiness, and execution contracts.
- Management role: review accumulated real-market evidence and decide capital scaling, not approve each order.
- Provider role: authoritative acceptance/rejection of each submitted request.
- Initial capital: may be zero; zero balance is not a local architecture blocker.
- Capital scaling: progressive and management-reviewed after real outcome evidence demonstrates acceptable opportunity quality and non-destructive loss behavior.
- 24-hour operation/analysis: later maturity target after the feedback loop is functioning; not a prerequisite for first real-market operation.

### Required evidence loop
REAL MARKET -> DECISION -> TRADE GATE -> ORDER ATTEMPT -> PROVIDER RESPONSE -> FILL/REJECTION -> OUTCOME -> OBSERVATION -> CALIBRATION -> MANAGEMENT CAPITAL REVIEW

### Governance rule
No per-trade management authorization request is required after phase-entry authorization. Any later restriction or halt must be a new explicit management decision, or a fail-closed technical/provider safety condition already defined by the contracts.


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


## CURRENT ROADMAP OVERRIDE — PROVIDER ATTEMPT PATH — 2026-10-15

**VERIFIED:** Operational dependency wiring, opt-in Toobit Spot/Futures adapter, allowlisted no-retry HTTPS transport, isolated durable SQLite intent claim, and persisted provider acceptance/rejection evidence. Offline E2E and focused CI #52 passed: https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38780574776 (`a2c2c0cae8742d36eb1f3f1b005426abe39541ac`).

**BLOCKED:** No live attempt until the authoritative standing-mandate record has valid timezone-aware `issued_at` and `expires_at`, and the current technical gates pass. No timestamps may be invented. The default execution path remains OFF; no production runtime, provider write, live order, cancellation, or production DB write was performed.

Historical roadmap statements that the pipeline remains unwired or provider submission is unimplemented are superseded. No per-trade management approval layer is introduced.


## Addendum — 2026-10-15 — Read-only order reconciliation

- Added the fail-closed reconciliation coordinator and offline tests. Positive identity-matched provider lookup persists immutable evidence and can resolve an existing claim; negative, failed, malformed, or mismatched lookup persists `UNRESOLVED_KEEP_QUARANTINED` and keeps the claim in `RECONCILIATION_REQUIRED`. It never retries or authorizes resubmission.
- CI at commit `2d37c36726b5542b8e79c8f4e4eefdb4c3bc2cad`: phase-entry focused verification PASS (57 tests); focused execution contract PASS (56 tests). Offline scope only.
- Toobit Spot client-order IDs are documented as unique among open orders; lifetime uniqueness is not established. The durable claim store enforces no reuse for intents represented in its provider namespace, but cannot prove the absence of external/unrecorded orders.
- Official references: https://api-docs.toobit.com/api/spot-account-and-trading.html and https://api-docs.toobit.com/api/usdt-m-api-v2
- Production order gate remains BLOCKED / NOT VERIFIED: submission disabled, no pipeline wiring, no provider writes, no live order, no cancellation, no production runtime or production DB write. No Futures exposure permission is inferred.
