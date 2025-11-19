# shared_helpers.py
import json, re, math, datetime
from decimal import Decimal

JSON_BLOCK_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE|re.MULTILINE)

def strip_fences(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return JSON_BLOCK_RE.sub("", s.strip())

def parse_json_strict(s: str):
    s = strip_fences(s)
    return json.loads(s)

def clamp(x, lo, hi, default=0.0):
    try:
        v = float(x)
        return max(lo, min(hi, v))
    except:
        return default

def now_utc_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
