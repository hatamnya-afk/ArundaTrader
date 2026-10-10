from datetime import datetime, timezone

CONTRACT_VERSION = "INFORMATION_CONTRACT_v0.1"

COMMON_FIELDS = [
    "contract_version","source","source_id","asset","timestamp",
    "title","text","event_type","sentiment","relevance",
    "confidence","freshness","provenance"
]

NEWS_FIELDS = COMMON_FIELDS + ["url"]
SOCIAL_FIELDS = COMMON_FIELDS + [
    "url","author_id","engagement","mention_count","momentum"
]

VALID_SENTIMENT = {"BULLISH","BEARISH","NEUTRAL","UNKNOWN"}

def _iso(v):
    if not isinstance(v,str) or not v:
        return False
    try:
        datetime.fromisoformat(v.replace("Z","+00:00"))
        return True
    except Exception:
        return False

def _base_ok(x):
    if not isinstance(x,dict):
        return False
    if x.get("contract_version") != CONTRACT_VERSION:
        return False
    if not x.get("source") or not x.get("source_id"):
        return False
    if not x.get("asset"):
        return False
    if not _iso(x.get("timestamp")):
        return False
    if x.get("sentiment") not in VALID_SENTIMENT:
        return False
    for k in ("relevance","confidence","freshness"):
        try:
            if not 0 <= float(x[k]) <= 1:
                return False
        except Exception:
            return False
    if not x.get("provenance"):
        return False
    return True

def validate_news(x):
    return _base_ok(x) and bool(x.get("url"))

def validate_social(x):
    if not _base_ok(x):
        return False
    try:
        float(x.get("engagement",0))
        float(x.get("mention_count",0))
        float(x.get("momentum",0))
    except Exception:
        return False
    return True

def validate_common(x):
    return _base_ok(x)

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def empty_news():
    return {k:None for k in NEWS_FIELDS}

def empty_social():
    return {k:None for k in SOCIAL_FIELDS}
