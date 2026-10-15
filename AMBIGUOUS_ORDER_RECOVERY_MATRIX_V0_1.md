# Ambiguous Order Recovery Matrix v0.1

- Date: 2026-10-12
- Scope: offline policy and isolated temporary SQLite tests only
- Branch: `fix/atomic-intent-claim-store-20261012`
- Related PR: https://github.com/hatamnya-afk/ArundaTrader/pull/31
- Live API / order actions: NOT performed
- Production database: NOT accessed or modified
- Pipeline wiring / execution authorization: NOT changed

## Purpose

Exercise the safety boundary when an order submission or lookup is ambiguous. This suite is not evidence that Toobit's API has strong consistency, durable client-ID uniqueness, exactly-once POST semantics, or exhaustive history recovery.

## Cases covered

1. No lookup result after a prior attempt.
2. Lookup transport timeout.
3. Provider lookup error.
4. Explicit `NO_SUCH_ORDER` / `NOT_FOUND` after a prior attempt.
5. Order found after an ambiguous submission.
6. Found terminal statuses: `FILLED`, `CANCELED`, and `REJECTED`.
7. Client-order-ID mismatch.
8. Missing exchange order ID.
9. Multiple matches.
10. Unknown local attempt history.
11. Durable claim persists through unknown outcome and NOT_FOUND.
12. Same client ID cannot be claimed for a different intent in the same provider namespace.
13. Concurrent claims for the same intent yield one durable claim and idempotent local replays.
14. A pure reconciliation precheck never grants submit or retry permission.

## Interpretation

- `NOT_FOUND` is not proof that an earlier submission was not accepted.
- A found order, including a terminal order, is evidence to reconcile, not permission to resubmit.
- Unknown/mismatched/multiple evidence remains blocked or requires reconciliation.
- Local SQLite uniqueness protects local claims only. It does not prove provider-side uniqueness or prevent duplicate orders caused by behavior outside this contract.
- The test suite deliberately does not implement speculative history scanning or declare history pagination exhaustive; those semantics require provider documentation or written confirmation.

## Verification record

CI status must be recorded from the GitHub Actions run associated with the commit containing this matrix. A successful offline suite is not a live-provider test and does not authorize execution.
