# Indian Job Market Visualizer

An interactive occupation treemap for India's labour market, showing employment size, pay, skill levels, demand signals, and AI exposure across 43 occupation groups.

## What this is

This is an India-focused version of [Karpathy's US job treemap](https://karpathy.ai/jobs) ([source](https://github.com/karpathy/jobs)), rebuilt from the ground up using official Indian government data sources. Unlike the US version, which draws from a single institution (the Bureau of Labor Statistics), this project stitches together four separate Indian sources -- NCO 2015, PLFS, NCS, and NSDC -- because no single Indian source provides occupation-level employment counts, wages, descriptions, and growth projections in one place.

The project is honest about its limitations. Where data is unavailable or approximate, fields are labelled as proxies or estimates rather than presented as authoritative statistics.

## Demo

> Screenshot or live demo link to be added after deployment.

## Data sources

| Source | Publisher | What it provides |
|--------|-----------|-----------------|
| **NCO 2015** (National Classification of Occupations) | Ministry of Labour and Employment | Occupation taxonomy, skill levels |
| **PLFS 2023--24** (Periodic Labour Force Survey) | MoSPI | Employment counts, average earnings |
| **NCS** (National Career Service) | Ministry of Labour and Employment | Descriptions, tasks, vacancy signals |
| **NSDC** (National Skill Development Corporation) | NSDC India | Qualification packs, training context |

See [docs/methodology.md](docs/methodology.md) for detailed source documentation, coverage dates, and limitations.

## Quick start

**Prerequisites:** Python 3.10+, [uv](https://docs.astral.sh/uv/) (recommended) or pip.

```bash
# Clone and install
git clone https://github.com/your-username/jobs-india.git
cd jobs-india
pip install -e .          # or: uv pip install -e .

# Set up API key for AI exposure scoring
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Run the pipeline (each step caches its output; safe to re-run)
python scripts/build_taxonomy.py       # Build NCO 2015 taxonomy
python scripts/build_employment.py     # Extract PLFS employment and earnings
python scripts/build_skills.py         # Parse NSDC qualification packs
python scripts/build_demand.py         # Extract NCS vacancy demand signals
python scripts/merge_occupations.py    # Merge all sources into unified dataset
python scripts/score.py                # LLM-score AI exposure (requires OPENROUTER_API_KEY in .env)
python scripts/build_site_data.py      # Build compact frontend dataset

# View the visualization
# Open site/index.html in a browser
```

Each script is incremental: it skips work if output files already exist. Use `--force` to regenerate.

## Project structure

```
jobs-india/
  data/
    raw/                   # Unmodified source files (PDFs, HTML, JSON)
    intermediate/          # Parsed and cleaned per-source outputs
    final/                 # Merged datasets ready for scoring and frontend
  scripts/
    build_taxonomy.py      # Parse NCO 2015 into occupation taxonomy
    scrape_ncs.py          # Playwright scraper for NCS occupation pages
    parse_ncs.py           # Convert NCS HTML into structured data
    build_employment.py    # Extract PLFS employment and earnings tables
    build_skills.py        # Parse NSDC qualification packs
    build_demand.py        # Extract NCS vacancy demand signals
    merge_occupations.py   # Join all sources into unified records
    score.py               # LLM-based AI exposure scoring via OpenRouter
    build_site_data.py     # Build site/data-india.json for the frontend
    make_prompt.py         # Package all data into a prompt for LLM analysis
  site/
    index.html             # Single-file D3.js treemap visualization
    data-india.json        # Compact dataset for the frontend (generated)
  docs/
    methodology.md         # Detailed source documentation and limitations
  claude/
    prompt.md              # Project specification and context
    skills.md              # Claude skills context
  .env                     # OPENROUTER_API_KEY (gitignored)
  .env.example             # Template for .env
  .gitignore
  pyproject.toml
  README.md
```

## Methodology

The full methodology document is at [docs/methodology.md](docs/methodology.md). It covers:

- What each source provides and what it does not
- How fields were derived (including which are official statistics vs. proxies vs. model estimates)
- Date mismatches between sources (NCO 2015 taxonomy, PLFS 2023--24 data, NCS/NSDC retrieved 2026)
- What the dataset does not claim
- How to update when new data is published

## Key differences from the US version

| Aspect | US version | India version |
|--------|-----------|---------------|
| **Granularity** | ~342 individual occupations | 43 occupation groups (2-digit NCO) |
| **Data source** | Single source (BLS) | Four stitched sources (NCO, PLFS, NCS, NSDC) |
| **Pay statistic** | Median annual pay per occupation | Average (mean) monthly earnings per group |
| **Education** | BLS entry-level education per occupation | Proxy from NCO skill levels and NSDC QPs |
| **Growth outlook** | BLS 10-year projections | NCS vacancy count proxy (not a forecast) |
| **Informal sector** | Small share of US workforce | ~80% of Indian workforce; portal data captures formal/semi-formal only |
| **AI exposure calibration** | US-centric scoring | India-specific rubric accounting for informality, physical work, multilingual interaction, and digital infrastructure |

## Honest limitations

Before using this data, understand what it does not cover:

- **No employment forecasts.** India does not publish occupation-level employment projections. The demand index is a portal-derived vacancy snapshot, not a projection.
- **Pay figures are averages, not medians.** Averages are pulled upward by high earners and may not represent what a typical worker earns.
- **Portal data misses the informal sector.** Approximately 80% of India's workforce is informal. NCS vacancies and NSDC qualification packs primarily reflect formal and semi-formal employment.
- **2-digit aggregation is coarse.** Each group contains occupations with wide variation in pay, skill requirements, and AI exposure. Group-level statistics smooth over this variation.
- **AI exposure scores are model estimates.** An LLM scored each occupation using a rubric. These are not empirical measurements.
- **The NCO 2015 taxonomy is from 2015.** Emerging occupations (gig economy, AI/ML, social media) lack dedicated codes.
- **Source dates do not align.** The taxonomy is from 2015, employment data from 2023--24, and web-scraped data from 2026.

## License

MIT

## Acknowledgments

- Inspired by [Andrej Karpathy's jobs project](https://github.com/karpathy/jobs) and the [US Job Market Visualizer](https://karpathy.ai/jobs)
- Occupation taxonomy from the [National Classification of Occupations 2015](https://labour.gov.in/), Ministry of Labour and Employment, Government of India
- Employment and earnings data from the [Periodic Labour Force Survey](https://www.mospi.gov.in/), Ministry of Statistics and Programme Implementation, Government of India
- Occupation descriptions from the [National Career Service](https://www.ncs.gov.in/), Ministry of Labour and Employment, Government of India
- Skills and training data from the [National Skill Development Corporation](https://nsdcindia.org/)
