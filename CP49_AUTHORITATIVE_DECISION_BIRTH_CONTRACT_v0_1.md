# CP49 — AUTHORITATIVE DECISION BIRTH CONTRACT v0.1

DATE: 2026-09-26

## STATUS
DESIGN APPROVED FOR CONTRACT DEFINITION / ID ISSUANCE ALGORITHM UNSELECTED / RUNTIME OFF

This artifact defines the ownership and lifecycle semantics of an authoritative Decision Birth. It does not introduce an identity-generation algorithm, execute the pipeline, write to the production database, or submit an exchange order.

## 1. CANONICAL BIRTH BOUNDARY
The authoritative boundary is immediately after semantic Decision evaluation:
Validated Signals + Scores → Decision Engine → AUTHORITATIVE DECISION BIRTH → Risk → Allocation → Position Size → Trade Gate

The Decision Engine determines the semantic result. The Authoritative Decision Birth establishes the canonical Decision Instance. Pipeline orchestration is not the identity owner.

## 2. DECISION BIRTH EVENT
The canonical Birth Event MUST contain, at minimum:
- decision_id
- asset
- decision_timestamp_ms
- snapshot_id or equivalent canonical input identity
- source
- the semantic decision payload produced by Decision Engine
- decision-time provenance / knowledge cutoff where required by downstream contracts

Conceptually:
DecisionBirth = { decision_id, asset, decision_timestamp_ms, snapshot_id, source, decision, provenance }

## 3. IDENTITY SEMANTICS
decision_id means: identity of THIS Decision Birth / Decision Instance.
It does NOT mean snapshot identity, provider identity, order-intent identity, execution-attempt identity, exchange order identity, position identity, or outcome identity.

## 4. OWNERSHIP
Owner of Decision ID issuance: Authoritative Decision Birth.
The issuance operation is part of the Birth Contract. It MUST NOT be delegated implicitly to arunda_pipeline.py, CP49 validation/binding modules, Risk, Allocation, Position Sizing, Trade Gate, Order Intent, Execution, or Observation.
The concrete issuer implementation remains a separate design decision.

## 5. ISSUANCE MOMENT
The identity MUST be issued as part of the atomic logical transition that creates the canonical Decision Birth Event.
Required ordering: semantic decision available → identity issuance owned by Birth Contract → Decision Birth Event exists → canonical Decision instance exists → downstream propagation.
An ID MUST NOT be created merely to satisfy a downstream function signature.

## 6. CANONICALITY
An identifier is canonical only when: it is issued under the authoritative Decision Birth contract; it identifies one Decision Birth instance; it is attached to that Birth Event at creation; downstream layers consume and propagate it unchanged; and no downstream layer is permitted to replace it.

## 7. UNIQUENESS
The final uniqueness mechanism is NOT YET SELECTED.
Required property: no two distinct Decision Birth instances may legitimately share the same canonical decision_id within the defined system identity domain.
The concrete mechanism for guaranteeing this property requires an explicit Management design decision.

## 8. STABILITY
After Birth, decision_id is immutable.
Decision Birth → Decision → Risk → Allocation → Position Size → Trade Gate → Order Intent → Execution Attempt → Observation must preserve the exact value.
No downstream layer may substitute a new Decision ID.

## 9. REPLACEMENT RULE
There is no silent replacement.
If the authoritative Birth operation cannot establish a valid canonical identity, the Birth MUST fail closed.
A later layer MUST NOT repair the condition by generating, deriving, or substituting another identifier.

## 10. FORBIDDEN ISSUANCE / DERIVATION
- UUID/random generation used as an unapproved semantic substitute
- hash-derived IDs
- timestamp-derived IDs
- asset-derived IDs
- snapshot-derived IDs
- intent-derived IDs
- counters/sequences introduced solely as a workaround
- risk/capital/quantity/notional/PnL-derived IDs
- manual/runtime-injected IDs
- fallback IDs
- synthetic IDs
- provider-selection IDs

These may not be introduced merely to make the existing CP49 contract pass.

## 11. PROVIDER / PIPELINE BOUNDARY
Provider modules and the pipeline may receive the canonical Birth Event, validate it, bind it, and propagate its identity.
They may not own Decision ID issuance.
cp49_production_decision_birth_producer_v0_1.py remains a validator/binder boundary until a concrete authoritative issuer is separately approved.

## 12. FAILURE SEMANTICS
If any required Birth identity condition is absent or invalid: AUTHORITATIVE DECISION BIRTH = BLOCKED.
No fallback identity is permitted.
The blocked state must remain observable and must not be relabeled as a valid Decision.

## 13. REQUIRED FUTURE ISSUER CONTRACT
Before concrete implementation, Management must select the actual issuance semantics:
DecisionIdentityIssuer → issue(authoritative birth context) → canonical decision_id

The selected issuer MUST specify: owner; issuance transaction/boundary; identity domain; uniqueness guarantee; persistence requirement; collision behavior; immutability; recovery behavior; provenance of issuance.
This artifact deliberately does not select an algorithm for those properties.

## 14. IMPLEMENTATION GATE
Only after the issuance semantics above are explicitly selected may implementation proceed.
Implementation must then be limited to: authoritative issuer; Birth Event construction; unchanged binding into existing CP49 boundary; unchanged downstream propagation; focused contract/static tests.
No live runtime is required for contract implementation verification.

## 15. SAFETY
- EXECUTION_ENABLED = FALSE
- no runtime execution
- no order submission
- no exchange/API write
- no production DB write
- no synthetic identity
- no closed checkpoint reopened

## MANAGEMENT STATUS
EXISTING AUTHORITATIVE SOURCE = NONE
BIRTH OWNERSHIP = DEFINED
BIRTH EVENT CONTRACT = DEFINED
ID OWNERSHIP = AUTHORITATIVE DECISION BIRTH
ID STABILITY = IMMUTABLE AFTER BIRTH
ID REPLACEMENT = FORBIDDEN
ISSUANCE ALGORITHM = MANAGEMENT DECISION REQUIRED
CONCRETE ISSUER = NOT IMPLEMENTED
RUNTIME = OFF

CP49 = BLOCKED / DESIGN BOUNDARY DEFINED / ISSUANCE SEMANTICS PENDING MANAGEMENT DECISION

# END CP49 AUTHORITATIVE DECISION BIRTH CONTRACT