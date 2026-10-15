# Toobit Futures client-order-ID and reconciliation evidence record v0.3

- Reviewed: 2026-10-15
- Support ticket: #20261012000242, reply dated 2026-10-13 11:04:32
- Scope: support answer says USDT-M and USDC-M constraints differ; exact values below are only safe to apply to USDT-M Futures regular orders because support did not provide USDC-M values.
- Live API/order actions: NOT performed
- Production database: NOT accessed
- Decision: client-ID facts recorded; execution/submission remains NOT APPROVED due unresolved ambiguous-timeout recovery.

## 1. Support-confirmed client ID constraints

For `POST /api/v2/futures/order`, `newClientOrderId`:

- Provider hard maximum: **255 characters**.
- Provider applies **no regex validation**.
- Recommended charset: `[A-Za-z0-9_-]`.
- Recommended lengths: 36 or 64 characters.
- No additional restrictions, normalization, or reserved prefixes were reported.
- Support explicitly states USDT-M and USDC-M constraints are not the same, but gives no USDC-M-specific values. Do not apply the USDT-M values to USDC-M.

Local conservative policy: use the provider-recommended charset and cap generated IDs at 64 characters, with deterministic IDs derived from canonical intent identity. This local cap is not represented as the provider's hard maximum.

## 2. Uniqueness and duplicate submissions

Support states uniqueness is order-level, IDs cannot be reused after FILLED/CANCELED/REJECTED or other listed terminal outcomes, and the behavior is the same for USDT-M/USDC-M and regular/other order types. However, the same reply says constraints differ between USDT-M and USDC-M; that ambiguity is recorded without inferring identical format constraints.

For duplicate POST requests, support says the repeated request is rejected, does not return the original order result, and labels this an idempotency guarantee. Operationally this is **not replay semantics**: an `ORDER_DUPLICATED` response after a timeout cannot be treated as the original response or as proof of the original order's final status. Never blindly retry an ambiguous request.

## 3. Lookup and recovery after timeout

Support states that after a successful submission the order will subsequently be queryable using `GET /api/v2/futures/order` and `origClientOrderId`, but gives no maximum propagation delay. Most importantly, support explicitly states **no official recovery procedure is specified** when a timed-out POST is followed by `NO_SUCH_ORDER`.

Therefore:

- `NOT_FOUND` after a previous or possibly accepted attempt is not permission to submit again.
- Keep the intent/client ID claim permanently held in `SUBMISSION_OUTCOME_UNKNOWN` / `RECONCILIATION_REQUIRED` until independently authoritative evidence resolves it.
- Do not automatically retry; no bounded wait can be inferred because no propagation bound was supplied.
- A duplicate-ID error does not return the original order result.

## 4. History endpoint

Support states `GET /api/v2/futures/history-orders`:

- Does not include orders that failed to be created (for example, idempotency checks or insufficient assets).
- Does not support direct query by client order ID; retrieval is via `orderId` and pagination.
- Retains order records for six months and sorts them by time.
- Support did not confirm pagination completeness guarantees sufficient for exhaustive reconstruction, nor an exhaustive client-ID recovery procedure after timeout.

History scanning may support manual investigation but is not a documented exhaustive recovery algorithm and must not unlock automatic retry.

## 5. Enforced implementation decision

- Client ID constraints: support-confirmed for USDT-M; local generated ID cap 64 and conservative recommended charset.
- USDC-M ID format policy: NOT VERIFIED; no values inferred.
- First-time submission: still disabled in this adapter until the end-to-end execution boundary, atomic durable claim, authorization, provider adapter, and outcome-evidence path are verified together.
- Ambiguous submission/timeout recovery: NOT RESOLVED; automatic retry is prohibited.
- `NOT_FOUND` after a possibly accepted submission: remains blocked indefinitely absent authoritative evidence; do not clear the claim.
- CI/offline tests are not live order evidence.

## Source record

Primary source: Toobit Support ticket #20261012000242, written reply 2026-10-13 11:04:32, reproduced by the project owner in the engineering conversation. Public API references: https://api-docs.toobit.com/api/usdt-m-api-v2 and https://api-docs.toobit.com/api/usdt-m-error-codes.html
