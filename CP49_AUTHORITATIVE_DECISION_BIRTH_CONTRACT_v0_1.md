# CP49 — AUTHORITATIVE DECISION BIRTH CONTRACT v0.1

DATE: 2026-09-26

## STATUS
DESIGN APPROVED / UUIDv4 ISSUANCE SELECTED / RUNTIME OFF

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
The concrete issuer is the CP49 Authoritative Decision Birth Issuer defined by the UUIDv4 issuance contract below.

## 5. ISSUANCE MOMENT
The identity MUST be issued as part of the atomic logical transition that creates the canonical Decision Birth Event.
Required ordering: semantic decision available → identity issuance owned by Birth Contract → Decision Birth Event exists → canonical Decision instance exists → downstream propagation.
An ID MUST NOT be created merely to satisfy a downstream function signature.

## 6. CANONICALITY
An identifier is canonical only when: it is issued under the authoritative Decision Birth contract; it identifies one Decision Birth instance; it is attached to that Birth Event at creation; downstream layers consume and propagate it unchanged; and no downstream layer is permitted to replace it.

## 7. UNIQUENESS AND ISSUANCE SEMANTICS
Management decision: canonical Decision IDs use UUIDv4 as opaque instance identities.

The identity domain is the set of authoritative Decision Birth Events of this ArundaTrader decision system. UUIDv4 is selected for identity opacity and independence from asset, market timestamp, snapshot contents, score, risk, sizing, order, and execution state.

Uniqueness is enforced operationally by the authoritative Birth persistence boundary: the persisted canonical Decision Birth record MUST have a UNIQUE constraint on decision_id. A collision is a Birth failure; the colliding candidate MUST NOT be accepted or substituted downstream. Before the Birth Event is committed, the issuer may retry issuance with a new UUIDv4 candidate. Once a Birth Event commits, its decision_id is immutable.

The UUIDv4 value is not semantically derived from business data and is not used as a timestamp, asset, snapshot, intent, or counter identity.

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
## 13. AUTHORITATIVE ISSUER CONTRACT
The selected issuance semantics are:

Decision Birth semantic result
→ Authoritative Decision Birth Issuer
→ UUIDv4 candidate
→ Birth persistence uniqueness check
→ canonical Decision Birth Event
→ unchanged downstream propagation

Issuer requirements:
- owner: Authoritative Decision Birth
- issuance boundary: the atomic logical Birth transition, after semantic decision evaluation and before the canonical Birth Event is committed
- identity domain: all authoritative Decision Birth Events in this system
- issuance mechanism: UUIDv4 opaque identifier
- uniqueness enforcement: UNIQUE(decision_id) at the authoritative Birth persistence boundary
- persistence: the canonical Birth Event persists the issued decision_id
- collision behavior: collision prevents Birth completion; retry is allowed only before Birth commit
- immutability: committed decision_id cannot change
- recovery: an uncommitted/failed Birth has no canonical identity; a committed Birth is recovered by its persisted decision_id
- provenance: the Birth Event records issuer contract/version and issuance event context; the UUID value itself carries no business provenance

The issuer MUST NOT use UUID input from callers, random IDs supplied by the pipeline, timestamp/asset/snapshot derivation, counters, hashes, fallbacks, or downstream substitution.

## 14. IMPLEMENTATION GATE
The issuance semantics are now selected. Implementation may proceed only at the authoritative Birth boundary; the current runtime remains OFF and no production schema migration or runtime execution is authorized by this artifact.
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
ISSUANCE ALGORITHM = UUIDv4 + PERSISTENT UNIQUE BIRTH CONSTRAINT
CONCRETE ISSUER = IMPLEMENTED AS ISOLATED CONTRACT MODULE / PIPELINE INTEGRATION PENDING
RUNTIME = OFF

CP49 = BLOCKED / ISSUANCE SEMANTICS DEFINED / AUTHORITATIVE BIRTH INTEGRATION PENDING

# END CP49 AUTHORITATIVE DECISION BIRTH CONTRACT