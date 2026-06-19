# 🔍 AI-Based Business Lead Discovery & Market Intelligence System

An automated Python pipeline that discovers, audits, and classifies businesses based on their **digital presence gaps** — powered by AI intelligence and a premium **Streamlit** dashboard.

The system identifies businesses across manufacturing, healthcare, hospitality, education and other high-value sectors that lack an online presence or maintain outdated websites, scoring each lead's digital transformation potential.

![Python](https://img.shields.io/badge/Python-3.10+-3776ab?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?logo=streamlit&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_AI-1.5_Flash-4285F4?logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-Educational-green)

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Streamlit Dashboard                          │
│  ┌─────────┐  ┌───────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │Dashboard │  │Leads Table│  │ AI Analysis  │  │   Settings    │   │
│  │KPI+Chart │  │Filter+CSV │  │Detail + Score│  │API Status     │   │
│  └─────────┘  └───────────┘  └──────────────┘  └───────────────┘   │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
            ┌──────────────▼──────────────┐
            │      Pipeline Orchestrator   │
            │         core/__init__.py     │
            └──┬──────┬──────┬──────┬─────┘
               │      │      │      │
     ┌─────────▼┐ ┌───▼────┐ ┌▼─────┐ ┌──▼──────────┐
     │ Scraper  │ │Website │ │  AI  │ │Google Sheets │
     │SerpAPI   │ │Checker │ │Gemini│ │  gspread     │
     │JustDial  │ │SSL/Mob │ │OpenAI│ │  Append/     │
     │Sulekha   │ │Selenium│ │Rules │ │  Overwrite   │
     └──────────┘ └────────┘ └──────┘ └──────────────┘
```

### Pipeline Stages

| Stage | Module | Description |
|-------|--------|-------------|
| 1. Discovery | `core/scraper.py` | Collects business data from SerpAPI (Google Maps), JustDial, Sulekha |
| 2. Digital Audit | `core/website_checker.py` | Classifies each site as No Website / Poor / Good |
| 3. AI Analysis | `core/analyzer.py` | Scores lead potential (High/Medium/Low) with reasoning |
| 4. Export | `core/sheets_client.py` | Syncs results to Google Sheets automatically |

---

## 📁 Project Structure

```
internship_positiveway/
├── app/
│   └── streamlit_app.py          # Streamlit dashboard (main entry point)
├── core/
│   ├── __init__.py               # Pipeline orchestrator
│   ├── config.py                 # Environment config & constants
│   ├── scraper.py                # Multi-source data collection
│   ├── website_checker.py        # Website quality auditing
│   ├── analyzer.py               # AI + heuristic classification
│   ├── data_pipeline.py          # Pandas cleaning & deduplication
│   └── sheets_client.py          # Google Sheets integration
├── tests/
│   ├── test_scraper.py
│   ├── test_website_checker.py
│   └── test_analyzer.py
├── credentials/                  # GCP Service Account key (gitignored)
├── data/                         # Local CSV cache (gitignored)
├── .env.example                  # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.10+** installed
- **Google Chrome** (for Selenium fallback — optional)

### 2. Clone & Install

```bash
git clone https://github.com/Abhisar-else/AI-Based-Business-Lead-Discovery-.git
cd internship_positiveway
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the template
copy .env.example .env     # Windows
# cp .env.example .env     # macOS/Linux
```

Edit `.env` with your API keys:

```env
# AI Provider (choose one — both are free tier)
GEMINI_API_KEY=your-gemini-api-key-here

# Google Maps data source (optional but recommended)
SERPAPI_KEY=your-serpapi-key-here

# Google Sheets export
SPREADSHEET_ID=your-google-spreadsheet-id-here
GOOGLE_CREDENTIALS_PATH=credentials/google_credentials.json
```

#### Where to get API keys:

| Key | Free Tier | Get it at |
|-----|-----------|-----------|
| **Gemini AI** | Generous free tier | [aistudio.google.com](https://aistudio.google.com) |
| **SerpAPI** | 100 searches/month | [serpapi.com](https://serpapi.com) |
| **Google Sheets** | Free | [GCP Console](https://console.cloud.google.com/iam-admin/serviceaccounts) |

> **Note:** The system works without any API keys! It uses JustDial/Sulekha scraping as data sources and heuristic rules for classification when AI keys are not configured.

### 4. Google Sheets Setup (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Google Sheets API**
3. Create a **Service Account** → Download the JSON key
4. Save it as `credentials/google_credentials.json`
5. Create a Google Sheet → Copy its ID from the URL
6. **Share** the sheet with the service account email (found in the JSON key)

### 5. Run the Dashboard

```bash
streamlit run app/streamlit_app.py
```

The dashboard opens at `http://localhost:8501`.

---

## 📊 Dashboard Features

### Tab 1: Dashboard
- **KPI Cards** — Total leads, High/Medium/Low potential counts
- **Bar Chart** — Lead potential distribution
- **Donut Chart** — Website status breakdown (No Website / Poor / Good)
- **Contact metrics** — Email/Phone coverage percentages

### Tab 2: Leads Table
- **Filterable** by Potential, Website Status, and name search
- **Download CSV** — filtered or full dataset
- **Export to Google Sheets** — one-click sync

### Tab 3: AI Analysis
- **Individual lead inspector** — view all details for a single business
- **Potential score card** with color-coded badge
- **AI reasoning** — the model's explanation for the score
- **Google Maps link** and website link

### Tab 4: Settings
- **API status indicators** — green/orange for each service
- **Connection tester** for Google Sheets
- **Setup instructions** inline

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend / UI | Streamlit, Plotly |
| Data Collection | requests, BeautifulSoup4, Selenium, SerpAPI |
| AI Analysis | Google Gemini 1.5 Flash, OpenAI GPT-4o-mini |
| Data Processing | Pandas |
| Storage | Google Sheets (gspread), CSV cache |
| Config | python-dotenv |
| Testing | pytest, pytest-mock |

---

## 🧪 Running Tests

```bash
pytest tests/ -v --tb=short
```

---

## 📋 Data Output Schema

| Column | Description | Example |
|--------|-------------|---------|
| Business Name | Company name | Apex Manufacturing Ltd. |
| Industry Category | Business sector | Manufacturing |
| Business Description | Services summary | Industrial parts fabrication |
| Location | City / Address | Indore, MP |
| Google Maps Link | Maps profile URL | https://maps.google.com/... |
| Website URL | Business website | https://apex-fab.com |
| Website Status | No / Poor / Good Website | Poor Website |
| Phone Number | Contact phone | +91 98765 43210 |
| Email Address | Contact email | info@apex-fab.com |
| Owner / Founder | Leadership name | John Doe |
| LinkedIn Profile | LinkedIn URL | https://linkedin.com/... |
| Potential Category | High / Medium / Low | High |
| Reasoning | AI classification rationale | No online presence, high opportunity |

---

## ⚖️ License & Compliance

This software is intended for **educational purposes** and public data research. Always:
- Respect `robots.txt` and platform ToS
- Use appropriate rate limiting (built into the scraper)
- Never collect private or protected data
