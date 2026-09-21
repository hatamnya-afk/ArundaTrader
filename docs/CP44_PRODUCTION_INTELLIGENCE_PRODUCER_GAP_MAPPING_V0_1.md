# CP44 — Production Intelligence Producer Gap Mapping v0.1

## Status

**BOUND / VERIFIED — PRODUCER GAP CONFIRMED**

This document records the bounded source-to-contract mapping for the CP44 Production Intelligence frontier. It does not activate runtime, allocation, Smart Risk, execution, or a production formula.

## Repository / Branch

- Repository: `hatamnya-afk/ArundaTrader`
- Branch: `sync/local-project-20260917`
- Intelligence contracts baseline: `3a42768daee644a141584167ce9f84356f3021fe`

## 1. Authoritative live source chain

```
Canonical Fabric
    ↓
Rolling Context
    ↓
Feature / Structure
    ↓
Production Signal Engine Binding
    ↓
Signal Engine
    ↓
Signal Validator
    ↓
Fusion
```

The live Market Signal path is provider-bound through the production binding and uses real Fabric observations with the existing continuity contract. The Signal Contract explicitly permits `confidence=None` and `timestamp=None`; the Signal layer does not calculate confidence or generate timestamps.

## 2. Predictive Evidence mapping

### Available native inputs

- Signal direction: `LONG` / `SHORT` / `NONE`
- Signal state: `ACTIVE` / `NEUTRAL`
- Structural reason: `STRUCTURAL_DIRECTION`
- Market/Fusion directional outputs exist downstream.

### Rejected mappings

- Signal `confidence` → Predictive Evidence: **REJECTED** because current Signal confidence is nullable and is not a predictive evidence measure.
- Fusion `confidence` → Predictive Evidence: **REJECTED** because Fusion confidence is a composite confidence metric, not a separately defined predictive-evidence observation.
- Fusion `fused_score` → Predictive Evidence: **REJECTED** because fused score is an output of Fusion and must not become a circular Market/Fusion input or be reinterpreted as probability.
- Opportunity score → Predictive Evidence: **REJECTED** without an explicit production contract binding; raw opportunity score is not automatically predictive evidence.

### Required producer

A provider-neutral **Predictive Evidence Producer** must consume currently observable, point-in-time inputs and explicitly construct `PredictiveEvidence` without converting score/confidence into probability.

No such production producer is currently proven on the branch.

## 3. Reliability mapping

### Available native inputs

Fusion exposes:

- `agreement`
- `available_weight`
- `missing_arm_penalty`
- `data_quality`
- `provenance_valid`
- arm-level confidence values for News/Social.

Rolling Context exposes real point count and context class.

### Rejected mappings

- Fusion `confidence` → Reliability: **REJECTED** as an implicit alias.
- `available_weight` → Reliability: **REJECTED** as an unapproved formula.
- `missing_arm_penalty` → Reliability: **REJECTED** as an unapproved formula.
- `agreement` → Reliability: **REJECTED** as an unapproved formula.
- Any combination of these fields → Reliability: **REJECTED** until a producer contract defines semantics and validation.

A Reliability Producer may use current observable provenance/quality/continuity facts, but its transformation must be contract-defined and must not use future outcomes, labels, realized returns, PnL, or post-outcome information.

No production Reliability Producer is currently proven on the branch.

## 4. Uncertainty mapping

### Available native inputs

Potential current-time observables include:

- missing-arm state,
- data quality,
- provenance validity,
- continuity/context availability,
- source completeness.

### Rejected mappings

- `1 - confidence` → Uncertainty: **REJECTED**
- `missing_arm_penalty` → Uncertainty: **REJECTED**
- `1 - agreement` → Uncertainty: **REJECTED**
- any arbitrary weighted combination → **REJECTED**

These would constitute an implicit production formula.

A provider-neutral Uncertainty Producer must therefore be separately specified and validated using only point-in-time observable information.

No production Uncertainty Producer is currently proven on the branch.

## 5. Calibration boundary

Calibration is not a live producer substitute.

Historical/OOS outcome labels may be used for research, calibration, and evaluation only. They must never enter the live producer path as:

- `outcome`
- `future_outcome`
- `label`
- `future_label`
- `realized_return`
- `pnl`
- `exit_price`
- `post_outcome`
- `calibrated_probability`

The CP44 production intelligence boundary already forbids these live fields.

## 6. Required next implementation boundary

The minimum architecture required to close this gap is:

```
LIVE SIGNAL / FUSION
        ↓
Point-in-Time Predictive Evidence Producer
        ↓
Point-in-Time Reliability Producer
        ↓
Point-in-Time Uncertainty Producer
        ↓
Existing Relative Conviction Candidate
        ↓
Existing Relative Allocation Boundary
        ↓
LOCKED until formula freeze + Management approval
```

The three producers must expose explicit provenance, observation timestamp, validation state, and source identity.

## 7. Non-negotiable controls

- No synthetic evidence.
- No placeholder numeric reliability.
- No placeholder numeric uncertainty.
- No conversion of Score into Probability.
- No conversion of raw Confidence into calibrated Reliability.
- No outcome leakage.
- No future fields.
- No modification to Smart Risk.
- No allocation activation.
- No runtime.
- No production DB write.
- No execution.
- Production allocation formula remains **UNFROZEN**.

## 8. Frontier verdict

**Producer Gap = CONFIRMED.**

The existing architecture supplies sufficient point-in-time structural, provenance, continuity, and Fusion observables to define the next provider-neutral producer contracts, but it does not yet contain three validated production producers.

Therefore CP44 remains:

**BLOCKED / NOT VERIFIED / NOT CLOSED**

and the next authorized work unit is the explicit contract design/implementation of the three producer boundaries, followed by compile-only and contract-level dry verification.