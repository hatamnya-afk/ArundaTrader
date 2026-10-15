# Standing-mandate journal — service configuration and operational path review

Status: **candidate implementation / not deployed to the operational host**  
Scope: durable authorization lifecycle only. This is not an execution enablement or order-submission instruction.

## Canonical location

The Windows configuration script defaults to:

`C:\ProgramData\ArundaTrader\security\standing_mandate_lifecycle.jsonl`

This is a persistent service-data location, separate from the Git checkout and trading database. The sibling lock file is created by the append-only store when the first authorized lifecycle event is appended.

Do not put the journal in a temporary directory, source-control checkout, or a path that is routinely cleaned. Do not commit the journal or copy it into chat. Backups must preserve append-only history and access restrictions; restore must be validated before service start.

## Configure the host (Windows, elevated PowerShell)

First identify the **actual Windows identity that runs the ArundaTrader process**. Do not assume a service name or use an interactive account if the scheduled/service process runs as another identity. The repository does not establish whether the host uses a Windows service, Task Scheduler, or a manually started process.

Run from the repository checkout after verifying the identity:

```powershell
.\ops\Configure-ArundaMandateJournal.ps1 -ServiceIdentity 'DOMAIN\service-account'
```

Replace the placeholder with the exact service/task identity. The script:
- creates only the protected parent directory;
- grants full access to SYSTEM and local Administrators and Modify access to the specified runtime identity;
- sets machine-level `ARUNDA_MANDATE_LIFECYCLE_PATH`;
- does **not** create, truncate, activate, revoke, or repair the journal.

The script uses `SupportsShouldProcess`; use `-WhatIf` first to inspect intended changes. Then run without `-WhatIf` from an elevated session. Restart the actual service/process after configuration so it inherits the machine environment. Confirm the service/task identity and effective ACLs independently.

## Initial activation is a separate management action

The configuration script intentionally does not seed an activation event. The journal must be initialized from the already-authorized management phase-entry record through the validated management boundary and `record_management_phase_entry`. Do not hand-edit JSONL, copy a test mandate ID, or fabricate issue/expiry timestamps. No expiry is required by default; an expiry is included only if management explicitly set one.

The canonical decision record currently identifies authorization on 2026-10-12, REAL_PRODUCTION, TOOBIT, SPOT + FUTURES, and ZERO_INITIAL_CAPITAL. It does not itself define a durable runtime journal path or an OS service identity. Those deployment facts must be verified on the host.

## Read-only startup preflight

After the authoritative activation event is persisted, run:

```powershell
$env:ARUNDA_MANDATE_LIFECYCLE_PATH = 'C:\ProgramData\ArundaTrader\security\standing_mandate_lifecycle.jsonl'
python .\standing_mandate_service_preflight_v0_1.py --mandate-id '<exact active mandate ID>'
```

Expected success is `MANDATE_SERVICE_PREFLIGHT=PASS`. A missing path, missing/corrupt journal, invalid lifecycle, or inactive identity returns a nonzero exit and must block startup. The preflight is read-only and makes no provider or database calls. The per-attempt boundary separately rereads the journal, so a revocation/replacement after startup also blocks subsequent attempts.

## Operational execution path audit

- Operational branch: `operational-main-20261007`.
- Its `arunda_pipeline.py` imports the legacy provider-neutral `exchange_execution_boundary.execute_order`; this candidate PR does not wire the new attempt boundary into the operational pipeline.
- Operational `execution_authorization_boundary_v0_1.py` does not yet consume durable lifecycle events.
- Candidate PR #38's isolated `exchange_execution_order_attempt_boundary_v0_1.py` now requires the durable journal before technical authorization, but this is not evidence that the operational path calls it.
- The operational Toobit adapter is read-only and advertises `order_submission=False`. No production submit path, runtime environment, service identity, or host ACL has been verified by this repository-only change.
- Therefore: lifecycle contract + candidate gate are tested; **service deployment and operational execution-path connection remain BLOCKED / NOT VERIFIED**.

## Mandatory safety status

No production runtime, provider write, order/cancel/withdrawal, database write, execution flag change, branch switch, merge, or operational pipeline modification was performed. PR #38 remains open and unmerged. The next promotion step requires explicit repository-governance authorization and a reviewed integration change; this document does not authorize a real order.
