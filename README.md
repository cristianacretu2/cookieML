# Cookie Scanner — GDPR Cookie Scanner & Audit Tool

A GDPR/ePrivacy compliance auditing tool that crawls websites, classifies the cookies they set using a trained Random Forest classifier, and generates interactive HTML audit reports.

## Overview

The tool runs a two-phase scan against a target website:

1. **Pre-consent scan** — using an incognito browser session with no interaction, to detect cookies set (and potential ePrivacy violations) before the user has given consent.
2. **Post-consent full crawl** — simulating consent and crawling the site to extract third-party tracking cookies and behavior.

Each scan produces a self-contained, interactive HTML report.

## Features

- Automated website crawling with a headless/incognito browser
- Cookie classification via a trained Random Forest model
- Two-phase scanning (pre-consent vs. post-consent) to detect ePrivacy issues
- Third-party tracker detection on the post-consent crawl
- Interactive, shareable HTML audit reports
- Model training pipeline (`train.sh`) separate from the scanning pipeline (`run.sh`)

## Tech Stack

- **Language:** Python
- **ML:** Random Forest classifier (scikit-learn) 
- **Output:** HTML (interactive reports)

## Project Structure

```
cookieML/
├── data/    # Training/reference data for cookie classification
├── model/   # Trained classifier
├── src/     # Core scanning and classification logic
├── docs/    # Documentation
├── main.py  # Entry point
├── run.sh   # Run a scan against a target site
└── train.sh # Train/retrain the classifier
```

## How to Run

```bash
# Run an audit against a site
./run.sh <site-url>

# Retrain the classifier
./train.sh
```

## Example Output

This repo includes real audit reports generated against live sites. Open any of them directly in a browser to see the tool's output.

## What I Learned

Building this project deepened my understanding of GDPR/ePrivacy compliance requirements, browser automation for compliance auditing, and applying a trained ML classifier to a real-world classification task (cookie categorization).

