#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Script Name: "clean_labels.py"
Author: Fabienne Van Cappel
Email: fabienne.vancappel@gmail.com
Date: October 2025
Clean up gold dataset label columns and record labeling progress.

- Unifies duplicate columns with suffixes _x / _y into:
    label_event_name
    label_start_datetime_iso
    label_venue

- Adds a progress summary:
    label_status ∈ {unlabeled, partially_labeled, fully_labeled}
    Console summary + appends a row to data/progress_report.csv

Input:  data/gold_sample_300_master.csv
Output: data/gold_sample_300_master_clean.csv
        data/progress_report.csv (appended)
"""

import os
import sys
import pandas as pd
from datetime import datetime

LABEL_BASES = ["label_event_name", "label_start_datetime_iso", "label_venue"]

def nonempty(x) -> bool:
    return isinstance(x, str) and x.strip() not in ("", "nan", "None")

def compute_status(row) -> str:
    vals = [nonempty(row.get(b, "")) for b in LABEL_BASES]
    filled = sum(vals)
    if filled == 0:
        return "unlabeled"
    if filled == len(LABEL_BASES):
        return "fully_labeled"
    return "partially_labeled"

def main():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    in_path  = os.path.join(data_dir, "gold_sample_300_master.csv")
    out_path = os.path.join(data_dir, "gold_sample_300_master_clean.csv")
    prog_csv = os.path.join(data_dir, "progress_report.csv")

    if not os.path.exists(in_path):
        print(f"[ERR] Missing input: {in_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(in_path, low_memory=False)

    # Unify duplicate label columns (_x/_y)
    for base in LABEL_BASES:
        x_col, y_col = f"{base}_x", f"{base}_y"
        if x_col in df.columns and y_col in df.columns:
            df[base] = df[y_col].combine_first(df[x_col])
            df.drop(columns=[x_col, y_col], inplace=True)
        elif x_col in df.columns:
            df.rename(columns={x_col: base}, inplace=True)
        elif y_col in df.columns:
            df.rename(columns={y_col: base}, inplace=True)
        else:
            # ensure column exists
            if base not in df.columns:
                df[base] = ""

    # Compute progress fields
    df["label_status"] = df.apply(compute_status, axis=1)
    total = len(df)
    fully = int((df["label_status"] == "fully_labeled").sum())
    partial = int((df["label_status"] == "partially_labeled").sum())
    unlabeled = int((df["label_status"] == "unlabeled").sum())

    #Save cleaned file
    df.to_csv(out_path, index=False)
    print(f"[OK] Cleaned dataset saved → {out_path}")

    # Append to progress report (or create with header)
    now = datetime.now().isoformat(timespec="seconds")
    row = {
        "timestamp": now,
        "total": total,
        "fully_labeled": fully,
        "partially_labeled": partial,
        "unlabeled": unlabeled,
        "pct_complete": round(100.0 * fully / total, 2) if total else 0.0,
    }
    if os.path.exists(prog_csv):
        prog_df = pd.read_csv(prog_csv)
        prog_df = pd.concat([prog_df, pd.DataFrame([row])], ignore_index=True)
    else:
        prog_df = pd.DataFrame([row], columns=["timestamp","total","fully_labeled","partially_labeled","unlabeled","pct_complete"])
    prog_df.to_csv(prog_csv, index=False)
    print(f"[OK] Progress appended → {prog_csv}")

    # Summary
    print("\n[SUMMARY]")
    print(f" total rows:        {total}")
    print(f" fully labeled:     {fully}")
    print(f" partially labeled: {partial}")
    print(f" unlabeled:         {unlabeled}")
    print(f" % complete:        {row['pct_complete']}%")

if __name__ == "__main__":
    main()

