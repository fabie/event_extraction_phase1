Run the Evaluation Notebook in Google Colab

Method 1: Upload Notebook to Colab (Easiest)
Go to https://colab.research.google.com
Click "File" → "Upload notebook"
Select phase1_evaluation.ipynb from your computer
Click "Files" icon (left sidebar) → "Upload" button
Upload your gold_standard_200_events.csv file
Click "Runtime" → "Run all"

Method 2: Open from GitHub
Go to https://colab.research.google.com
Click "File" → "Open notebook"
Select "GitHub" tab
Enter your GitHub repo URL or username
Select evaluation/phase1_evaluation.ipynb
Upload your CSV data file when prompted
Run the notebook

Method 3: Reproduce Locally
Run Rule-Based Extraction
bash
python scripts/baseline_extract.py \
  --input data/gold_standard_200_events.csv \
  --output data/rule_based_extraction_results.csv

Calculate Metrics
bash
# Use provided evaluation notebook or script
python scripts/eval_baseline.py \
  --preds data/rule_based_extraction_results.csv


What You Need
Input File: gold_standard_200_events.csv (your labeled dataset)
Python Packages: Already installed in Colab (pandas, numpy, re)
Runtime: Python 3, no GPU needed

What Works
Date pattern recognition is reliable for standard formats
Coverage is generally good (attempts extraction on most events)
Easy events can be handled reasonably well

What Needs Improvement
Event name extraction requires semantic understanding
Venue extraction needs context awareness
Classic UI noise filtering is critical == ref. “Action Navigation”
Complex/non-standard formats need adaptive approaches

Next Phase with NER Transformer will:
Learn UI patterns vs. content patterns 
Use context to filter noise 
Understand semantic meaning 

=============================================
Phase 1 Performance Evaluation Results
Baseline Performance (200 Events)
Average Exact F1: 0.278
Average Partial F1: 0.399
Field Performance
DateTime (Best): F1=0.550 - Reliable date pattern recognition
Venue: F1=0.147 - Struggles with UI noise and context
Event Name (Worst): F1=0.140 - Difficulty with navigation elements

Key Findings
Strengths: Date extraction works well for standard formats (74% F1 on easy events) 
Weaknesses: Event name extraction is confused by UI elements, and needs semantic understanding 
Performance Gap: 60% drop in F1 scores from easy to hard events
Evaluation Files
evaluation/phase1_evaluation.ipynb - Full Colab notebook
evaluation/phase1_evaluation.pdf - Static PDF report
evaluation/README.txt - Detailed metrics and analysis
