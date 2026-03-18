#!/usr/bin/env python3
"""
Packages all occupation data into a single Markdown file for LLM analysis.

Reads site/data-india.json and generates prompt.md at the repo root with:
  - Project overview
  - Aggregate statistics
  - Tier breakdowns by AI exposure
  - Per-occupation details
  - Methodology notes
"""

import json
import statistics
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SITE_DATA_PATH = ROOT / "site" / "data-india.json"
PROMPT_OUT = ROOT / "prompt.md"


def fmt_int(n) -> str:
    """Format integer with commas, or 'N/A'."""
    if n is None:
        return "N/A"
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return "N/A"


def fmt_float(n, decimals=1) -> str:
    """Format float or 'N/A'."""
    if n is None:
        return "N/A"
    try:
        return f"{float(n):.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def fmt_currency(n) -> str:
    """Format as Indian rupees."""
    if n is None:
        return "N/A"
    try:
        return f"Rs {int(n):,}/mo"
    except (ValueError, TypeError):
        return "N/A"


def tier_label(exposure) -> str:
    """Map AI exposure score to tier label."""
    if exposure is None:
        return "Unscored"
    e = float(exposure)
    if e <= 1:
        return "Minimal (0-1)"
    elif e <= 3:
        return "Low (2-3)"
    elif e <= 5:
        return "Moderate (4-5)"
    elif e <= 7:
        return "High (6-7)"
    elif e <= 9:
        return "Very High (8-9)"
    else:
        return "Maximum (10)"


def make_prompt():
    """Generate the prompt.md file."""
    if PROMPT_OUT.exists():
        print(f"[INFO] Output already exists: {PROMPT_OUT}")
        print("       Delete it to regenerate. Skipping.")
        return

    if not SITE_DATA_PATH.exists():
        print(f"[ERROR] Site data not found: {SITE_DATA_PATH}")
        print("        Run build_site_data.py first.")
        return

    with open(SITE_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or not data:
        print("[ERROR] Site data is empty or invalid.")
        return

    print(f"[INFO] Loaded {len(data)} occupation records.")

    # ---------------------------------------------------------------------------
    # Compute aggregate statistics
    # ---------------------------------------------------------------------------
    total_occupations = len(data)
    scored = [r for r in data if r.get("ai_exposure") is not None]
    unscored = [r for r in data if r.get("ai_exposure") is None]
    exposures = [r["ai_exposure"] for r in scored]

    with_employment = [r for r in data if r.get("employment_count") is not None]
    total_employment = sum(r["employment_count"] for r in with_employment) if with_employment else None

    with_pay = [r for r in data if r.get("pay_median_monthly") is not None]
    pay_values = [r["pay_median_monthly"] for r in with_pay]

    # Tier breakdown
    tiers: dict[str, list[dict]] = {}
    for r in data:
        t = tier_label(r.get("ai_exposure"))
        if t not in tiers:
            tiers[t] = []
        tiers[t].append(r)

    # Tier order for display
    tier_order = [
        "Maximum (10)",
        "Very High (8-9)",
        "High (6-7)",
        "Moderate (4-5)",
        "Low (2-3)",
        "Minimal (0-1)",
        "Unscored",
    ]

    # ---------------------------------------------------------------------------
    # Build Markdown
    # ---------------------------------------------------------------------------
    lines = []

    # --- Header ---
    lines.append("# Indian Job Market: AI Exposure Analysis")
    lines.append("")
    lines.append("This document contains structured data on Indian occupations classified by the")
    lines.append("National Classification of Occupations (NCO 2015), enriched with employment statistics")
    lines.append("from the Periodic Labour Force Survey (PLFS), skill/education data from NSDC, demand")
    lines.append("signals from the National Career Service (NCS) portal, and AI exposure scores generated")
    lines.append("using an India-specific rubric.")
    lines.append("")

    # --- Aggregate Statistics ---
    lines.append("## Aggregate Statistics")
    lines.append("")
    lines.append(f"- **Total occupation groups (2-digit NCO):** {total_occupations}")
    lines.append(f"- **AI-scored occupations:** {len(scored)}/{total_occupations}")

    if total_employment:
        lines.append(f"- **Total employment (PLFS):** {fmt_int(total_employment)}")

    if exposures:
        lines.append(f"- **Mean AI exposure:** {fmt_float(statistics.mean(exposures))}")
        lines.append(f"- **Median AI exposure:** {fmt_float(statistics.median(exposures))}")
        lines.append(f"- **Min AI exposure:** {fmt_float(min(exposures))}")
        lines.append(f"- **Max AI exposure:** {fmt_float(max(exposures))}")

        if len(exposures) > 1:
            lines.append(f"- **Std dev AI exposure:** {fmt_float(statistics.stdev(exposures))}")

    if pay_values:
        lines.append(f"- **Median pay (across groups):** {fmt_currency(statistics.median(pay_values))}")

    lines.append("")

    # --- Tier Breakdown ---
    lines.append("## AI Exposure Tier Breakdown")
    lines.append("")
    lines.append("| Tier | Count | Occupations |")
    lines.append("|------|-------|-------------|")

    for tier_name in tier_order:
        tier_records = tiers.get(tier_name, [])
        if not tier_records:
            continue
        titles = [r.get("occupation_title", "?") for r in tier_records[:5]]
        titles_str = ", ".join(titles)
        if len(tier_records) > 5:
            titles_str += f", ... (+{len(tier_records) - 5} more)"
        lines.append(f"| {tier_name} | {len(tier_records)} | {titles_str} |")

    lines.append("")

    # --- Detailed Tier Sections ---
    for tier_name in tier_order:
        tier_records = tiers.get(tier_name, [])
        if not tier_records:
            continue

        lines.append(f"### {tier_name}")
        lines.append("")

        # Sort by exposure (descending) then by title
        tier_records.sort(
            key=lambda r: (-(r.get("ai_exposure") or -1), r.get("occupation_title", "")),
        )

        for r in tier_records:
            code = r.get("occupation_code", "?")
            title = r.get("occupation_title", "Unknown")
            exposure = r.get("ai_exposure")
            lines.append(f"**NCO {code}: {title}** (AI Exposure: {fmt_float(exposure)})")

            details = []
            if r.get("employment_count") is not None:
                details.append(f"Employment: {fmt_int(r['employment_count'])}")
            if r.get("pay_median_monthly") is not None:
                details.append(f"Pay: {fmt_currency(r['pay_median_monthly'])}")
            if r.get("skill_level"):
                details.append(f"Skill level: {r['skill_level']}")
            if r.get("demand_index") is not None:
                details.append(f"Demand index: {r['demand_index']}/100")
            if details:
                lines.append("  " + " | ".join(details))

            if r.get("ai_rationale"):
                lines.append(f"  *{r['ai_rationale']}*")

            if r.get("description"):
                desc = r["description"][:300]
                if len(r["description"]) > 300:
                    desc += "..."
                lines.append(f"  > {desc}")

            lines.append("")

    # --- Per-occupation Detail Table ---
    lines.append("## Per-Occupation Summary Table")
    lines.append("")
    lines.append("| Code | Title | AI Exp | Employment | Pay | Skill | Demand |")
    lines.append("|------|-------|--------|------------|-----|-------|--------|")

    for r in sorted(data, key=lambda x: x.get("occupation_code", "")):
        code = r.get("occupation_code", "?")
        title = (r.get("occupation_title") or "Unknown")[:40]
        exp = fmt_float(r.get("ai_exposure"))
        emp = fmt_int(r.get("employment_count"))
        pay = fmt_currency(r.get("pay_median_monthly"))
        skill = r.get("skill_level", "N/A") or "N/A"
        demand = str(r.get("demand_index", "N/A"))
        lines.append(f"| {code} | {title} | {exp} | {emp} | {pay} | {skill} | {demand} |")

    lines.append("")

    # --- Methodology Notes ---
    lines.append("## Methodology Notes")
    lines.append("")
    lines.append("### Data Sources")
    lines.append("1. **NCO 2015 Taxonomy**: National Classification of Occupations 2015, "
                  "published by the Ministry of Labour and Employment, Government of India. "
                  "Provides the occupation classification framework at 2-digit group level.")
    lines.append("2. **PLFS Employment Data**: Periodic Labour Force Survey, conducted by the "
                  "National Statistical Office (NSO). Provides employment counts and wage estimates "
                  "by occupation.")
    lines.append("3. **NCS Portal Data**: National Career Service (ncs.gov.in) occupation pages, "
                  "scraped and parsed for descriptions, tasks, and sector information.")
    lines.append("4. **NSDC Qualification Packs**: National Skill Development Corporation standards, "
                  "used to derive education proxies, training requirements, and key competencies. "
                  "Supplemented with embedded fallback data for full coverage.")
    lines.append("5. **Demand Index**: Portal-derived demand proxy based on NCS and broader Indian "
                  "job portal activity patterns. Explicitly labelled as a proxy, not a measure of "
                  "actual labour market demand.")
    lines.append("")
    lines.append("### AI Exposure Scoring")
    lines.append("- Scored using an LLM (Google Gemini Flash 1.5 via OpenRouter) with a custom "
                  "India-specific rubric.")
    lines.append("- Scale: 0 (minimal exposure) to 10 (maximum exposure).")
    lines.append("- India-specific factors considered: informality, physical presence requirements, "
                  "human intermediation, multilingual interaction, digital infrastructure gaps, and "
                  "coordination-heavy but low-software work patterns.")
    lines.append("- Calibration anchors range from agricultural labourers (0-1) to data entry "
                  "operators and BPO agents (10).")
    lines.append("")
    lines.append("### Limitations")
    lines.append("- Employment data is survey-based and may not capture the full informal sector.")
    lines.append("- AI exposure scores are LLM-generated estimates, not empirical measurements.")
    lines.append("- Demand indices are portal-derived proxies that reflect formal digital hiring "
                  "activity and underrepresent informal sector demand.")
    lines.append("- Occupation groupings at the 2-digit level are broad; within-group variation "
                  "can be significant.")
    lines.append("- Pay data where available reflects formal sector reported wages and may not "
                  "capture informal sector earnings.")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by jobs-india pipeline | {total_occupations} occupation groups*")
    lines.append("")

    # ---------------------------------------------------------------------------
    # Write output
    # ---------------------------------------------------------------------------
    content = "\n".join(lines)
    PROMPT_OUT.write_text(content, encoding="utf-8")

    print(f"[INFO] Generated {PROMPT_OUT}")
    print(f"       {len(lines)} lines, {len(content)} characters")
    print(f"       {len(scored)} scored occupations, {len(unscored)} unscored")


if __name__ == "__main__":
    make_prompt()
