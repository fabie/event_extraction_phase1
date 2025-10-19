

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: "reddit_collect.py"
Author: Fabienne Van Cappel
Email: fabienne.vancappel@gmail.com
Date: October, 2025
"""


import os
import time
import json
import csv
import praw

def make_reddit():
    cid = os.environ.get("REDDIT_CLIENT_ID")
    sec = os.environ.get("REDDIT_CLIENT_SECRET")  # may be None for installed app
    ua  = os.environ.get("REDDIT_USER_AGENT")
    rtk = os.environ.get("REDDIT_REFRESH_TOKEN")
    un  = os.environ.get("REDDIT_USERNAME")
    pw  = os.environ.get("REDDIT_PASSWORD")

    if not (cid and ua):
        raise RuntimeError("Missing REDDIT_CLIENT_ID or REDDIT_USER_AGENT")

    if rtk:
        return praw.Reddit(
            client_id=cid,
            client_secret=sec,
            refresh_token=rtk,
            user_agent=ua,
            check_for_async=False,
        )
    if un and pw:
        return praw.Reddit(
            client_id=cid,
            client_secret=sec,
            user_agent=ua,
            username=un,
            password=pw,
            check_for_async=False,
        )
    r = praw.Reddit(client_id=cid, client_secret=sec, user_agent=ua, check_for_async=False)
    r.read_only = True
    return r

# Collection function
def collect_from_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    reddit = make_reddit()
    all_rows = []

    for city_cfg in cfg["cities"]:
        city = city_cfg["city"]
        sub  = city_cfg["subreddit"]
        queries = city_cfg.get("queries", [])
        limit = int(city_cfg.get("limit_per_query", 50))
        tf = city_cfg.get("time_filter", "month")
        rate = float(cfg.get("rate_limit_seconds", 1.0))

        print(f"[INFO] {city} — r/{sub}: {len(queries)} queries × {limit}")
        for q in queries:
            try:
                for p in reddit.subreddit(sub).search(q, sort="new", time_filter=tf, limit=limit):
                    title = (p.title or "").strip()
                    body  = (getattr(p, "selftext", "") or "").strip()
                    url   = f"https://www.reddit.com{p.permalink}"
                    text  = f"{title}\n\n{body}".strip()
                    if not text:
                        continue
                    all_rows.append({
                        "city": city,
                        "source": "reddit",
                        "url": url,
                        "raw_description": text,
                        "event_name": "",
                        "start_datetime": "",
                        "venue": ""
                    })
                time.sleep(rate)
            except Exception as e:
                print(f"[WARN] Query '{q}' failed: {e}")

    out_csv = os.path.join(os.path.dirname(config_path), "..", "data", cfg.get("out_csv", "reddit_collected.csv"))
    out_csv = os.path.abspath(out_csv)

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["city","source","url","raw_description","event_name","start_datetime","venue"])
        w.writeheader()
        w.writerows(all_rows)

    print(f"[OK] Saved {len(all_rows)} rows to {out_csv}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        raise SystemExit("Usage: reddit_collect.py config.json")
    collect_from_config(sys.argv[1])

