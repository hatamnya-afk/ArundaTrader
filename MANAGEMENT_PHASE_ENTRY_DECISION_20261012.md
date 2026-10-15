# MANAGEMENT PHASE-ENTRY DECISION — 2026-10-12

## Decision
**AUTHORIZED — ENTER THE REAL-PRODUCTION TRADING PHASE**

## Authority
- Authorizer: Project owner / Management
- Source: Explicit authorization given in the project conversation on 2026-10-12: “مجوز ورود داری سلطان”
- Environment: REAL_PRODUCTION
- Provider: TOOBIT
- Markets in scope: SPOT and FUTURES
- Mandate type: One-time standing phase-entry mandate
- Capital policy: ZERO_INITIAL_CAPITAL; record genuine provider responses and real outcomes; progressively add capital only after management review of demonstrated quality.
- Per-trade management approval: NOT REQUIRED.

## Standing mandate continuity policy
- The intended operating model is continuous autonomous trading, 24 hours a day, without periodic management renewal.
- The management phase-entry mandate has no calendar expiry. It remains in force until formally revoked by management or its authorized scope is changed.
- A fabricated expiry timestamp must not be introduced merely to satisfy an implementation contract.
- This policy does not override current-request readiness, instrument/provider validation, risk limits, trade gates, idempotency, ambiguous-outcome quarantine, or technical execution authorization.
- The software implementation must represent this standing mandate without requiring `issued_at` or `expires_at` solely as periodic authorization expiry fields. Any separate timestamp retained for audit must not silently act as an expiry.
- Per-trade management approval is not required. Each order remains subject to the autonomous Decision → Risk → Trade Gate → Readiness → Technical Execution Authorization → Final Execution Attempt path.

## Meaning of this authorization
This decision authorizes phase entry as a standing management mandate. It does not assert that every technical order-attempt precondition has already passed, and it is not evidence that a live order has been sent or filled.

The existing Decision → Risk → Trade Gate → Readiness → Technical Execution Authorization → Final Execution Attempt → Provider → Outcome path remains authoritative. Provider acceptance/rejection is authoritative; acceptance and fill are distinct.

## Mandatory boundaries
- No fabricated, synthetic, backfilled, interpolated, forward-filled, padded, or blended evidence.
- No weakening of order-idempotency or ambiguous-outcome safeguards.
- A timed-out or ambiguous submission must not be blindly retried.
- No database repair or mutation as part of this decision record.
- This record does not itself wire or activate the production pipeline.
- A real order attempt may occur only when the existing technical execution gate verifies all required current request, provider/instrument, readiness, mandate, and safety evidence.
- PR #31 remains Draft/unmerged unless separately authorized.
- No claim of live-provider verification may be based on offline fixtures or mocked transports.

## Next action
Implement and test the standing-mandate continuity policy across the management mandate producer, execution authorization boundary, and focused tests. Do not invent timestamps. Keep live execution blocked until the code contract and its focused verification consistently implement this policy and all independent order-attempt gates pass.

## Status
Management phase-entry decision: **AUTHORIZED — STANDING, NO CALENDAR EXPIRY**.
Technical real-order gate: **BLOCKED UNTIL IMPLEMENTATION AND VERIFICATION**.
Execution/pipeline activation: **NOT PERFORMED BY THIS RECORD**.

# END
