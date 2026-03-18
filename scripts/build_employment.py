#!/usr/bin/env python3
"""
build_employment.py
===================
Builds the PLFS employment and earnings dataset at the NCO 2-digit level
and writes it to data/intermediate/plfs_employment.csv.

Embedded seed data is based on approximate distributions from the
Periodic Labour Force Survey (PLFS) Annual Report July 2023 - June 2024,
using usual status (ps+ss) workforce estimates for India's ~562 million
total workforce.

The script can later be extended to parse published PLFS PDF tables
directly.

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
# Embedded PLFS 2023-24 employment estimates (approximate)
#
# Total workforce (usual status ps+ss): ~562 million
#
# Each tuple: (nco_2digit_code, employment_count, avg_monthly_earnings_inr)
#
# The 1-digit distribution percentages (which sum to ~100%):
#   MG 0  Armed Forces         ~0.3%  =  ~1.7M
#   MG 1  Managers              ~3.5%  = ~19.7M
#   MG 2  Professionals         ~4.5%  = ~25.3M
#   MG 3  Technicians           ~2.5%  = ~14.1M
#   MG 4  Clerical              ~2.0%  = ~11.2M
#   MG 5  Services/Sales       ~12.0%  = ~67.4M
#   MG 6  Skilled Agriculture  ~23.0%  =~129.3M
#   MG 7  Craft/Trades         ~12.0%  = ~67.4M
#   MG 8  Operators             ~7.0%  = ~39.3M
#   MG 9  Elementary           ~33.0%  =~185.5M
#                              ------   --------
#                              ~99.8%   ~560.9M (rounding)
# ---------------------------------------------------------------------------

EMPLOYMENT_DATA: list[tuple[str, int, int]] = [
    # ── Major Group 0: Armed Forces (~1.7M) ──────────────────────────────
    # 01 Commissioned Officers       ~0.3M
    # 02 Non-commissioned Officers   ~0.5M
    # 03 Other Ranks                 ~0.9M
    ("01",   300_000, 55_000),
    ("02",   500_000, 35_000),
    ("03",   900_000, 25_000),

    # ── Major Group 1: Managers (~19.7M) ─────────────────────────────────
    # 11 Chief Executives etc.       ~3.0M
    # 12 Administrative/Commercial   ~5.5M
    # 13 Production/Specialised      ~5.2M
    # 14 Hospitality/Retail Mgrs     ~6.0M
    ("11", 3_000_000, 80_000),
    ("12", 5_500_000, 60_000),
    ("13", 5_200_000, 55_000),
    ("14", 6_000_000, 45_000),

    # ── Major Group 2: Professionals (~25.3M) ────────────────────────────
    # 21 Science & Engineering       ~4.0M
    # 22 Health Professionals        ~3.5M
    # 23 Teaching Professionals      ~8.5M
    # 24 Business & Admin Profs      ~4.0M
    # 25 ICT Professionals           ~3.3M
    # 26 Legal/Social/Cultural       ~2.0M
    ("21", 4_000_000, 45_000),
    ("22", 3_500_000, 50_000),
    ("23", 8_500_000, 35_000),
    ("24", 4_000_000, 42_000),
    ("25", 3_300_000, 60_000),
    ("26", 2_000_000, 30_000),

    # ── Major Group 3: Technicians & Assoc. Professionals (~14.1M) ──────
    # 31 Science/Engineering Assoc.  ~3.5M
    # 32 Health Associates           ~2.5M
    # 33 Business/Admin Associates   ~4.5M
    # 34 Legal/Social/Cultural Assoc ~1.8M
    # 35 ICT Technicians             ~1.8M
    ("31", 3_500_000, 25_000),
    ("32", 2_500_000, 22_000),
    ("33", 4_500_000, 28_000),
    ("34", 1_800_000, 20_000),
    ("35", 1_800_000, 35_000),

    # ── Major Group 4: Clerical Support Workers (~11.2M) ─────────────────
    # 41 General/Keyboard Clerks     ~3.5M
    # 42 Customer Services Clerks    ~3.0M
    # 43 Numerical/Material Clerks   ~3.0M
    # 44 Other Clerical              ~1.7M
    ("41", 3_500_000, 18_000),
    ("42", 3_000_000, 16_000),
    ("43", 3_000_000, 22_000),
    ("44", 1_700_000, 15_000),

    # ── Major Group 5: Service and Sales Workers (~67.4M) ────────────────
    # 51 Personal Service Workers    ~18.0M
    # 52 Sales Workers               ~30.0M
    # 53 Personal Care Workers       ~8.4M
    # 54 Protective Services Workers ~11.0M
    ("51", 18_000_000, 12_000),
    ("52", 30_000_000, 14_000),
    ("53",  8_400_000, 10_000),
    ("54", 11_000_000, 18_000),

    # ── Major Group 6: Skilled Agricultural, Forestry & Fishery (~129.3M)
    # 61 Market-oriented Ag Workers  ~85.0M
    # 62 Forestry/Fishery/Hunting    ~12.0M
    # 63 Subsistence Farmers etc.    ~32.3M
    ("61", 85_000_000,  9_000),
    ("62", 12_000_000, 10_000),
    ("63", 32_300_000,  6_000),

    # ── Major Group 7: Craft and Related Trades Workers (~67.4M) ─────────
    # 71 Building Trades (excl Elec) ~20.0M
    # 72 Metal/Machinery Trades      ~15.0M
    # 73 Handicraft/Printing         ~5.5M
    # 74 Electrical/Electronic       ~10.0M
    # 75 Food/Wood/Garment/Other     ~16.9M
    ("71", 20_000_000, 14_000),
    ("72", 15_000_000, 16_000),
    ("73",  5_500_000, 12_000),
    ("74", 10_000_000, 18_000),
    ("75", 16_900_000, 13_000),

    # ── Major Group 8: Plant & Machine Operators, Assemblers (~39.3M) ────
    # 81 Stationary Plant/Machine Op ~12.0M
    # 82 Assemblers                  ~5.3M
    # 83 Drivers/Mobile Plant Op     ~22.0M
    ("81", 12_000_000, 16_000),
    ("82",  5_300_000, 14_000),
    ("83", 22_000_000, 20_000),

    # ── Major Group 9: Elementary Occupations (~185.5M) ──────────────────
    # 91 Cleaners & Helpers          ~30.0M
    # 92 Agricultural Labourers      ~75.0M
    # 93 Mining/Construction/Mfg Lab ~42.0M
    # 94 Food Preparation Assistants ~12.0M
    # 95 Street Sales/Service        ~16.5M
    # 96 Refuse/Other Elementary     ~10.0M
    ("91", 30_000_000,  8_000),
    ("92", 75_000_000,  6_500),
    ("93", 42_000_000,  9_000),
    ("94", 12_000_000,  7_500),
    ("95", 16_500_000,  7_000),
    ("96", 10_000_000,  6_000),
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
