
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: "build_master_gold.py"
Author: Fabienne Van Cappel
Email: fabienne.vancappel@gmail.com
Date: Ocotber 2025
Orchestrate: flag -> prefill -> filter-merge into one master gold set.
- Keeps ONLY rows flagged as event-like.
- Adds prefilled candidates (cand_event_name, cand_start_datetime_iso, cand_venue).
"""

import os
import subprocess
import pandas as pd

HERE = os.path.dirname(__file__)
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))

# Inputs
PREFILL_IN   = os.path.join(DATA, "gold_sample_300.csv")
PREFILL_OUT  = os.path.join(DATA, "gold_sample_300_prefilled.csv")
FLAG_IN      = PREFILL_OUT                      # we’ll flag the prefilled file for convenience
FLAG_OUT     = os.path.join(DATA, "gold_sample_300_flagged.csv")
MASTER_OUT   = os.path.join(DATA, "gold_sample_300_master.csv")

def run(cmd):
    print("[RUN]", " ".join(cmd))
    subprocess.check_call(cmd)

# 1) Prefill candidates (name/venue and date candidate)
def main():
    run([
        "python3", os.path.join(HERE, "prefill_candidates.py"),
        "--input",  PREFILL_IN,
        "--output", PREFILL_OUT,
        "--prefill-labels",
        "--with-date-candidate",
    ])

    # 2) Flag event-like rows (filter chatter)
    run([
        "python3", os.path.join(HERE, "flag_event_candidates.py"),
        "--input",  FLAG_IN,
        "--output", FLAG_OUT,
    ])

    # 3) Merge-filter: keep only flagged rows and carry prefilled candidates forward
    flagged = pd.read_csv(FLAG_OUT, low_memory=False)
    if "is_event_candidate" in flagged.columns:
        flagged = flagged[flagged["is_event_candidate"] == True].copy()
        print(f"[INFO] Retained {len(flagged)} flagged event-like rows")
    else:
        print("[WARN] No 'is_event_candidate' column — keeping all rows")

    prefilled = pd.read_csv(PREFILL_OUT, low_memory=False)

    # Merge on URL (unique key across pipeline)
    keep_cols_prefill = ["url","cand_event_name","cand_start_datetime_iso","cand_venue",
                         "label_event_name","label_start_datetime_iso","label_venue",
                         "label_confidence","label_notes"]
    keep_cols_prefill = [c for c in keep_cols_prefill if c in prefilled.columns]

    merged = pd.merge(flagged, prefilled[keep_cols_prefill], on="url", how="left")

    merged.to_csv(MASTER_OUT, index=False)
    print(f"[OK] Master gold set saved → {MASTER_OUT}")
    print(f"[SUMMARY] {len(merged)} rows in master")

if __name__ == "__main__":
    main()

