# ARUNDA ECOSYSTEM — MASTER PROJECT MAP
## Canonical cross-repository orientation — 2026-10-08

> READ THIS FIRST.
> This file exists to prevent project-path reconstruction from chat memory.
> It is the permanent map of the relationship between ArundaTrader, AroondaAI,
> their separate technical roadmaps, the verified historical work, and the
> broader management/product vision.

## 1. TWO REPOSITORIES — ONE ECOSYSTEM

### ArundaTrader
Repository: hatamnya-afk/ArundaTrader

ArundaTrader is the real-market trading environment:
REAL INFORMATION → DATA FABRIC → DYNAMIC UNIVERSE → OPPORTUNITY → SIGNAL →
VALIDATION → FUSION → SCORE → DECISION / DECISION BIRTH → SMART RISK →
TRADE GATE → TRADE READY → ORDER INTENT → PRE-EXECUTION → EXCHANGE-AGNOSTIC
BOUNDARY → PROJECT COMPLETION → TOOBIT ADAPTER → LIVE ACCOUNT/CONSTRAINT READ →
PROVIDER ORDER PREPARATION → PROVIDER-NEUTRAL ORDER ATTEMPT → EXPLICIT
EXECUTION AUTHORIZATION → FIRST REAL ORDER → FIRST REAL FILL → REAL OUTCOME →
OBSERVATION → CALIBRATION.

### AroondaAI
Repository: hatamnya-afk/AroondaAI

AroondaAI is an independent local intelligence system.
Its canonical roadmap is BIRTH → GROWTH → INDEPENDENCE.
ArundaTrader is explicitly the FIRST ENVIRONMENT, not part of Aroonda Core.

Aroonda's environment loop is:
OBSERVE → UNDERSTAND → ANALYZE → PROPOSE → CONTROLLED ACTION →
OBSERVE RESULT → EVALUATE → REMEMBER.

## 2. NEVER CONFUSE THE THREE ROADMAP LEVELS

### A. ArundaTrader technical roadmap
This is the concrete path to first real order, fill, outcome, observation,
and calibration. It is not the complete Aroonda/product vision.

### B. AroondaAI master roadmap
Canonical file: AroondaAI/ROADMAP.md

The verified Trader-facing Aroonda sequence includes:
CP64 Environment Intelligence Bridge
CP65 ArundaTrader Classroom / Control Center
CP66 Command / Dialogue Environment
CP67 Trader Improvement Loop
CP68 Experience & Cross-Environment Transfer
CP69 Canonical Runtime Observation Bridge
CP70 Output Supervision / Self-Model
CP71 Capability Gap → Sandbox → Build
CP72 Controlled Self-Improvement Loop

These are Aroonda checkpoints, not ArundaTrader checkpoints.

### C. Broader management/product vision
This is intentionally separate until formally promoted into a canonical roadmap:

REAL FEEDBACK → ANALYSIS → IMPROVEMENT → UI / EVIDENCE →
AROONDA INTELLIGENCE → PREDICTION → SIGNAL / RECOMMENDATION /
SOFTWARE PRODUCT → IF PROVEN: BLOCKCHAIN.

Important: the prediction/customer-product/blockchain stages are currently
management vision, not claims of existing GitHub checkpoint implementation.

## 3. ARUNDATRADER — HISTORICAL WORK THAT MUST NOT BE REDONE

The following are already closed/verified and must not be reconstructed or
reimplemented without direct, provable regression:

Data Fabric; Dynamic Universe; Real Market; Dynamic Signal; Opportunity;
Validation/Fusion/Score/Decision; Decision Birth / canonical decision identity;
Smart Risk; Trade Gate; Trade Lifecycle; Exit Evidence; PortfolioRisk;
Account/Balance Producer; CP37-J; CP37-KA; controlled release test v0.1;
CP38-A through CP38-N as recorded in governance; CP39; CP40; CP41; CP43;
Project Completion; Toobit Exchange Binding; Dynamic Execution Asset Universe;
Exchange-Agnostic Adapter Contract; Exchange-Neutral Order Preparation;
Provider-Neutral Order Attempt Boundary; Final Execution-Attempt Contract.

DO NOT REDO CLOSED WORK. Reopening requires direct, provable regression.

## 4. IMPORTANT RESOLVED ARCHITECTURAL ISSUE

The historical Toobit exposure_allowed investigation is not a permanent
Core architecture blocker.

READY ≠ BALANCE > 0
BALANCE > 0 ≠ PROVIDER ACCEPTANCE
PROVIDER ACCEPTANCE ≠ FILL

Provider acceptance/rejection is environmental evidence.

Do not manufacture exposure_allowed.
Do not infer permission from balance, leverage, margin mode, empty positions,
risk limits, API-key permission, or hypothetical acceptance.

## 5. CURRENT ARUNDATRADER SAFETY AND FRONTIER

EXECUTION AUTHORIZATION = FALSE.

Therefore:
- no live order;
- no provider write;
- no withdrawal;
- no DB mutation;
- no automatic execution activation;
- no Toobit wiring into arunda_pipeline.py.

Latest known operational branch:
operational-main-20261007

Latest known execution-attempt contract:
448806f

Current frontier:
MANAGEMENT REVIEW / EXPLICIT EXECUTION-ATTEMPT GATE.

The next real-order attempt requires separate explicit management authorization.
A verified contract is never an execution authorization.

## 6. ARCHITECTURAL INVARIANTS

ArundaTrader:
CORE → EXCHANGE-AGNOSTIC EXECUTION BOUNDARY → REPLACEABLE EXCHANGE ADAPTER → TOOBIT

Toobit is the first adapter, not the architecture.
Market providers such as KuCoin / Bybit / Gate are information providers.
Provider-specific symbols and payload semantics do not belong in Core.

AroondaAI:
AROONDA CORE → CAPABILITY LAYER → ENVIRONMENT INTERFACE →
ENVIRONMENT ADAPTER → EXTERNAL ENVIRONMENT

Trader-specific behavior stays outside Aroonda Core.

## 7. WHAT MUST NEVER HAPPEN AGAIN

A future Builder/Manager must never:
1. Treat the Trader technical roadmap as the entire project roadmap.
2. Treat Aroonda roadmap checkpoints as Trader implementation checkpoints.
3. Reconstruct closed work from chat memory.
4. Reopen CLOSED/VERIFIED work without proven regression.
5. Treat a historical blocker as the current blocker without checking latest state.
6. Turn a provider capability gap into a Core architecture requirement.
7. Bind Core directly to Toobit.
8. Assume a missing artifact must be rebuilt.
9. Use another workspace as the canonical project.
10. Infer authorization from readiness or provider metadata.
11. Activate execution because a contract test passes.
12. Promote future product vision into Git-backed implementation status without
explicit management decision.

## 8. MANDATORY BUILDER ENTRY

ArundaTrader:
1. Read this file.
2. Read CURRENT_BUILDER_HANDOFF.md.
3. Read PROJECT_STATE.md.
4. Read CURRENT_FRONTIER.md.
5. Read CHECKPOINTS.md.
6. Read MANAGEMENT_ROADMAP.md.
7. Inspect Git branch, HEAD, and status.
8. Identify the single current frontier.
9. Work only inside that scope.
10. Stop at management gates.

AroondaAI:
1. Read this file.
2. Read ROADMAP.md.
3. Read PROJECT_STATE.md.
4. Read ARCHITECTURE.md.
5. Read CURRENT_FRONTIER.md.
6. Read CHECKPOINTS.md.
7. Inspect Git state.
8. Identify the single current frontier.
9. Work only inside that scope.
10. Stop at management gates.

If state is ambiguous:
STOP → REPORT STATE AMBIGUITY → DO NOT GUESS → DO NOT MODIFY.

## 9. SOURCE-OF-TRUTH RULE

This file is authoritative for CROSS-REPOSITORY TOPOLOGY and PROJECT DIRECTION.

It does not replace repository-local checkpoint state.

ArundaTrader implementation truth:
repository governance documents → verified code/contracts → Git history → chat.

AroondaAI implementation truth:
PROJECT_STATE.md / CURRENT_FRONTIER.md / CHECKPOINTS.md / ROADMAP.md /
ARCHITECTURE.md.

No future Builder should need chat history to discover:
- where ArundaTrader ends;
- where AroondaAI begins;
- why they are connected;
- which roadmap is technical;
- which roadmap is intelligence growth;
- which stages are only future management vision.

## 10. CHANGE CONTROL

Change this map only when:
- cross-repository architecture changes;
- canonical roadmap relationship changes;
- a major management frontier changes;
- future vision is explicitly promoted into a canonical roadmap.

Every change must record what changed, why, affected repository/roadmap,
whether any closed checkpoint was reopened, and the new current frontier.

## FINAL MANAGEMENT VERDICT

The project is ONE ECOSYSTEM, not one repository and not one roadmap.

ARUNDATRADER = REAL-MARKET TRADING ENVIRONMENT.
AROONDAAI = INDEPENDENT INTELLIGENCE SYSTEM.
ARUNDATRADER = FIRST ENVIRONMENT OF AROONDAAI.
TRADER TECHNICAL ROADMAP ≠ AROONDA MASTER ROADMAP ≠ FUTURE PRODUCT VISION.

This file is the permanent GitHub entry point intended to prevent future
state reconstruction, duplicate work, roadmap conflation, and accidental
reopening of closed stages.

# END MASTER PROJECT MAP
