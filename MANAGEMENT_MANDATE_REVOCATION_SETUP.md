# Management Mandate Revocation Authority — Runtime Contract

## Security model

- The management authority exclusively holds the Ed25519 private signing key.
- ArundaTrader holds only the trusted Ed25519 public key, encoded as standard Base64 raw 32-byte public-key material.
- Each final order-attempt evaluation fetches a fresh status from the configured HTTPS endpoint. Status is never inferred from the original standing mandate or a cached report.
- Missing configuration/source, transport errors, redirects, oversized/malformed responses, invalid signatures, unexpected source IDs, mismatched mandate IDs, stale/future timestamps, and REVOKED status all block the attempt.

## Required environment

- `ARUNDA_MANDATE_STATUS_URL`: absolute HTTPS endpoint serving one signed status object.
- `ARUNDA_MANDATE_STATUS_SOURCE_ID`: exact expected source ID contained in the signed object.
- `ARUNDA_MANDATE_STATUS_PUBLIC_KEY_B64`: Base64-encoded raw 32-byte Ed25519 public key from the management authority.

Do not put the private key in this repository, the trading process, environment of the trading process, or its logs. Provision the public key through the deployment's trusted configuration channel. The endpoint and public key are not yet provisioned in the current environment; leave execution disabled until they are.

## Signed response schema

The endpoint must return exactly these six fields:

```json
{
  "schema_version": "1",
  "mandate_id": "REAL-PROD-MANDATE-001",
  "status": "ACTIVE",
  "observed_at": "2026-10-16T07:00:00+00:00",
  "source_id": "management-authority-prod",
  "signature": "<base64 Ed25519 signature>"
}
```

The signature is calculated over the UTF-8 bytes of the JSON object containing the first five fields (excluding `signature`), serialized with lexicographically sorted keys, separators `,` and `:` without spaces, and `ensure_ascii=False`. The signed values must be exact and case-sensitive. `status` is `ACTIVE` or `REVOKED`.

Runtime freshness policy: maximum age 30 seconds; maximum accepted clock lead 5 seconds. Redirects are rejected, request timeout is 3 seconds, and the response cap is 16 KiB.

## Verification

Offline contract tests cover valid ACTIVE, REVOKED, invalid signature, stale observation, missing source, mismatched mandate ID, future timestamp, missing public key, and unexpected source ID. Passing offline CI verifies the contract implementation only; it does not prove the authority service is deployed or the runtime environment configured.
