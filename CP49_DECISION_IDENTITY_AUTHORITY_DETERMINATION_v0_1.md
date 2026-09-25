# CP49 — DECISION IDENTITY AUTHORITY DETERMINATION v0.1

**DATE:** 2026-09-26

## STATUS

**DETERMINED / IMPLEMENTATION BLOCKED / RUNTIME OFF**

## DETERMINATION

The authoritative Decision Birth identity source is **not currently present in the inspected real production path**.

The canonical location of semantic Decision Birth remains the Decision Engine boundary:

`Validated Signals + Scores → Decision Engine → Authoritative Decision Birth → Risk → Allocation → Position Sizing → Trade Gate`

The Decision Engine may construct the semantic decision, but the current CP49 contract deliberately requires `decision_id` as an already-existing input. It does not and must not manufacture the identity.

## FORENSIC EVIDENCE

The inspected production path contains no authoritative pre-existing `decision_id` in:

- `ProductionSignalInput`;
- `dynamic_signals`;
- `validated_signals`;
- `market_signal_map`;
- the inspected Decision Engine upstream call chain;
- the existing production decision binding;
- the CP49 boundary/provider modules.

The CP49 provider/producer modules are validators and binders only. They are not issuers.

The existing execution lifecycle consumes and propagates `decision_id`; it does not provide a legitimate Decision Birth identity source.

## EXCLUDED SOURCES

The following are explicitly rejected as Decision Identity Authority:

- UUID/random identity;
- hash-derived identity;
- timestamp-derived identity;
- asset-derived identity;
- snapshot-derived identity;
- intent-derived identity;
- counter/sequence generated for this purpose;
- risk budget, capital, quantity, notional, PnL, or other business values;
- manual/runtime-injected identity;
- fallback or synthetic identity;
- canonical provider-selection identity.

These mechanisms would violate the CP49 identity contract.

## IMPLEMENTATION DECISION

**Do not implement an artificial issuer.**

No new identity-generation mechanism is introduced in this step.

The only valid implementation path is to establish an actual authoritative Decision Birth identity source whose identity already exists at the moment of Decision Birth, then pass that identity unchanged into the existing CP49 canonical identity boundary and Decision Engine.

Until that source is explicitly established and authorized, CP49 remains blocked.

## NEXT AUTHORIZED TECHNICAL GATE

1. Establish the authoritative Decision Birth identity source and its exact ownership/issuance semantics.
2. Connect that existing identity to the real Decision Birth boundary.
3. Verify unchanged propagation:
   `Decision Birth → Decision → Risk → Allocation → Position Size → Trade Gate → Order Intent → Observation`.
4. Run no live pipeline/runtime as part of this work.

## SAFETY

- `EXECUTION_ENABLED = FALSE`
- no runtime executed;
- no order submitted;
- no exchange/API write;
- no production DB write;
- no synthetic identity introduced;
- no closed checkpoint reopened.

# END CP49 DECISION IDENTITY AUTHORITY DETERMINATION
