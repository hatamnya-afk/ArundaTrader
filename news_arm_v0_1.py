import re
import time
import hashlib
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from information_contract_v0_1 import (
    CONTRACT_VERSION, validate_news
)

ENGINE_VERSION = "NEWS_ARM_v0.1"

RSS_SOURCES = {
    "COINDESK": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "COINTELEGRAPH": "https://cointelegraph.com/rss",
    "DECRYPT": "https://decrypt.co/feed",
}

ALIASES = {
    "BTC":["bitcoin","btc"],
    "ETH":["ethereum","ether","eth"],
    "SOL":["solana","sol"],
    "XRP":["xrp","ripple"],
    "DOGE":["dogecoin","doge"],
    "ADA":["cardano","ada"],
    "AVAX":["avalanche","avax"],
    "DOT":["polkadot","dot"],
    "LINK":["chainlink","link"],
    "TRX":["tron","trx"],
    "LTC":["litecoin","ltc"],
    "BCH":["bitcoin cash","bch"],
    "ATOM":["cosmos","atom"],
    "UNI":["uniswap","uni"],
    "MATIC":["polygon","matic"],
}

POS = {
    "surge","rally","bullish","approval","approved","adoption",
    "partnership","launch","record","growth","inflow","upgrade"
}
NEG = {
    "crash","fall","bearish","hack","hacked","lawsuit","ban",
    "outflow","exploit","fraud","collapse","liquidation","warning"
}

def clean(s):
    return re.sub(r"\s+"," ",s or "").strip()

def parse_date(v):
    if not v:
        return datetime.now(timezone.utc).isoformat()
    try:
        return parsedate_to_datetime(v).astimezone(timezone.utc).isoformat()
    except Exception:
        try:
            return datetime.fromisoformat(v.replace("Z","+00:00")).astimezone(timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

def fetch(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={"User-Agent":"ArundaTrader-InformationArm/0.1"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def detect_asset(text):
    t = clean(text).lower()
    hits=[]
    for asset, aliases in ALIASES.items():
        for a in aliases:
            if re.search(r"\b"+re.escape(a)+r"\b",t):
                hits.append(asset)
                break
    return hits

def sentiment(text):
    t=clean(text).lower()
    p=sum(1 for x in POS if x in t)
    n=sum(1 for x in NEG if x in t)
    if p>n: return "BULLISH"
    if n>p: return "BEARISH"
    return "NEUTRAL"

def parse_rss(source, data):
    root=ET.fromstring(data)
    out=[]
    for item in root.iter():
        if item.tag.lower().split("}")[-1] not in ("item","entry"):
            continue
        def val(names):
            for child in item:
                tag=child.tag.lower().split("}")[-1]
                if tag in names and child.text:
                    return clean(child.text)
            return ""
        title=val({"title"})
        desc=val({"description","summary","content"})
        link=val({"link"})
        pub=val({"pubdate","published","updated","date"})
        text=f"{title} {desc}"
        assets=detect_asset(text)
        if not title or not assets:
            continue
        ts=parse_date(pub)
        sid=hashlib.sha256(
            f"{source}|{link}|{title}|{ts}".encode()
        ).hexdigest()
        for asset in assets:
            item={
                "contract_version":CONTRACT_VERSION,
                "source":source,
                "source_id":sid,
                "asset":asset,
                "timestamp":ts,
                "title":title,
                "text":desc,
                "event_type":"NEWS_EVENT",
                "sentiment":sentiment(text),
                "relevance":1.0,
                "confidence":0.70,
                "freshness":1.0,
                "provenance":{
                    "source":source,
                    "url":link,
                    "engine":ENGINE_VERSION
                },
                "url":link
            }
            if validate_news(item):
                out.append(item)
    return out

def run():
    results=[]
    errors=[]
    for source,url in RSS_SOURCES.items():
        try:
            results.extend(parse_rss(source,fetch(url)))
        except Exception as e:
            errors.append(f"{source}:{type(e).__name__}")
    return {
        "engine":ENGINE_VERSION,
        "items":results,
        "errors":errors,
        "db_writes":0
    }

if __name__=="__main__":
    r=run()
    print("NEWS_ARM="+("PASS" if r["items"] else "NO_DATA"))
    print("ITEMS=",len(r["items"]))
    print("ERRORS=",len(r["errors"]))
    print("DB_WRITE=0")
