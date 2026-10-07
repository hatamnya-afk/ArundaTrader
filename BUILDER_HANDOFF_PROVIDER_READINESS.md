# BUILDER HANDOFF — PROVIDER READINESS → MAIN

## Status
**MAIN ONLY / STATIC FORENSIC MAP / NO RUNTIME**

This is the next Builder checkpoint after MCP-01 → MAIN selective integration.

## Source of truth
- Canonical branch: `main`
- Authoritative handoff: `MCP01_HANDOFF_TO_MAIN.md`
- Do NOT use `cp46-f-futures-readiness-20261006` as a merge source.
- Do NOT create a new branch.

## Exact objective
Map the already-closed provider-readiness contracts onto MAIN and identify the **minimum** missing boundary. Do not implement anything yet.

Required contracts:
1. CP46-A3: SHORT => Futures; Spot SELL is never SHORT.
2. Provider order translation must use authoritative provider symbol/semantics.
3. Toobit contract/filter evidence must be authoritative.
4. Toobit account evidence must be authoritative; balance is not permission.
5. Open/recent order evidence must be authoritative.
6. Server timestamp must be authoritative.
7. Futures contract/account/exposure evidence must be provider-derived.
8. Provider preflight must fail closed.
9. Quantity provenance remains mandatory.
10. Execution stays OFF.

## Important current finding
A Main-tree search currently finds the legacy files:
- `toobit_provider_preflight_evidence_v0_1.py`
- `test_cp49_toobit_provider_preflight_evidence_v0_1.py`

The following authoritative CP46-D/F/provider modules were **not found on MAIN by exact-name/code search** and must therefore be mapped before any copy/implementation decision:
- `cp46_d_production_provider_preflight_v0_1.py`
- `cp46_d_provider_execution_handoff_v0_1.py`
- `execution_venue_routing_policy_v0_1.py`
- `provider_order_translation_v0_1.py`
- `provider_preflight_v0_1.py`
- `execution_quality_v0_1.py`
- `exchange_execution_contract.py`

This is a **finding, not permission to copy them**.

## Required PowerShell commands
Run from the local MAIN workspace:

```
pwd
git branch --show-current
git status --short
git log -1 --oneline
git remote -v
git ls-tree -r --name-only HEAD | Select-String -Pattern 'provider|toobit|execution_quality|routing|translation|preflight|exchange_execution'
git grep -n -E 'SHORT|FUTURES|Spot SELL|venue|routing|provider_order|contract|filters|account|open.?orders|recent.?orders|server.?timestamp|exposure|fail.?closed|quantity_source|position_quantity|trade_event_id|exchange_order_id' -- '*.py'
git grep -n -E 'TRADE_READY|ORDER_INTENT|CANONICAL_ORDER|EXECUTION_QUALITY|PROVIDER_PREFLIGHT|EXECUTION_BOUNDARY|assert_execution_disabled|bind_authoritative_decision_birth|emit_mcp01_evidence' -- arunda_pipeline.py
```

Read-only comparison against the divergent source branch, only if needed:

```
git show 26b73995cc0f51946af13cfe1574dc28bddf2173:cp46_d_production_provider_preflight_v0_1.py
git show 26b73995cc0f51946af13cfe1574dc28bddf2173:cp46_d_provider_execution_handoff_v0_1.py
git show 26b73995cc0f51946af13cfe1574dc28bddf2173:execution_venue_routing_policy_v0_1.py
git show 26b73995cc0f51946af13cfe1574dc28bddf2173:provider_order_translation_v0_1.py
git show 26b73995cc0f51946af13cfe1574dc28bddf2173:provider_preflight_v0_1.py
git show 26b73995cc0f51946af13cfe1574dc28bddf2173:execution_quality_v0_1.py
git show 26b73995cc0f51946af13cfe1574dc28bddf2173:exchange_execution_contract.py
```

## Required output — ONLY forensic map
Return one compact table:

| Contract | MAIN status (PRESENT/PARTIAL/MISSING/BLOCKED) | Exact MAIN file:function | Authoritative source | Gap | Minimum patch |
|---|---|---|---|---|---|

Then list:
- files that MUST change, if any;
- files that MUST NOT change;
- dependencies required only if a patch is approved;
- whether DB mutation would be required;
- whether Runtime would be required later.

## Hard prohibitions
- NO Runtime.
- NO provider API call.
- NO order write.
- NO real trade.
- NO DB mutation.
- NO commit/push of code.
- NO branch creation/switch.
- NO merge/rebase/cherry-pick.
- NO wholesale copy from CP46-F.
- NO strategy/Decision/Risk/Trade-Gate redesign.
- Do not reopen CLOSED/VERIFIED checkpoints.
- Do not fix missing contracts by inventing evidence or generic calculations.

## Stop condition
Stop immediately after the forensic map. Management must approve the minimum patch before Builder changes any provider-readiness code.
