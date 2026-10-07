# CP47 — MAIN SELECTIVE INTEGRATION MANIFEST

Status: SELECTIVE_DEPENDENCY_CLOSURE_STAGED
Base: main
Source: cp46-f-futures-readiness-20261006 @ 26b73995cc0f51946af13cfe1574dc28bddf2173
Branch: cp47-main-selective-integration-20261007

## Current frontier

Restore the authoritative Dynamic Production dependency closure on main without changing
strategy semantics, risk policy, gate semantics, quantity semantics, database governance,
or execution authorization.

## Closure staged

The branch now carries the provider-neutral Dynamic Production stack required by the
existing main pipeline, including:

- Dynamic universe/opportunity/market-data/signal/validation/news/social/fusion/score/decision boundaries
- Signal, scoring, risk-budget, risk, position-sizing and Trade Gate engines/contracts
- Market structure/regime/snapshot/data, indicator, feature and market-analysis dependencies
- CP44 real portfolio/balance/smart-risk boundaries
- CP49 authoritative Decision Birth issuer, source boundary, producer and persistence contract
- CP46 provider preflight/translation/handoff and Toobit read-only boundaries
- MCP-01 observation/evidence/management projection dependencies
- execution-contract dependencies needed for fail-closed import/runtime integrity

## Critical identity correction

Decision identity is NOT issued by Dynamic Decision.

Authoritative flow remains:

REAL MARKET → semantic Decision evaluation → CP49 Authoritative Decision Birth issuer
→ Birth persistence/uniqueness boundary → canonical decision_id → Dynamic Decision consumer
→ Risk → Trade Gate → Order Intent → Canonical Order Request → Execution boundary.

The existing real-market snapshot identity is derived from the actual closed-candle timestamp
and provider source in the CP49 Birth producer. No synthetic snapshot_id is introduced.

## Safety invariants

- Execution remains OFF.
- No real order submission.
- No execution activation.
- No DB repair/change.
- No synthetic/fill/backfill/interpolation/forward-fill/padding/blending.
- No strategy/risk/gate redesign.
- No CLOSED/VERIFIED stage reopened.
- No wholesale CP46 merge.
- No reset/rebase/clean/delete/force operations.

## Verification gate

Before merge:
1. Focused CP47 Decision Birth and provider-boundary tests.
2. Import/static closure verification.
3. One controlled real-market runtime with execution OFF.
4. Confirm CP49 Birth persistence, cardinality, identity propagation and fail-closed execution.
5. PR remains Draft until all gates pass.

## Management verdict

The branch is the selective integration staging line.
It is NOT merge-ready until the closure is executable and verified end-to-end.
