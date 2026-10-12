# Decision Market Follow-Through v0.1 — Static Contract

## Purpose
Measure how real market prices behaved after an authoritative decision, independently of order submission, provider acceptance, fill, or trade PnL.

## Inputs
- Persisted, authoritative `decision_id`, asset, LONG/SHORT direction, decision timestamp (Unix milliseconds), decision reference price, and one source identifier.
- Actual OHLC candles for the same asset and same source, with candle-close timestamps strictly after the decision and an observed candle ending exactly at the requested horizon.
- The horizon is supplied by the caller; this contract does not invent a universal horizon.

## Outputs
- Directional terminal price return.
- Maximum favorable excursion (MFE).
- Maximum adverse excursion (MAE).
- Horizon and source provenance, observation count, completeness status.

## Hard rules
- This is **market follow-through / decision-quality evidence**, never trade PnL or a claim of fill.
- No fill, execution, acceptance, or profit is inferred.
- Pre-decision candles and candles whose open time overlaps the decision timestamp do not contribute to metrics; overlapping candles are excluded to prevent pre-decision highs/lows leaking into the result.
- Missing exact horizon endpoint returns `INCOMPLETE`; no extrapolation or forward-fill.
- Asset/source mismatch, duplicate timestamps, invalid OHLC, non-finite/non-positive prices, missing identity, or invalid horizon fail closed.
- No synthetic/backfilled/interpolated prices, network, database, or runtime wiring in this module.
- One source per evaluation; no blending.
- This module is a pure calculation boundary and does not persist or feed calibration by itself.

## Acceptance boundary
Eleven focused offline tests cover LONG/SHORT calculations, pre-decision and overlapping-candle exclusion, incomplete horizon, source/asset mismatch, invalid OHLC, duplicate timestamps, invalid candle times, and invalid horizon. Passing unit tests would verify the calculation contract only—not production data availability, persistence, runtime wiring, or calibration quality.
