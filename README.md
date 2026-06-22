# AI-Based Business Lead Discovery & Market Intelligence System

Python + Streamlit application for finding business leads, auditing their digital presence, classifying opportunity level with AI or rules, and exporting results to CSV or Google Sheets.

## What It Does

- Discovers businesses by industry and location.
- Pulls structured Google Maps-style results through Serper.dev when configured.
- Falls back to public directory scraping sources.
- Checks each business website for reachability, SSL, mobile readiness, load time, and contact signals.
- Classifies each lead as `High`, `Medium`, or `Low` potential using Gemini, OpenAI fallback, or deterministic heuristics.
- Shows results in a Streamlit dashboard with charts, filters, CSV download, and Google Sheets export.

## Architecture

```text
Streamlit Dashboard
        |
        v
core.run_pipeline()
        |
        +-- core.scraper          -> business discovery
        +-- core.website_checker  -> website quality audit
        +-- core.analyzer         -> AI/rule lead scoring
        +-- core.data_pipeline    -> cleaning, schema, CSV cache
        +-- core.sheets_client    -> Google Sheets append/refresh
```

## Project Structure

```text
internship_positiveway/
  app/
    streamlit_app.py
  core/
    __init__.py
    analyzer.py
    config.py
    data_pipeline.py
    scraper.py
    sheets_client.py
    website_checker.py
  tests/
    test_analyzer.py
    test_scraper.py
    test_sheets_client.py
    test_website_checker.py
  .env.example
  .gitignore
  README.md
  requirements.txt
```

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file:

```powershell
copy .env.example .env
```

Run the dashboard:

```bash
streamlit run app/streamlit_app.py
```

The app opens at `http://localhost:8501`.

## Environment Variables

```env
GEMINI_API_KEY=your-gemini-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
SERPER_API_KEY=your-serper-api-key-here

SPREADSHEET_ID=your-google-spreadsheet-id-here
SHEET_NAME=Business Leads
GOOGLE_CREDENTIALS_PATH=credentials/google_credentials.json
GOOGLE_SERVICE_ACCOUNT_JSON=
```

Only `SPREADSHEET_ID` plus one Google credential method is required for Google Sheets. AI and Serper keys are optional; the app has fallback behavior.

## Google Sheets Setup

1. Create or open a Google Sheet.
2. Copy the spreadsheet ID from its URL.
3. Put the ID in `.env` as `SPREADSHEET_ID`.
4. In Google Cloud Console, enable the Google Sheets API.
5. Create a Service Account and download its JSON key.
6. Save the JSON as `credentials/google_credentials.json`.
7. Share the Google Sheet with the service account email.
8. In the dashboard Settings tab, click `Test Connection`.

For hosted deployments, set `GOOGLE_SERVICE_ACCOUNT_JSON` to the full service-account JSON string instead of uploading a credentials file.

## Dashboard Features

- Sidebar search controls for industry, location, and max leads.
- API status indicators for Serper.dev, Gemini, OpenAI, and Google Sheets.
- Dashboard tab with KPI cards and Plotly charts.
- Leads table with filtering, search, CSV download, Sheets append, and Sheets refresh.
- AI Analysis tab for inspecting a single lead.
- Settings tab with setup status and Google Sheets connection test.

## Data Output Schema

| Column | Description |
| --- | --- |
| Business Name | Company or listing name |
| Industry Category | Selected/search category |
| Business Description | Listing description |
| Location | City or address |
| Google Maps Link | Maps/profile URL when available |
| Website URL | Business website |
| Website Status | No Website, Poor Website, or Good Website |
| Phone Number | Contact phone |
| Email Address | Contact email |
| Owner / Founder | Owner/founder if discovered |
| LinkedIn Profile | LinkedIn URL if discovered |
| Potential Category | High, Medium, or Low |
| Reasoning | AI or rule-based rationale |
| Collected At | Collection timestamp |

## Tests

Run the full suite:

```bash
pytest tests/ -v --tb=short
```

The test suite mocks network/API behavior and does not require real Google credentials.

## Safety Notes

- Do not commit `.env`.
- Do not commit `credentials/*.json`.
- Rotate any key that was ever accidentally committed or rejected by GitHub push protection.
- Respect target sites' terms of service and rate limits.
