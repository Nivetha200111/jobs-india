# Methodology

## Overview

The Indian Job Market Visualizer is an interactive occupation treemap for India's labour market. It attempts to answer the question: **what does the landscape of Indian occupations look like when measured by employment size, pay, skill level, labour demand signals, and exposure to AI?**

The dataset is built by stitching together multiple official Indian government sources, each with different coverage periods, granularity levels, and data collection methods. Unlike the US version of this project (which draws from a single institution, the Bureau of Labor Statistics), no single Indian source provides all the fields needed. This document explains exactly what each source contributes, what decisions were made to combine them, and what the resulting dataset does **not** claim.

This is a research and visualization tool, not an official government publication.

---

## Source stack

### Source 1: NCO 2015 (National Classification of Occupations)

| Attribute | Detail |
|-----------|--------|
| **What it provides** | Occupation taxonomy: codes, titles, hierarchy (major group > subdivision > minor group > unit group), skill levels (1--4) mapped to ISCED education bands |
| **Publisher** | Ministry of Labour and Employment, Government of India |
| **Format** | PDF (Volume I: structure and descriptions; Volume II: alphabetical index) |
| **Coverage** | Approximately 4,000 occupation titles at the 4-digit (unit group) level, organized into 10 major groups at the 1-digit level. This project uses the **2-digit subdivision level** (43 occupations) |
| **URL** | https://labour.gov.in/sites/default/files/National%20Classification%20of%20Occupations%20_Vol%20I-%202015.pdf |
| **Base standard** | NCO 2015 closely follows ISCO-08 (International Standard Classification of Occupations) |
| **Retrieval date** | 2026-03-18 |

**What NCO 2015 does not provide:** Employment counts, wages, demand forecasts, or descriptions rich enough to stand alone. It is a classification system, not a labour market survey.

**Skill levels defined by NCO 2015:**

| Skill Level | ISCED Equivalent | Typical Education |
|-------------|-----------------|-------------------|
| 1 | ISCED 1 | Primary education or less |
| 2 | ISCED 2--3 | Secondary education, apprenticeship |
| 3 | ISCED 5 | Diploma, associate degree |
| 4 | ISCED 6--8 | Bachelor's degree or higher |

---

### Source 2: PLFS Annual Report, July 2023 -- June 2024

| Attribute | Detail |
|-----------|--------|
| **What it provides** | Employment counts (distribution of workers by occupation), average monthly earnings by occupation group and sector, workforce participation rates |
| **Publisher** | Ministry of Statistics and Programme Implementation (MoSPI) |
| **Format** | PDF with embedded tables |
| **Coverage period** | July 2023 through June 2024 |
| **URL** | https://www.mospi.gov.in/publication/periodic-labour-force-survey-plfs-annual-report-july-2023-june-2024 |
| **Retrieval date** | 2026-03-18 |

**Limitations:**

- PLFS is a **sample survey** covering approximately 1 lakh (100,000) households. It is not a census or administrative count. All employment figures are survey estimates with associated sampling error.
- Published tables in the annual report only report occupation-level data at the **1-digit and 2-digit NCO level**. Per-occupation detail at the 3-digit or 4-digit level would require unit-level microdata, which may or may not be available at https://microdata.gov.in/.
- Earnings data in published tables are **averages (means), not medians**. The field `pay_median_monthly` in the dataset is labelled with this caveat; the name was chosen for parity with the US version's field structure, but the underlying statistic is an average. This distinction matters because averages are pulled upward by high earners.
- Earnings are reported separately for rural and urban sectors and by employment type (regular wage/salaried, self-employed, casual labour). The combined figure used in this dataset is a weighted combination, not a simple average of the two sectors.
- MoSPI revised the short-term PLFS methodology in 2025. Monthly and quarterly bulletins after the revision represent a different series and are not directly comparable to the annual report figures used here.

---

### Source 3: NCS (National Career Service)

| Attribute | Detail |
|-----------|--------|
| **What it provides** | Occupation descriptions, task lists, sector information, related occupations, and vacancy counts (as a demand signal) |
| **Publisher** | Ministry of Labour and Employment |
| **Format** | Server-rendered web pages (scraped using Playwright) |
| **URL** | https://www.ncs.gov.in/content-repository/Pages/ViewNcoDetails.aspx |
| **Coverage** | Many NCO codes are covered, but not all. Quality varies from rich, detailed pages to thin stubs with minimal information |
| **Retrieval date** | 2026-03-18 |

**Important caveat about vacancy counts:** NCS is also a government job portal. The vacancy counts extracted from NCS pages reflect **listings on this specific portal**, not total job openings across the Indian economy, and certainly not employment forecasts. Portal-derived vacancy counts are influenced by which employers choose to list on NCS, which tends to skew toward government and formal-sector positions. They should be treated as a **directional signal**, not a measurement of labour demand.

---

### Source 4: NSDC (National Skill Development Corporation)

| Attribute | Detail |
|-----------|--------|
| **What it provides** | Qualification Packs (QPs), National Occupational Standards (NOS), competency requirements, education and training context for job roles |
| **Publisher** | NSDC India, via approximately 40 Sector Skill Councils |
| **Format** | Web pages and individual qualification pack PDFs |
| **URL** | https://nsdcindia.org/national-occupational-standards |
| **Coverage** | Organized by sector skill council; each sector has multiple job roles with defined competencies. Coverage is strongest for formal-sector roles with established training pathways |
| **Retrieval date** | 2026-03-18 |

**Mapping challenge:** NSDC job roles do not map 1:1 to NCO codes. A single NCO 2-digit subdivision may correspond to dozens of NSDC qualification packs across multiple sector skill councils, or to none at all. Mapping required fuzzy matching and manual review. The resulting `education_proxy` and `training_context` fields are best-effort derivations, not official per-occupation education requirements.

---

## Aggregation decisions

### Why 2-digit NCO?

The choice to aggregate at the 2-digit NCO subdivision level (43 occupations) was driven by data availability:

- **PLFS published tables** report employment distribution and earnings at the 1-digit and 2-digit NCO level. Going finer (3-digit or 4-digit) would require unit-level microdata that may not be publicly available or may lag behind the annual report year.
- **NCS pages** are organized around NCO codes and can be scraped at multiple levels, but coverage becomes patchier at finer granularity.
- **NSDC qualification packs** map more naturally to specific job roles than to NCO subdivisions; at 2-digit, aggregation is feasible.

The 2-digit level provides the best balance of:

1. Enough granularity to be interesting (43 distinct occupation groups vs. 10 at 1-digit)
2. Enough data coverage to populate most fields for most occupations
3. Enough sample size within each group for PLFS estimates to be meaningful

The US version uses approximately 342 individual occupations (roughly equivalent to 6-digit SOC codes). The 2-digit NCO level is a much coarser view. This is an honest trade-off driven by what the published Indian data supports.

---

## Field-by-field methodology

### `occupation_code` and `occupation_title`

- **Source:** NCO 2015
- **Method:** Directly from the classification. Codes are 2-digit strings (e.g., "21" for Science and Engineering Professionals).

### `occupation_group`

- **Source:** NCO 2015
- **Method:** The parent 1-digit major group title (e.g., "Professionals" for all codes 21--26).

### `employment_count`

- **Source:** PLFS Annual Report, July 2023 -- June 2024
- **What it represents:** Estimated number of workers in the Indian economy employed in this occupation group during the survey period. This is a **survey estimate**, not a census count. The PLFS samples approximately 1 lakh households; national estimates are derived through statistical weighting.
- **Units:** Persons (in thousands or absolute count, depending on the table extracted)
- **Important:** These are point-in-time estimates with sampling uncertainty. PLFS does not publish confidence intervals in its summary tables, but the underlying sample size means estimates for smaller occupation groups carry more uncertainty.

### `pay_median_monthly`

- **Source:** PLFS Annual Report, July 2023 -- June 2024, earnings tables
- **What it actually is:** Despite the field name, this is the **average (mean) monthly earnings**, not the median. PLFS published tables report averages. The field name was retained for structural compatibility with the US version of this project, but users should understand this is a mean.
- **Why this matters:** Mean earnings are pulled upward by high earners. In occupation groups with wide pay dispersion (e.g., Managers, where a CEO and a small shop manager are in the same group), the average will overstate what a typical worker earns.
- **Sector combination:** The figure combines rural and urban sectors. PLFS reports these separately; the combined figure used here is a weighted combination based on the employment distribution across sectors.
- **Currency:** Indian Rupees (INR), monthly

### `pay_median_annual`

- **Source:** Derived
- **Method:** `pay_median_monthly * 12`. This is a simple annualization and does not account for seasonal employment patterns, bonuses, or other non-monthly compensation. Many Indian workers, especially in agriculture and construction, do not work all 12 months.

### `skill_level`

- **Source:** NCO 2015
- **What it represents:** The NCO-defined skill level (1--4) for the occupation subdivision. These map to ISCED education bands:
  - Level 1: Primary education or less
  - Level 2: Secondary education, apprenticeship
  - Level 3: Diploma, associate degree
  - Level 4: Bachelor's degree or higher
- **Limitation:** The skill level is assigned at the subdivision level and applies uniformly to all occupations within that group. Individual workers within a group may have education levels that differ significantly from the group's assigned skill level.

### `education_proxy`

- **Source:** Derived from NCO 2015 skill levels and NSDC Qualification Packs
- **What it is:** A best-effort estimate of the typical education or training level associated with an occupation group. It is constructed by:
  1. Starting with the NCO skill level band
  2. Cross-referencing with NSDC Qualification Packs that map to the occupation group
  3. Synthesizing a representative description (e.g., "Bachelor's degree or higher (NCO skill level 4)")
- **What it is NOT:** This is not equivalent to the BLS "typical entry-level education" field, which is assigned per occupation based on detailed analysis. The Indian education proxy is a group-level derivation, not an official per-occupation requirement.

### `description` and `tasks`

- **Source:** NCS occupation pages where available
- **Method:** Scraped from NCS and extracted via HTML parsing. Where NCS pages are stubs or unavailable, descriptions fall back to the NCO 2015 classification text embedded in the taxonomy.
- **Coverage:** Not all occupation codes have rich NCS pages. Some descriptions are thin.

### `training_context`

- **Source:** NSDC Qualification Packs
- **Method:** Relevant NSDC QPs mapped to the occupation group, with key competencies summarized.
- **Coverage:** Strongest for formal-sector roles with established skill council coverage. Weak or absent for informal-sector occupations.

### `demand_index`

- **Source:** NCS vacancy counts
- **Method:** Count of active vacancies listed on the NCS job portal for occupation codes within the group, at the time of retrieval.
- **Critical caveat:** This is a **portal-derived proxy**, not an employment forecast. It reflects listings on one government job portal and is biased toward:
  - Government and public-sector positions
  - Formal-sector employers
  - Employers who choose to use NCS specifically
- It does not capture private-sector hiring through other channels (Naukri, LinkedIn, direct hiring, informal networks, etc.).
- It should never be interpreted as "number of jobs available" or "projected job growth."

### `demand_index_method`

- **Source:** Metadata
- **Content:** A string describing the method, e.g., "NCS vacancy count, retrieved 2026-03-18"

### `ai_exposure`

- **Source:** LLM-scored (model-derived estimate)
- **Method:** Each occupation's description and metadata are sent to a large language model (via OpenRouter) with an India-specific scoring rubric. The model assigns a score from 0 to 10 based on how much AI is expected to reshape the occupation in the Indian context.
- **India-specific calibration factors:**
  - Informality: Occupations operating outside digital workflows receive lower scores
  - Physical presence: India has proportionally more physical, field-based work
  - Human intermediation: Trust layers, local language negotiation, and in-person verification are common
  - Multilingual interaction: Customer-facing work often requires navigating multiple languages
  - Digital infrastructure: Rural and semi-urban areas have lower digitization
  - Low-software, high-coordination work: Many Indian occupations involve coordination without heavy software use
- **Calibration anchors:**
  - 0--1 (Minimal): Agricultural labourers, construction workers, domestic helpers, street vendors
  - 2--3 (Low): Electricians, auto mechanics, security guards, anganwadi workers, tailors
  - 4--5 (Moderate): Nurses, police constables, bank clerks, primary school teachers, lab technicians
  - 6--7 (High): College lecturers, middle managers, chartered accountants, journalists, pharmacists
  - 8--9 (Very high): Software developers, data analysts, content writers, graphic designers, financial analysts
  - 10 (Maximum): Data entry operators, BPO/KPO voice agents, medical transcriptionists
- **What it is NOT:** An empirical measurement. No field study was conducted. These are model-derived estimates based on occupation descriptions and a structured rubric. Different models, different prompts, or different rubrics would produce different scores.

### `ai_rationale`

- **Source:** LLM output
- **Content:** 2--3 sentence explanation of the key factors driving the AI exposure score in the Indian context.

### `source_meta`

- **Source:** Assembled during the merge step
- **Content:** Per-field provenance tracking: source name, source URL, coverage period, and retrieval date.

---

## Date mismatches

The sources used in this dataset were published or retrieved at different times:

| Source | Reference Date | Notes |
|--------|---------------|-------|
| NCO 2015 | Published 2015 | The classification has not been officially updated since 2015. Occupation structures may have evolved, particularly in technology and gig economy roles that have emerged or grown significantly since 2015. |
| PLFS Annual Report | July 2023 -- June 2024 | The most recent annual report available at the time of data collection. Employment and earnings data reflect this 12-month period. |
| NCS pages | Retrieved March 2026 | Web content is not versioned; page content may change between retrievals. Vacancy counts are point-in-time snapshots. |
| NSDC Qualification Packs | Retrieved March 2026 | QPs are periodically updated by sector skill councils. The versions retrieved may not match the versions current during the PLFS survey period. |
| AI exposure scores | Scored March 2026 | Model-derived; reflects the model's training data and the state of AI capabilities as understood at scoring time. |

The most significant mismatch is between the **NCO 2015 taxonomy** (11 years old at the time of this dataset) and the **PLFS 2023--24 employment data**. While PLFS uses NCO 2015 codes, the real-world occupation landscape has shifted in ways the 2015 classification does not fully capture. For example, gig economy workers, social media managers, and AI/ML engineers do not have dedicated NCO 2015 codes and are absorbed into broader categories.

---

## What this dataset does NOT claim

This section is important. Users should read it before drawing conclusions from the visualization.

1. **This is not an employment forecast.** There are no 10-year projections. India does not publish occupation-level employment projections comparable to the BLS Occupational Outlook Handbook. The `demand_index` field is a portal-derived vacancy snapshot, not a forecast.

2. **This is not a wage survey with medians.** The pay figures come from PLFS, which is a sample survey reporting **averages (means)**, not medians. Averages are sensitive to outliers. A small number of very high earners in an occupation group can pull the average significantly above what a typical worker earns. The field is named `pay_median_monthly` for structural compatibility with the US version, but the underlying statistic is a mean.

3. **Vacancy counts are not job openings are not total employment.** The `demand_index` reflects listings on one government job portal (NCS). It does not represent total hiring across the economy. Most private-sector hiring in India happens through other channels. Most informal-sector work is not listed on any portal.

4. **AI exposure scores are model-derived estimates, not empirical measurements.** No field study, employer survey, or task-level analysis was conducted. An LLM was given occupation descriptions and a rubric, and it produced scores. These scores are useful for relative comparison and discussion but should not be cited as research findings.

5. **Approximately 80% of India's workforce is in the informal sector.** Portal-derived data (NCS vacancies, NSDC qualification packs) overwhelmingly reflects formal and semi-formal employment. The visualization therefore has a structural blind spot: the occupations where most Indians work (agriculture, construction, domestic work, street vending) are the ones with the thinnest portal-derived data.

6. **The education proxy is not equivalent to the BLS entry-level education requirement.** The BLS assigns a specific "typical entry-level education" to each occupation based on detailed analysis. The Indian `education_proxy` is derived from NCO skill level bands and NSDC qualification packs at the group level. It is a rough guide, not an authoritative per-occupation requirement.

7. **2-digit aggregation hides significant within-group variation.** A single 2-digit NCO subdivision can contain occupations with very different pay, skill requirements, and AI exposure. For example, NCO 25 ("ICT Professionals") includes both senior software architects and junior help-desk technicians. The group-level averages smooth over this variation.

8. **The dataset does not cover the gig economy well.** Platform-based work (ride-hailing, food delivery, freelance digital work) does not have dedicated NCO 2015 codes and is distributed across multiple categories or missing entirely.

---

## Comparison with the US BLS-based version

This project is inspired by Karpathy's US Job Market Visualizer, which draws almost entirely from the Bureau of Labor Statistics (BLS). The table below summarizes what the US version has and how the Indian version addresses (or cannot address) each element.

| Feature | US version (BLS) | India version | Gap |
|---------|------------------|---------------|-----|
| **Occupation taxonomy** | SOC codes, ~342 detailed occupations | NCO 2015, 43 occupations at 2-digit level | Much coarser granularity |
| **Single authoritative source** | BLS provides nearly everything | Must stitch 4+ sources (NCO, PLFS, NCS, NSDC) | More complex pipeline, more provenance tracking |
| **Employment counts** | BLS per-occupation counts (administrative + survey) | PLFS survey estimates at 2-digit NCO | Lower granularity, sample-based |
| **Pay data** | BLS median annual pay per occupation | PLFS average (mean) monthly earnings at 2-digit NCO | Average not median; group-level not per-occupation |
| **Entry-level education** | BLS per-occupation typical education | Proxy from NCO skill levels + NSDC QPs | Group-level proxy, not per-occupation |
| **10-year employment projections** | BLS publishes per-occupation | Not available; no Indian equivalent | Cannot be replicated; NCS vacancy proxy is not a substitute |
| **Occupation descriptions** | Standardized BLS OOH pages for every occupation | NCS pages (uneven coverage and quality) | Some occupations have thin or no descriptions |
| **Growth outlook** | BLS "faster than average" / "declining" categories | Not available | Replaced by NCS vacancy demand proxy, which measures something different |
| **Informal sector** | Small share of US workforce | ~80% of Indian workforce | Fundamental structural difference; portal data captures a minority of workers |

**Choices made to bridge the gap:**

- Accepted 2-digit granularity rather than fabricating finer-grained data
- Used averages where medians are unavailable, with clear labelling
- Created a `demand_index` from NCS vacancies as a directional proxy, not a forecast replacement
- Derived `education_proxy` from taxonomy skill levels rather than claiming per-occupation education requirements
- Added India-specific calibration to AI exposure scoring to account for informality, physical work, and digital infrastructure differences
- Tracked provenance per field so users can see exactly where each number comes from

---

## How to update

When a new PLFS Annual Report is published (typically with a 6--12 month lag after the survey period ends):

1. **Download the new PLFS report** from the MoSPI website: https://www.mospi.gov.in/
2. **Run the employment extraction script:**
   ```
   python scripts/build_employment.py --force
   ```
   This will re-extract employment and earnings tables from the new PDF. You may need to adjust table extraction parameters if MoSPI changes the PDF layout.
3. **Update NCS data** (optional, if you want fresher demand signals):
   ```
   python scripts/scrape_ncs.py
   ```
   This will scrape any NCS pages not already cached. To force a full refresh, delete `data/raw/ncs_html/` first.
4. **Re-merge and re-score:**
   ```
   python scripts/merge_occupations.py --force
   python scripts/score.py --force
   python scripts/build_site_data.py --force
   ```
5. **Update this methodology document** with the new PLFS coverage period and retrieval dates.
6. **Check for NCO updates.** As of 2026, NCO 2015 has not been revised. If a new NCO edition is published, the taxonomy script and all downstream mappings will need to be rebuilt.

**Note on PLFS methodology changes:** MoSPI revised the short-term PLFS series in 2025. If you are considering using quarterly or monthly PLFS bulletins, be aware that the post-2025 series may not be directly comparable to the annual report series used here. Consult the MoSPI methodology notes before mixing series.
