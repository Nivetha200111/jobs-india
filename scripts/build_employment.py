#!/usr/bin/env python3
"""
build_employment.py
===================
Builds the PLFS employment and earnings dataset at the NCO 2-digit level
and writes it to data/intermediate/plfs_employment.csv.

Data is extracted from the official PLFS Annual Report (July 2023 - June 2024)
published by NSSO/MoSPI on 23 September 2024.

Employment distribution: Table 25 of the PLFS Annual Report
    "Percentage distribution of workers in usual status (ps+ss) by
    occupation group/sub-division/division as per NCO 2015"
    Rural+Urban, Person column.

Earnings: Table 50 of the PLFS Annual Report
    "Average wage/salary earnings (Rs.) during the preceding calendar month
    from regular wage/salaried employment among regular wage salaried
    employees in CWS by occupation Divisions (1-digit code of NCO-2015)"
    Rural+Urban, Person column.

Total workforce:
    WPR (all ages, persons, usual status ps+ss) = 43.7% (Statement 3)
    India projected population mid-2023-24 ≈ 1,428 million
    Total workers ≈ 624 million

Armed forces (01, 02, 03) are not covered by PLFS civilian survey.
Figures from Ministry of Defence annual reports (~1.4M active personnel).

Usage:
    python scripts/build_employment.py          # writes CSV
    python scripts/build_employment.py --force  # overwrite even if file exists

No external dependencies -- uses only the Python standard library.
"""

import csv
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root is one level above the scripts/ directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "intermediate" / "plfs_employment.csv"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COVERAGE_PERIOD = "Jul 2023 - Jun 2024"
SECTOR = "combined"
EMPLOYMENT_TYPE = "all"

# ---------------------------------------------------------------------------
# Official PLFS 2023-24 data (July 2023 - June 2024)
#
# Employment distribution: Table 25, rural+urban, person column
# Total workforce: WPR 43.7% × 1,428M population = 624M
#
# Earnings: Table 50, rural+urban, person column
# (Regular wage/salaried employees only — covers ~21.7% of workforce.
#  Self-employed avg ~₹13,900/mo, casual labour avg ~₹433/day.)
#
# Division-level distribution (1-digit, Table 25):
#   Div 1  Managers           3.16%  →  19.7M   Earnings: ₹42,993
#   Div 2  Professionals      5.28%  →  33.0M   Earnings: ₹35,776
#   Div 3  Technicians        2.26%  →  14.1M   Earnings: ₹24,199
#   Div 4  Clerks             2.11%  →  13.2M   Earnings: ₹23,616
#   Div 5  Service & Sales   11.54%  →  72.0M   Earnings: ₹14,628
#   Div 6  Skilled Agri.     37.97%  → 236.9M   Earnings: ₹11,319
#   Div 7  Craft & Trades    11.09%  →  69.2M   Earnings: ₹15,350
#   Div 8  Operators          5.32%  →  33.2M   Earnings: ₹15,906
#   Div 9  Elementary        21.28%  → 132.8M   Earnings: ₹10,667
#                            ------    ------
#                           100.01%    624.1M
# ---------------------------------------------------------------------------

# Total workforce (PLFS 2023-24, usual status ps+ss, all ages)
TOTAL_WORKFORCE = 624_000_000

# Sub-division percentages from Table 25 (rural+urban, person)
# and Division-level earnings from Table 50 (rural+urban, person)
_PLFS_DATA: list[tuple[str, float, int]] = [
    # (nco_2digit, pct_of_total, division_level_avg_earnings)

    # ── Division 0: Armed Forces (not in PLFS, from MoD data) ────────
    # ~1.4M active military (defence.gov.in annual reports)
    ("01",  0.032, 55_000),   # Commissioned Officers ~200K
    ("02",  0.064, 35_000),   # NCOs ~400K
    ("03",  0.128, 25_000),   # Other Ranks ~800K

    # ── Division 1: Managers (3.16%) — Earnings ₹42,993 ──────────────
    ("11",  1.86, 42_993),    # Chief Executives, Senior Officials
    ("12",  0.65, 42_993),    # Administrative & Commercial Managers
    ("13",  0.38, 42_993),    # Production & Specialised Managers
    ("14",  0.27, 42_993),    # Hospitality, Retail & Other Managers

    # ── Division 2: Professionals (5.28%) — Earnings ₹35,776 ────────
    ("21",  0.44, 35_776),    # Science & Engineering Professionals
    ("22",  0.46, 35_776),    # Health Professionals
    ("23",  2.30, 35_776),    # Teaching Professionals
    ("24",  0.67, 35_776),    # Business & Administration Professionals
    ("25",  0.79, 35_776),    # ICT Professionals
    ("26",  0.61, 35_776),    # Legal, Social & Cultural Professionals

    # ── Division 3: Technicians (2.26%) — Earnings ₹24,199 ──────────
    ("31",  0.69, 24_199),    # Science & Engineering Assoc. Professionals
    ("32",  0.56, 24_199),    # Health Associate Professionals
    ("33",  0.71, 24_199),    # Business & Admin Associate Professionals
    ("34",  0.19, 24_199),    # Legal, Social & Cultural Associates
    ("35",  0.11, 24_199),    # ICT Technicians

    # ── Division 4: Clerks (2.11%) — Earnings ₹23,616 ───────────────
    ("41",  1.07, 23_616),    # General & Keyboard Clerks
    ("42",  0.28, 23_616),    # Customer Services Clerks
    ("43",  0.34, 23_616),    # Numerical & Material Recording Clerks
    ("44",  0.41, 23_616),    # Other Clerical Support Workers

    # ── Division 5: Service & Sales (11.54%) — Earnings ₹14,628 ─────
    ("51",  2.09, 14_628),    # Personal Service Workers
    ("52",  8.30, 14_628),    # Sales Workers
    ("53",  0.20, 14_628),    # Personal Care Workers
    ("54",  0.95, 14_628),    # Protective Services Workers

    # ── Division 6: Skilled Agriculture (37.97%) — Earnings ₹11,319 ─
    ("61", 34.06, 11_319),    # Market-oriented Skilled Agri Workers
    ("62",  0.55, 11_319),    # Market-oriented Skilled Forestry/Fishery
    ("63",  3.37, 11_319),    # Subsistence Farmers, Fishers, Hunters

    # ── Division 7: Craft & Trades (11.09%) — Earnings ₹15,350 ──────
    ("71",  3.23, 15_350),    # Building & Related Trades Workers
    ("72",  1.58, 15_350),    # Metal, Machinery & Related Trades
    ("73",  1.22, 15_350),    # Handicraft & Printing Workers
    ("74",  0.87, 15_350),    # Electrical & Electronic Trades Workers
    ("75",  4.18, 15_350),    # Food/Wood/Garment & Other Craft Workers

    # ── Division 8: Plant & Machine Operators (5.32%) — Earnings ₹15,906
    ("81",  1.16, 15_906),    # Stationary Plant & Machine Operators
    ("82",  0.08, 15_906),    # Assemblers
    ("83",  4.08, 15_906),    # Drivers & Mobile Plant Operators

    # ── Division 9: Elementary Occupations (21.28%) — Earnings ₹10,667
    ("91",  1.61, 10_667),    # Cleaners & Helpers
    ("92",  7.92, 10_667),    # Agricultural, Forestry & Fishery Labourers
    ("93", 10.86, 10_667),    # Mining, Construction, Mfg Labourers
    ("94",  0.10, 10_667),    # Food Preparation Assistants
    ("95",  0.28, 10_667),    # Street & Related Sales/Service Workers
    ("96",  0.51, 10_667),    # Refuse Workers & Other Elementary
]

# Convert percentage distribution to absolute employment counts
EMPLOYMENT_DATA: list[tuple[str, int, int]] = [
    (code, round(pct / 100 * TOTAL_WORKFORCE), earnings)
    for code, pct, earnings in _PLFS_DATA
]

# CSV column headers
CSV_COLUMNS = [
    "nco_code",
    "employment_count",
    "avg_monthly_earnings",
    "sector",
    "employment_type",
    "coverage_period",
]


def build_employment(force: bool = False) -> None:
    """Build the PLFS employment CSV from embedded seed data."""
    if OUTPUT_PATH.exists() and not force:
        print(f"[skip] {OUTPUT_PATH} already exists. Use --force to overwrite.")
        return

    # Ensure the output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    total_employment = 0
    row_count = 0

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)

        for nco_code, employment_count, avg_earnings in EMPLOYMENT_DATA:
            writer.writerow([
                nco_code,
                employment_count,
                avg_earnings,
                SECTOR,
                EMPLOYMENT_TYPE,
                COVERAGE_PERIOD,
            ])
            total_employment += employment_count
            row_count += 1

    print(f"[done] Wrote {row_count} rows to {OUTPUT_PATH}")
    print(f"       Total workforce covered: {total_employment:,.0f}")


# ---------------------------------------------------------------------------
# Summary statistics (printed to stdout when run standalone)
# ---------------------------------------------------------------------------
def print_summary() -> None:
    """Print a quick summary of the embedded data."""
    total = sum(emp for _, emp, _ in EMPLOYMENT_DATA)
    weighted_earnings = sum(emp * earn for _, emp, earn in EMPLOYMENT_DATA)
    avg_earn = weighted_earnings / total if total else 0

    print(f"\n--- PLFS 2023-24 Embedded Data Summary ---")
    print(f"  Total workforce:          {total:>15,.0f}")
    print(f"  NCO 2-digit groups:       {len(EMPLOYMENT_DATA):>15d}")
    print(f"  Weighted avg earnings:    INR {avg_earn:>11,.0f}/month")

    # Per major group
    major_groups: dict[str, list[tuple[str, int, int]]] = {}
    for code, emp, earn in EMPLOYMENT_DATA:
        mg = code[0]
        major_groups.setdefault(mg, []).append((code, emp, earn))

    print(f"\n  {'MG':>4}  {'Employment':>15}  {'Share':>7}  {'Avg Earn (INR)':>15}")
    print(f"  {'----':>4}  {'---------------':>15}  {'------':>7}  {'---------------':>15}")
    for mg in sorted(major_groups):
        mg_emp = sum(e for _, e, _ in major_groups[mg])
        mg_weighted = sum(e * ea for _, e, ea in major_groups[mg])
        mg_avg = mg_weighted / mg_emp if mg_emp else 0
        share = mg_emp / total * 100
        print(f"  {mg:>4}  {mg_emp:>15,.0f}  {share:>6.1f}%  {mg_avg:>15,.0f}")


# ---------------------------------------------------------------------------
# Future extension point: parse directly from PLFS PDF tables
# ---------------------------------------------------------------------------
def parse_plfs_pdf(pdf_path: str) -> list[tuple[str, int, int]]:
    """
    Placeholder for PDF-based extraction of PLFS published tables.

    When the official PLFS Annual Report PDF is available at *pdf_path*,
    this function can be implemented to extract employment and earnings
    tables directly. For now it raises NotImplementedError so callers
    know to rely on the embedded data.
    """
    raise NotImplementedError(
        "PDF parsing is not yet implemented. "
        "Install pdfplumber or tabula-py and extend this function."
    )


if __name__ == "__main__":
    force = "--force" in sys.argv
    build_employment(force=force)
    print_summary()
