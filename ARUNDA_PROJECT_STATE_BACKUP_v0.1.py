from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent

timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_path = BASE_DIR / f"ARUNDA_PROJECT_STATE_BACKUP_{timestamp}.txt"

content = r"""
====================================================================================================
ARUNDA TRADER — PROJECT STATE BACKUP
====================================================================================================

BACKUP TYPE       : PROJECT PATH / STATE / FRONTIER
MODE              : READ ONLY
DATABASE WRITES   : NONE
ENGINE MODIFIED   : NO
PURPOSE           : CROSS-CHAT CONTEXT RECOVERY

====================================================================================================
CORE PROJECT RULES
====================================================================================================

1. DO NOT REBUILD
2. DO NOT RESET
3. DO NOT REDESIGN
4. DO NOT RE-AUDIT VERIFIED CLOSED STAGES FROM ZERO
5. Preserve VERIFIED / CLOSED stages permanently.
6. Distinguish:
   - BUILT
   - VERIFIED
   - CURRENT FRONTIER
   - BLOCKED
   - NEXT ACTION
7. Audit stages must remain READ ONLY unless a later stage explicitly authorizes repair.
8. No synthetic data.
9. No interpolation.
10. No forward fill.
11. No back fill.
12. No look-ahead.
13. No database writes during diagnostic / forensic / reconstruction audits.

====================================================================================================
PROJECT
====================================================================================================

PROJECT NAME       : ArundaTrader
DATABASE           : arunda.db
DATABASE PATH      : C:\Users\ASUS\ArundaTrader\arunda.db
ENGINE             : market_data_engine.py

====================================================================================================
INDICATOR PATH — COMPLETED STAGES
====================================================================================================

----------------------------------------------------------------------------------------------------
STAGE 01
----------------------------------------------------------------------------------------------------

NAME:
FORMULA_COVERAGE_AUDIT_v0.1

STATUS:
CLOSED / VERIFIED

RESULT:
16/16 formulas detected
16/16 database fields present

COVERAGE STATUS:
COMPLETE


----------------------------------------------------------------------------------------------------
STAGE 02
----------------------------------------------------------------------------------------------------

NAME:
INDICATOR_CONVENTION_AUDIT_v0.1

STATUS:
CLOSED / VERIFIED

RESULT:
Convention/source signals successfully inventoried for the indicator layer.

Target indicators include:
EMA20
EMA50
RSI14
MACD
MACD_SIGNAL
MACD_HIST
ATR14
ADX14
BB_MIDDLE
BB_UPPER
BB_LOWER
BB_WIDTH
VOLUME_SMA20
VOLUME_RATIO
VOLATILITY
TECHNICAL_SCORE


----------------------------------------------------------------------------------------------------
STAGE 03
----------------------------------------------------------------------------------------------------

NAME:
INDICATOR_CONVENTION_RECONSTRUCTION_v0.1

STATUS:
CLOSED / VERIFIED

RESULT:
EXPECTED INDICATORS : 16
RECONSTRUCTED       : 16
UNRESOLVED          : 0

RECONSTRUCTION STATUS:
COMPLETE

DATABASE WRITE:
NONE

FORMULA CALCULATION:
NONE


----------------------------------------------------------------------------------------------------
STAGE 04
----------------------------------------------------------------------------------------------------

NAME:
INDICATOR_STANDARD_CONFORMANCE_AUDIT_v0.1

STATUS:
CLOSED / VERIFIED

STANDARD BASELINE:

EMA:
alpha = 2/(period+1)
initial seed = arithmetic mean of first period values
recursive EMA

RSI:
Wilder RSI
arithmetic initial averages
Wilder recursive smoothing

MACD:
12-26-9

ATR:
Wilder ATR

ADX:
Wilder ADX

Bollinger:
20,2

Volume:
SMA20

Volatility:
non-annualized return volatility

RESULT:

CONFORMANT : 13
PARTIAL    : 3
FAIL       : 0

PARTIAL:
EMA20
EMA50
RSI14

All other 13 indicators:
CONFORMANT


----------------------------------------------------------------------------------------------------
STAGE 05
----------------------------------------------------------------------------------------------------

NAME:
INDICATOR_STANDARD_CONVENTION_RECONSTRUCTION_v0.1

STATUS:
CLOSED AS SUPERSEDED / NOT FINAL TRUTH

INITIAL RESULT:

SYMBOLS READY      : 4
TOTAL EXACT        : 0
TOTAL MISMATCH     : 0
TOTAL UNRESOLVED   : 56

RECONSTRUCTION STATUS:
REVIEW_REQUIRED

REASON:
INSUFFICIENT TARGET RESOLUTION

IMPORTANT:
This result must NOT be treated as evidence that indicators match.
Target resolution was insufficient at that point.


----------------------------------------------------------------------------------------------------
STAGE 06
----------------------------------------------------------------------------------------------------

NAME:
INDICATOR_STANDARD_CONVENTION_RESOLUTION_AUDIT_v0.1

STATUS:
CLOSED / VERIFIED

RESULT:

EMA COMPONENTS RESOLVED : 3 / 3
RSI COMPONENTS RESOLVED : 5 / 5
TOTAL COMPONENTS        : 8 / 8

AUDIT STATUS:
RESOLVED

REASON:
ALL TARGET CONVENTION SIGNALS RESOLVED


----------------------------------------------------------------------------------------------------
STAGE 07
----------------------------------------------------------------------------------------------------

NAME:
INDICATOR_STANDARD_CONVENTION_RECONSTRUCTION_v0.2

STATUS:
SUPERSEDED / NON-FINAL RESULT

RESULT:

SYMBOLS READY      : 4
TOTAL EXACT        : 0
TOTAL MISMATCH     : 0
TOTAL UNRESOLVED   : 12

CAUSE:
The selected analysis targets contained NULL stored indicator values.

IMPORTANT:
Do not use this stage as final evidence.
The workflow correctly moved backward to target resolution instead of modifying the database.


----------------------------------------------------------------------------------------------------
STAGE 08
----------------------------------------------------------------------------------------------------

NAME:
INDICATOR_STANDARD_CONVENTION_TARGET_RESOLUTION_AUDIT_v0.1

STATUS:
CLOSED / VERIFIED

DATABASE:
arunda.db

TARGETS:

BTC:
Analysis ID : 847
Source Time : 2026-08-20T10:17:00.000Z
Engine      : MARKET_DATA_CMC_SNAPSHOT_v0.2
Stored EMA20: 71569.40969362899
Stored EMA50: 69966.78842790793
Stored RSI14: 74.61504113462527
Raw CMC ID  : 832
Raw Close   : 72171.6864554891
Price Identity: EXACT

ETH:
Analysis ID : 848
Source Time : 2026-08-20T10:16:00.000Z
Engine      : MARKET_DATA_CMC_SNAPSHOT_v0.2
Stored EMA20: 2277.1506197667823
Stored EMA50: 2222.0347925609094
Stored RSI14: 67.71311000664949
Raw CMC ID  : 833
Price Identity: EXACT

SOL:
Analysis ID : 849
Source Time : 2026-08-20T10:17:00.000Z
Engine      : MARKET_DATA_CMC_SNAPSHOT_v0.2
Stored EMA20: 87.23161534657187
Stored EMA50: 85.32351770994416
Stored RSI14: 66.56623130395164
Raw CMC ID  : 834
Price Identity: EXACT

XRP:
Analysis ID : 850
Source Time : 2026-08-20T10:17:00.000Z
Engine      : MARKET_DATA_CMC_SNAPSHOT_v0.2
Stored EMA20: 1.1467309668203796
Stored EMA50: 1.1172552939512015
Stored RSI14: 74.43952252222653
Raw CMC ID  : 835
Price Identity: EXACT

FINAL:

SYMBOLS CHECKED : 4
READY TARGETS   : 4
BLOCKED TARGETS : 0
RAW TARGETS EXACT: 4

TARGET RESOLUTION STATUS:
READY


----------------------------------------------------------------------------------------------------
STAGE 09
----------------------------------------------------------------------------------------------------

NAME:
INDICATOR_STANDARD_CONVENTION_COMPARISON_AUDIT_v0.1

STATUS:
CLOSED / VERIFIED

LOOKBACK:
120

MIN HISTORY:
60

ACTUAL HISTORY:
64 valid closes per symbol

TOLERANCE:
ABS = 1e-10
REL = 1e-10

RESULT:

BTC:
EMA20 MISMATCH
EMA50 MISMATCH
RSI14 MISMATCH

ETH:
EMA20 MISMATCH
EMA50 MISMATCH
RSI14 MISMATCH

SOL:
EMA20 MISMATCH
EMA50 MISMATCH
RSI14 MISMATCH

XRP:
EMA20 MISMATCH
EMA50 MISMATCH
RSI14 MISMATCH

FINAL:

SYMBOLS CHECKED : 4
TOTAL EXACT     : 0
TOTAL MATCH     : 0
TOTAL MISMATCH  : 12
TOTAL UNRESOLVED: 0
BLOCKED         : 0

COMPARISON STATUS:
DIFFERENCE_DETECTED

CONCLUSION:
CURRENT IMPLEMENTATION DIFFERS FROM STANDARD CONVENTION


----------------------------------------------------------------------------------------------------
STAGE 10
----------------------------------------------------------------------------------------------------

NAME:
INDICATOR_STANDARD_CONVENTION_DIFFERENCE_FORENSIC_AUDIT_v0.3

STATUS:
CLOSED / VERIFIED

IMPORTANT:
v0.1 and v0.2 contained implementation bugs.
v0.3 executed successfully.

ENGINE:

PATH:
C:\Users\ASUS\ArundaTrader\market_data_engine.py

SOURCE SIZE:
34304 characters

SOURCE LINES:
1997

FUNCTION SIGNALS:

EMA FUNCTION    : TRUE
EMA SERIES      : TRUE
RSI FUNCTION    : TRUE

EMA CONVENTION SIGNALS:

EMA ALPHA       : TRUE
EMA SEED        : TRUE
EMA RECURSIVE   : FALSE

RSI CONVENTION SIGNALS:

GAIN / LOSS     : TRUE
INITIAL AVG     : TRUE
WILDER SMOOTH   : TRUE
RSI FORMULA     : TRUE

FORENSIC RESULT:

BTC:
3 mismatches

ETH:
3 mismatches

SOL:
3 mismatches

XRP:
3 mismatches

TOTAL:

EMA20_MISMATCH : 4
EMA50_MISMATCH : 4
RSI14_MISMATCH : 4

TOTAL EXACT:
0

TOTAL MISMATCH:
12

TOTAL UNRESOLVED:
0

FORENSIC CONCLUSION:

STATUS:
DIFFERENCE_CONFIRMED

REASON:
CURRENT IMPLEMENTATION VALUES DIFFER FROM STANDARD CONVENTION


====================================================================================================
IMPORTANT CURRENT FINDING
====================================================================================================

The following differences are now CONFIRMED:

EMA20:
Current implementation != standard convention
for BTC, ETH, SOL, XRP

EMA50:
Current implementation != standard convention
for BTC, ETH, SOL, XRP

RSI14:
Current implementation != standard convention
for BTC, ETH, SOL, XRP

This is NOT caused by:
- missing target
- NULL indicator target
- insufficient target resolution
- insufficient history
- raw price identity mismatch

The comparison had:
4 READY targets
4 EXACT raw price identities
64 valid closes per target
12/12 differences confirmed


====================================================================================================
CURRENT FORENSIC SOURCE SIGNALS
====================================================================================================

EMA:
EMA function exists.
EMA series exists.
EMA alpha signal exists.
EMA seed signal exists.
EMA recursive signal NOT conclusively identified by current forensic detector.

RSI:
Gain/loss separation exists.
Initial average exists.
Wilder smoothing exists.
RSI formula exists.

IMPORTANT:
These signals identify components but do NOT yet establish the exact complete current implementation convention.

Therefore:
DO NOT MODIFY market_data_engine.py yet.


====================================================================================================
FAILED / SUPERSEDED FORENSIC ATTEMPTS
====================================================================================================

Attempt:
INDICATOR_STANDARD_CONVENTION_DIFFERENCE_FORENSIC_AUDIT_v0.1

Problem:
History query resolved only one row.

Result:
INSUFFICIENT

Attempt:
v0.2

Problem:
Python runtime error:

TypeError:
'<' not supported between instances of 'str' and 'NoneType'

Cause:
Sorting mixed engine_version values containing None.

Attempt:
intermediate generated scripts

Problems:
- accidental Markdown code fence inside .py
- malformed __file__ expression
- unclosed dictionary
- unterminated string

These are SCRIPT GENERATION ERRORS only.
They do NOT invalidate the verified v0.3 forensic result.


====================================================================================================
CURRENT FRONTIER
====================================================================================================

CURRENT FRONTIER:

INDICATOR_CURRENT_CONVENTION_FORENSIC_RECONSTRUCTION_v0.1

PURPOSE:

Precisely reconstruct the CURRENT implementation convention used by
market_data_engine.py for:

EMA20
EMA50
RSI14

WITHOUT modifying anything.

Required investigation:

EMA:
1. Exact alpha implementation.
2. Exact seed implementation.
3. Exact seed position.
4. Whether EMA is recursive.
5. Whether pandas ewm or manual recursion is used.
6. adjust parameter / equivalent behavior.
7. min_periods behavior.
8. Exact source window.
9. Whether current EMA is calculated from full history or truncated history.
10. Exact handling of NaN / missing values.

RSI:
1. Exact gain/loss construction.
2. Exact initial average gain.
3. Exact initial average loss.
4. Exact initialization position.
5. Exact Wilder smoothing implementation.
6. Exact RSI formula.
7. Exact handling of zero loss / zero gain.
8. Exact source window.
9. Exact missing-value handling.
10. Exact final value generation.

The output must identify:

CURRENT CONVENTION
versus
STANDARD CONVENTION

and ideally reproduce the stored values exactly.

No repair yet.


====================================================================================================
NEXT DECISION TREE
====================================================================================================

IF current convention can be reconstructed exactly:
    -> compare CURRENT vs STANDARD mechanically
    -> quantify deterministic difference
    -> decide whether standardization is architecturally justified

IF current convention cannot be reconstructed exactly:
    -> remain FORENSIC / REVIEW_REQUIRED
    -> do NOT modify engine

ONLY AFTER forensic reconstruction is complete:
    -> possible repair design stage

Potential future stage:
INDICATOR_STANDARD_CONVENTION_REPAIR_PLAN_v0.1

BUT THIS STAGE IS NOT CURRENT.


====================================================================================================
DATABASE SAFETY
====================================================================================================

All stages in this branch:

DATABASE WRITE OPERATIONS:
NONE

ENGINE MODIFICATIONS:
NONE

FORMULA WRITE:
NONE

The database remains untouched by these audits.


====================================================================================================
RECOVERY RULE
====================================================================================================

If a new chat starts:

1. Read this backup first.
2. Do NOT repeat stages marked CLOSED / VERIFIED.
3. Do NOT treat superseded unresolved stages as current truth.
4. Current truth is:
   DIFFERENCE_CONFIRMED
5. Current frontier is:
   INDICATOR_CURRENT_CONVENTION_FORENSIC_RECONSTRUCTION_v0.1
6. Do not repair anything until current convention is exactly reconstructed.


====================================================================================================
END OF PROJECT STATE BACKUP
====================================================================================================
"""

backup_path.write_text(content, encoding="utf-8")

print("=" * 100)
print("ARUNDA PROJECT STATE BACKUP")
print("=" * 100)
print(f"BACKUP CREATED : {backup_path}")
print(f"SIZE           : {backup_path.stat().st_size:,} bytes")
print("DATABASE WRITE : NONE")
print("ENGINE MODIFY  : NONE")
print("STATUS         : COMPLETE")
print("=" * 100)