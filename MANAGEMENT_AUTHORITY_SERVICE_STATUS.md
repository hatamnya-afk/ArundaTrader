# Management Authority Service — Frontier Record

Date: 2026-10-16  
Operational branch: `operational-main-20261007`

## Status

- **BUILT (source artifacts):** independent Ed25519 authority API source, container definition, dependency manifests, deployment/security runbook, secret/runtime-state ignore rules, and offline contract tests under `management_authority_service/`.
- **NOT VERIFIED:** deployment, durable state initialization, production secret delivery, HTTPS endpoint, trusted public key, operator network restrictions, TLS behavior, and real trader-to-authority handshake.
- **CURRENT FRONTIER:** deploy the authority as a separate service, verify the response from the trader's actual runtime network, provision the public key and endpoint through trusted configuration, and confirm valid ACTIVE/REVOKED handling without placing private key material in ArundaTrader.
- **BLOCKED:** real order attempts and all production execution remain closed until the authority deployment and every existing phase-entry gate are independently verified.

## Implemented service contract

- Read endpoint: `GET /v1/mandate-status`; returns the exact six-field Ed25519 signed schema already consumed by `management_mandate_revocation_runtime_v0_1.py`.
- State-change endpoint: `PUT /v1/mandate-status`; requires an operator bearer token from a mounted secret file, strict request schema, an explicit reason, and writes state/audit evidence.
- Signing private seed and operator token are read from secret files external to source control. No key-generation endpoint or private-key export endpoint exists.
- Initial state must be initialized as `REVOKED`. Status is never assumed ACTIVE when configuration/state/key is missing.
- Service is intended for separate deployment, one worker, persistent restricted state volume, TLS reverse proxy/managed ingress, and network restrictions on PUT.

## Verification boundary

Offline unit tests and CI can validate serialization/signature compatibility and operator authentication only. They do not establish a running deployment or production trust. The trader's 30-second freshness limit means intermediary caches must be disabled. Public key, source ID, and endpoint must be provisioned from verified authority metadata, not invented.

## Explicit non-actions

- No repair branch was merged.
- No order, cancellation, production runtime, exchange write, database write, or execution switch activation occurred.
- No production endpoint, source ID, keypair, or private key was fabricated.
- Keep `EXECUTION_ENABLED`, `ORDER_SUBMISSION_ENABLED`, and all provider write controls disabled until independent deployment verification is recorded.
