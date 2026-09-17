# ArundaTrader

Modular, layered, exchange-agnostic real-market analysis and trading-decision system.

## Start here

A new Builder/Manager must read these files in order:

1. [`PROJECT_STATE.md`](PROJECT_STATE.md)
2. [`ARCHITECTURE.md`](ARCHITECTURE.md)
3. [`CHECKPOINTS.md`](CHECKPOINTS.md)
4. [`CURRENT_FRONTIER.md`](CURRENT_FRONTIER.md)
5. [`BUILDER_PROTOCOL.md`](BUILDER_PROTOCOL.md)
6. [`MANAGEMENT_ROADMAP.md`](MANAGEMENT_ROADMAP.md)
7. [`REPOSITORY_STRUCTURE.md`](REPOSITORY_STRUCTURE.md)

## Current frontier

**CP44 — REAL-MARKET CONTROLLED TEST**

Latest controlled runtime observation: **6 assets reached ELIGIBLE**.

This is runtime evidence, not a CP44 closure claim.

Forward route:

`ELIGIBLE → RISK → TRADE GATE → TRADE READY / ORDER INTENT READINESS → CONTROLLED EVIDENCE`

## Safety

- `EXECUTION AUTHORIZATION = FALSE`
- Order write is forbidden.
- Database write is forbidden.
- Withdrawal is forbidden.
- No exchange write or execution is authorized by repository synchronization.
- `arunda_pipeline.py` is protected.

## Source-of-truth model

The Local Original at `C:\Users\ASUS\ArundaTrader` remains the primary operational/recovery object.

GitHub is the controlled durable project-management, state, provenance, and Builder-handoff source.

Repository organization is intentionally conservative: operational source paths are preserved until dependency/path analysis proves a physical relocation safe.

## Repository organization

- Governance: root control documents
- Operational source: existing project paths preserved
- Verification: `tests/`
- Evidence/forensic: `evidence/`
- Historical/archive: `historical/`
- Structure rules: `REPOSITORY_STRUCTURE.md`

The synchronized Local snapshot excludes production databases, database journals, backups, archives, temporary binaries, and quarantine material according to `LOCAL_SYNC_MANIFEST.json`.

# END ARUNDA TRADER
