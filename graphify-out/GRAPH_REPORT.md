# Graph Report - internship_positiveway  (2026-06-22)

## Corpus Check
- 16 files · ~10,911 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 212 nodes · 366 edges · 10 communities (8 shown, 2 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 6 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5a77c47c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]

## God Nodes (most connected - your core abstractions)
1. `WebsiteStatus` - 19 edges
2. `check_website()` - 16 edges
3. `analyze_business()` - 14 edges
4. `search_businesses()` - 13 edges
5. `extract_contact_info()` - 11 edges
6. `_clean_phone()` - 11 edges
7. `run_pipeline()` - 10 edges
8. `_analyze_with_heuristics()` - 10 edges
9. `_is_mobile_friendly()` - 10 edges
10. `_has_contact_info()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `TestCheckWebsite` --uses--> `WebsiteStatus`  [INFERRED]
  tests/test_website_checker.py → core/website_checker.py
- `TestClassify` --uses--> `WebsiteStatus`  [INFERRED]
  tests/test_website_checker.py → core/website_checker.py
- `TestHasContactInfo` --uses--> `WebsiteStatus`  [INFERRED]
  tests/test_website_checker.py → core/website_checker.py
- `TestMobileFriendly` --uses--> `WebsiteStatus`  [INFERRED]
  tests/test_website_checker.py → core/website_checker.py
- `run_pipeline()` --calls--> `analyze_business()`  [EXTRACTED]
  core/__init__.py → core/analyzer.py

## Import Cycles
- None detected.

## Communities (10 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (43): _progress_handler(), streamlit_app.py — AI Business Lead Discovery Dashboard  A premium Streamlit int, Callback from pipeline → UI updates., has_sheets_config(), build_dataframe(), clean_dataframe(), export_to_csv_bytes(), filter_by_potential() (+35 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (26): _build_detail_string(), check_website(), _check_with_requests(), _check_with_selenium(), _classify(), _has_contact_info(), _is_mobile_friendly(), BeautifulSoup (+18 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (32): has_serper_key(), _clean_phone(), extract_contact_info(), _extract_justdial_website(), _get_headers(), BeautifulSoup, scraper.py — Business Discovery & Data Collection Module  Strategy (anti-blockin, Scrape JustDial for business listings (India-focused).     Falls back gracefully (+24 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (17): analyze_business(), _analyze_with_gemini(), _analyze_with_openai(), get_analysis_mode(), analyzer.py — AI-Powered Business Intelligence Module  Uses Google Gemini 1.5 Fl, OpenAI GPT-4o-mini fallback with JSON mode., Classify a business lead's digital transformation potential.      Tries (in orde, Return human-readable description of the active analysis mode. (+9 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (20): 1. Prerequisites, 2. Clone & Install, 3. Configure Environment, 4. Google Sheets Setup (Optional), 5. Run the Dashboard, 🔍 AI-Based Business Lead Discovery & Market Intelligence System, 📊 Dashboard Features, 📋 Data Output Schema (+12 more)

### Community 5 - "Community 5"
Cohesion: 0.31
Nodes (4): _analyze_with_heuristics(), Rule-based classification used when no AI API is available.     Returns the same, Test the deterministic heuristic classifier., TestHeuristicAnalysis

### Community 6 - "Community 6"
Cohesion: 0.22
Nodes (8): Graphify Execution Implementation Plan, Task 1: Install Graphify & Establish Python Interpreter, Task 2: Detect Files, Task 3: Extraction (AST & Semantic), Task 4: Build Graph and Analyze, Task 5: Label Communities, Task 6: Export HTML Visualization, Task 7: Save Manifest & Cleanup

## Knowledge Gaps
- **26 isolated node(s):** `DataFrame`, `Response`, `graphify`, `Workflow: graphify`, `Pipeline Stages` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `check_website()` connect `Community 1` to `Community 0`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `search_businesses()` connect `Community 2` to `Community 0`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Why does `analyze_business()` connect `Community 3` to `Community 0`, `Community 5`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `WebsiteStatus` (e.g. with `TestCheckWebsite` and `TestClassify`) actually correct?**
  _`WebsiteStatus` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `streamlit_app.py — AI Business Lead Discovery Dashboard  A premium Streamlit int`, `Callback from pipeline → UI updates.`, `DataFrame` to the rest of the system?**
  _88 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.07493061979648474 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.08880666049953746 - nodes in this community are weakly interconnected._