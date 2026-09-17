# ARUNDA TRADER — MANAGEMENT ROADMAP

## AUTHORITY
This document records the Management-approved strategic path for completing the exchange-agnostic Core before any exchange binding or real-capital deployment.

## PRIMARY OBJECTIVE
Complete and prove the trading system independently of Toobit or any other exchange, through a deterministic Trade-Ready / Pre-Execution boundary.

The Core must remain portable. Exchange-specific work is a later integration phase and must not be allowed to block completion of the exchange-agnostic Core.

## APPROVED ROADMAP

### PHASE A — EXCHANGE-AGNOSTIC CORE

REAL MARKET DATA
→ ANALYSIS
→ OPPORTUNITY
→ SIGNAL
→ SCORE
→ DECISION
→ RISK
→ POSITION SIZE
→ TRADE GATE
→ TRADE INTENT
→ PRE-EXECUTION READY
→ EXECUTION-READY PACKAGE

This phase is completed without requiring a live exchange account, live exchange balance, private exchange API, signature, order submission, or real trading capital.

Capital and portfolio requirements inside the Core must use provider-neutral abstractions/contracts. They must not be hardwired to Toobit or any exchange.

### PHASE B — PROJECT VERIFICATION / RELEASE PREPARATION

After the complete Core path reaches Trade-Ready:

PROJECT VERIFICATION
→ FULL TEST / CONTROLLED VERIFICATION
→ CLEANUP
→ CONTRACT / BOUNDARY REVIEW
→ DOCUMENTATION SYNC
→ PACKAGE
→ SERIOUS PORTABLE BACKUP

The backup is the ready-to-carry project state. If the exchange or deployment environment changes later, the Core remains intact and only the provider/exchange boundary is adapted.

### PHASE C — EXCHANGE BINDING

Only after Phase A and Phase B are complete:

EXCHANGE ADAPTER
→ PUBLIC / ACCOUNT / BALANCE / CONSTRAINT SOURCES
→ PRIVATE API INTEGRATION
→ SIGNATURE / AUTHENTICATION
→ EXCHANGE-SPECIFIC VALIDATION
→ READ-ONLY / CONTROLLED TESTS

Toobit is one possible adapter/environment, not a prerequisite for Core completion.

### PHASE D — CONTROLLED REAL TEST

Only after exchange binding has itself been implemented and tested:

EXCHANGE VERIFIED
→ MANAGEMENT AUTHORIZATION
→ USER PROVIDES REAL CAPITAL
→ CONTROLLED REAL TEST
→ REAL OBSERVATION
→ RESULT VALIDATION

Real capital is intentionally deferred until this phase. No Builder should request or require user capital during Phase A merely to complete the Core.

## CAPITAL RULE

The absence of live exchange Account/Balance data is NOT a blocker for the exchange-agnostic Core roadmap.

Do not:
- request real capital for Core development
- treat Toobit Account/Balance availability as a prerequisite for Trade-Ready Core completion
- promote `capital_config.py` TEST/LEGACY values to production
- invent synthetic capital or portfolio values
- hardcode fixed-15 capital/sizing
- bypass provenance or fail-closed controls

When the project reaches Phase C, exchange-specific Account/Balance binding is implemented and tested at that time.

## TOOBIT RULE

The known Toobit `-1022 INVALID_SIGNATURE` condition is a future exchange-binding issue. It does not define the architecture or frontier of the exchange-agnostic Core.

Do not move the condition into Core and do not reopen its diagnostics unless Management explicitly authorizes exchange-binding work.

## BUILDER HANDOFF RULE

Every new Builder/Manager session must read this roadmap together with:
- PROJECT_STATE.md
- ARCHITECTURE.md
- CHECKPOINTS.md
- CURRENT_FRONTIER.md
- BUILDER_PROTOCOL.md

The Builder must continue from the active frontier while preserving this roadmap.

Do not reinterpret the deferred capital phase as a current blocker.
Do not start exchange binding before the Core and package phases are complete.

## CURRENT STRATEGIC FRONTIER

Continue the exchange-agnostic Core toward:

TRADE INTENT → PRE-EXECUTION READY → EXECUTION-READY PACKAGE

Then verify, clean, package, and back up the project before beginning exchange binding.

# END MANAGEMENT ROADMAP
