# Independent Management Authority — Deployment Runbook

## Purpose and isolation

Deploy this service as a **separate service/runtime and trust boundary** from ArundaTrader. This directory contains source only; it must never contain generated private keys, admin tokens, production state, or secret values. Do not deploy the service inside the trader process or mount authority secrets into the trader host/container.

The public GET endpoint is authenticated cryptographically: HTTPS protects transport and the response's Ed25519 signature authenticates the exact status payload to the trader's pinned public key. The status GET intentionally requires no bearer token because the existing trader client contract sends no read token. The state-changing PUT endpoint requires a high-entropy operator bearer token and must be reachable only over HTTPS and preferably an operator VPN/allowlist. Do not expose PUT directly to the public internet.

## Required secrets and configuration

- `ARUNDA_AUTHORITY_SOURCE_ID`: stable, exact source identity, e.g. `management-authority-prod`.
- `ARUNDA_AUTHORITY_MANDATE_ID`: exact standing mandate identifier the trader presents.
- `ARUNDA_AUTHORITY_PRIVATE_KEY_FILE`: path to a mounted secret file containing **Base64 of the raw 32-byte Ed25519 private seed**. Default: `/run/secrets/ed25519_private_key_b64`.
- `ARUNDA_AUTHORITY_ADMIN_TOKEN_FILE`: path to a mounted secret file containing a random operator token, no newline. Default: `/run/secrets/authority_admin_token`.
- `ARUNDA_AUTHORITY_STATE_FILE`: persistent writable state path. Default: `/var/lib/arunda-authority/status.json`.

Initialize the persistent state file to exactly `{"mandate_id":"<exact mandate ID>","status":"REVOKED"}` before first start. Start REVOKED; switch to ACTIVE only after an explicit management decision. Keep the state volume durable and restrict it to the service identity. Back up and monitor the audit log without exposing reasons or tokens to public clients.

## Key ceremony (offline, trusted workstation)

1. Generate an Ed25519 keypair on a trusted administrative workstation or HSM/KMS that supports Ed25519 signing. Never generate production keys in CI or in the trader environment.
2. If using the file-backed implementation, export the 32-byte private seed once, Base64-encode it, and deliver it directly to the authority host's secret manager/mounted secret file through a secure channel. Do not paste it into chat, source control, CI variables, issue comments, or logs. Restrict read access to the authority service identity and authorized key custodians.
3. Derive/export the 32-byte raw public key and Base64-encode it. Transfer the public key independently through the trusted trader deployment configuration channel as `ARUNDA_MANDATE_STATUS_PUBLIC_KEY_B64`.
4. Record the public-key fingerprint, source ID, mandate ID, custodian, creation date, and recovery/rotation procedure in the organization's secret inventory. Private key must never be copied to ArundaTrader.
5. The initial implementation loads a file-backed key. For production, prefer an HSM/KMS signing adapter where supported; do not assume this filesystem implementation provides hardware-backed key protection.

Example key generation is intentionally not automated by the web service. Use a vetted offline ceremony/tooling and securely erase temporary private material after verified transfer.

## Network and container deployment

- Build from this directory and deploy as a distinct service with one worker (in-process locking is not a distributed lock).
- Mount the private-key and admin-token secrets read-only; mount the state directory as a persistent writable volume. Never bake secrets into the image.
- Put a TLS-terminating reverse proxy or managed HTTPS ingress in front. Enforce TLS 1.2+; do not trust arbitrary forwarded headers. Restrict `PUT /v1/mandate-status` at the ingress/network layer to the operator network.
- Run as the unprivileged container user; apply resource limits, image scanning, log redaction, patching, monitoring and backups.
- Use `GET /healthz` for liveness only. Use `GET /readyz` for readiness: it checks configured source/mandate identity, parseable state matching the configured mandate, and a loadable Ed25519 private key. It returns only a generic ready/not-ready result, never the mandate status or secret details. Readiness does not mean the mandate is ACTIVE and does not authorize trading.
- Do not run multiple service replicas against this file-backed state without replacing the in-process lock with a transactional shared store and concurrency control.
- Validate ownership and write/fsync permissions on the mounted state volume as the container's unprivileged UID; Dockerfile ownership of the image directory does not guarantee ownership of a runtime-mounted volume.

## API

### Liveness and readiness

- `GET /healthz`: process liveness only; it does not inspect state or secrets.
- `GET /readyz`: readiness check for identity configuration, valid matching state, and loadable signing key. A 200 response means the service can serve a signed status; it does **not** mean the mandate is ACTIVE or that trading is authorized. A 503 response must keep the service out of rotation.

### Read current signed state

`GET /v1/mandate-status`

Returns exactly the fields expected by ArundaTrader:
```json
{
  "schema_version": "1",
  "mandate_id": "REAL-PROD-MANDATE-001",
  "status": "REVOKED",
  "observed_at": "2026-10-16T07:00:00+00:00",
  "source_id": "management-authority-prod",
  "signature": "<Base64 Ed25519 signature>"
}
```

The signature covers the first five fields serialized as UTF-8 JSON with sorted keys, separators `,` and `:` and no spaces, matching `management_mandate_revocation_runtime_v0_1.py`. `observed_at` is freshly generated on each GET. The application sends `Cache-Control: no-store, max-age=0` and `Pragma: no-cache`; ingress/CDN configuration must preserve these headers and must not cache this endpoint.

### Set state (operator-only)

`PUT /v1/mandate-status`

Headers: `Authorization: Bearer <operator token>`, `Content-Type: application/json`.

Body:
```json
{"status":"REVOKED","reason":"Operator initiated revocation after review"}
```

Allowed statuses are exactly `ACTIVE` and `REVOKED`. A reason of 8–500 characters is required and written to the authority audit log. Return payload never includes the reason or token. Invalid/missing credentials are rejected. Treat the operator token as a secret; rotate it after suspected exposure.

The audit request is durably appended before state mutation. A failed audit append prevents the state change. State is written to a same-directory temporary file, flushed/fsynced, atomically replaced, then the parent directory is fsynced. If the process fails after the audit append but before the state transition completes, the audit can contain a request that did not become current state; reconcile audit entries against the signed current state rather than treating a request record as proof of a completed transition. If directory fsync fails after replacement, the caller can receive a generic 503 even though the replacement may already be visible; read the current signed status before retrying to avoid assuming the transition did not occur.

## Trader-side configuration and acceptance gate

Only after the authority is deployed behind verified HTTPS:

- `ARUNDA_MANDATE_STATUS_URL=https://<verified-authority-host>/v1/mandate-status`
- `ARUNDA_MANDATE_STATUS_SOURCE_ID=<exact ARUNDA_AUTHORITY_SOURCE_ID>`
- `ARUNDA_MANDATE_STATUS_PUBLIC_KEY_B64=<Base64 raw 32-byte public key>`

Verify from the trader's actual deployment identity: valid signature; exact source and mandate IDs; timestamp age at most 30 seconds and future skew at most 5 seconds; response size under 16 KiB; no redirects; TLS certificate/hostname validation; correct ACTIVE permits only this gate to continue; REVOKED, missing/malformed configuration, timeout, unavailable service, invalid signature, stale timestamp, wrong identity, or any unrecognized status blocks the attempt. Do not disable TLS verification or loosen freshness to make a test pass.

## Key rotation and incident response

Use a planned dual-key migration in the trader verifier before rotating keys; the current verifier accepts one pinned public key only. Until dual-key support is implemented and deployed, a key rotation is a controlled maintenance event: stop order attempts, provision and verify the new public key through trusted configuration, then resume only after independent verification. If the private key or operator token may be compromised, revoke immediately through a trusted operator channel, isolate the service, preserve audit evidence, rotate credentials, and keep order execution disabled until the new trust chain is verified.

## Current status

**DESIGNED / NOT DEPLOYED / NOT VERIFIED.** A source commit or passing offline tests does not create a live service, TLS endpoint, trusted key, operator authentication deployment, or production authorization. Do not enable execution based on this runbook alone.
