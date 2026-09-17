# ARUNDA TRADER — MANAGEMENT ROADMAP

## AUTHORITY
This document is the authoritative management route for project advancement. The roadmap is the only path.

## FINAL OBJECTIVE
Complete and verify ArundaTrader as a **profit-seeking, intelligent, exchange-agnostic real-market decision system** before binding any exchange.

## CORE ARCHITECTURAL PRINCIPLE
The system must not be designed around Toobit, Binance, or any other exchange. Exchange adapters are downstream consumers of an already-complete exchange-agnostic Order Intent / Boundary contract.

Until `EXCHANGE-AGNOSTIC BOUNDARY`, the core must remain provider-neutral.

## PROFIT-SEEKING OBJECTIVE
The primary optimization objective is **maximum validated profit opportunity capture**, not minimum risk and not maximum risk.

Risk management exists to make allocation intelligent and evidence-based, not to impose an arbitrary universal profit ceiling.

The system must distinguish:
- Opportunity / profit assessment — how attractive the opportunity is.
- Risk / invalidation — where the thesis is invalid and what constraints apply.
- Capital allocation — how much capital the validated opportunity deserves.
- Position sizing — how allocation becomes quantity using Entry and Stop/Invalidation.
- Trade Gate — whether the complete decision is internally valid and executable in principle.

Capital amount is a scale/input boundary, not the intelligence of the system. The same opportunity logic must work across different valid capital amounts.

Allocation is an intelligent output. It is not architecturally fixed to 20%, 50%, 0.5%, or any other universal ceiling. Depending on validated opportunity and constraints, allocation may be 0% through 100%.

100% allocation is neither inherently required nor forbidden; it is simply one possible output of the intelligence when validated by the complete opportunity, invalidation, liquidity, exposure, and portfolio state.

## MANDATORY LIFECYCLE
### PHASE A — EXCHANGE-AGNOSTIC PROJECT COMPLETION

```text
REAL MARKET DATA
    ↓
DYNAMIC UNIVERSE
    ↓
OPPORTUNITY
    ↓
SIGNAL
    ↓
SCORE
    ↓
DECISION
    ↓
PROFIT / OPPORTUNITY INTELLIGENCE
    ↓
ENTRY + INVALIDATION / STOP
    ↓
SMART RISK
    ↓
CAPITAL ALLOCATION
    ↓
POSITION SIZING
    ↓
PORTFOLIO / TRADE GATE
    ↓
TRADE READY
    ↓
ORDER INTENT
    ↓
PRE-EXECUTION
    ↓
EXCHANGE-AGNOSTIC BOUNDARY
```

Rules:
- No exchange-specific architecture becomes Core.
- Exchange adapters remain replaceable environment boundaries.
- Dynamic runtime cardinality is preserved: `ELIGIBLE[N] → RISK[N] → TRADE_GATE[N]`.
- `15` is legacy test-universe history, not a production cardinality contract.
- `6` is only a runtime observation from one run, not a target or contract.
- Closed/verified checkpoints remain historical truth unless Management proves regression.
- No runtime, DB write, API write, or execution is implied merely by roadmap position.

Current position:
- CP41 = CLOSED / VERIFIED / PASS
- CP43 = CLOSED / VERIFIED / PASS
- CP44 = CURRENT FRONTIER / MANAGEMENT-AUTHORIZED / IMPLEMENTATION VERIFIED / REAL-MARKET CONTROLLED TEST PENDING / NOT CLOSED

### PHASE B — EXCHANGE BINDING
May begin only after Phase A completion is explicitly closed and recorded in all four governance documents.

### PHASE C — FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST
After Phase B authorization, integrate the selected exchange through the exchange adapter boundary and perform final controlled testing. No real order is implied.

### PHASE D — REAL TRADING
Requires Phase A/B/C closure, satisfied execution/risk/constraint gates, and explicit Management authorization.

## CP44 MANAGEMENT STATE
The authorized CP44 implementation has now been verified on `sync/local-project-20260917` at `b9c029ed7ef1da9a7d7fb53617769a35b8280246`.

Verified evidence:
- five CP44 Smart Risk/Entry surfaces compile successfully with Python 3.13.15;
- existing Smart Risk test exits `0`;
- corrected Dynamic Smart Risk boundary test exits `0` with `CP44_DYNAMIC_BOUNDARY_PASS`;
- explicit `BTC/USDT` LONG entry/invalidation geometry is accepted;
- entry `100000.0`, invalidation `99000.0`, stop distance `1000.0`;
- Smart Risk result `APPROVED`;
- dynamic snapshot cardinality `1 → 1`;
- no order, execution, API write, or production DB write occurred.

The earlier controlled real-market runtime observed **6 assets reaching ELIGIBLE**. That remains runtime evidence only and is not a cardinality target or closure proof.

## CP44 FORWARD CHAIN
```text
ELIGIBLE[N]
   ↓
ENTRY + INVALIDATION / STOP
   ↓
PROFIT / OPPORTUNITY ASSESSMENT
   ↓
SMART RISK
   ↓
CAPITAL ALLOCATION
   ↓
POSITION SIZE
   ↓
TRADE GATE
   ↓
TRADE READY
   ↓
ORDER INTENT
```

Do not rebuild or redesign Opportunity / Signal / Score / Fusion / Decision merely to reproduce the observed ELIGIBLE state.

## CP44 CURRENT BLOCKER
The implementation boundary is verified, but production-compatible real Entry + Invalidation/Stop is not yet proven as the input to Smart Risk authority during the authorized real-market runtime.

The active route must also establish opportunity-driven capital allocation semantics and prove dynamic `ELIGIBLE[N] → RISK[N] → TRADE_GATE[N]` without legacy fixed-15 assumptions.

The legacy `market_entry_stop_adapter.py` fixed-15 snapshot path must not become the production route.

## SAFETY BOUNDARY
- EXECUTION AUTHORIZATION = FALSE
- ORDER WRITE = FORBIDDEN
- DATABASE WRITE = FORBIDDEN
- WITHDRAW = FORBIDDEN
- Exchange writes = FORBIDDEN
- Signature work = FORBIDDEN
- No test capital.
- `arunda_pipeline.py` remains protected.

## CHECKPOINT ADVANCEMENT GATE
At the end of EVERY checkpoint update:
1. PROJECT_STATE.md
2. CURRENT_FRONTIER.md
3. CHECKPOINTS.md
4. MANAGEMENT_ROADMAP.md

Record BUILT, VERIFIED, CLOSED/BLOCKED/NOT VERIFIED, evidence, blocker, CURRENT FRONTIER, NEXT ACTION, and authorized branch/file scope.

A checkpoint is not governance-complete until the four documents are synchronized and internally consistent.

## BRANCH GOVERNANCE
No branch for personal workflow, experimentation, convenience, speculative work, or parallel truth. Historical branches may be preserved for provenance. Active branches require explicit Management authorization and recorded purpose/source/target/relationship.

## FILE GOVERNANCE
No file outside authorized checkpoint scope becomes Canonical project truth. Temporary, generated, backup, quarantine, forensic, review, and unrelated artifacts require classification before promotion.

## REPOSITORY ORGANIZATION
Repository organization is classification-first and behavior-neutral.
- Governance/control documents remain at repository root.
- Operational source paths are preserved until dependency/path analysis authorizes relocation.
- Verification, evidence/forensic, and historical material have explicit navigation locations.
- `README.md` and `REPOSITORY_STRUCTURE.md` provide the repository navigation/control layer.

## CURRENT GOVERNANCE GATE
Repository consolidation is CLOSED by Management.
CP44 remains the active frontier.

## CURRENT NEXT ACTION
1. Execute the single authorized CP44 real-market controlled runtime from the established downstream ELIGIBLE boundary.
2. Verify production-compatible Entry + Invalidation/Stop, opportunity-driven allocation, quantity/exposure, Trade Gate, Trade Ready, Order Intent, and pre-execution readiness with dynamic N.
3. Preserve all execution, order, API-write, and DB-write prohibitions.
4. Synchronize all four governance documents again at CP44 completion before closure.

# END MANAGEMENT ROADMAP
