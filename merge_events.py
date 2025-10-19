
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: "merge_events.py"
Author: Fabienne Van Cappel
Email: fabienne.vancappel@gmail.com
Date: October,  2025
"""

"""
Merge city_portals_collected.csv and reddit_collected.csv from ../data,
dedupe by URL, and optionally keep only event-ish rows  
"""

import os
import sys
import re
import pandas as pd

NEEDED_COLS = ["city","source","url","raw_description","event_name","start_datetime","venue"]

EVENT_REGEX = re.compile(
    r'\b(event|concert|festival|meetup|market|parade|race|fair|comedy|live music|open mic|screening|art walk|gallery|workshop|talk|reading|tour|show|performance|opening|exhibit|class|seminar|webinar)\b',
    re.I
)

# Ensure required columns exist and order them
def ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    for c in NEEDED_COLS:
        if c not in df.columns:
            df[c] = ""
    return df[NEEDED_COLS].copy()

def main():

    # Resolve repo root from this script’s folder (i.e. C692-W2/scripts -> C692-W2)
    REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    base = os.path.join(REPO_ROOT, "data")

    city_p   = os.path.join(base, "city_portals_collected.csv")
    reddit_p = os.path.join(base, "reddit_collected.csv")

    print(f"[INFO] Repo root: {REPO_ROOT}")
    print(f"[INFO] Looking for city data at:   {city_p}")
    print(f"[INFO] Looking for reddit data at: {reddit_p}")

    if not os.path.exists(city_p):
        raise SystemExit(f"[ERROR] Missing file: {city_p}")
    if not os.path.exists(reddit_p):
        raise SystemExit(f"[ERROR] Missing file: {reddit_p}")

    # Flags
    do_filter = True
    if len(sys.argv) > 1 and sys.argv[1] == "--no-filter":
        do_filter = False

    print("[INFO] Loading CSVs...")
    city   = pd.read_csv(city_p,  low_memory=False)
    reddit = pd.read_csv(reddit_p, low_memory=False)

    print(f"[INFO] City rows:   {len(city):,}")
    print(f"[INFO] Reddit rows: {len(reddit):,}")

    city   = ensure_cols(city)
    reddit = ensure_cols(reddit)

    # Merge & Dedupe
    combo = pd.concat([city, reddit], ignore_index=True)
    before = len(combo)
    combo = combo.dropna(subset=["url"])
    combo = combo.drop_duplicates(subset=["url"])
    after = len(combo)

    out_all = os.path.join(base, "all_sources_merged.csv")
    combo.to_csv(out_all, index=False)
    print(f"[OK] Merged & deduped: {before:,} -> {after:,}  Saved: {out_all}")

    # Optional event-ish filter
    if do_filter:
        mask = combo["raw_description"].fillna("").str.contains(EVENT_REGEX)
        filtered = combo[mask].copy()
        out_evt = os.path.join(base, "all_sources_eventy.csv")
        filtered.to_csv(out_evt, index=False)
        print(f"[OK] Event-ish kept: {len(filtered):,}  Saved: {out_evt}")
        show = filtered
    else:
        show = combo

    # Summaries
    def vc(s):
        try:
            return s.value_counts(dropna=False).head(10)
        except Exception:
            return "n/a"

    print("\n[SUMMARY] By source:\n", vc(show["source"]))
    print("\n[SUMMARY] By city:\n", vc(show["city"]))

    # Peek
    cols = ["city","source","url"]
    peek = show[cols].head(10)
    print("\n[SAMPLE rows]\n", peek.to_string(index=False) if len(peek) else "(empty)")

    print("\n[DONE] Outputs:")
    print(f"  - {out_all}")
    if do_filter:
        print(f"  - {out_evt}")

if __name__ == "__main__":
    main()

