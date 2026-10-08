# ARUNDATRADER — CURRENT BUILDER HANDOFF

## CROSS-REPOSITORY MASTER MAP — READ FIRST

Read `ARUNDA_ECOSYSTEM_MASTER_MAP.md` before this handoff. It is the permanent map of the relationship between ArundaTrader and AroondaAI, the three roadmap levels, the closed work that must not be repeated, and the current management direction. This prevents state reconstruction from chat memory.
## 2026-10-08 — READ THIS FIRST

This file is the operational handoff for the next Builder session.
Canonical workspace:
C:\Users\ASUS\ArundaTrader

Repository:
hatamnya-afk/ArundaTrader

Active GitHub branch:
operational-main-20261007

## 1. MANAGEMENT VERDICT

CP46-A6 = VERIFIED / PASS / CLOSED.

The former Toobit provider-capability finding about a missing provider-native
Futures `exposure_allowed` Boolean is HISTORICAL EXTERNAL PROVIDER-CAPABILITY
EVIDENCE ONLY. It is NOT an active ArundaTrader blocker.

Architectural decision:
- Provider-native `exposure_allowed` is NOT required for provider-neutral
  order-request preparation or a future explicitly authorized order attempt.
- Zero account balance does NOT locally block construction/submission of an
  order request.
- Balance > 0 is NOT provider acceptance.
- Provider acceptance is NOT a fill.
- The provider remains authoritative for final acceptance/rejection.
- Do not infer exposure permission from balance, leverage, margin type, empty
  positions, risk limits, API-key permission, or hypothetical acceptance.

## 2. VERIFIED EVIDENCE

CP46-A6 focused suite:
58/58 PASS.

Final execution-attempt contract:
28/28 PASS at commit 448806f.

Previously verified Toobit read-only evidence:
- ExchangeInfo HTTP 200.
- Authoritative Futures instrument resolved to BTC-SWAP-USDT.
- Futures balance HTTP 200.
- Futures account leverage HTTP 200.
- Futures positions HTTP 200.
- Futures open orders HTTP 200.
- Futures history orders HTTP 200.
- Server time HTTP 200.
- Provider state was read-only; no order/cancel/withdrawal was performed.

## 3. ARCHITECTURE — DO NOT REDESIGN

CORE
→ EXCHANGE-AGNOSTIC EXECUTION BOUNDARY
→ REPLACEABLE EXCHANGE ADAPTER
→ TOOBIT

Toobit is the first execution adapter, not the architecture.

Market-information providers such as KuCoin/Bybit/Gate remain information
providers, not execution architecture.

No provider-specific symbol/payload semantics belong in Core.

## 4. SAFETY — STILL CLOSED

EXECUTION AUTHORIZATION = FALSE

Therefore:
- NO LIVE ORDER.
- NO ORDER WRITE.
- NO PROVIDER WRITE.
- NO WITHDRAWAL.
- NO DATABASE MUTATION.
- NO `arunda_pipeline.py` WIRING.
- NO automatic execution activation.

A verified execution contract does NOT authorize a real order.

## 5. CURRENT FRONTIER

EXPLICIT EXECUTION-ATTEMPT READINESS CONTRACT
EXECUTION-CLOSED

The next Builder must verify/refine only the explicit readiness/authorization
contract governing a future real attempt.

The next real-order attempt requires a SEPARATE explicit management
authorization and a separately defined scope.

## 6. DO NOT DO

- Do not reopen CP46-A6.
- Do not re-audit closed/verified checkpoints without direct proven regression.
- Do not redesign Core.
- Do not bind Core to Toobit.
- Do not manufacture `exposure_allowed`.
- Do not send an order merely as a capability probe.
- Do not run provider write operations.
- Do not mutate the production DB.
- Do not modify protected `arunda_pipeline.py`.
- Do not use synthetic data, interpolation, forward-fill, back-fill, padding,
  fabrication, or silent source blending.
- Do not merge/rebase/reset/clean/delete/force.
- Do not commit backup/quarantine/runtime artifacts.

## 7. LOCAL WORKTREE CONTEXT

At the end of the current Builder session the intended tracked changes are:
- provider_preflight_v0_1.py
- test_cp46_a6_provider_preflight_v0_1.py
- test_cp46_d_production_provider_preflight_v0_1.py
- test_cp46_d_provider_execution_handoff_v0_1.py
- test_cp49_toobit_provider_preflight_evidence_v0_1.py
- PROJECT_STATE.md
- CURRENT_FRONTIER.md
- CHECKPOINTS.md
- MANAGEMENT_ROADMAP.md

Untracked backup/runtime/database artifacts exist locally. They are NOT part
of the approved A6 change and must not be committed or deleted without
explicit authorization.

## 8. GOVERNANCE RULE

At every checkpoint synchronize:
1. PROJECT_STATE.md
2. CURRENT_FRONTIER.md
3. CHECKPOINTS.md
4. MANAGEMENT_ROADMAP.md

The governance documents are the repository-level source of truth.
Historical stale A6 BLOCKED language must be treated as historical only once
the current governance state explicitly records A6 VERIFIED/PASS/CLOSED.

## 9. HANDOFF COMMAND

Start from the canonical workspace and inspect repository state first.
Do not restart the project.

Required first checks:
- git branch --show-current
- git log -1 --oneline
- git status --short
- read the four governance documents
- confirm EXECUTION AUTHORIZATION = FALSE
- confirm the current frontier above

Then work only inside the explicitly approved frontier.

END OF HANDOFF
