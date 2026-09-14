# ARUNDA ARCHITECTURE GUARDRAILS

## Purpose
Permanent guardrails for continued development. These rules protect the verified production path from accidental regression, redesign, or unsafe execution.

## Non-Negotiables
1. Contract-first architecture.
2. Modular, layered I/O boundaries.
3. Production state is DB-backed where the existing architecture requires persistence.
4. Read-only analysis layers do not write to production DB unless explicitly authorized as a writer.
5. Production launch boundary is explicit: 2026-08-31T00:00:00+00:00.
6. Pre-launch, test, legacy, and backup artifacts are not production truth.
7. REAL DATA ONLY; never synthesize, interpolate, forward-fill, back-fill, pad, fabricate cardinality, or blend market-provider observations.
8. One candle must have one source with provenance.
9. Fail closed on missing, ambiguous, invalid, or unauthorized inputs.
10. Order Intent and Execution remain independently gated.
11. No real order, trade, withdrawal, or exchange write without explicit authorization.
12. No strategy, threshold, signal, fusion, score, decision, risk, or closed-layer redesign while solving downstream infrastructure unless regression evidence requires it.

## Provider Rule
Market data:
- Canonical: KuCoin
- Failover: Bitget
- Never blend sources.

Private account capability:
- Capability owner: ToobitTradingAdapter
- Account/balance access is read-only in the current safety state.

## Capital Rule
Static configuration values are not exchange balance.
Actual account balance must come only from an authorized read of the real account capability.
Capital transfer is forbidden until the complete technical path is declared ready for capital.

## Current Safety Flags
ORDER_INTENT=OFF
EXECUTION=OFF
REAL_ORDER=FALSE
REAL_TRADE=FALSE
DB_WRITES=0

## Development Discipline
- Inspect current production source before patching.
- Prefer GitHub as durable review/state storage for long diagnostics and state records.
- Keep secrets out of GitHub permanently.
- Do not use backup files as production source of truth.
- Do not run a second runtime merely to compensate for an avoidable diagnostic mistake.
- After runtime, use compact reporting and move to the next frontier instead of repeating closed audits.
