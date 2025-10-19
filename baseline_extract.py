#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Name: "baseline_extract.py"
Author: Fabienne Van Cappel
Email: fabienne.vancappel@gmail.com
Date: Oct. 2025
Baseline event extraction (rules + heuristics).

Input CSV needs columns:
  - raw_description  (str)
  - city             (str, optional but improves time zone handling)
  - url              (optional; sometimes contains dates)
  - label_event_name / label_start_datetime_iso / label_venue (optional; used only by eval script)

Outputs:
  - Same CSV + columns:
      pred_event_name
      pred_start_datetime_iso
      pred_venue
"""

import re
import argparse
import pandas as pd
from datetime import datetime

# Date parsing
try:
    import dateparser
    from dateparser.search import search_dates
    HAS_DP = True
except Exception:
    HAS_DP = False

# TimeZone (TZ) map by city
try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:
    ZoneInfo = None

CITY_TZ = {
    "Denver": "America/Denver",
    "Austin": "America/Chicago",
    "Daytona Beach": "America/New_York",
    "San Francisco": "America/Los_Angeles",
}

# Regex helpers
TITLE_SPLIT = re.compile(r"[\n\r]+| {2,}|\|")
CLEAN_WS    = re.compile(r"\s+")

VENUE_PATS = [
    re.compile(r"\b(?:where|location)\s*:\s*(.+?)(?:\n|$)", re.I),
    re.compile(r"\b(?:venue)\s*:\s*(.+?)(?:\n|$)", re.I),
    re.compile(r"\bat\s+([A-Z][\w&\-\s.,']{3,})", re.I),  # "at Red Rocks Amphitheatre"
]

ISO_DATE  = re.compile(r'\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b')
MDY_SLASH = re.compile(r'\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](\d{2,4})\b')
RANGE_MONTH = re.compile(
    r'\b(?P<mon>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+'
    r'(?P<d1>\d{1,2})\s*[-–—]\s*(?P<d2>\d{1,2})\s*,?\s*(?P<y>\d{4})\b',
    re.I
)

def _norm(t: str) -> str:
    if not isinstance(t, str): return ""
    t = t.replace("–","-").replace("—","-")
    t = CLEAN_WS.sub(" ", t).strip()
    return t

# Extraction rules
def guess_event_name(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return ""
    chunks = [CLEAN_WS.sub(" ", c).strip(" -\t") for c in TITLE_SPLIT.split(raw)]
    chunks = [c for c in chunks if c and len(c) >= 4]
    for c in chunks[:5]:
        # short-ish, has spaces, not a trailing header-like colon
        if len(c) <= 120 and (" " in c) and not c.endswith(":"):
            return c
    return (chunks[0][:120] if chunks else "").strip()

def guess_venue(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    for pat in VENUE_PATS:
        m = pat.search(text)
        if m:
            v = m.group(1).strip(" •-–—|,")
            # split on separators → take first chunk
            return re.split(r"\s{2,}|\s*\|\s*|\s*•\s*|\s*[—–-]\s*", v)[0][:120]
    return ""

def _to_iso(dt, tz: str | None) -> str:
    if not dt: return ""
    if dt.tzinfo is None and tz and ZoneInfo:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    try:
        return dt.isoformat(timespec="minutes")
    except Exception:
        return dt.isoformat()

def _range_start_hint(text: str) -> str | None:
    m = RANGE_MONTH.search(text)
    if not m: return None
    return f"{m.group('mon')} {m.group('d1')}, {m.group('y')}"

# Robust date guess
def guess_start_dt(text: str, city: str | None, url: str | None = None) -> str:
    if not HAS_DP or not isinstance(text, str) or not text.strip():
        return ""
    tz = CITY_TZ.get(str(city), "America/Denver")
    t  = _norm(text)
    settings = {"PREFER_DATES_FROM":"future", "RETURN_AS_TIMEZONE_AWARE": bool(ZoneInfo)}
    if ZoneInfo:
        settings["TIMEZONE"] = tz
        settings["RELATIVE_BASE"] = datetime.now(ZoneInfo(tz))

    # 1) ISO / 2) MDY / 3) Month-day range → start
    for pat in (ISO_DATE, MDY_SLASH):
        m = pat.search(t)
        if m:
            dt = dateparser.parse(m.group(0), settings=settings)
            if dt: return _to_iso(dt, tz)
    hint = _range_start_hint(t)
    if hint:
        dt = dateparser.parse(hint, settings=settings)
        if dt: return _to_iso(dt, tz)

    # 4) Search first date-like range
    try:
        found = search_dates(t, settings=settings)
        if found:
            _, dt = found[0]
            if dt: return _to_iso(dt, tz)
    except Exception:
        pass

    # 5) Fallback: whole-text
    dt = dateparser.parse(t, settings=settings)
    if dt: return _to_iso(dt, tz)

    # 6) Fallback: URL
    if isinstance(url, str) and url:
        m = ISO_DATE.search(url)
        if m:
            dt = dateparser.parse(m.group(0))
            if dt: return _to_iso(dt, tz)

    return ""

#CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True,  help="e.g., data/gold_sample_300_master.csv")
    ap.add_argument("--output", required=True, help="e.g., data/baseline_preds_300.csv")
    ap.add_argument("--max-rows", type=int, default=None, help="optional cap for quick tests")
    args = ap.parse_args()

    df = pd.read_csv(args.input, low_memory=False)
    if args.max_rows:
        df = df.head(args.max_rows).copy()

    for c in ["raw_description","city","url"]:
        if c not in df.columns:
            df[c] = ""

    # Predictions
    df["pred_event_name"]         = df["raw_description"].apply(guess_event_name)
    df["pred_venue"]              = df["raw_description"].apply(guess_venue)
    df["pred_start_datetime_iso"] = [guess_start_dt(txt, city, url) for txt, city, url
                                     in zip(df["raw_description"], df["city"], df["url"])]

    df.to_csv(args.output, index=False)
    print(f"[OK] Wrote {args.output} (rows={len(df)})")
    if not HAS_DP:
        print("[NOTE] dateparser not installed; pred_start_datetime_iso will be empty. Run: pip install dateparser")

if __name__ == "__main__":
    main()

