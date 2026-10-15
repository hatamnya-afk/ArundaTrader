> ## CURRENT ADDENDUM — 2026-10-15 — ORDER RECONCILIATION CONTRACT
>
> - Added `execution_order_reconciliation_v0_1.py`: only already-fenced ambiguous claims may be reconciled; exact client-ID and symbol identity must match; no order submit/cancel/retry is performed.
> - Added durable normalized reconciliation evidence to the isolated `SQLiteIntentClaimStore`: client ID, venue/symbol, provider order ID/status, executed quantity/price, provider timestamp, detail code and observation timestamp. Evidence ID reuse with conflicting contents fails closed.
> - Corrected Toobit Futures lookup to documented `GET /api/v1/futures/order`. Official docs: [Spot Query Order](https://api-docs.toobit.com/api/spot-account-and-trading.html) and [Futures Query Order](https://api-docs.toobit.com/api/usdt-m-account-and-trading.html) both document `origClientOrderId`; Futures also documents category and order status fields.
> - Client ID is deterministic (`A` + 31 SHA-256 hex chars of canonical intent ID). Toobit documents Spot client IDs as unique among open orders, not globally unique forever. Therefore the safety invariant is Arunda's permanent unique constraint in the durable claim store; collision means block before submission. This guarantee is not a production guarantee until that store is durably configured and wired into the authorized runtime.
> - **Offline verification:** [Focused Execution Contract Tests](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38802980657) — 57 passed; [Phase-entry focused verification](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38802986919) — 58 tests, OK. Scope is offline contract tests only.
> - A negative/failed/malformed lookup is **not** proof of non-execution. It records `UNRESOLVED_KEEP_QUARANTINED` / `RECONCILIATION_REQUIRED`; no resubmit is allowed. This resolves the ambiguity safely by policy, not by assuming an undocumented provider guarantee.
> - **Operational status remains BLOCKED / NOT VERIFIED:** the durable claim/evidence store and reconciliation helper are not wired into `arunda_pipeline.py` or an authorized production runtime. No provider write, order, cancellation, production runtime, or production DB write was performed; submission switches remain OFF.
>
> ---
>
> ## CURRENT ADDENDUM — 2026-10-15 — STANDING-MANDATE EXPIRY POLICY
>
> - The active phase-entry mandate is revocation-controlled with **no calendar expiry**; do not require or fabricate `issued_at`/`expires_at` merely to create a standing mandate. If an explicit expiry is supplied, it must be timezone-aware, future-dated, and consistent with issuance.
> - Code changes are committed on `operational-main-20261007`: management producer `bdc61f8`; technical authorization boundary `fdcd9de`; management tests `4a02fc5`; final-attempt tests `507ab01` and corrective test-fixture commit `eca7b35`.
> - The final-attempt test fixture was corrected to use only an in-memory claim-store double and a fake adapter stable client ID, and to assert the boundary's specific fail-closed errors. This is offline test scaffolding only; it does not contact Toobit.
> - **Focused verification: VERIFIED / PASS for the scoped tests only.** GitHub Actions run `38801470736` on commit `29f36d33c188ce917d78dfbfde1c0517cbb20b47` completed successfully: `20 passed in 0.05s` across `test_management_execution_authorization_v0_1.py` and `test_final_execution_attempt_contract_v0_1.py`. This does not verify the full suite, Toobit live submission, provider recovery guarantees, or production pipeline integration.
> - This change does **not** authorize a live attempt. Toobit submission remains disabled/unverified; provider client-order-ID and ambiguous-recovery guarantees and outcome capture remain blockers. No pipeline wiring, runtime, live order, provider write, cancellation, or production DB write is authorized by this addendum.
>
> This dated addendum supersedes older statements below that claim the mandate must have calendar expiry fields; those older entries remain historical evidence.
>
> ---
>
# FINAL REAL-ORDER ATTEMPT GATE — MANAGEMENT REVIEW PACKAGE
## ArundaTrader — 2026-10-12

### PURPOSE
Define the exact boundary that must be satisfied before a future real provider order attempt can be made under the already-authorized real-production phase.

This document does NOT authorize execution.

### GOVERNING MANAGEMENT INVARIANT

Management authorization is **ONE-TIME REAL-PRODUCTION PHASE-ENTRY MANDATE**.

The management decision is only:

`AUTHORIZE REAL-PRODUCTION TRADING PHASE`

Once explicitly authorized:
- the trader operates autonomously;
- SPOT and FUTURES are both in scope;
- no per-trade management approval exists;
- no individual order, asset, direction, quantity, order-type, exposure, or `attempt_id` is sent to Management for approval;
- individual trade selection and sizing remain inside Decision → Risk → Trade Gate → Readiness;
- Technical Execution Authorization verifies the current request against the active standing mandate;
- the provider remains authoritative for ACCEPT / REJECT.

### VERIFIED ENTRY
- Provider-neutral execution-attempt contract: VERIFIED / PASS.
- Core remains exchange-agnostic.
- Toobit remains a replaceable adapter.
- The phase-entry decision is now explicitly AUTHORIZED (see MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md). Technical execution authorization remains FALSE until a current request and valid, unexpired standing mandate pass every technical gate.

### OWNERSHIP

| Concept | Canonical owner |
|---|---|
| Management phase entry | `management_execution_authorization_v0_1.py` |
| Management review packaging | `management_review_package_v0_1.py` — review-only; never an authorization producer |
The Management boundary is closed-schema: trade/attempt fields and aliases are rejected, and unclassified fields fail closed.
| Technical execution authorization | `execution_authorization_boundary_v0_1.py` |
| Execution readiness | `execution_attempt_readiness_contract_v0_1.py` |
| Final attempt composition | `final_execution_attempt_contract_v0_1.py` |
| Provider-neutral attempt | `exchange_execution_order_attempt_boundary_v0_1.py` |

**Critical distinction:**
`Management Mandate ≠ Execution Attempt`

An `attempt_id` may exist in the execution-attempt/evidence domain. It must not become a Management authorization input.

### REQUIRED PRECONDITIONS

1. Canonical order request is valid.
2. Execution-ready package and readiness state agree.
3. Selected execution instrument is authoritative and unambiguous.
4. Approved provider read-only evidence is available where required by the existing execution contracts.
5. Provider-specific translation remains entirely inside the adapter.
6. No hidden authorization inference exists.
7. The active Management input is a valid `STANDING_MANDATE`, not an attempt-level approval.
8. The standing mandate covers `REAL_PRODUCTION`, SPOT + FUTURES, provider, capital policy, evidence requirements, and expiry.
9. Safety interlocks remain fail-closed.
10. The execution attempt is observable and produces the existing evidence/outcome record.
11. A provider rejection is real environmental evidence, not permission to weaken contracts.
12. Acceptance and fill remain distinct states.
13. Zero provider balance is not converted into a local architecture blocker.

### EXECUTION PATH

```
ONE-TIME MANAGEMENT DECISION
        │
        ▼
REAL-PRODUCTION PHASE ENTRY
        │
        ▼
STANDING_MANDATE
        │
        ▼
AUTONOMOUS TRADER
        │
        ├── SPOT
        └── FUTURES
              │
              ▼
Decision
   ↓
Risk
   ↓
Trade Gate
   ↓
Readiness
   ↓
Technical Execution Authorization
   ↓
Final Execution Attempt Contract
   ↓
Provider-Neutral Attempt Boundary
   ↓
Provider
   ├── ACCEPT
   └── REJECT
        ↓
    REAL EVIDENCE
```

There is **no** `TRADE → MANAGEMENT APPROVAL → TRADE` path.

### ZERO-BALANCE RULE

A zero account balance is valid environmental state. It must not be converted into a local trade blocker before the provider request.

Zero balance does not imply acceptance. If a valid provider attempt is eventually made under the standing mandate and the provider rejects it because of balance, margin, permissions, instrument constraints, or another provider condition, that rejection is real provider evidence.

No contract weakening, fabricated acceptance, inferred permission, or synthetic evidence is allowed.

### MANAGEMENT SAFETY BOUNDARY

The phase-entry decision is already explicitly authorized by MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md. That management decision does not override unresolved technical gates.

Current technical interlocks remain:
- EXECUTION AUTHORIZATION = FALSE until a current ready request and valid, unexpired standing mandate pass technical validation.
- Provider order submission remains fail-closed in the current Toobit adapter.
- Order submission/cancellation/withdrawal and provider writes remain forbidden until their specific technical contracts are verified.
- Database mutation remains forbidden.
- No production runtime or live order is authorized by this review document.

Once technical gates pass, the standing mandate is the management authorization context. **No new management authorization is requested for individual trades.**

### EVIDENCE REQUIRED FOR FUTURE AUTHORIZED OPERATION

Record existing real evidence without fabrication or backfill:
- decision identity and timestamp/provenance;
- canonical order request;
- execution-ready package identity;
- execution attempt identity where applicable;
- execution instrument;
- provider readiness evidence;
- active standing-mandate identity;
- exact provider request outcome;
- provider order identifier if accepted;
- fill status and fill evidence if any;
- rejection reason if rejected;
- post-attempt account/position/order evidence where authorized;
- complete execution state.

The standing mandate itself is not recreated for each attempt.

### CURRENT MANAGEMENT AND TECHNICAL DISPOSITION

- Management phase-entry decision: **AUTHORIZED — 2026-10-12**.
- Current operational branch: operational-main-20261007.
- Technical real-order gate: **OPEN / BLOCKED / NOT VERIFIED**.
- Current Toobit adapter: order_submission=False; submit entrypoints fail closed with EXECUTION_DISABLED_ORDER_SUBMISSION_NOT_IMPLEMENTED.
- Standing mandate artifact: **incomplete for runtime use** because MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md does not carry the required timezone-aware issued_at and expires_at fields. No expiry has been fabricated; management's authorization remains recorded, while technical validation must reject an incomplete mandate.
- PR #31 (Add atomic per-intent claim store contract) remains Draft and unmerged. Its offline CI run #38237269560 passed 88 tests in 1.28s. This validates only offline contract/recovery fixtures and isolated temporary SQLite, not Toobit API semantics or live execution.
- Official Toobit material reviewed in PR #31 does not establish client-order-ID maximum length/allowed charset, uniqueness/reuse scope after terminal states, duplicate POST replay semantics, lookup consistency/retention, or exhaustive history recovery by client ID. These must be supported by authoritative documentation or written provider confirmation. Do not guess values.
- Global Selection Quality Loop focused CI passed 11 tests on the operational branch; production evidence accumulation and calibration effectiveness remain NOT VERIFIED.

### REQUIRED NEXT ACTIONS — FAIL-CLOSED

1. Complete a formally time-bounded standing-mandate observation without inventing issuance/expiry timestamps or silently choosing a policy.
2. Obtain authoritative Toobit documentation or written support confirmation for the unresolved client-order-ID and ambiguous-recovery semantics.
3. Implement/verify the provider adapter submit path only against verified constraints; keep unknown outcomes blocked and never blindly retry.
4. Run focused CI on the intended operational code lineage and verify commit/branch identity.
5. Verify order-attempt outcome capture and reconciliation contracts before any production runtime.
6. Do not run a production runtime, send an order, cancel, withdraw, enable execution, or write to the provider/database while any gate remains open.

The standing phase-entry mandate means no per-trade management approval is required; it does **not** waive any of the above technical gates.

## CURRENT IMPLEMENTATION VERIFICATION — 2026-10-15

Status: **EXECUTION PATH CODE VERIFIED / LIVE ATTEMPT BLOCKED**.

- Operational branch has an opt-in Toobit adapter and allowlisted HTTPS transport for Spot `POST /api/v1/spot/order` and Futures v2 `POST /api/v2/futures/order`, based on the official API endpoint/response documentation.
- Adapter remains submission-OFF by default; runtime injection requires both `ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT=1` and `ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION=1`, credentials, and an absolute separate `ARUNDA_EXECUTION_CLAIM_DB`.
- The claim factory refuses to use the production trading database. Stable intent-derived client ID, atomic durable claim, pre-submit outcome-unknown fence, one POST maximum, response identity checks, and accepted/rejected outcome persistence are implemented.
- Offline end-to-end test verifies exactly one mocked POST and durable provider-accepted state.
- Latest focused CI run #52 PASS: https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38780574776 (commit `a2c2c0cae8742d36eb1f3f1b005426abe39541ac`) (commit `351d3321d0f17828fe2f0e54dc56ca7d7aec9362`).

### Remaining live gate

**BLOCKED / NOT VERIFIED:** `MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md` still lacks authoritative timezone-aware `issued_at` and `expires_at`. The code must not invent them. No live provider request, order, cancellation, production runtime, or production DB write has been performed.

Transport exceptions and malformed/mismatched responses remain `SUBMISSION_OUTCOME_UNKNOWN`; the claim cannot be replayed. Reconciliation must be read-only. Acceptance is not fill, and the offline mock test is not evidence of a live Toobit response.

The standing mandate remains one-time phase-entry authorization; no per-trade management approval is introduced. Historical lines above that say submission is unimplemented or the pipeline is unwired are superseded by this current implementation status; the default-off safety state remains intact.

# END


## Addendum — 2026-10-15 — Read-only order reconciliation

- Added the fail-closed reconciliation coordinator and offline tests. Positive identity-matched provider lookup persists immutable evidence and can resolve an existing claim; negative, failed, malformed, or mismatched lookup persists `UNRESOLVED_KEEP_QUARANTINED` and keeps the claim in `RECONCILIATION_REQUIRED`. It never retries or authorizes resubmission.
- CI at commit `2d37c36726b5542b8e79c8f4e4eefdb4c3bc2cad`: phase-entry focused verification PASS (57 tests); focused execution contract PASS (56 tests). Offline scope only.
- Toobit Spot client-order IDs are documented as unique among open orders; lifetime uniqueness is not established. The durable claim store enforces no reuse for intents represented in its provider namespace, but cannot prove the absence of external/unrecorded orders.
- Official references: https://api-docs.toobit.com/api/spot-account-and-trading.html and https://api-docs.toobit.com/api/usdt-m-api-v2
- Production order gate remains BLOCKED / NOT VERIFIED: submission disabled, no pipeline wiring, no provider writes, no live order, no cancellation, no production runtime or production DB write. No Futures exposure permission is inferred.
