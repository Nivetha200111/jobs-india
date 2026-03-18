# Build an Indian Job Market Visualizer

You are building a new repository from scratch.

This project is an India-focused labour-market visualization tool inspired by Karpathy's US job treemap (karpathy.ai/jobs, github.com/karpathy/jobs). It must be honest about the fact that India does not have one single BLS-style source.

## Project goal

Build a research-grade interactive explorer of Indian occupations.

The final product should let a user:

- See occupations as a treemap
- Compare occupations by employment size (tile area)
- Switch color layers: pay, skill level, demand proxy, AI exposure
- Inspect each occupation to understand what the job is, how common it is, how it is paid, what skills it tends to require, and how AI may reshape it
- Read a methodology page that clearly explains sources, coverage, gaps, and proxy fields

## What you are building

A repo with these major parts:

### 1. Data ingestion layer
Fetch or load official Indian labour-market and occupation sources:
- NCO 2015 PDF → occupation taxonomy
- PLFS annual tables → employment and earnings
- NCS web pages → occupation descriptions and vacancy signals
- NSDC web pages → qualification packs and skills metadata

### 2. Normalization layer
Convert those heterogeneous sources into a consistent occupation dataset with one record per occupation containing all available fields plus source provenance.

### 3. Scoring layer
Run an LLM scoring pass over each occupation to add AI exposure scores (0-10) with India-specific calibration.

### 4. Presentation layer
Build a compact frontend dataset and a single-file static site with a D3.js treemap visualization.

### 5. Methodology layer
A `docs/methodology.md` that explains every source, every proxy, every date mismatch, and what the dataset does not claim.

## The original US pipeline (for reference)

The US version this is based on has this pipeline:

```
parse_occupations.py  → occupations.json (342 entries: title, url, category, slug)
scrape.py             → html/<slug>.html (raw BLS pages, Playwright, non-headless)
parse_detail.py       → pages/<slug>.md (clean Markdown per occupation)
process.py            → batch wrapper for parse_detail.py
make_csv.py           → occupations.csv (structured fields from HTML)
score.py              → scores.json (AI exposure 0-10 + rationale via OpenRouter)
build_site_data.py    → site/data.json (compact merge of CSV + scores)
site/index.html       → D3.js treemap, 4 color layers
make_prompt.py        → prompt.md (all data in one file for LLM analysis)
```

Key design patterns to carry forward:
- Raw source files are the source of truth, cached locally
- Every pipeline stage is incremental (skip if output exists)
- LLM scores are checkpointed after each call (resumable)
- Frontend is a single HTML file with no build step
- OpenRouter for LLM calls (API key in `.env`)

## Official source stack

As of 2026-03-18, use these sources in this priority order:

### Source 1: NCO 2015 — occupation taxonomy
- **What:** National Classification of Occupations 2015
- **Publisher:** Ministry of Labour and Employment
- **URL:** https://labour.gov.in/sites/default/files/National%20Classification%20of%20Occupations%20_Vol%20I-%202015.pdf
- **Format:** PDF
- **Use for:** occupation_code, occupation_title, occupation_group, skill_level (NCO defines 4 skill levels)
- **Coverage:** ~4000 occupation titles at 4-digit level, 10 major groups at 1-digit
- **Notes:** Pick an aggregation level (2-digit or 3-digit) based on how much employment data you can attach. Going to 4-digit will leave many codes with no PLFS data.

### Source 2: PLFS — employment and earnings
- **What:** Periodic Labour Force Survey Annual Report, July 2023 – June 2024
- **Publisher:** MoSPI
- **URL:** https://www.mospi.gov.in/publication/periodic-labour-force-survey-plfs-annual-report-july-2023-june-2024
- **Format:** PDF with tables (may need camelot/tabula for extraction)
- **Use for:** employment_count, pay_median_monthly, workforce participation
- **Key tables:**
  - Distribution of workers by NCO 2015 division (1-digit) and subdivision (2-digit)
  - Average earnings by NCO division, sector (rural/urban), employment type
- **Newer releases:** MoSPI revised the short-term PLFS methodology in 2025. The latest quarterly/monthly bulletins exist but represent a changed series — use with caution.
  - Latest quarterly: PLFS Quarterly Bulletin, October-December 2025
  - Latest monthly: PLFS Monthly Bulletin, January 2026
  - Methodology change reference: https://www.mospi.gov.in/publication/periodic-labour-force-survey-plfs-quarterly-bulletin
- **Microdata:** For finer-grained occupation-level estimates, unit-level PLFS data may be at https://microdata.gov.in/ — re-check availability before attempting.

### Source 3: NCS — descriptions and demand signals
- **What:** National Career Service occupation pages
- **Publisher:** Ministry of Labour and Employment
- **URL:** https://www.ncs.gov.in/content-repository/Pages/ViewNcoDetails.aspx
- **Format:** Server-rendered web pages (likely needs Playwright)
- **Use for:** description, tasks, sectors, related occupations, vacancy_count
- **Coverage:** Many NCO codes covered but not all; quality varies
- **Vacancy data:** NCS is also a job portal — vacancy counts can serve as a demand proxy but must be labeled as portal-derived, never as employment or forecast

### Source 4: NSDC — skills and training
- **What:** Qualification Packs and National Occupational Standards
- **Publisher:** NSDC India
- **URL:** https://nsdcindia.org/national-occupational-standards
- **Format:** Web pages, individual QP PDFs
- **Use for:** education_proxy, training_context, competency requirements
- **Coverage:** ~40 sector skill councils, each with multiple job roles
- **Notes:** NSDC job roles don't map 1:1 to NCO codes; fuzzy matching required

### Source 5: Microdata archive
- **What:** Unit-level PLFS survey data
- **Publisher:** MoSPI
- **URL:** https://microdata.gov.in/
- **Use for:** Deriving occupation-level employment and earnings at 3-digit or 4-digit NCO when published tables are insufficient
- **Notes:** May lag behind the annual report year. Check availability before building a dependency.

## Non-negotiable rules

1. Never claim an official India-wide occupation forecast if you cannot cite one
2. Never treat portal vacancies as total employment
3. Never mix stock metrics (employment) and flow metrics (vacancies) without labeling
4. Never present a proxy as a direct equivalent of a missing official field
5. Always record absolute dates for source coverage and retrieval
6. Prefer official government sources over articles, blogs, or consulting reports
7. If a field cannot be supported honestly, rename or drop it — do not fabricate

## Data model

Each occupation record should contain:

```json
{
  "occupation_code": "21",
  "occupation_title": "Science and Engineering Professionals",
  "occupation_group": "Professionals",
  "employment_count": 5200000,
  "pay_median_monthly": 35000,
  "pay_median_annual": 420000,
  "skill_level": 4,
  "education_proxy": "Bachelor's degree or higher (NCO skill level 4)",
  "description": "Science and engineering professionals conduct research...",
  "tasks": ["Conduct research", "Design experiments", "..."],
  "training_context": "Relevant NSDC qualification packs: ...",
  "demand_index": 1250,
  "demand_index_method": "NCS vacancy count, retrieved 2026-03-18",
  "ai_exposure": 7,
  "ai_rationale": "Predominantly knowledge work with significant digital component...",
  "source_meta": {
    "employment": {"source": "PLFS Annual Report Jul 2023-Jun 2024", "url": "...", "coverage": "Jul 2023-Jun 2024", "retrieved": "2026-03-18"},
    "description": {"source": "NCS", "url": "...", "retrieved": "2026-03-18"},
    "skills": {"source": "NSDC QP", "url": "...", "retrieved": "2026-03-18"}
  }
}
```

## Implementation plan

### Step 1: Repository setup
```
jobs-india/
  data/
    raw/                 # Unmodified downloads (HTML, PDF extracts, CSVs)
    intermediate/        # Parsed per-source outputs
    final/               # Merged datasets ready for scoring and frontend
  scripts/               # All pipeline scripts
  site/                  # Static frontend (index.html + data-india.json)
  docs/
    methodology.md       # Source documentation
  claude/                # Claude context (skills.md, prompt.md)
  .env                   # OPENROUTER_API_KEY (gitignored)
  .gitignore
  pyproject.toml
  README.md
```

pyproject.toml dependencies:
```toml
[project]
name = "jobs-india"
version = "0.1.0"
description = "Indian Job Market Visualizer — occupation treemap with AI exposure scoring"
requires-python = ">=3.10"
dependencies = [
    "beautifulsoup4>=4.14.0",
    "httpx>=0.28.0",
    "playwright>=1.58.0",
    "python-dotenv>=1.2.0",
    "camelot-py[cv]>=0.11.0",
    "tabula-py>=2.9.0",
]
```

### Step 2: Build taxonomy (scripts/build_taxonomy.py)
- Parse NCO 2015 PDF into `data/raw/nco_2015.json`
- Extract all codes at 1-digit, 2-digit, 3-digit, and 4-digit levels
- Include: code, title, parent_code, skill_level, description (where available)
- Decide the working aggregation level based on data availability from other sources
- Output: `data/raw/nco_2015.json`

### Step 3: Extract PLFS data (scripts/build_employment.py)
- Extract employment and earnings tables from the PLFS Annual Report PDF
- Use camelot-py or tabula-py for table extraction; fall back to manual data entry if PDF tables are too messy
- Map to NCO codes at the available granularity
- Output: `data/intermediate/plfs_employment.csv` with columns: nco_code, employment_count, avg_monthly_earnings, sector (rural/urban/combined), employment_type, coverage_period
- If published tables only go to 2-digit NCO, that's the ceiling unless you use microdata

### Step 4: Scrape NCS pages (scripts/scrape_ncs.py)
- Use Playwright to navigate the NCS occupation repository
- For each NCO code in the taxonomy, attempt to load the NCS detail page
- Save raw HTML to `data/raw/ncs_html/<nco_code>.html`
- Cache: skip if HTML already exists
- Be polite: 1-2 second delay between requests

### Step 5: Parse NCS pages (scripts/parse_ncs.py)
- Convert raw NCS HTML into structured data
- Extract: description, tasks, sectors, typical employers, related occupations
- Output: `data/intermediate/ncs_pages/<nco_code>.md` (Markdown) and `data/intermediate/ncs_data.json` (structured)

### Step 6: Build skills layer (scripts/build_skills.py)
- Scrape or parse NSDC qualification packs relevant to each occupation group
- Extract: education/training requirements, key competencies
- Map to NCO codes (fuzzy matching where needed)
- Output: `data/intermediate/nsdc_skills.json`

### Step 7: Build demand proxy (scripts/build_demand.py)
- Extract NCS vacancy counts or activity signals per occupation code
- Label explicitly as "portal-derived demand proxy"
- Output: `data/intermediate/ncs_demand.json`

### Step 8: Merge everything (scripts/merge_occupations.py)
- Join taxonomy + PLFS + NCS + NSDC + demand into unified records
- One record per occupation at the chosen aggregation level
- Handle missing data: set to null, never fabricate
- Track provenance per field
- Output: `data/final/occupations_india.json` and `data/final/occupations_india.csv`

### Step 9: Score AI exposure (scripts/score.py)
- For each occupation, send its description + metadata to an LLM via OpenRouter
- Use India-specific scoring rubric (see below)
- Temperature 0.2, structured JSON response
- Checkpoint after each call to `data/final/india_scores.json`
- Resumable: skip already-scored occupations

### Step 10: Build site data (scripts/build_site_data.py)
- Merge occupations + scores into compact `site/data-india.json`
- Only include fields needed by the frontend
- Output: `site/data-india.json`

### Step 11: Build frontend (site/index.html)
- Single-file static site
- D3.js treemap
- Color layers: Pay (INR), Skill Level (NCO 1-4), Demand Proxy (NCS vacancies), AI Exposure (0-10)
- Tile area: employment count
- Tooltips with occupation details
- Legend explaining each metric and its source
- Methodology link
- Clear labels distinguishing official data from proxies

### Step 12: Generate analysis prompt (scripts/make_prompt.py)
- Package all occupation data, aggregate statistics, tier breakdowns, and scoring rationale into a single Markdown file
- Designed for copy-paste into an LLM for data-grounded conversation
- Output: `prompt.md` at repo root

### Step 13: Write methodology (docs/methodology.md)
- Explain every source: what it provides, what it doesn't, coverage dates
- Explain every proxy: what it approximates, how it was derived
- Explain date mismatches between sources
- Explain aggregation decisions
- Explain what the dataset does NOT claim
- Explain AI exposure scoring methodology and India-specific calibration

## AI exposure scoring rubric (India-specific)

Use this system prompt for scoring:

```
You are an expert analyst evaluating how exposed different occupations are to AI, specifically in the Indian labour market context.

Rate the occupation's overall AI Exposure on a scale from 0 to 10.

AI Exposure measures: how much will AI reshape this occupation in India? Consider direct effects (AI automating tasks) and indirect effects (AI making workers so productive that fewer are needed).

India-specific considerations:
- Informality: Many occupations operate outside digital workflows with cash-based, relationship-driven transactions. AI exposure is lower for informal work.
- Physical presence: India has proportionally more physical, field-based, and manual work than the US.
- Human intermediation: Trust layers, local language negotiation, and in-person verification are common in Indian business.
- Multilingual interaction: Customer-facing work often requires navigating multiple languages and dialects.
- Digital infrastructure: Rural and semi-urban areas have lower internet penetration and digitization.
- Low-software but high-coordination work: Many Indian occupations involve coordination, logistics, and people management without heavy software use.

The key signal remains whether the work product is fundamentally digital. If the job can be done entirely on a computer — writing, coding, analyzing — AI exposure is high (7+). But in India, more occupations have physical, informal, or interpersonal barriers than equivalent US roles.

Calibration anchors for India:
- 0-1 Minimal: agricultural labourers, construction workers, domestic helpers, street vendors
- 2-3 Low: electricians, auto mechanics, security guards, anganwadi workers, tailors
- 4-5 Moderate: nurses, police constables, bank clerks, primary school teachers, lab technicians
- 6-7 High: college lecturers, middle managers, chartered accountants, journalists, pharmacists
- 8-9 Very high: software developers, data analysts, content writers, graphic designers, financial analysts
- 10 Maximum: data entry operators, BPO/KPO voice agents, medical transcriptionists

Respond with ONLY a JSON object:
{"exposure": <0-10>, "rationale": "<2-3 sentences explaining key factors in India context>"}
```

## UI and copy requirements

The interface must make these distinctions clear to users:
- **Official survey-based employment** (PLFS) vs **portal-derived demand** (NCS vacancies)
- **Survey-based pay** (PLFS average monthly earnings) vs no equivalent of BLS median annual pay
- **Taxonomy source** (NCO 2015)
- **Model-derived scores** (AI exposure via LLM)
- **Education proxy** (derived from NCO skill levels / NSDC, not official per-occupation requirements)

Avoid product copy that sounds more certain than the data really is. Use phrases like "estimated from survey data", "portal-derived proxy", "LLM-scored estimate" in tooltips and legends.

## Definition of done

The project is done when a new user can open the repo and understand:
- What the project is
- What question it answers
- Where the data came from
- Which fields are official statistics
- Which fields are proxies or model-derived
- How the visualization should be interpreted
- What the dataset does NOT claim

Build something honest, inspectable, and useful rather than something that imitates the US version too literally.
