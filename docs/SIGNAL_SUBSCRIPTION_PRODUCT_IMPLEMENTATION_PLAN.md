# Signal Subscription Product Roadmap

Date: 2026-10-16
Status: Management-approved direction; implementation not yet verified.

## Objective
Build a customer-facing signal software product. Customers see selected, evidence-qualified signals and pay monthly. The product must remain independent of live order execution.

## Existing evidence
- ArundaTrader operational branch: operational-main-20261007.
- Open ArundaTrader PR #37 proposes a local, read-only selection-quality dashboard using existing real-market outcome evidence. It is not merged into the operational branch; review its full diff and tests before reuse.
- AroondaAI has CP69 canonical observation consumption and CP72 read-only runtime analysis. Its current frontier forbids Trader mutation, order submission, and new real Trader runtime from this bridge work.
- The inspected AroondaAI run_chat.py launches a Tkinter chat UI and does not show the CP69/CP72 analysis wired into a customer-facing signal dashboard.
- Customer accounts, monthly billing, subscription expiry/entitlement, and customer signal publication are not verified as implemented.

## Delivery sequence
1. Audit PR #37, source evidence contracts, and CP69/CP72 contracts. Do not build a duplicate dashboard.
2. Complete an operator read-only Control Center showing source freshness/provenance, asset selection, signals, available pipeline/gate status, quality evidence, outcomes, and Aroonda advisory analysis.
3. Define a versioned signal-publication policy. Publish only signals with attributable real post-launch evidence and explicit qualification criteria. Missing, stale, malformed, or contradictory evidence must fail closed. Never synthesize, backfill, interpolate, forward-fill, pad, fabricate, or silently blend data.
4. Build customer accounts, monthly billing, renewal/expiry/cancellation handling, server-side entitlement checks, customer/operator role separation, audit logging, and security controls only after the signal contract is verified. No payment provider, hosting, domain, or deployment is presumed to exist.
5. Integrate Aroonda through existing CP69/CP72 boundaries as read-only advisory analysis, with observation identity and uncertainty clearly separated from observed facts.
6. Only after signal quality is reviewed and explicitly approved may management consider a separate staged-capital trading phase.

## Safety
No closed checkpoint reopening without provable regression. Do not modify arunda_pipeline.py, run a production runtime, write to the production database or exchange, or activate order submission in this product work. Current execution authorization remains FALSE. Signal publication, customer billing, and live trading remain separate capabilities.

## Immediate next action
Review the complete PR #37 diff and its source-data contract, then create the smallest test-backed integration change on a dedicated branch. Do not merge automatically.
