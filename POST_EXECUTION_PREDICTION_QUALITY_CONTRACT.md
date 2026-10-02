# ARUNDA TRADER — POST-EXECUTION PREDICTION QUALITY CONTRACT

## STATUS

**MANAGEMENT DIRECTIVE / CANONICAL FUTURE WORK / NOT YET IMPLEMENTED**

This document defines the mandatory engineering target immediately after the first successful real Toobit execution path is proven. It exists so a future Builder can continue from GitHub without reconstructing intent from chat history.

---

## 1. PRIMARY OBJECTIVE

The primary long-term value of ArundaTrader is **validated prediction quality and signal intelligence**.

Exchange, account capital, and individual order success are downstream environment concerns.

The system must measure from real market evidence:

~~~
TRADER PREDICTION → REAL MARKET BEHAVIOR → OUTCOME → ERROR ANALYSIS → PREDICTION QUALITY
~~~

The objective is to determine:
- how often Trader predictions are correct;
- how often they are wrong;
- under which market conditions they succeed or fail;
- whether confidence is calibrated against reality;
- which intelligence inputs correlate with successful predictions;
- which recurring failure patterns should drive future controlled improvement.

Do not optimize merely for number of executed orders or immediate P&L.

---

## 2. MANDATORY PER-SELECTION RECORD

Every analytical selection reaching the Trade Ready / Canonical Order Request boundary must remain traceable, including selections that later fail at the provider boundary.

Minimum identity chain:

~~~
decision_id → intent_id → canonical_order_request → execution/provider observation → market outcome
~~~

The prediction/outcome record must preserve, at minimum:
- asset / market identity;
- provider-independent asset identity;
- venue/provider when execution is attempted;
- decision_id;
- intent_id;
- snapshot_id;
- prediction timestamp;
- prediction direction;
- prediction confidence;
- prediction score;
- entry/reference price used by the prediction;
- invalidation/stop information when applicable;
- Market / News / Social evidence references or feature provenance when already available;
- selected evaluation horizon;
- execution attempt state;
- provider response state;
- final outcome classification;
- realized market behavior at the evaluation horizon;
- outcome timestamp;
- reason for invalid/non-comparable outcome, when applicable.

No future market information may be inserted into the prediction record itself.

---

## 3. OUTCOME TAXONOMY

A failed provider operation is **not automatically a prediction failure**.

Every selection must be classified into one top-level evidence class:

### A. PREDICTION EVALUABLE
A real market outcome exists for the defined horizon and can be compared against the prediction.

Subclasses:
- PREDICTION_CORRECT
- PREDICTION_WRONG

### B. PROVIDER / EXECUTION FAILURE
The Trader produced a valid prediction, but the environment prevented or altered execution.

Examples:
- provider symbol unavailable;
- provider rejected request;
- authentication/signature failure;
- network/transport failure;
- provider-side constraint rejection;
- account constraint rejection.

These are execution/environment evidence and must not be counted as Trader prediction errors.

### C. OBSERVATION FAILURE
The system cannot establish a trustworthy outcome observation.

Examples:
- missing required real market observation;
- incomplete observation window;
- corrupted/untrusted evidence;
- unresolved provenance.

These must be excluded from prediction accuracy until resolved by authoritative evidence.

### D. INVALID / NON-COMPARABLE
The original prediction or evaluation contract is structurally invalid or the outcome cannot legitimately be compared.

These must be excluded from accuracy denominators and separately counted.

No silent dropping is permitted.

---

## 4. PREDICTION QUALITY

The first primary metric is **real-world prediction accuracy** over an explicitly defined eligible population.

~~~
ACCURACY = CORRECT_EVALUABLE_PREDICTIONS / ALL_EVALUABLE_PREDICTIONS
~~~

The denominator must contain both correct and wrong predictions.

Provider failures, observation failures, and non-comparable records must not silently enter or leave the denominator.

No single accuracy percentage may be reported without:
- evaluation population size;
- correct count;
- wrong count;
- excluded/non-comparable count;
- provider/execution failure count;
- observation failure count;
- evaluation horizon;
- time period;
- asset population.

---

## 5. DIRECTIONAL ANALYSIS

Quality must be measurable separately for:
- LONG predictions;
- SHORT predictions;
- each supported evaluation horizon;
- each meaningful market regime when the regime is already available from authoritative project data;
- individual assets when sample size is sufficient;
- aggregate universe.

Do not declare an asset or signal type superior from a tiny sample. Small samples must remain explicitly marked as insufficient evidence.

---

## 6. CONFIDENCE CALIBRATION

Trader confidence must eventually be compared with observed correctness.

Required future analysis:

~~~
PREDICTED CONFIDENCE ↔ OBSERVED SUCCESS RATE
~~~

The system must detect:
- high confidence + frequent failure;
- low confidence + frequent success;
- confidence that tracks reality;
- confidence that is systematically over- or under-estimated.

Confidence is not truth merely because Trader produced it.

---

## 7. SIGNAL / INTELLIGENCE ANALYSIS

When provenance permits, future analysis must compare outcomes against the independent intelligence inputs:

~~~
MARKET ARM
NEWS ARM
SOCIAL ARM
~~~

The purpose is not to assume causality. The purpose is to measure whether particular evidence patterns are associated with correct or incorrect predictions.

Questions:
- Which evidence combinations repeatedly accompany correct predictions?
- Which evidence combinations repeatedly accompany wrong predictions?
- Does one arm become unreliable under particular conditions?
- Are failures concentrated around volatility, liquidity, regime changes, news events, or other observable states?
- Does the same error recur across multiple assets?

No causal claim may be made from correlation alone.

---

## 8. MARKET-BEHAVIOR RECORD

The outcome record must describe what actually happened after the prediction.

At minimum, where the selected horizon permits:
- reference price;
- horizon-end price;
- realized return;
- realized direction;
- maximum favorable excursion;
- maximum adverse excursion;
- whether invalidation was reached;
- whether the predicted directional thesis remained valid;
- observation quality/provenance.

This separates directional correctness from magnitude/payoff.

A prediction can be directionally correct while producing a small or economically irrelevant move.

---

## 9. EXECUTION MUST REMAIN SEPARATE

Never collapse:
- PREDICTION QUALITY
- EXECUTION QUALITY
- PROVIDER AVAILABILITY
- ACCOUNT/CAPITAL STATE
- REALIZED P&L

Example:
Trader predicts LONG correctly, but Toobit rejects the order because the symbol is unavailable.

Result:
- Prediction = EVALUABLE/CORRECT
- Execution = PROVIDER_FAILURE

It must not become Prediction = WRONG.

Conversely, if Toobit accepts the order and the market subsequently moves materially against the defined prediction horizon, that is genuine predictive evidence.

---

## 10. NO PRE-FILTERING OF ANALYTICAL SELECTIONS

The analytical population must not be pre-filtered merely to make execution statistics look better.

The current selection set must be allowed to encounter real provider reality.

Provider rejection is useful evidence.

Preserve the distinction between:

~~~
TRADER SELECTION FAILURE
PROVIDER / ENVIRONMENT FAILURE
~~~

This principle is mandatory for early real-world evidence collection.

---

## 11. NO PREMATURE LEARNING MUTATION

Outcome analysis must initially be **observational and evidentiary**.

A future Builder must not silently change:
- Signal rules;
- Fusion rules;
- Score thresholds;
- Decision rules;
- Risk rules;
- Trade Gate rules;
- asset selection rules;
- confidence semantics;

merely because a small sample looks unfavorable.

Any future self-improvement mechanism must be separately governed, versioned, testable, and attributable to the evidence that caused the proposed change.

---

## 12. ANTI-LEAKAGE REQUIREMENT

Prediction evaluation must be immune to future-information leakage.

For every prediction:

~~~
PREDICTION_TIMESTAMP < OUTCOME_OBSERVATION_TIMESTAMP
~~~

The prediction record must contain only information available at prediction time.

Future candles, future news, future social events, future prices, or post-decision derived labels must never be fed backward into the original prediction features.

---

## 13. REQUIRED AGGREGATES

The future reporting layer must support at least:

### Global
- total predictions;
- evaluable predictions;
- correct;
- wrong;
- accuracy %;
- provider failures;
- observation failures;
- non-comparable records.

### Direction
- LONG accuracy;
- SHORT accuracy.

### Confidence
Accuracy by confidence range.

### Asset
Accuracy per asset with sample count.

### Time
Accuracy by day/week/month and rolling window.

### Regime
Accuracy by already-defined market regime.

### Intelligence provenance
Outcome distribution by available Market / News / Social evidence provenance.

### Execution
Provider acceptance/rejection/failure separately from prediction correctness.

---

## 14. STATISTICAL DISCIPLINE

No maturity claim should be based on a single successful trade or a handful of observations.

Every aggregate must expose sample size.

When sample size is too small, report:

~~~
INSUFFICIENT_EVIDENCE
~~~

rather than manufacturing certainty.

The complete observation history must remain available so metrics can be recomputed without changing historical labels.

---

## 15. FUTURE MATURITY LOOP

~~~
REAL MARKET
   ↓
MARKET + NEWS + SOCIAL
   ↓
TRADER INTELLIGENCE
   ↓
PREDICTION
   ↓
REAL MARKET OUTCOME
   ↓
LABEL
   ├── CORRECT
   ├── WRONG
   ├── PROVIDER/EXECUTION FAILURE
   ├── OBSERVATION FAILURE
   └── NON-COMPARABLE
          ↓
ERROR ANALYSIS
          ↓
PREDICTION QUALITY
          ↓
CONTROLLED IMPROVEMENT
          ↓
NEW VERSION
          ↓
NEW REAL-MARKET EVIDENCE
~~~

The target is progressively **more reliable predictive intelligence** supported by real evidence.

---

## 16. FIRST IMPLEMENTATION SCOPE FOR THE NEXT BUILDER

After the first real Toobit execution result is actually evidenced:

1. Inspect the existing CP69 observation payload and canonical decision/order identity chain.
2. Identify the smallest authoritative place to attach prediction/outcome provenance.
3. Define a provider-neutral prediction outcome contract.
4. Define immutable outcome labels and exclusion reasons.
5. Implement append-only observation/evaluation records without changing closed contracts.
6. Implement a deterministic evaluator for the selected horizon.
7. Add focused tests for:
   - correct prediction;
   - wrong prediction;
   - provider rejection;
   - execution/transport failure;
   - observation failure;
   - non-comparable outcome;
   - no future-information leakage;
   - denominator correctness.
8. Produce a first aggregate report with explicit sample sizes.
9. Only after evidence exists, propose controlled improvements.
10. Do not alter closed checkpoints merely to implement this capability.

---

## 17. BUILDER PROHIBITIONS

The next Builder must not:
- call provider rejection a prediction failure;
- remove difficult assets from the analytical population;
- silently discard wrong predictions;
- alter historical labels;
- use future data in prediction features;
- infer causality from correlation;
- optimize for a prettier accuracy number;
- claim maturity from insufficient sample size;
- modify closed CP39/CP44/CP46-A..H/CP47/CP48/CP64..CP71 without direct regression evidence;
- redesign the execution bridge to solve a prediction-quality question;
- couple prediction-quality logic to Toobit-specific behavior;
- introduce synthetic market outcomes;
- use test/fabricated outcomes as production prediction evidence.

---

## 18. ACCEPTANCE GATE

This work is complete only when a future Builder can answer from repository evidence:

> For every eligible Trader prediction, what did Trader predict, what actually happened in the real market, was the prediction correct, and if not, was the failure predictive or environmental?

And can produce a reproducible aggregate:

~~~
CORRECT / WRONG / PROVIDER_FAILURE / OBSERVATION_FAILURE / NON_COMPARABLE
~~~

with explicit denominator and sample size.

---

## 19. MANAGEMENT HANDOFF

Immediate post-first-execution route:

~~~
REAL TOOBIT RESPONSE
→ CP69 EVIDENCE
→ PREDICTION OUTCOME RECORD
→ REAL MARKET COMPARISON
→ ERROR ANALYSIS
→ PREDICTION QUALITY
→ CONTROLLED MATURITY
~~~

This document is the durable engineering handoff.

**Do not reconstruct this objective from conversational memory.**

# END POST-EXECUTION PREDICTION QUALITY CONTRACT
