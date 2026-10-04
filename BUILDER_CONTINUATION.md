# ARUNDA TRADER — BUILDER CONTINUATION BRIEF
## PURPOSE

This file is the **context-loss continuation contract** for the next Builder/Manager.

If the current Builder/Chat becomes unavailable, the next Builder MUST continue the project from this document and the canonical governance documents. Do not spend days re-searching the history or rebuilding the architecture from scratch.

Primary governance order:
1. PROJECT_STATE.md
2. ARCHITECTURE.md
3. CHECKPOINTS.md
4. CURRENT_FRONTIER.md
5. BUILDER_PROTOCOL.md
6. MANAGEMENT_ROADMAP.md
7. THIS FILE

Repository governance wins over conversational memory.

---

## 1. PROJECT GOAL

ArundaTrader is being completed as a **real-market trading decision and execution system**.

There is NO separate "laboratory mode".

The intended operating model is:

REAL MARKET
→ DYNAMIC UNIVERSE
→ OPPORTUNITY
→ SIGNAL
→ VALIDATION
→ FUSION
→ SCORE
→ DECISION BIRTH
→ RISK
→ POSITION SIZING
→ TRADE GATE
→ TRADE READY
→ ORDER INTENT
→ CANONICAL ORDER REQUEST
→ EXECUTION BOUNDARY
→ PROVIDER
→ REAL PROVIDER RESPONSE
→ OBSERVATION
→ ANALYSIS
→ MANAGEMENT CAPITAL DECISION

Zero account capital does NOT mean the Trader stops thinking, deciding, sizing, gating, or building a real order request.

A real provider rejection caused by the actual account state is valid evidence.

Capital deployment is a MANAGEMENT decision after Trader output quality is observed and analyzed.

---

## 2. CLOSED AREAS — DO NOT REOPEN

Unless direct regression evidence exists, do NOT reopen or redesign:

- CP39 / Capital Independence
- Zero-Capital Contract
- CP44
- CP46-A..H
- CP47
- CP48
- CP64..CP71
- CP69 observation contract

Do NOT:
- redesign Risk/Data Fabric;
- reconstruct historical BUY rules;
- invent score/confidence thresholds;
- invent capital or quantity;
- synthesize data;
- repair/change the production DB;
- move exchange-specific logic into Core;
- redesign the architecture because Toobit rejects a request;
- run repetitive audits of already-verified checkpoints.

---

## 3. CURRENT MASTER ROUTE

CURRENT FRONTIER:

**TRADER COMPLETION
→ REAL-MARKET E2E OUTPUT PROOF
→ OUTPUT OBSERVATION / CONSUMPTION
→ OUTPUT ANALYSIS
→ MANAGEMENT CAPITAL DECISION**

Immediate technical boundary:

**Canonical Order Request
→ real execution boundary
→ real Toobit response
→ CP69 evidence**

After that:

**CP69 canonical observation
→ Trader UI / observation surface
→ Aroonda read-only consumer
→ analysis / explanation / gap detection**

Aroonda does NOT replace ArundaTrader execution authority.

---

## 4. CURRENT EXECUTION ARCHITECTURE

The verified production path is:

CanonicalOrderRequest
→ CP46-D provider preflight
→ CP46-E execution eligibility
→ CP49 readiness / safety gate
→ CP46-F exact ProviderOrderRequest binding
→ CP46-G execution consumer handoff
→ adapter.submit_order()
→ Toobit live transport
→ real provider response
→ CP69 observation

Important implementation surfaces:

- cp49_live_execution_bridge_v0_1.py
- cp46_g_binding_execution_consumer_handoff_v0_1.py
- toobit_trading_adapter.py
- toobit_spot_order_live_transport_v0_1.py
- cp49_first_execution_readiness_v0_1.py
- cp49_first_execution_evidence_contract_v0_1.py
- cp69_runtime_observation.py
- arunda_pipeline.py

Do not bypass CP46-G or call execute_order directly from a new bridge.

---

## 5. EXECUTION CONTROL

Explicit Management execution control:

ARUNDA_EXECUTION_MANAGEMENT_AUTHORIZED=TRUE

This means execution authorization only.

It does NOT mean:
- capital authorization;
- strategy authorization;
- permission to redesign contracts;
- permission to repeat runtimes indefinitely.

The current governance requires fail-closed behavior and no automatic retry.

---

## 6. IMPORTANT REAL-WORLD FINDINGS ALREADY ESTABLISHED

### Toobit authenticated read-only path

Authenticated:

GET /api/v1/account

returned HTTP 200 and a valid account identity, with an empty balances array.

This established that:
- API authentication works;
- API key/secret are valid;
- server timestamp handling is accepted on the signed account endpoint;
- HMAC/query construction works on the signed account endpoint;
- the account can legitimately expose zero balances.

Therefore, do NOT restart generic API-key/signature/time investigations merely because an order endpoint returned -1021.

### Order transport investigation

The observed -1021 diagnostics were not sufficient proof of a real provider rejection when produced through fake/mock response paths.

Do NOT label a mocked -1021 as real Toobit evidence.

The remaining question is the **real order endpoint request/response behavior**.

---

## 7. CURRENT CONTROLLED PROBE

The project is currently at the boundary where Management authorized a **single real provider submission probe**.

There is no existing production selector for "one order only".

Do NOT modify production pipeline merely to add a probe selector.

The approved approach is a temporary external probe that:
- imports arunda_pipeline;
- wraps execute_canonical_request;
- permits exactly ONE real execution-boundary call;
- blocks before a second call;
- prints the first real execution result;
- is not a production architecture change.

Temporary file intended:

cp49_single_order_real_probe_v0_1.py

Expected invocation:

python .\cp49_single_order_real_probe_v0_1.py

IMPORTANT:
The probe must never accidentally submit a second provider order.

If the first invocation fails before reaching the provider, do not infer that a real order was attempted. Inspect the returned status/error and adjust the probe boundary carefully. Do not blindly run another real submission.

If a real provider response is obtained, record it as evidence once.

---

## 8. RESULT INTERPRETATION

Only evidence may establish these states:

EXECUTION=ON
means the real execution path was enabled/entered.

REAL_ORDER=True
means a real provider order request was actually submitted.

REAL_TRADE=True
means the provider accepted/executed the order.

Valid real rejection:

EXECUTION=ON
REAL_ORDER=True
REAL_TRADE=False
PROVIDER_STATUS=REJECTED

Do NOT convert:
- local validation failure into provider rejection;
- mock response into provider evidence;
- empty balance observation into a fabricated insufficient-balance response;
- missing output into success/failure.

---

## 9. WHAT THE NEXT BUILDER SHOULD DO

### FIRST
Read the seven governance documents listed at the top.

### SECOND
Establish actual repository branch and HEAD.

### THIRD
Inspect only the immediate CP49 execution-boundary surfaces.

### FOURTH
Continue the single-order controlled probe already authorized by Management.

### FIFTH
If a real provider response is obtained:
1. preserve the exact result;
2. record CP69 evidence;
3. update the governance state;
4. move forward.

### SIXTH
Do NOT spend days searching for an already-solved architecture problem.

The architecture is already established.

The Builder's job is now to **prove the remaining real boundary, observe the output, analyze it, and advance**.

---

## 10. IF THE CHAT CONTEXT IS LOST

Do NOT ask:

"What was the architecture?"
"What were CP44/46/47/48 doing?"
"Should we redesign Risk?"
"Should we rebuild the data fabric?"
"Should we invent a laboratory mode?"
"Should we create fake capital?"
"Should we rerun every old test?"

The answer is already documented.

Ask only:

1. What is the current HEAD?
2. What is the current frontier?
3. Has the single authorized real provider probe produced actual evidence?
4. If yes, what exactly did the provider return?
5. If not, what exact boundary blocked it?
6. What is the smallest next action that proves that boundary?

Then continue.

---

## 11. HARD SAFETY / GOVERNANCE RULES

Never:
- reset;
- rebase;
- force-push;
- clean/delete unknown local artifacts;
- modify the production DB;
- fabricate data;
- backfill/interpolate/fill/pad/blend;
- synthesize decision identity;
- synthesize capital;
- invent provider outcomes;
- automatically retry a failed real runtime;
- reopen closed checkpoints without regression evidence;
- redesign Core because of provider-specific behavior.

When repository state and chat memory disagree, repository evidence wins until Management resolves the discrepancy.

---

## 12. MANAGEMENT PRINCIPLE

**BUILD → VERIFY → RECORD → ADVANCE**

The repository must be self-explanatory enough that a new Builder can continue the project immediately after context loss.

The Builder is NOT expected to rediscover the project.

The Builder is expected to **continue it**.

---

## 13. CURRENT HANDOFF SNAPSHOT

At the time this continuation contract was created:

- CP49 is the active execution-boundary work.
- The full production architecture is already established.
- Authenticated Toobit account read works.
- Empty account balances are compatible with the zero-capital operating model.
- Mock -1021 diagnostics are not real provider evidence.
- Management has authorized one controlled real provider submission.
- The next meaningful action is to execute/finish that single controlled probe and capture the actual provider response.
- After that, move to CP69 observation/consumption and output analysis.
- Do not restart historical architecture investigation.

**THIS IS A FORWARD HANDOFF, NOT A HISTORICAL RE-AUDIT.**
