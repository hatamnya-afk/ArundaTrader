# CURRENT GOVERNANCE OVERRIDE — 2026-10-08

> **THIS SECTION IS THE ACTIVE STATE.**
> Historical sections below are preserved as evidence/history and MUST NOT be interpreted as the current frontier when they conflict with this section.
>
> ## CURRENT CROSS-REPOSITORY MAP
> Read `ARUNDA_ECOSYSTEM_MASTER_MAP.md` first.
>
> ## VERIFIED POSITION
> The provider-neutral execution-attempt contract is VERIFIED / PASS / CLOSED for its defined scope.
> Latest verified endpoint: `448806f`.
>
> ## CURRENT FRONTIER
> **MANAGEMENT REVIEW — EXPLICIT REAL-ORDER ATTEMPT GATE**
>
> The next task is to define and inspect the bounded, explicit management gate for a future real provider order attempt. This is preparation/governance only.
>
> ## SAFETY
> `EXECUTION AUTHORIZATION = FALSE`
> `ORDER WRITE = FORBIDDEN`
> `PROVIDER WRITE = FORBIDDEN`
> `DATABASE WRITE = FORBIDDEN`
> `arunda_pipeline.py` remains unwired.
>
> ## FORBIDDEN
> - Do not submit an order.
> - Do not call provider write endpoints.
> - Do not activate execution.
> - Do not reopen CP46-A6.
> - Do not redesign Core or bind Core to Toobit.
> - Do not treat historical A6 BLOCKED text as the current frontier.
>
> ## ALLOWED NOW
> - Define the explicit real-attempt gate.
> - Verify its preconditions, authorization separation, scope, safety interlocks, and evidence requirements.
> - Prepare a management decision package.
>
> **STOP CONDITION:** after the gate package is verified, STOP. A separate explicit execution authorization is required before any provider write.

---

# ARUNDA TRADER — CURRENT FRONTIER

## STATUS
CURRENT FRONTIER — PROVIDER-NEUTRAL EXECUTION PATH COMPLETION

## EXCHANGE-AGNOSTIC ADAPTER CONTRACT
Status: VERIFIED / REPLACEABLE

The execution boundary now has an explicit provider-neutral adapter contract. The Core does not name Toobit and can target another exchange adapter implementing the same contract.

Toobit remains only the currently selected concrete execution environment. Its capabilities are advertised separately and its order submission/cancellation are still disabled.

Next: complete the provider-neutral handoff from canonical order request through the selected adapter without binding Core to any exchange. Only after that, under separate explicit authorization, may a real order attempt occur.


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
Management review of the separately authorized controlled real-order-attempt gate. No execution activation is implied by this verification.


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
