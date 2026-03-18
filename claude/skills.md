# Claude Skills: Indian Job Market Visualizer

Last verified: 2026-03-18

## What this project is

An India-focused labour-market explorer — the Indian counterpart of Karpathy's US job treemap at karpathy.ai/jobs (source: github.com/karpathy/jobs). The product lets a user visually explore occupations across the Indian economy using an interactive treemap.

The interaction model:
- Each tile represents an occupation or occupation group
- Tile area represents employment size
- Tile color represents a selected metric
- The user can switch layers: pay, skill level, demand proxy, AI exposure
- Each occupation has a detail view with description, source metadata, and methodology notes

This is a transparent, source-backed research and visualization tool, not a formal government forecast.

## How the original US version works

The US version has a clean linear pipeline:

1. `parse_occupations.py` — parses the BLS A-Z index HTML into `occupations.json` (342 entries with title, URL, category, slug)
2. `scrape.py` — Playwright (non-headless, BLS blocks bots) downloads raw HTML for all 342 occupation detail pages into `html/`
3. `parse_detail.py` — converts one HTML page into clean Markdown (Quick Facts table, sections for duties, work environment, pay, outlook, etc.)
4. `process.py` — batch-runs `parse_detail.py` across all HTML files, outputting `pages/<slug>.md`
5. `make_csv.py` — BeautifulSoup extracts structured fields (pay, education, job count, growth outlook, SOC code) from HTML into `occupations.csv`
6. `score.py` — sends each occupation's Markdown description to an LLM (Gemini Flash via OpenRouter) with a scoring rubric, produces `scores.json` with 0-10 AI exposure + rationale
7. `build_site_data.py` — merges CSV stats and AI exposure scores into `site/data.json`
8. `site/index.html` — single-file static site with D3.js treemap, four color layers (BLS Outlook, Median Pay, Education, Digital AI Exposure)
9. `make_prompt.py` — generates `prompt.md`, a ~45K-token document packaging all data for LLM analysis

Tech stack: Python 3.10+, `uv` for dependency management, Playwright for scraping, BeautifulSoup for parsing, httpx for API calls, python-dotenv for secrets, D3.js for the frontend treemap. Dependencies in `pyproject.toml`, lockfile in `uv.lock`.

Key design choices:
- Raw HTML is the source of truth (cached in `html/`)
- Incremental caching at every pipeline stage (skip if output exists)
- `scores.json` checkpointed after each LLM call (resumable)
- Single-file frontend with no build step
- OpenRouter API key in `.env`

## Why India is harder

The US version relies on one institution (BLS) for everything: occupation definitions, wages, employment counts, outlook projections, education requirements, and detailed descriptions — all on standardized pages.

India requires a stitched-source approach:

| Data need | US source | India source | Status |
|-----------|-----------|--------------|--------|
| Occupation taxonomy | BLS SOC codes | NCO 2015 (Ministry of Labour) | PDF-based, ~4000 occupations across 4-digit codes |
| Employment counts | BLS OOH (per occupation) | PLFS annual report (MoSPI) | Published tables give 1-digit and 2-digit NCO breakdowns; unit-level microdata needed for finer granularity |
| Wages | BLS median annual pay per occupation | PLFS earnings tables (MoSPI) | Monthly, survey-based, limited occupation-level granularity in published tables |
| Education requirements | BLS entry-level education per occupation | No direct equivalent | Must proxy from NSDC qualification packs or NCO skill-level classification |
| Descriptions | BLS OOH detail pages (standardized HTML) | NCS occupation pages (ncs.gov.in) | Exist but format varies, not all NCO codes covered |
| Growth outlook | BLS 10-year projections per occupation | No equivalent | Must either omit or build a proxy from NCS vacancy signals |
| Skills / training | BLS on-the-job training field | NSDC Qualification Packs / NOS | Good coverage for formal-sector roles, weak for informal |

Additional India-specific challenges:
- Informality: ~80% of workforce is in the informal sector; portal vacancies only capture formal/semi-formal demand
- PLFS is a sample survey (~1 lakh households), not an administrative census
- Wage data is reported monthly and varies by rural/urban, regular/casual employment
- NCO 2015 has ~4000 fine-grained codes but PLFS published tables only report at 1-digit or 2-digit level
- NCS coverage is uneven — some occupations have rich pages, others are stubs
- NSDC qualification packs are sector-specific and don't map 1:1 to NCO codes
- No standardized "Quick Facts" table equivalent — parsing is source-specific

## Data sources (verified 2026-03-18)

### 1. NCO 2015 — National Classification of Occupations
- **Purpose:** Canonical occupation taxonomy (codes, titles, hierarchy, skill levels)
- **Publisher:** Ministry of Labour and Employment, Government of India
- **URL:** https://labour.gov.in/sites/default/files/National%20Classification%20of%20Occupations%20_Vol%20I-%202015.pdf
- **Format:** PDF (Volume I: structure and descriptions; Volume II: alphabetical index)
- **Coverage:** ~4000 occupation titles across 4-digit codes, organized into 10 major groups (1-digit), subdivisions (2-digit), minor groups (3-digit), and unit groups (4-digit)
- **Skill levels:** NCO defines 4 skill levels mapped to ISCED education bands
- **Notes:** This is the India equivalent of SOC codes. Use as the backbone for occupation_code and occupation_group. Pick an aggregation level (likely 2-digit or 3-digit) based on how much data you can attach from other sources.

### 2. PLFS — Periodic Labour Force Survey
- **Purpose:** Employment counts, workforce participation, earnings
- **Publisher:** MoSPI (Ministry of Statistics and Programme Implementation)
- **Latest annual report:** PLFS Annual Report, July 2023 – June 2024
- **URL:** https://www.mospi.gov.in/publication/periodic-labour-force-survey-plfs-annual-report-july-2023-june-2024
- **Format:** PDF with embedded tables; also check for Excel/CSV appendices
- **Key tables for this project:**
  - Distribution of workers by NCO 2015 division (1-digit) and subdivision (2-digit)
  - Average earnings by occupation group, sector (rural/urban), and employment type (regular wage/salaried, self-employed, casual)
  - Workforce participation rates
- **Microdata:** Unit-level PLFS data may be available at https://microdata.gov.in/ for deriving finer occupation-level estimates (3-digit or 4-digit NCO)
- **Methodology change:** MoSPI revised the short-term PLFS series in 2025. Monthly and quarterly bulletins after the revision are a different series — treat carefully. Reference: https://www.mospi.gov.in/publication/periodic-labour-force-survey-plfs-quarterly-bulletin
- **Notes:** PLFS is the closest India has to BLS employment data. Published tables usually go to 2-digit NCO; for finer granularity you need the microdata.

### 3. NCS — National Career Service
- **Purpose:** Occupation descriptions, tasks, sectors, related occupations, vacancy signals
- **Publisher:** Ministry of Labour and Employment
- **URL:** https://www.ncs.gov.in/content-repository/Pages/ViewNcoDetails.aspx
- **Format:** Web pages (server-rendered, may need Playwright)
- **Coverage:** Covers many NCO codes but not all; quality varies from rich descriptions to thin stubs
- **Vacancy data:** NCS also hosts a job portal; vacancy counts can serve as a demand proxy but must be labeled as portal-derived, not an employment forecast
- **Notes:** This is the closest equivalent to BLS OOH detail pages. The scraper for this project needs to handle the NCS page structure specifically. Some pages may require navigating through the NCO code tree.

### 4. NSDC — National Skill Development Corporation
- **Purpose:** Qualification packs, national occupational standards, skill metadata
- **Publisher:** NSDC India
- **URL:** https://nsdcindia.org/national-occupational-standards
- **Format:** Web; individual qualification pack PDFs
- **Coverage:** Organized by sector skill councils (~40 sectors); each sector has multiple job roles with defined competencies
- **Notes:** Useful for enriching education_proxy and training_context. Mapping NSDC job roles to NCO codes is not always 1:1 and may require fuzzy matching.

## Recommended data model

```
occupation_code       # NCO 2015 code (e.g., "21" for Science and Engineering Professionals)
occupation_title      # Human-readable title
occupation_group      # Parent group name
employment_count      # From PLFS; integer; attach coverage period
pay_median_monthly    # From PLFS earnings tables; INR; label as survey-based
pay_median_annual     # Derived: monthly * 12 (label as derived)
skill_level           # From NCO 2015 skill-level mapping (1-4)
education_proxy       # From NSDC qualification packs or NCO skill-level band
description           # From NCS occupation page
tasks                 # From NCS occupation page
training_context      # From NSDC qualification packs
demand_index          # From NCS vacancy counts; label as portal-derived proxy
demand_index_method   # "NCS vacancy count, retrieved YYYY-MM-DD"
ai_exposure           # 0-10, LLM-scored
ai_rationale          # 2-3 sentence explanation
source_meta           # JSON: {source_name, source_url, coverage_period, published_on, retrieved_on}
```

## Recommended pipeline (mirroring the US version's structure)

1. **build_taxonomy.py** — Parse NCO 2015 PDF into `data/raw/nco_2015.json` with all codes, titles, hierarchy, skill levels. Pick aggregation level.
2. **scrape_ncs.py** — Playwright scrape NCS occupation pages into `data/raw/ncs_html/`. Cache raw HTML.
3. **parse_ncs.py** — Convert NCS HTML into clean Markdown in `data/intermediate/ncs_pages/`. Extract descriptions and tasks.
4. **build_employment.py** — Extract PLFS employment and earnings tables into `data/intermediate/plfs_employment.csv`. May require PDF table extraction (camelot/tabula) or manual data entry for key tables.
5. **build_skills.py** — Scrape/parse NSDC qualification packs into `data/intermediate/nsdc_skills.json`.
6. **build_demand.py** — Extract NCS vacancy signals into `data/intermediate/ncs_demand.json`. Label explicitly as proxy.
7. **merge_occupations.py** — Join all intermediate data into `data/final/occupations_india.json` and `data/final/occupations_india.csv`.
8. **score.py** — LLM scoring via OpenRouter with India-specific rubric. Output `data/final/india_scores.json`. Checkpoint after each call.
9. **build_site_data.py** — Merge into compact `site/data-india.json`.
10. **site/index.html** — D3.js treemap with color layers: Pay, Skill Level, Demand Proxy, AI Exposure.
11. **make_prompt.py** — Package all data into a single `prompt.md` for LLM analysis.

## Recommended repo structure

```
jobs-india/
  data/
    raw/               # Unmodified source files (HTML, PDF extracts)
    intermediate/      # Parsed/cleaned per-source outputs
    final/             # Merged, ready-to-use datasets
  scripts/             # All pipeline scripts
  site/                # Static frontend
  docs/
    methodology.md     # Source explanations, coverage, gaps, proxies
  claude/              # Claude context files (this file, prompt.md)
  .env                 # OPENROUTER_API_KEY (gitignored)
  .gitignore
  pyproject.toml
  README.md
```

## Tech stack

- Python 3.10+, managed with `uv`
- Playwright for web scraping (NCS pages may block headless browsers)
- BeautifulSoup for HTML parsing
- camelot-py or tabula-py for PDF table extraction (PLFS tables)
- httpx for OpenRouter API calls
- python-dotenv for .env loading
- D3.js for the treemap frontend (single-file, no build step)

## Source discipline rules

- Keep `employment_count` (PLFS stock) separate from `vacancy_count` (NCS flow)
- Keep official statistics separate from portal-derived indicators
- Never call a proxy an official forecast
- Attach dates to every source reference
- If source years differ across fields, expose the mismatch in methodology
- If a field cannot be supported honestly, rename or drop it — do not fabricate data
- Prefer official sources over articles, blogs, or consulting decks

## AI exposure scoring — India calibration

The score measures how much AI is likely to reshape the work (not whether the job disappears). For India, the rubric must account for:

- **Informality:** Many occupations operate outside digital workflows; AI exposure is lower when work is informal, cash-based, and relationship-driven
- **Physical presence:** India has proportionally more physical, field-based, and manual work
- **Human intermediation:** Trust layers, local language negotiation, and in-person verification are common
- **Multilingual interaction:** Customer-facing work in India often requires navigating multiple languages and dialects
- **Digital infrastructure gaps:** Rural and semi-urban areas have lower internet penetration and digitization
- **Low-software but high-coordination work:** Many Indian occupations involve coordination, logistics, and people management without heavy software use

Calibration anchors (India-specific):
- 0-1 Minimal: agricultural labourers, construction workers, domestic helpers
- 2-3 Low: electricians, auto mechanics, security guards, anganwadi workers
- 4-5 Moderate: nurses, police constables, bank clerks, school teachers (primary)
- 6-7 High: college lecturers, middle managers, chartered accountants, journalists
- 8-9 Very high: software developers, data analysts, content writers, graphic designers
- 10 Maximum: data entry operators, BPO/KPO voice agents, medical transcriptionists
