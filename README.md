# ModelPulse

ModelPulse is a dataset-agnostic, comprehensive platform for model risk management, monitoring, and validation. It automates data profiling, metric calculation, stability monitoring, and performance evaluation without hardcoding any specific model's schema.

## Features

- **Dataset Agnostic**: Ingest any tabular CSV data and map it dynamically to standardized roles (`target`, `prediction_score`, `decision`, etc.).
- **Automatic Profiling**: Detect missing values, malformed timestamps, truncated risk ratings, and duplicate IDs automatically upon upload.
- **Advanced Metrics Engine**: Calculates AUC, Gini, KS, Bad Rates, Approval Rates, PSI (Population Stability Index), and CSI (Characteristic Stability Index).
- **Run Orchestration & Alerting**: Schedule runs against a stable or drifted baseline and automatically trigger alerts based on severity thresholds.
- **Fairness & Statistical Tests**: Includes Disparate Impact (4/5ths rule) analysis and statistical testing (Hosmer-Lemeshow, Chi-Square, Binomial, Mann-Whitney).
- **Automated Reporting**: Generates downloadable PDF and HTML reports with embedded Base64 charts.

## Prerequisites

- Python 3.10+
- `pip` or `uv` for dependency management

### Report Generation Engine (PDF, DOCX, HTML)

ModelPulse generates publication-grade governance reports in three formats:
- **PDF Reports**: Rendered via headless Puppeteer/Chromium (`app/scripts/generate_pdf.js`) for pixel-perfect KPMG report layouts, with automatic fallback to standalone HTML if headless Chrome dependencies are absent.
- **Word (DOCX) Reports**: Built natively via `python-docx` with embedded KPMG branding, regulatory tables, and high-resolution chart images.
- **Interactive HTML**: Self-contained single-page governance reports suitable for browser inspection and archival.

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd modelpulse-google
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   ```bash
   cp .env.example .env
   ```

4. **Run the server:**
   ```bash
   python -m uvicorn main:app --reload
   ```

5. **Run the Smoke Tests (Optional):**
   ```bash
   python scripts/smoke_test.py --phase 8
   ```
   This will run the full acceptance grid across all six synthetic datasets and verify 120/120 checks.

## The Two-Act Demo

You can demonstrate the power of ModelPulse using the included synthetic datasets in the `data/` directory.

### Act 1: The Standard Validation Flow

1. **The Baseline**
   - Upload `healthy_baseline.csv` and auto-map its columns.
   - Create a monitor and trigger a baseline run. The model is completely healthy.
2. **The Stable Current Period**
   - Upload `healthy_current_stable.csv`, map it, and run it against the baseline monitor.
   - ModelPulse confirms that performance and stability remain unchanged. Zero alerts are fired.
3. **The Drifted Current Period**
   - Upload `healthy_current_drifted.csv`, map it, and run it against the baseline monitor.
   - The dashboard lights up: PSI crosses the critical 0.25 threshold, AUC declines significantly, and the bad-rate-on-booked triples.
   - Generate an SR 11-7 PDF report to see the full audit trail.

### Act 2: When the Data Itself is the Problem

"What happens when the model is fundamentally broken from the start?"

1. **Upload the Client File**
   - Upload `underwriting_scorecard_clean.csv`.
   - The heuristic engine auto-maps `actual_default`, `model_score`, and `probability_of_default` correctly, despite the dataset's unique vocabulary.
2. **Review Insights**
   - Run the monitor standalone (no baseline needed).
   - The insights engine immediately spots severe issues without relying on confident nonsense:
     - **Band Consistency Error**: The `score_band` column contradicts the `model_score` for 13% of the rows.
     - **Score/PD Contradiction**: The `model_score` and `probability_of_default` have virtually zero correlation, indicating one of them is wildly incorrect.
     - **Decision-Score Gap**: The approved vs. declined score gap is near-zero (643.1 vs 644.8), proving that the decisions were not actually score-driven.
