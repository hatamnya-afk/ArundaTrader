# ARUNDA TRADER — CURRENT FRONTIER

## MANAGEMENT DIRECTIVE
The exchange-agnostic Core must be completed before exchange binding and real-capital deployment. Lack of a live exchange Account/Balance source is NOT a blocker for completing the Core.

Authoritative roadmap: `MANAGEMENT_ROADMAP.md`

## CURRENT FRONTIER
Continue the Core toward:

TRADE INTENT → PRE-EXECUTION READY → EXECUTION-READY PACKAGE

Then:

PROJECT VERIFICATION → FULL TEST / CLEANUP → PACKAGE → SERIOUS PORTABLE BACKUP

Only after that:

EXCHANGE BINDING → EXCHANGE-SPECIFIC TESTS → MANAGEMENT AUTHORIZATION → USER CAPITAL → CONTROLLED REAL TEST

## CLOSED STATE
CP38 = CLOSED / VERIFIED / PASS (with CP38-B = DESIGN PASS as previously recorded)
CP39 = CLOSED / VERIFIED / PASS
CP40 = CLOSED / VERIFIED
CP41 = CLOSED / VERIFIED / PASS

Closed checkpoints are historical truth and are not to be re-audited without a demonstrated regression.

## CP42 — CORRECTED INTERPRETATION
CP42 inspected production-source binding requirements. Its earlier conclusion treated absence of a live exchange Account/Balance producer as a blocker for the Core. Management has now explicitly corrected that interpretation.

The Core does NOT require a live exchange account, exchange balance, private API, signature, or real capital in order to progress through the exchange-agnostic Trade-Ready path.

Capital/portfolio requirements inside Core must be represented through provider-neutral abstractions/contracts. Exchange-specific Account/Balance binding belongs to the later Exchange Binding phase.

Therefore the known Toobit `-1022 INVALID_SIGNATURE` condition is NOT the current Core frontier. It remains a future exchange-binding issue.

## CAPITAL RULE
Real capital is intentionally deferred until the exchange-binding phase has been implemented and tested.

During Core development:
- do not request user capital
- do not require a live exchange Account/Balance source
- do not promote `capital_config.py` TEST/LEGACY values to production
- do not use synthetic/fabricated/fallback capital
- do not hardcode fixed-15 capital/sizing

When exchange binding becomes current, Account/Balance and related exchange constraints are implemented and tested at that stage.

## CORE BOUNDARY
The following remain provider-neutral and must remain exchange-agnostic:

REAL MARKET DATA → ANALYSIS → OPPORTUNITY → SIGNAL → SCORE → DECISION → RISK → POSITION SIZE → TRADE GATE → TRADE INTENT → PRE-EXECUTION READY

No Toobit/private API, signature, order write, execution authorization, order submission, real trade, or production DB write is part of this Core frontier.

## CURRENT STRATEGIC OBJECTIVE
Build the complete independent trading engine to a verified Trade-Ready / Pre-Execution boundary, then prepare a clean portable release package and serious backup before connecting any exchange.

## BUILDER INSTRUCTION
Every new Builder/Manager session must read `MANAGEMENT_ROADMAP.md` first as the strategic routing document, together with:
- PROJECT_STATE.md
- ARCHITECTURE.md
- CHECKPOINTS.md
- CURRENT_FRONTIER.md
- BUILDER_PROTOCOL.md

The Builder must follow the roadmap literally. Do not reinterpret deferred real capital as a current blocker. Do not start exchange binding before Core completion, verification, cleanup, packaging, and backup.

# END CURRENT FRONTIER
