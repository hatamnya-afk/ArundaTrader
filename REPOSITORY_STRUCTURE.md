# ARUNDA TRADER — REPOSITORY STRUCTURE

## Purpose
This document defines how the synchronized Local project is organized in GitHub without changing the Local original project's filesystem paths.

## Source-of-truth rule
- Local Original: `C:\Users\ASUS\ArundaTrader` remains the primary operational/recovery object.
- GitHub: durable project-management, state, provenance, and Builder-handoff source.
- `main`: canonical project lineage.
- `sync/local-project-20260917`: controlled consolidation branch only until Management accepts canonical promotion.

## Canonical classes

### 1. Governance / Management
Authoritative project-control files remain at repository root because existing Builder workflows and references depend on their paths:
- `PROJECT_STATE.md`
- `ARCHITECTURE.md`
- `CHECKPOINTS.md`
- `CURRENT_FRONTIER.md`
- `BUILDER_PROTOCOL.md`
- `MANAGEMENT_ROADMAP.md`
- `MANAGEMENT_APPROVAL_CP44.md`
- `ARUNDA_RUNTIME_ANCHOR_AND_BUILDER_HANDOFF.md`
- `LOCAL_SYNC_MANIFEST.json`
- `REPOSITORY_STRUCTURE.md`

Do not relocate these files without an explicit governance migration.

### 2. Operational Source
The synchronized Python/source files that implement the established ArundaTrader runtime remain at their existing paths.

**Important:** do not mass-move operational modules into invented folders. Import paths, runtime entry points, scripts, and external tooling must be audited before any source relocation.

### 3. Verification / Tests
Tests and verification assets are conceptually classified as verification material. Existing paths are preserved until dependency/path analysis authorizes a physical move.

See `tests/README.md`.

### 4. Evidence / Forensic
Forensic scripts, diagnostic reports, inspection utilities, and historical validation artifacts are evidence/analysis material, not automatically operational truth.

Existing synchronized paths are preserved for provenance. They are not promoted into the operational contract merely because they exist in the snapshot.

See `evidence/README.md`.

### 5. Historical / Archive
Historical artifacts, old repairs, backup-derived material, and obsolete investigation outputs are not current project truth.

The Local copies remain untouched. GitHub synchronization excludes the known Local backup/quarantine/archive classes listed in `LOCAL_SYNC_MANIFEST.json`.

See `historical/README.md`.

### 6. Local-only protected material
The following remain Local-only and must not be casually promoted to GitHub:
- production databases
- database journals
- backup databases
- archives
- `.bak` / `.tmp` artifacts
- credentials or secrets
- quarantine material

## Current runtime boundary
The active project frontier is CP44. The established upstream boundary is **ELIGIBLE**; the latest controlled runtime observation recorded by Management is **6 ELIGIBLE assets**.

Forward route:
`ELIGIBLE → RISK → TRADE GATE → TRADE READY / ORDER INTENT READINESS → CONTROLLED EVIDENCE`

## Safety
- `EXECUTION AUTHORIZATION = FALSE`
- Order write forbidden.
- Database write forbidden.
- Withdrawal forbidden.
- `arunda_pipeline.py` protected.
- No upstream rebuild/re-design/re-audit solely to reproduce the observed ELIGIBLE state.

## Organization rule
Organization means **classification + discoverability + provenance first**. Physical relocation is allowed only after dependency/path audit proves that the move is behavior-neutral.

# END REPOSITORY STRUCTURE
