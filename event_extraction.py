

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: "event_extraction.py"
Author: Fabienne Van Cappel
Email: fabienne.vancappel@gmail.com
Date: October, 2025
"""

"""
Reads a merged CSV (e.g., merged_events.csv), filters to event-like rows
Deduplicates by URL, and writes a gold set CSV ready for labeling
Example:
  python3 scripts/event_extraction.py \
    --input data/merged_events.csv \
    --output data/gold_sample_300.csv \
    --sample 300 \
    --with-candidates \
    --with-date-candidate \
    --prefill-labels \
    --include-sports \
    --balance-by-city
"""

import os
import re
import argparse
import pandas as pd
from datetime import datetime

# -------------------- Regex patterns --------------------
EVENT_REGEX = re.compile(
    r'\b(?:event|concert|festival|meetup|market|parade|race|fair|comedy|'
    r'live music|open mic|screening|art walk|gallery|workshop|talk|reading|'
    r'tour|show|performance|opening|exhibit|class|seminar|webinar)\b',
    re.I
)

SPORTS_REGEX = re.compile(
    r'\b(?:game|match|tournament|playoff|playoffs|final|finals|kickoff|tipoff|'
    r'tailgate|scrimmage|friendly|meet|regatta|'
    r'5k|10k|half\s*marathon|marathon|triathlon|'
    r'soccer|football|basketball|baseball|hockey|volleyball|tennis|golf|rugby|'
    r'lacrosse|softball|track|field|swim|wrestling|boxing|mma|ufc|'
    r'nascar|f1|formula\s*1|indycar|motogp|grand\s*prix)\b',
    re.I
)

EXCLUDE_REGEX = re.compile(r'\b(video game|gaming pc|console|streaming)\b', re.I)

TITLE_SPLIT = re.compile(r"[\n\r]+| {2,}|\|")
CLEAN_WS    = re.compile(r"\s+")

VENUE_PATTERNS = [
    re.compile(r"\b(?:where|location)\s*:\s*(.+?)(?:\n|$)", re.I),
    re.compile(r"\b(?:venue)\s*:\s*(.+?)(?:\n|$)", re.I),
    re.compile(r"\bat\s+([A-Z][\w&\-\s.,']{3,})", re.I),
]

# Date candidate
try:
    import dateparser
    HAS_DATEPARSER = True
except Exception:
    HAS_DATEPARSER = False

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

CITY_TZ = {
    "Denver":        "America/Denver",
    "Austin":        "America/Chicago",
    "Daytona Beach": "America/New_York",
    "San Francisco": "America/Los_Angeles",
}

# -------------------- Candidate helpers --------------------

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
    for pat in VENUE_PATTERNS:
        m = pat.search(text)
        if m:
            v = m.group(1).strip(" •-–—|,")
            return re.split(r"\s{2,}|\s*\|\s*|\s*•\s*|\s*—\s*|\s*–\s*", v)[0][:120]
    return ""

def parse_start_datetime_iso(text: str, city: str | None) -> str:
    if not HAS_DATEPARSER or not isinstance(text, str) or not text.strip():
        return ""
    # Quick check
    if not re.search(r'(\b\d{1,2}/\d{1,2}(/\d{2,4})?\b|'
                     r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|'
                     r'\b\d{1,2}(:\d{2})?\s*(am|pm)\b|'
                     r'\btoday|tomorrow|tonight|this\s+weekend\b)', text, re.I):
        return ""
    tz = CITY_TZ.get(city or "", None)
    settings = {"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": bool(ZoneInfo and tz)}
    if tz and ZoneInfo:
        settings["TIMEZONE"] = tz
        settings["RELATIVE_BASE"] = datetime.now(ZoneInfo(tz))
    dt = dateparser.parse(text, settings=settings)
    if not dt:
        return ""
    if dt.tzinfo is None and tz and ZoneInfo:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    try:
        return dt.isoformat(timespec="minutes")
    except Exception:
        return dt.isoformat()

# -------------------- Main --------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to merged CSV (e.g., data/merged_events.csv)")
    ap.add_argument("--output", required=True, help="Path to write gold CSV (e.g., data/gold_sample_300.csv)")
    ap.add_argument("--sample", type=int, default=300, help="Rows to sample (0 = take all)")
    ap.add_argument("--min-len", type=int, default=60, help="Minimum raw_description length")
    ap.add_argument("--include-sports", action="store_true", help="Also match sports events")
    ap.add_argument("--with-candidates", action="store_true",
                    help="Append cand_event_name / cand_venue (and optional cand_start_datetime_iso)")
    ap.add_argument("--with-date-candidate", action="store_true",
                    help="Also compute cand_start_datetime_iso (requires dateparser)")
    ap.add_argument("--prefill-labels", action="store_true",
                    help="Prefill label_event_name / label_venue from candidates")
    ap.add_argument("--balance-by-city", action="store_true",
                    help="If set, sample roughly equally per city")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    args = ap.parse_args()

    inp, out = args.input, args.output
    n, min_len = args.sample, args.min_len
    include_sports, prefill = args.include_sports, args.prefill_labels
    add_cand, add_date_cand = (args.with_candidates or args.prefill_labels), args.with_date_candidate

    if not os.path.exists(inp):
        raise SystemExit(f"[ERROR] Missing input file: {inp}")

    df = pd.read_csv(inp, low_memory=False)

    # Ensure required columns
    for c in ["url", "raw_description"]:
        if c not in df.columns:
            df[c] = ""

    # Clean and Dedupe by URL
    df["url"] = df["url"].astype(str).str.strip()
    df = df.dropna(subset=["url"])
    df = df.drop_duplicates(subset=["url"]).copy()

    text = df["raw_description"].fillna("").astype(str)

    # Build mask
    contains_event = text.str.contains(EVENT_REGEX, na=False)
    mask = contains_event
    if include_sports:
        contains_sports = text.str.contains(SPORTS_REGEX, na=False)
        mask = mask | contains_sports
    mask = mask & ~text.str.contains(EXCLUDE_REGEX, na=False) & (text.str.len() >= min_len)

    eventy = df[mask].copy()
    if eventy.empty:
        raise SystemExit("[ERROR] No rows passed the event filter. Check your input or relax filters (--min-len).")

    # -------- Balanced sampling by city (optional) --------

    if n and n < len(eventy):
        if args.balance_by_city and "city" in eventy.columns:
            # remove empty city values
            eventy["city"] = eventy["city"].astype(str).str.strip()
            eventy = eventy[eventy["city"].ne("")].copy()
            if eventy.empty:
                gold = eventy.sample(n, random_state=args.seed).copy()
            else:
                k = max(1, n // eventy["city"].nunique())
                gold = (
                    eventy
                    .groupby("city", group_keys=False)
                    .apply(lambda g: g.sample(min(len(g), k), random_state=args.seed))
                )
                # if we are short due to small groups, top up randomly
                if len(gold) < n:
                    remain = eventy[~eventy.index.isin(gold.index)]
                    need = n - len(gold)
                    if not remain.empty:
                        gold = pd.concat([gold, remain.sample(min(need, len(remain)), random_state=args.seed)])
                gold = gold.sample(n=min(n, len(gold)), random_state=args.seed).copy()
        else:
            gold = eventy.sample(n, random_state=args.seed).copy()
    else:
        gold = eventy.copy()

    # Add label columns
    for c in ["label_event_name", "label_start_datetime_iso", "label_venue",
              "label_confidence", "label_notes"]:
        if c not in gold.columns:
            gold[c] = ""

    # Candidates (needed for prefill)
    if add_cand:
        gold["cand_event_name"] = gold["raw_description"].astype(str).apply(guess_event_name)
        gold["cand_venue"]      = gold["raw_description"].astype(str).apply(guess_venue)
        if add_date_cand:
            if not HAS_DATEPARSER:
                print("[WARN] dateparser not installed; skipping cand_start_datetime_iso")
            else:
                city_series = gold["city"] if "city" in gold.columns else None
                cities = city_series.tolist() if city_series is not None else [None]*len(gold)
                gold["cand_start_datetime_iso"] = [
                    parse_start_datetime_iso(txt, city) for txt, city in zip(gold["raw_description"], cities)
                ]

    # Prefill labels from candidates
    if prefill:
        if "cand_event_name" in gold.columns:
            gold["label_event_name"] = gold["cand_event_name"]
        if "cand_venue" in gold.columns:
            gold["label_venue"] = gold["cand_venue"]
        # keep label_start_datetime_iso blank unless you want to prefill from cand_start_datetime_iso

    # Order columns neatly
    preferred = ["city", "source", "url", "raw_description",
                 "event_name", "start_datetime", "venue",
                 "label_event_name", "label_start_datetime_iso", "label_venue",
                 "label_confidence", "label_notes"]
    if add_cand:
        preferred += ["cand_event_name", "cand_venue"]
        if add_date_cand:
            preferred += ["cand_start_datetime_iso"]
    cols = [c for c in preferred if c in gold.columns] + [c for c in gold.columns if c not in preferred]

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    gold[cols].to_csv(out, index=False)

    print(f"[OK] Wrote gold set: {out} (rows={len(gold)})")
    print(f"[OK] Filters: include_sports={include_sports}, min_len={min_len}, sample={n or 'ALL'}, balance_by_city={args.balance_by_city}")
    if add_cand:
        msg = "cand_event_name, cand_venue"
        if add_date_cand and HAS_DATEPARSER: msg += ", cand_start_datetime_iso"
        elif add_date_cand: msg += " (date skipped: dateparser not installed)"
        print(f"[OK] Added candidates: {msg}")
    if prefill:
        print("[OK] Prefilled label_event_name and label_venue from candidates")

if __name__ == "__main__":
    main()

