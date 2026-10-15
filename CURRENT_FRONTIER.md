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


## CURRENT FRONTIER OVERRIDE — 2026-10-15

**Frontier:** Operational final-attempt dependency wiring and provider-outcome evidence.

**VERIFIED**
- Operational verifier accepts explicit adapter and durable claim-store dependencies; default path instantiates neither.
- Toobit submit adapter + allowlisted HTTPS transport are opt-in, no-retry, and validate order identity in provider response.
- SQLite claim store is isolated from the production trading DB and prevents replay across restarts.
- Pre-submit durable fence and post-response accepted/rejected evidence persistence are connected.
- Offline end-to-end lifecycle test passed with a mock provider response and exactly one mock POST.
- Focused CI #52 PASS on `a2c2c0cae8742d36eb1f3f1b005426abe39541ac`: https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38780574776

**BLOCKED / NOT VERIFIED**
- Live attempt remains blocked because the authoritative standing-mandate artifact lacks timezone-aware `issued_at` and `expires_at`.
- No live exchange request, real order, production runtime, or production DB write was performed.
- Live provider semantics and end-to-end outcome evidence are not claimed from offline mocks.

Execution remains OFF by default. The two explicit runtime switches must not be enabled while the mandate or any technical gate is invalid. Earlier frontier text claiming the pipeline is unwired or the adapter cannot submit is historical and superseded; Core remains exchange-agnostic and the standing mandate remains one-time, not per-trade.


## Addendum — 2026-10-15 — Read-only order reconciliation

- Added the fail-closed reconciliation coordinator and offline tests. Positive identity-matched provider lookup persists immutable evidence and can resolve an existing claim; negative, failed, malformed, or mismatched lookup persists `UNRESOLVED_KEEP_QUARANTINED` and keeps the claim in `RECONCILIATION_REQUIRED`. It never retries or authorizes resubmission.
- CI at commit `2d37c36726b5542b8e79c8f4e4eefdb4c3bc2cad`: phase-entry focused verification PASS (57 tests); focused execution contract PASS (56 tests). Offline scope only.
- Toobit Spot client-order IDs are documented as unique among open orders; lifetime uniqueness is not established. The durable claim store enforces no reuse for intents represented in its provider namespace, but cannot prove the absence of external/unrecorded orders.
- Official references: https://api-docs.toobit.com/api/spot-account-and-trading.html and https://api-docs.toobit.com/api/usdt-m-api-v2
- Production order gate remains BLOCKED / NOT VERIFIED: submission disabled, no pipeline wiring, no provider writes, no live order, no cancellation, no production runtime or production DB write. No Futures exposure permission is inferred.
