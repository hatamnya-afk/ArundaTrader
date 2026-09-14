# ARUNDA MASTER STATE — 2026-09-14

## Operating Rule
This file is a durable project-state reference. It records current truth and must not be confused with old checkpoints, backups, or experimental artifacts.

## Core Pipeline
REAL MARKET DATA → DYNAMIC REAL UNIVERSE → MARKET ANALYSIS → NEWS + SOCIAL INTELLIGENCE → SIGNAL → VALIDATION → FUSION → SCORE → DECISION → RISK → TRADE GATE → REAL ELIGIBLE OPPORTUNITY → ORDER INTENT → AUTHORIZED EXECUTION → REAL TRADE → OUTCOME → LIVE OBSERVATION → CALIBRATION

## Current Frontier
Risk Budget → Stop Loss → Position Sizing → Exposure → Order Intent

## Current Opportunity
A real eligible opportunity was previously established:
- Asset: FIL/USDT
- Direction: LONG
- Trade gate: TRADE_READY
- Confidence: 0.5866659583936658
- Score: 55.05453166480238
- Market data points: 149

This does not authorize order creation or execution.

## Safety State
- ORDER_INTENT = OFF
- EXECUTION = OFF
- REAL_ORDER = FALSE
- REAL_TRADE = FALSE
- DB_WRITES = 0
- Fail closed = TRUE

## Capital / Account Boundary
- Toobit is the verified private-account capability owner.
- CP25-N verified the newly created API key for read-only account authentication.
- Real account balance was successfully read and is currently zero; this is an account state, not an API failure.
- No capital should be transferred until the Builder explicitly declares the complete technical path ready for capital.
- Static capital_config.py values are configuration defaults only and must never be treated as real exchange balance.

## Verified Capital Components
- capital_contract.py: BUILT
- capital_config.py: BUILT
- risk_budget_engine.py: BUILT
- position_sizing_engine.py: BUILT, dependency review pending

## Known Dependency Gap
The current GitHub review snapshot did not contain verified production sources for:
- position_sizing_contract.py
- stop_loss_engine.py

Do not reconstruct these from backup files without explicit source validation.

## Production Data Rules
- REAL DATA ONLY.
- No synthetic data.
- No interpolation, forward-fill, back-fill, padding, blending, or fabricated cardinality.
- One candle = one source.
- Provenance is mandatory.
- Production launch boundary: 2026-08-31T00:00:00+00:00.
- Legacy/pre-launch market_technical data must not influence production signal, analysis, training, calibration, accuracy, or prediction.
- KuCoin is canonical market-data provider; Bitget is failover. Never blend providers.
- Dynamic universe; no fixed production 15-asset dependency.

## Change Discipline
- Do not reopen CLOSED / VERIFIED layers without regression evidence.
- Do not patch before the relevant contract and dependency sources are understood.
- Do not patch backups as production.
- No unauthorized runtime.
- No exchange writes or order submission.
- No production DB writes.

## Next Action
Verify the production sources and contracts for Position Sizing dependencies, then verify the pipeline connection. Only after contract consistency is proven should a narrowly scoped patch be considered.
