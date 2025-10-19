
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: "prefill_candidates.py"
Author: Fabienne Van Cappel
Email: fabienne.vancappel@gmail.com
Date: October, 2025
"""
"""
Prefill candidates for event labeling.

Inputs:
  - CSV with columns: raw_description  (required)
    Optional helpful columns: city, url, start_datetime (raw/messy)

Outputs:
  - Same CSV schema + columns:
      cand_event_name
      cand_venue
      cand_start_datetime_iso        (if --with-date-candidate)
  - If --prefill-labels, also copies:
      cand_event_name -> label_event_name    (if empty)
      cand_venue      -> label_venue         (if empty)
    (dates stay as candidates for human review unless you prefer to copy them too)

Usage:
  python3 scripts/prefill_candidates.py \
    --input data/gold_sample_300.csv \
    --output data/gold_sample_300_prefilled.csv \
    --prefill-labels \
    --with-date-candidate
"""

import re
import unicodedata
import argparse
import pandas as pd
from datetime import datetime

# --- Date parsing setup ---
try:
    import dateparser
    from dateparser.search import search_dates
    HAS_DP = True
except Exception:
    HAS_DP = False

# --- City → timezone (adjust as needed) ---
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None

CITY_TZ = {
    "Denver": "America/Denver",
    "Austin": "America/Chicago",
    "Daytona Beach": "America/New_York",
}

# ---------- Text helpers ----------
TITLE_SPLIT = re.compile(r"[\n\r]+| {2,}|\|")
CLEAN_WS    = re.compile(r"\s+")

VENUE_PATS = [
    re.compile(r"\b(?:where|location)\s*:\s*(.+?)(?:\n|$)", re.I),
    re.compile(r"\b(?:venue)\s*:\s*(.+?)(?:\n|$)", re.I),
    re.compile(r"\bat\s+([A-Z][\w&\-\s.,']{3,})", re.I),  # "at Red Rocks Amphitheatre"
]

def normalize_text(t: str) -> str:
    if not isinstance(t, str):
        return ""
    t = t.replace("–", "-").replace("—", "-")
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

# Month-day range like "Oct 3-5, 2025" -> "Oct 3, 2025"
RANGE_MONTH = re.compile(
    r'\b(?P<mon>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+'
    r'(?P<d1>\d{1,2})\s*-\s*(?P<d2>\d{1,2})\s*,?\s*(?P<y>\d{4})\b',
    re.I
)
def extract_range_start(text: str) -> str | None:
    m = RANGE_MONTH.search(text)
    if not m:
        return None
    mon, d1, y = m.group("mon"), m.group("d1"), m.group("y")
    return f"{mon} {d1}, {y}"

ISO_DATE  = re.compile(r'\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b')
MDY_SLASH = re.compile(r'\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](\d{2,4})\b')

# Candidate extraction
def guess_event_name(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return ""
    chunks = [CLEAN_WS.sub(" ", c).strip(" -\t") for c in TITLE_SPLIT.split(raw)]
    chunks = [c for c in chunks if c and len(c) >= 4]
    for c in chunks[:5]:
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
            
            # Split on obvious separators and take first chunk
            return re.split(r"\s{2,}|\s*\|\s*|\s*•\s*|\s*—\s*|\s*–\s*", v)[0][:120]
    return ""

def to_iso(dt, tz: str | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None and tz and ZoneInfo:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    try:
        return dt.isoformat(timespec="minutes")
    except Exception:
        return dt.isoformat()

# Return best-guess start datetime in ISO
# Prefers explicit patterns (ISO / MDY / ranges), then search_dates, then parse all
def cand_dt(raw_text: str, city: str | None, url: str | None = None, start_field: str | None = None) -> str:
   
    if not HAS_DP:
        return ""
    tz = CITY_TZ.get(str(city), "America/Denver")

    # 0) Try existing start field first (if present and non-empty)
    if isinstance(start_field, str) and start_field.strip():
        dt = dateparser.parse(start_field, settings={"TIMEZONE": tz, "RETURN_AS_TIMEZONE_AWARE": bool(ZoneInfo)})
        if dt:
            return to_iso(dt, tz)

    t = normalize_text(raw_text)
   
    # If no text, parse the URL (last resort)
    if not t:
        if isinstance(url, str) and url:
            u = normalize_text(url)
            m = ISO_DATE.search(u)
            if m:
                dt = dateparser.parse(m.group(0))
                return to_iso(dt, tz)
        return ""

    settings = {
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": bool(ZoneInfo),
    }
    if ZoneInfo:
        settings["TIMEZONE"] = tz
        settings["RELATIVE_BASE"] = datetime.now(ZoneInfo(tz))

    # 1) Explicit ISO in text
    m = ISO_DATE.search(t)
    if m:
        dt = dateparser.parse(m.group(0), settings=settings)
        if dt:
            return to_iso(dt, tz)

    # 2) Slashed MDY in text
    m = MDY_SLASH.search(t)
    if m:
        dt = dateparser.parse(m.group(0), settings=settings)
        if dt:
            return to_iso(dt, tz)

    # 3) Month-day ranges such as "Oct 3-5, 2025" -> start day
    hint = extract_range_start(t)
    if hint:
        dt = dateparser.parse(hint, settings=settings)
        if dt:
            return to_iso(dt, tz)

    # 4) Pull first date-like substring via search_dates
    try:
        found = search_dates(t, settings=settings) if HAS_DP else None
        if found:
            _, dt = found[0]
            if dt:
                return to_iso(dt, tz)
    except Exception:
        pass

    # 5) Fallback: parse whole text
    dt = dateparser.parse(t, settings=settings)
    if dt:
        return to_iso(dt, tz)

    # 6) URL fallback (again)
    if isinstance(url, str) and url:
        u = normalize_text(url)
        m = ISO_DATE.search(u)
        if m:
            dt = dateparser.parse(m.group(0))
            if dt:
                return to_iso(dt, tz)

    return ""

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",  required=True, help="Path to CSV (e.g., data/gold_sample_300.csv)")
    ap.add_argument("--output", required=True, help="Path to write prefilled CSV")
    ap.add_argument("--prefill-labels", action="store_true",
                    help="Copy candidates into label_event_name/label_venue if blank")
    ap.add_argument("--with-date-candidate", action="store_true",
                    help="Compute cand_start_datetime_iso (requires dateparser)")
    args = ap.parse_args()

    df = pd.read_csv(args.input, low_memory=False)

    # Ensure core columns exist for downstream labeling
    for c in ["city","url","raw_description",
              "label_event_name","label_start_datetime_iso","label_venue",
              "label_confidence","label_notes"]:
        if c not in df.columns:
            df[c] = ""

    # Candidates: name + venue
    df["cand_event_name"] = df["raw_description"].astype(str).apply(guess_event_name)
    df["cand_venue"]      = df["raw_description"].astype(str).apply(guess_venue)

    # Candidate: start datetime (optional)
    if args.with_date_candidate:
        if not HAS_DP:
            print("[WARN] dateparser not installed; skipping cand_start_datetime_iso")
        else:
            cities = df["city"] if "city" in df.columns else [None]*len(df)
            urls   = df["url"]  if "url"  in df.columns else [None]*len(df)
            starts = df["start_datetime"] if "start_datetime" in df.columns else [None]*len(df)
            df["cand_start_datetime_iso"] = [
                cand_dt(txt, city, url, start)
                for txt, city, url, start in zip(df["raw_description"], cities, urls, starts)
            ]

    # Prefill label columns from candidates (event name + venue)
    if args.prefill_labels:
        mask_empty_name  = df["label_event_name"].astype(str).str.strip().eq("")
        mask_empty_venue = df["label_venue"].astype(str).str.strip().eq("")
        df.loc[mask_empty_name,  "label_event_name"] = df["cand_event_name"]
        df.loc[mask_empty_venue, "label_venue"]      = df["cand_venue"]
        # Keep label_start_datetime_iso for human verification (copy if you really want)
        # if "cand_start_datetime_iso" in df.columns:
        #     mask_empty_dt = df["label_start_datetime_iso"].astype(str).str.strip().eq("")
        #     df.loc[mask_empty_dt, "label_start_datetime_iso"] = df["cand_start_datetime_iso"]

    df.to_csv(args.output, index=False)
    print(f"[OK] Prefilled → {args.output}")

    # Coverage stats
    def filled(col): return int(df[col].astype(str).str.strip().ne("").sum()) if col in df.columns else 0
    cov = {
        "cand_event_name":         filled("cand_event_name"),
        "cand_venue":              filled("cand_venue"),
        "cand_start_datetime_iso": filled("cand_start_datetime_iso"),
        "label_event_name":        filled("label_event_name"),
        "label_venue":             filled("label_venue"),
        "label_start_datetime_iso":filled("label_start_datetime_iso"),
    }
    print("[COVERAGE]", cov)

if __name__ == "__main__":
    main()

