# READ-ONLY TOOBIT LIVE EVIDENCE CAPTURE — MANAGEMENT AUTHORIZATION
Date: 2026-10-14
Status: SCOPE AUTHORIZED BY PROJECT OWNER; EXECUTION PENDING SECURE RUNTIME ACCESS

## Decision and purpose
The project owner explicitly approved proceeding and confirmed that the project manager should decide within protocol while preserving continuity for the next Builder. This record authorizes a narrowly bounded read-only evidence-capture step so the project does not wait indefinitely for a separate approval.
This is a governance authorization for read-only evidence gathering only. It does not authorize production pipeline runtime, a trade, or any provider/database write.

## Authorized read-only scope
Use the existing Toobit adapter/provider boundary and a securely configured execution environment to capture genuine, timestamped provider evidence for:
1. Spot balances, preserving free/locked/total distinctions.
2. Account-wide Futures positions and balances across both USDT-M and USDC-M categories, with explicit category coverage.
3. Open and recent orders only to establish current account/order state and reconciliation context.
4. Server time and relevant authoritative instrument/account metadata needed to establish provenance.
5. Approved valuation policy documents and source references for every non-zero held asset; capture current source/rate/timestamp evidence only where the source and policy are authenticated.
6. Verifiable risk policy identity/version/effective interval, risk-per-trade, maximum portfolio risk, maximum concurrent positions, and position-specific allocated-risk/stop evidence where available.

All evidence must preserve source, venue/category, account scope, observation timestamp, retrieval time, cycle/correlation identity, and raw-response provenance or a secure immutable digest where appropriate. Never put API keys, secrets, signatures, or private account credentials in Git, logs, reports, chat, or committed artifacts.

## Hard prohibitions
- No order submission, including test/dust orders.
- No order cancellation, withdrawal, transfer, account-setting change, leverage/margin change, or any other provider write.
- No production pipeline/runtime activation.
- No database writes or repair/mutation.
- Do not enable EXECUTION_ENABLED, ORDER_SUBMISSION_ENABLED, ORDER_CANCELLATION_ENABLED, WITHDRAWAL_ENABLED, EXCHANGE_WRITE_ENABLED, or DATABASE_WRITE_ENABLED.
- Do not fabricate, infer, synthesize, backfill, interpolate, forward-fill, pad, or blend balances, positions, valuation rates, stops, quantities, allocated risk, fills, policy approvals, or timestamps.
- Do not infer Futures exposure permission from balance, leverage, margin type, risk limits, empty positions, or API-key permissions.
- Do not treat a management mandate as a per-trade approval, or this evidence-capture authorization as an order authorization.

## Validation and fail-closed outcomes
- Validate full Spot and both Futures category coverage; report missing categories or incomplete pagination as BLOCKED.
- Reject duplicate normalized asset rows, malformed/non-finite/negative quantities, future timestamps, stale observations without an explicit approved freshness policy, and mismatched cycle/account/policy/source identities.
- Require approved source identity/reference and timestamped rates for all non-zero assets. A label such as APPROVED alone is not authentication.
- Do not convert missing stop/risk allocation/policy evidence into zero risk. Portfolio risk remains BLOCKED until every applicable position is covered by authentic policy and allocation evidence.
- Report each item as VERIFIED, BLOCKED, or NOT VERIFIED, distinguishing real-provider evidence from offline tests.
- Keep the actual raw account payload out of public or committed documentation unless properly redacted and explicitly safe; record secure artifact location/hash and evidence metadata instead.

## Required execution sequence
1. Confirm the intended runtime is the operational lineage operational-main-20261007 and that credentials are available only through its secure environment/secret store.
2. Use only GET/read-only endpoints through the existing Toobit adapter or a focused read-only capture command. Before execution, inspect the exact call path to ensure no write-capable helper or pipeline runtime is reachable.
3. Capture Spot, Futures USDT-M, Futures USDC-M, open/recent orders, and server-time evidence as a bounded capture; no trading pipeline invocation.
4. Validate evidence against the ledger producer and approved risk/valuation policy contracts. Preserve raw evidence securely and emit a redacted report.
5. Record exact timestamps, response statuses, coverage, provenance, validation results, and blockers. Never claim success if the capture did not actually run.
6. Synchronize PROJECT_STATE.md, CURRENT_FRONTIER.md, CHECKPOINTS.md, and MANAGEMENT_ROADMAP.md with the actual result. Do not promote candidate-branch code or claim operational PASS based on this authorization record.

## Current factual status at authorization
- Management phase-entry mandate for REAL_PRODUCTION, Toobit Spot and Futures was already recorded AUTHORIZED on 2026-10-12.
- The final real-order gate remains OPEN / BLOCKED / NOT VERIFIED. The adapter's order submission remains disabled/unverified, mandate expiry and client-order-ID/recovery semantics remain blockers.
- Live account-wide ledger, approved current valuation rates, authenticated risk policy, and per-position allocated risk have NOT been verified by the current evidence set.
- This record authorizes read-only evidence capture only; it does not itself prove connection, capture, or verification.

## Immediate next action
A Builder with access to the project's secure execution environment must perform the bounded read-only capture above. If this chat environment lacks the repository runtime or secret-store access, state that operational limitation precisely and hand off the exact command/path required; never ask the owner to paste secrets into chat and never pretend the API was called.
