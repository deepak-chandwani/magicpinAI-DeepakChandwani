import re
from datetime import datetime, timezone

RUPEE = "₹"


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def first_name(name):
    if not name:
        return "there"
    s = str(name).replace("'s", "").strip()
    parts = re.split(r"\s+", s)
    titles = {"dr", "dr.", "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "mr", "prof", "prof."}
    while parts and parts[0].lower() in titles:
        parts.pop(0)
    return parts[0] if parts else "there"


def money(v):
    try:
        return f"₹{int(float(v)):,}"
    except Exception:
        return str(v)


def pct(v, decimals=0):
    if v is None:
        return None
    try:
        n = float(v)
        # Challenge data mixes 0.18 and 18-style percentages.
        if abs(n) <= 1:
            n *= 100
        return f"{n:.{decimals}f}%"
    except Exception:
        return str(v)


def clean_text(value, max_len=180):
    if value is None:
        return ""
    s = re.sub(r"\s+", " ", str(value)).strip()
    return s[:max_len]


def active_offers(merchant):
    return [
        o for o in merchant.get("offers", [])
        if str(o.get("status", "active")).lower() in {"active", "live"}
    ]


def best_offer(merchant, keywords=()):
    offers = active_offers(merchant)
    if not offers:
        return None
    for kw in keywords:
        for offer in offers:
            if kw.lower() in str(offer.get("title", "")).lower():
                return offer
    return offers[0]


def language_style(identity):
    pref = (identity or {}).get("language_pref")
    if pref:
        return str(pref).lower()
    langs = (identity or {}).get("languages") or []
    if "hi" in [str(x).lower() for x in langs]:
        return "hi-en"
    return "en"


def get_nested(obj, *keys, default=None):
    cur = obj
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur
