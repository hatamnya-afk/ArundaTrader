# Toobit Futures client-order-ID evidence record

- Evidence record version: 0.2
- Reviewed: 2026-10-12
- Scope: USDT-M/USDC-M Futures **regular order** API v2 only
- Decision: documented API surface verified; execution policy NOT VERIFIED
- Runtime/live API access: NOT performed
- Order submission/cancellation: NOT performed

## Official sources and exact findings

### A. Regular-order submission
Source: https://api-docs.toobit.com/api/usdt-m-api-v2
Section: “New regular order (TRADE)”, `POST /api/v2/futures/order`, lines 110–123 in the reviewed page.

The parameter table identifies `newClientOrderId` as a mandatory `STRING`, described only as “Client order id”. It does **not** specify a maximum length or permitted character set. Examples are not treated as normative constraints.

### B. Direct order lookup
Source: https://api-docs.toobit.com/api/usdt-m-api-v2
Section: “Get one regular order (USER_DATA)”, `GET /api/v2/futures/order`, lines 459–498.

The request accepts `orderId` or `origClientOrderId` (mutually exclusive). The example response contains `orderId`, `clientOrderId`, and `status`. This establishes the documented lookup interface and response fields, not a guarantee of immediate consistency, indefinite retention, or complete lookup after every terminal state.

### C. Historical order lookup surface
Source: https://api-docs.toobit.com/api/usdt-m-api-v2
Section: “History regular orders (USER_DATA)”, `GET /api/v2/futures/history-orders`, lines 595–639.

The documented history endpoint uses an `orderId` cursor and `limit` (default 20, maximum 1000), plus optional time filters. The documented excerpt does not promise that querying the direct lookup endpoint or one history page provides exhaustive recovery by client ID. Any recovery implementation must account for cursoring/pagination and verify actual endpoint behavior separately.

### D. Duplicate identifier error
Source: https://api-docs.toobit.com/api/usdt-m-error-codes.html
Section: `-1141 ORDER_DUPLICATED`, lines 295–298 in the reviewed page.

The official error catalog says “Duplicate clientOrderId”. This supports that duplicate-ID rejection exists. It does **not** establish that replaying the same POST returns the original order response, that the server guarantees exactly-once effects, or that the ID remains reserved after the order is closed/canceled/filled.

### E. Documented uniqueness scope
Source: https://api-docs.toobit.com/api/usdt-m-account-and-trading
Section: Futures order submission parameter table, line 531 (and repeated at line 735).

The older v1 page describes `newClientOrderId` as “A unique id among open orders”. This is a limited uniqueness scope, not evidence of durable global uniqueness after the order leaves the open-order set. This v1 wording is not silently generalized to all v2 order types.

## Explicitly unresolved — do not guess

1. Maximum client-ID length for the v2 regular-order endpoint.
2. Allowed character set / formal validation regex for the v2 regular-order endpoint.
3. Whether uniqueness is per account, symbol, order type, category, or another scope in v2.
4. Whether the same ID remains reserved after FILLED, CANCELED, REJECTED, or other terminal states.
5. Whether duplicate POST is idempotent replay or merely rejected as duplicate.
6. Whether a timeout followed by `GET /api/v2/futures/order?origClientOrderId=...` is immediately conclusive.
7. Direct-lookup retention, consistency, and behavior for orders no longer open.
8. History pagination completeness and a documented client-ID search capability.

## Enforced decision

The evidence ledger may be marked partially evidence-verified, but the adapter execution policy must remain `verified=false`, with no max length or regex populated. The provider-neutral attempt boundary must fail closed for Toobit until the missing format constraints are established by an authoritative Toobit specification or written confirmation, and the required duplicate/recovery semantics are resolved. An offline test passing is not a substitute for provider guarantees.

## Verification
- Dedicated tests: `test_toobit_client_order_id_policy_v0_1.py`
- Workflow: `.github/workflows/atomic-intent-claim-contract.yml`
- Latest observed CI before this evidence-record-only change: 71 tests passed (offline/fake-transport suite). No live provider request was made.
