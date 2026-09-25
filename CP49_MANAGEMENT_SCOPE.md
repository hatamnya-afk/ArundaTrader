# CP49 — AUTONOMOUS REAL-MARKET DECISION + CONTROLLED FIRST EXECUTION ATTEMPT — MANAGEMENT SCOPE

**DATE:** 2026-09-25

**STATUS:** MANAGEMENT SCOPE DEFINED / IMPLEMENTATION NOT AUTHORIZED / EXECUTION OFF

## OBJECTIVE

Establish the minimum provider-neutral contract boundary required to let ArundaTrader autonomously select and validate a real-market opportunity and, only under a separate human authorization gate, reach exactly one controlled first real execution attempt.

This scope does not authorize execution.

## REQUIRED SINGLE PIPELINE

`REAL MARKET DATA → MARKET-FIRST UNIVERSE → OPPORTUNITY → SIGNAL → VALIDATION/FUSION → SCORE → DECISION → ENTRY/INVALIDATION → RISK → ALLOCATION → POSITION SIZE → TRADE GATE → TRADE READY → ORDER INTENT → PROVIDER PREFLIGHT → EXECUTION BOUNDARY`

There is one intelligence/capital path. Capital state is an observed input, never a reason to create a second pipeline.

## AUTONOMOUS DECISION CONTRACT

ArundaTrader must determine, from the real decision-time market state:

- selected asset;
- direction;
- entry;
- invalidation/stop;
- opportunity/profit assessment;
- risk state;
- capital allocation;
- position size;
- execution venue, when available;
- unique Decision ID;
- complete provenance and decision-time knowledge cutoff.

No Management/runtime script may inject a fixed asset, direction, thesis, entry, quantity, or trade selection.

## CAPITAL / QUANTITY BOUNDARY

- Observed capital remains an input.
- If capital > 0, quantity must originate from the existing validated Risk → Allocation → Position Sizing chain.
- If capital = 0, the same pipeline continues; zero capital must not stop intelligence or create a simulation path.
- The existing approved zero-capital Research Trade quantity contract may be used only under its exact configured conditions.
- Research quantity is not capital, not risk budget, and not a substitute for observed balance.
- No silent quantity invention, estimation, rounding, normalization, or mutation.

## PROVIDER PREFLIGHT

Use the existing provider adapter boundary and CP46-H verified read-only capability.

Preflight must fail closed on:

- authentication/configuration failure;
- stale or contradictory provider state;
- symbol/contract mismatch;
- balance/margin conflict;
- position/open-order conflict;
- timestamp failure;
- unresolved provider quantity/constraint state;
- any execution-safety inconsistency.

No parallel execution path may be introduced.

## FIRST-ATTEMPT LIFECYCLE

Exactly one attempt is permitted after a separate explicit Management/runtime authorization.

`Decision → Order Intent → Provider Preflight → Execution Attempt → Exchange Response → Observation`

Possible observed outcomes:

- ACCEPTED;
- REJECTED;
- BLOCKED;
- INCONCLUSIVE.

No automatic retry, loop, duplicate order, or recovery submission is permitted.

An exchange rejection such as insufficient balance is recorded as a real provider outcome. It is not relabeled as a software failure unless evidence establishes a software defect.

## OBSERVATION ENVELOPE

The first attempt must preserve, without future-information leakage:

- Decision ID;
- decision timestamp;
- knowledge cutoff;
- selected market and venue;
- decision/risk/allocation/quantity provenance;
- Order Intent identity;
- provider preflight evidence;
- execution-attempt timestamp;
- request identity and non-secret request metadata;
- exchange response/status;
- latency;
- rejection/error code where supplied;
- post-attempt provider state where safely observable;
- final PASS/BLOCK/INCONCLUSIVE classification;
- Aroonda observation and lesson linkage.

Secrets must never be persisted or exposed.

## AROONDA AI BOUNDARY

Aroonda AI is observer, analyst, supervisor, and learner.

It may:

- analyze the complete decision and execution chain;
- separate decision-time evidence from outcome-time evidence;
- detect anomalies and contradictions;
- identify recurring failure modes;
- state uncertainty explicitly;
- produce lessons and management recommendations.

It may not silently rewrite historical decisions, market state, execution records, contracts, or governance.

## NON-TOOBIT OPPORTUNITIES

Market-first analysis remains independent of Toobit.

A valid opportunity with no executable current venue may remain analysis-only.

Any hypothetical outcome evaluation must be explicitly timestamp-safe and may not use future price, future signal, later venue availability, or post-outcome information as decision-time evidence.

## COMMAND CENTER REQUIREMENT

The existing CP48 Command Center remains a read-only projection surface.

The event chain must remain auditable:

`Market Snapshot → Opportunity → Signal → Decision → Risk → Allocation → Position Size → Trade Gate → Order Intent → Provider Preflight → Execution Attempt → Exchange Response → Aroonda Observation → Lesson`

The UI is not the source of truth and cannot authorize execution.

## ACCEPTANCE GATES

1. Autonomous decision contract is explicit and provider-neutral.
2. No manually injected symbol/direction/thesis/quantity is accepted.
3. Dynamic cardinality is preserved.
4. Capital > 0 and capital = 0 use the same intelligence pipeline.
5. Quantity provenance is explicit and immutable at this boundary.
6. Provider preflight uses the existing Toobit adapter boundary.
7. One-attempt lifecycle is explicit and fail-closed.
8. Observation Envelope preserves decision-time and outcome-time separation.
9. Command Center identity/provenance remains auditable.
10. Aroonda observation cannot mutate history.
11. Focused tests and compile/static verification pass.
12. No runtime execution is performed during contract implementation verification.
13. A separate human authorization is required before any live execution attempt.

## STRICT OUT OF SCOPE

- enabling `EXECUTION_ENABLED`;
- enabling `ORDER_SUBMISSION_ENABLED`;
- enabling `EXCHANGE_WRITE_ENABLED`;
- creating or submitting a real order during implementation verification;
- automatic retry/loop;
- capital deployment;
- production DB writes unless separately authorized by an applicable contract;
- modification of `arunda_pipeline.py` unless explicitly authorized;
- synthetic/fill/backfill/interpolation/padding/blending;
- forced market, direction, thesis, entry, or quantity;
- rebuilding closed CP46-A1..H, CP47, or CP48;
- new UI work beyond the existing CP48 projection boundary.

## IMPLEMENTATION ORDER

1. Implement/verify the minimum autonomous decision boundary.
2. Implement/verify the first-attempt lifecycle and authorization gate.
3. Implement/verify the Observation Envelope.
4. Implement/verify Aroonda observation linkage.
5. Add focused tests.
6. Compile/static verify.
7. Synchronize the four governance documents.
8. Stop and obtain separate explicit runtime authorization.
9. Only then may a single first real execution attempt be considered.

## SAFETY BASELINE

`EXECUTION_ENABLED = FALSE`

`ORDER_SUBMISSION_ENABLED = FALSE`

`EXCHANGE_WRITE_ENABLED = FALSE`

`DATABASE_WRITE_ENABLED = FALSE`

## MANAGEMENT DETERMINATION

This file is a scoped CP49 management artifact. It does not itself authorize implementation, runtime execution, order submission, exchange writes, or capital deployment.

The canonical project frontier remains:

**AUTONOMOUS REAL-MARKET DECISION + CONTROLLED FIRST REAL EXECUTION ATTEMPT + OBSERVATION REQUIREMENTS**

# END CP49 MANAGEMENT SCOPE
