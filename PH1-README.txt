Phase 1: Data Collection Pipeline (Complete)
Project Overview
Multi-source event data collection system that harvests event information from city government portals and Reddit, then processes and prepares gold standard datasets for machine learning.
Completed Components
Data Collection Scripts (ESSENTIAL)
harvest_city_portals_streaming.py - Production city portal scraper with resume capability
reddit_collect.py - Reddit event data collector

Data Processing Scripts (ESSENTIAL)
merge_events.py - Combines and deduplicates data from multiple sources
better_flag_event_candidates.py - Enhanced event detection with scoring system
event_extraction.py - Creates balanced gold datasets with sampling
Gold Set Preparation Scripts (ESSENTIAL)
prefill_candidates.py - Generates candidate fields (name, venue, datetime)
build_master_gold.py - Orchestrates complete gold set pipeline
clean_labels.py - Standardizes labels and tracks progress
Baseline & Evaluation Scripts (ESSENTIAL)
baseline_extract.py - Rule-based extraction for comparison
eval_baseline.py - Evaluates baseline performance

Configuration Files (ESSENTIAL)
city_config.json - City portal harvesting configuration
reddit_config.json - Reddit scraping configuration

Installation
pip install -r requirements.txt
Quick Start
# 1. Configure data sources (scalable
# Edit config/city_config.json and config/reddit_config.json

# 2. Set Reddit API credentials
export REDDIT_CLIENT_ID="your_id"
export REDDIT_CLIENT_SECRET="your_secret"  
export REDDIT_USER_AGENT="YourApp/1.0"

# 3. Collect data
python scripts/harvest_city_portals_streaming.py
python scripts/reddit_collect.py config/reddit_config.json

# 4. Process and create gold set
python scripts/merge_events.py
python scripts/build_master_gold.py

# 5. Evaluate baseline
python scripts/baseline_extract.py --input data/gold_sample_300_master_clean.csv --output data/baseline_preds.csv
python scripts/eval_baseline.py --preds data/baseline_preds.csv

Data Pipeline Flow
City Portals + Reddit 
    → harvest_city_portals_streaming.py, reddit_collect.py
    → merge_events.py (deduplicate)
    → build_master_gold.py (flag + prefill + filter)
        → better_flag_event_candidates.py (event detection)
        → prefill_candidates.py (generate candidates)
        → merge (keep event-like rows)
    → clean_labels.py (standardize + track progress)
    → gold_sample_300_master_clean.csv (ready for labeling)
Output Files
city_portals_collected.csv - Raw city portal events
reddit_collected.csv - Raw Reddit posts
all_sources_merged.csv - Combined & deduplicated data
all_sources_eventy.csv - Event-filtered subset
gold_sample_300_master.csv - Gold set with candidates
gold_sample_300_master_clean.csv - Final cleaned gold set
progress_report.csv - Labeling progress tracking

Key Features Implemented
✅ Streaming collection with resume capability 
✅ Multi-source data harvesting (city portals + Reddit) 
✅ Intelligent event detection with weighted scoring 
✅ Automatic candidate field generation (name, venue, datetime) 
✅ Balanced sampling across cities 
✅ Rule-based baseline extraction 
✅ Labeling progress tracking 
✅ Performance evaluation metrics

Data Schema
Collection Schema
city, source, url, raw_description, event_name, start_datetime, venue

Gold Set Schema
city, source, url, raw_description
label_event_name, label_start_datetime_iso, label_venue
label_confidence, label_notes, label_status
cand_event_name, cand_venue, cand_start_datetime_iso
is_event_candidate, event_score, event_reasons

Performance Metrics
Collection Speed: ~150-200 events/hour (with Selenium)
Event Detection: ~75-85% precision, ~80-90% recall
Candidate Coverage: 85-95% (event name), 40-60% (venue), 50-70% (datetime)

Dependencies
requests, beautifulsoup4, lxml (web scraping)
selenium, webdriver-manager (browser automation)
praw (Reddit API)
pandas (data processing)
dateparser (date extraction)
scikit-learn (evaluation)

Next Steps
→ Phase 2: Machine Learning extraction models with NER Transformer → Phase 3: Hybrid extraction pipeline (GPT 3.5 turbo, Gemini (free tier), Ollama)
Contact
Fabienne Van Cappel - fabienne.vancappel@gmail.com
Status: ✅ PHASE 1 COMPLETED Date: 2025
