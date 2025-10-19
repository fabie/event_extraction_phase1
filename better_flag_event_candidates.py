
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: "better_flag_event_candidates.py"
Author: Fabienne Van Cappel
Email: fabienne.vancappel@gmail.com
Date: October, 2025

"""


import re, argparse, pandas as pd

#Signals
EVENT_WORDS = re.compile(
    r'\b(concert|festival|meetup|market|parade|race|fair|comedy|'
    r'live music|open mic|screening|art walk|gallery|workshop|talk|reading|'
    r'tour|show|performance|opening|exhibit|class|seminar|webinar|'
    r'game|match|tournament|tailgate|5k|10k|marathon|triathlon|'
    r'jam|gig|open\s*house|block\s*party|hackathon|conference|con|'
    r'play|recital)\b', re.I
)
DATE_HINTS = re.compile(
    r'(\b\d{1,2}/\d{1,2}(/\d{2,4})?\b|'                         # 9/12, 09/12/2025
    r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|' # Sept, October
    r'\b\d{1,2}(:\d{2})?\s*(am|pm)\b|'                          # 7 pm, 7:30 pm
    r'\btoday|tomorrow|tonight|this\s+weekend\b|'               # relative
    r'\b(202[4-9]-\d{2}-\d{2})\b)',                             # 2025-10-03
    re.I
)
VENUE_HINTS = re.compile(r'\b(at|venue|location|on the lawn|amphitheater|arena|park|theater|centre|center)\b', re.I)
LINK_HINTS = re.compile(
    r'(eventbrite\.|meetup\.com|facebook\.com/events|tickets?|rsvp|austintexas\.gov|daytonabeach\.gov|denver\.org)',
    re.I
)

# Chatter / Negative cues (demote likely non-events) ---
NEGATIVE = re.compile(
    r'\b(hate|rant|schizophren|aggressive brother|adhd|depression|neurodivergent|'
    r'punishment|fantasy football punishment|heatstroke|was a fun looking group|'
    r'first permanent white settlement|history in \d{3,4}|ticket queue|gotten tickets|'
    r'partnering with a bunch|PSA|petition|help me|struggling|off topic)\b', re.I
)

MIN_LEN      = 60   # shorter than this is likely chatter unless very strong signals
LONG_LEN     = 140  # long posts with date+venue can be events
THRESHOLD    = 50   # score cutoff for is_event_candidate

# Return (score, breakdown)
def score_row(text: str) -> tuple[int, dict]:
    t = (text or "").strip()
    if not t:
        return 0, {"empty": True}

    hits = {
        "event_word":  bool(EVENT_WORDS.search(t)),
        "date_hint":   bool(DATE_HINTS.search(t)),
        "venue_hint":  bool(VENUE_HINTS.search(t)),
        "link_hint":   bool(LINK_HINTS.search(t)),
        "negative":    bool(NEGATIVE.search(t)),
        "short":       len(t) < MIN_LEN,
        "long":        len(t) >= LONG_LEN,
    }

    score = 0
    
    # Positive signals
    if hits["event_word"]: score += 35
    if hits["date_hint"]:  score += 30
    if hits["venue_hint"]: score += 20
    if hits["link_hint"]:  score += 40
    if hits["long"]:       score += 5   # small boost for long descriptive posts

    # Combos
    if hits["event_word"] and (hits["date_hint"] or hits["venue_hint"]): score += 20
    if hits["date_hint"] and hits["venue_hint"]: score += 15
    if hits["event_word"] and hits["link_hint"]: score += 15

    # Penalties
    if hits["negative"]: score -= 40
    if hits["short"] and not (hits["event_word"] and hits["date_hint"]): score -= 25

    # Attach
    score = max(0, min(100, score))
    return score, hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV with raw_description")
    ap.add_argument("--output", required=True, help="CSV with is_event_candidate flag")
    args = ap.parse_args()

    df = pd.read_csv(args.input, low_memory=False)
    if "raw_description" not in df.columns:
        df["raw_description"] = ""

    scores, reasons, flags = [], [], []
    for txt in df["raw_description"].astype(str):
        s, h = score_row(txt)
        scores.append(s)
        reasons.append(h)
        flags.append(s >= THRESHOLD)

    df["event_score"] = scores
    df["event_reasons"] = reasons
    df["is_event_candidate"] = flags

    out_all = args.output
    out_eventy = args.output.replace(".csv", "_eventy.csv")

    df.to_csv(out_all, index=False)
    df[df["is_event_candidate"]].to_csv(out_eventy, index=False)
    kept = int(df["is_event_candidate"].sum())

    print(f"[OK] Wrote {out_all}")
    print(f"[OK] Wrote {out_eventy} (kept {kept}/{len(df)})")
    print("[HINT] Threshold={}, positives need event_word + (date/venue/link) or strong link signal.".format(THRESHOLD))

if __name__ == "__main__":
    main()

