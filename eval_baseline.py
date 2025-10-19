
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Name: "eval_baseline.py"
Author: Fabienne Van Cappel
Email: fabienne.vancappel@gmail.com
Date: 2025
Evaluate baseline predictions vs labels on exact match
"""

import argparse
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

FIELDS = [
    ("label_event_name",        "pred_event_name"),
    ("label_start_datetime_iso","pred_start_datetime_iso"),
    ("label_venue",             "pred_venue"),
]

def norm(s):
    return " ".join(str(s).strip().lower().split()) if isinstance(s, str) else ""

def score_exact(df, gold_col, pred_col):
    mask = df[gold_col].astype(str).str.strip().ne("")
    if not mask.any():
        return {"support": 0, "precision": 0, "recall": 0, "f1": 0}
    gold = df.loc[mask, gold_col].fillna("").apply(norm).tolist()
    pred = df.loc[mask, pred_col].fillna("").apply(norm).tolist()

    # Treat exact string equality as "correct"
    y_true = [1 if g == p and g != "" else 0 for g, p in zip(gold, pred)]
    y_pred = [1 if p != "" else 0 for p in pred]

    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    return {"support": int(mask.sum()), "precision": prec, "recall": rec, "f1": f1}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True, help="CSV produced by baseline_extract.py")
    args = ap.parse_args()

    df = pd.read_csv(args.preds, low_memory=False)
    rows = []
    for g, p in FIELDS:
        rows.append({"field": g.replace("label_", ""), **score_exact(df, g, p)})
    out = args.preds.replace(".csv", "_eval.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"[OK] Wrote {out}")

if __name__ == "__main__":
    main()

