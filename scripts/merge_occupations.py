#!/usr/bin/env python3
"""
Joins all intermediate data into unified occupation records.

Reads:
  - data/raw/nco_2015.json            (NCO taxonomy)
  - data/intermediate/plfs_employment.csv  (PLFS employment stats)
  - data/intermediate/ncs_data.json   (NCS parsed data)
  - data/intermediate/nsdc_skills.json (NSDC skills/education)
  - data/intermediate/ncs_demand.json (demand signals)

Produces one record per 2-digit NCO occupation with all available fields.
Missing data -> null (never fabricated).
Tracks provenance per field in source_meta.

Outputs:
  - data/final/occupations_india.json
  - data/final/occupations_india.csv
"""

import argparse
import csv
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
NCO_PATH = ROOT / "data" / "raw" / "nco_2015.json"
PLFS_PATH = ROOT / "data" / "intermediate" / "plfs_employment.csv"
NCS_DATA_PATH = ROOT / "data" / "intermediate" / "ncs_data.json"
SKILLS_PATH = ROOT / "data" / "intermediate" / "nsdc_skills.json"
DEMAND_PATH = ROOT / "data" / "intermediate" / "ncs_demand.json"
JSON_OUT = ROOT / "data" / "final" / "occupations_india.json"
CSV_OUT = ROOT / "data" / "final" / "occupations_india.csv"


def load_json(path: Path) -> list | dict | None:
    """Load JSON file if it exists, else return None."""
    if not path.exists():
        print(f"  [SKIP] {path.name} not found")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  [OK]   {path.name} loaded")
        return data
    except Exception as exc:
        print(f"  [ERR]  {path.name}: {exc}")
        return None


def load_csv(path: Path) -> list[dict] | None:
    """Load CSV file into list of dicts if it exists."""
    if not path.exists():
        print(f"  [SKIP] {path.name} not found")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print(f"  [OK]   {path.name} loaded ({len(rows)} rows)")
        return rows
    except Exception as exc:
        print(f"  [ERR]  {path.name}: {exc}")
        return None


def normalize_list(data) -> list:
    """Ensure data is a list."""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Try common wrapper keys
        for key in ("occupations", "codes", "data", "nco"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return list(data.values()) if data else []
    return []


def get_code(entry: dict) -> str:
    """Extract code from various field names."""
    for key in ("code", "nco_code", "nco", "Code", "NCO_Code", "nco_2digit"):
        if key in entry:
            return str(entry[key]).strip()
    return ""


def get_title(entry: dict) -> str:
    """Extract title from various field names."""
    for key in ("title", "occupation", "name", "Title", "Occupation", "group_title"):
        if key in entry:
            return str(entry[key]).strip()
    return ""


def safe_float(val) -> float | None:
    """Convert to float or return None."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_int(val) -> int | None:
    """Convert to int or return None."""
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def merge_occupations(force: bool = False):
    """Main merge function."""
    if not force and JSON_OUT.exists() and CSV_OUT.exists():
        print(f"[INFO] Outputs already exist:")
        print(f"       {JSON_OUT}")
        print(f"       {CSV_OUT}")
        print("       Delete them to regenerate. Skipping.")
        return

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)

    print("[INFO] Loading input files ...")

    # Load all data sources
    nco_raw = load_json(NCO_PATH)
    plfs_raw = load_csv(PLFS_PATH)
    ncs_raw = load_json(NCS_DATA_PATH)
    skills_raw = load_json(SKILLS_PATH)
    demand_raw = load_json(DEMAND_PATH)

    nco_list = normalize_list(nco_raw)
    ncs_list = normalize_list(ncs_raw)
    skills_list = normalize_list(skills_raw)
    demand_list = normalize_list(demand_raw)

    # ---------------------------------------------------------------------------
    # Build lookup maps keyed by 2-digit NCO code
    # ---------------------------------------------------------------------------

    # NCO taxonomy -> aggregate to 2-digit groups
    nco_groups: dict[str, dict] = {}
    for entry in nco_list:
        code = get_code(entry)
        title = get_title(entry)
        if len(code) < 2:
            continue
        group = code[:2]
        if group not in nco_groups:
            nco_groups[group] = {
                "codes": [],
                "titles": [],
                "parent_title": entry.get("parent_title"),
                "skill_level": entry.get("skill_level"),
                "description": entry.get("description"),
            }
        nco_groups[group]["codes"].append(code)
        nco_groups[group]["titles"].append(title)

    # PLFS employment data -> index by 2-digit code
    plfs_map: dict[str, dict] = {}
    if plfs_raw:
        for row in plfs_raw:
            # Try various column names for the NCO code
            code = ""
            for key in ("nco_2digit", "nco_code", "code", "NCO", "occupation_code"):
                if key in row and row[key]:
                    code = str(row[key]).strip()[:2]
                    break
            if not code or len(code) < 2:
                continue
            plfs_map[code] = row

    # NCS parsed data -> index by 2-digit code (aggregate)
    ncs_map: dict[str, list[dict]] = {}
    for entry in ncs_list:
        code = get_code(entry)
        if len(code) < 2:
            continue
        group = code[:2]
        if group not in ncs_map:
            ncs_map[group] = []
        ncs_map[group].append(entry)

    # Skills data -> index by 2-digit code
    skills_map: dict[str, dict] = {}
    for entry in skills_list:
        code = entry.get("nco_2digit", "")
        if code:
            skills_map[code] = entry

    # Demand data -> index by 2-digit code
    demand_map: dict[str, dict] = {}
    for entry in demand_list:
        code = entry.get("nco_2digit", "")
        if code:
            demand_map[code] = entry

    # ---------------------------------------------------------------------------
    # Determine the universe of 2-digit codes
    # ---------------------------------------------------------------------------
    all_codes = set()
    all_codes.update(nco_groups.keys())
    all_codes.update(plfs_map.keys())
    all_codes.update(skills_map.keys())
    all_codes.update(demand_map.keys())

    print(f"\n[INFO] Found {len(all_codes)} unique 2-digit NCO groups across all sources.")

    # ---------------------------------------------------------------------------
    # Merge into unified records
    # ---------------------------------------------------------------------------
    records = []
    for code in sorted(all_codes):
        source_meta = {}

        # --- Taxonomy ---
        nco_info = nco_groups.get(code, {})
        if nco_info:
            source_meta["taxonomy"] = "nco_2015.json"

        # Determine group title
        group_title = None
        # Prefer skills group_title (it's the cleanest)
        if code in skills_map:
            group_title = skills_map[code].get("group_title")
        # Fallback to demand
        if not group_title and code in demand_map:
            group_title = demand_map[code].get("group_title")
        # Fallback to first NCO title
        if not group_title and nco_info.get("titles"):
            group_title = nco_info["titles"][0]

        # --- PLFS employment ---
        plfs = plfs_map.get(code, {})
        employment_count = None
        pay_median_monthly = None
        employment_share_pct = None

        if plfs:
            source_meta["employment"] = "plfs_employment.csv"
            # Try common column names
            for key in ("employment_count", "employed", "workers", "count", "employment"):
                if key in plfs:
                    employment_count = safe_int(plfs[key])
                    if employment_count is not None:
                        break

            for key in ("pay_median_monthly", "avg_monthly_earnings", "median_pay", "wages_median", "median_earnings", "pay_median"):
                if key in plfs:
                    pay_median_monthly = safe_float(plfs[key])
                    if pay_median_monthly is not None:
                        break

            for key in ("employment_share_pct", "share_pct", "pct", "share"):
                if key in plfs:
                    employment_share_pct = safe_float(plfs[key])
                    if employment_share_pct is not None:
                        break

        # --- NCS data ---
        ncs_entries = ncs_map.get(code, [])
        description = None
        tasks = None
        sectors = None
        if ncs_entries:
            source_meta["ncs_data"] = "ncs_data.json"
            # Use the first entry with a description
            for ncs in ncs_entries:
                if ncs.get("description") and not description:
                    description = ncs["description"]
                if ncs.get("tasks") and not tasks:
                    tasks = ncs["tasks"]
                if ncs.get("sectors") and not sectors:
                    sectors = ncs["sectors"]

        # --- Skills ---
        skill_info = skills_map.get(code, {})
        education_proxy = None
        training_context = None
        key_competencies = None
        # Use NCO taxonomy skill_level (numeric 1-4) as primary source
        skill_level = nco_info.get("skill_level") if nco_info else None

        if skill_info:
            source_meta["skills"] = skill_info.get("source", "nsdc_skills.json")
            education_proxy = skill_info.get("education_proxy")
            training_context = skill_info.get("training_context")
            key_competencies = skill_info.get("key_competencies")

        # Fall back to taxonomy description if NCS description not available
        if not description and nco_info:
            description = nco_info.get("description")

        # --- Demand ---
        demand_info = demand_map.get(code, {})
        demand_index = None
        demand_label = None

        if demand_info:
            source_meta["demand"] = demand_info.get("source", "ncs_demand.json")
            demand_index = demand_info.get("demand_index")
            demand_label = demand_info.get("demand_label", "portal-derived demand proxy")

        # --- Build unified record ---
        record = {
            "occupation_code": code,
            "occupation_title": group_title,
            "occupation_group": nco_info.get("parent_title", f"NCO-{code}") if nco_info else f"NCO-{code}",
            "sub_occupation_count": len(nco_info.get("codes", [])) if nco_info else None,
            "description": description,
            "tasks": tasks,
            "sectors": sectors,
            "employment_count": employment_count,
            "employment_share_pct": employment_share_pct,
            "pay_median_monthly": pay_median_monthly,
            "education_proxy": education_proxy,
            "training_context": training_context,
            "skill_level": skill_level,
            "key_competencies": key_competencies,
            "demand_index": demand_index,
            "demand_label": demand_label,
            "source_meta": source_meta,
        }

        records.append(record)
        n_fields = sum(1 for k, v in record.items() if v is not None and k != "source_meta")
        print(f"  NCO {code}: {(group_title or 'Unknown')[:55]:55s} ({n_fields} fields populated)")

    # ---------------------------------------------------------------------------
    # Write outputs
    # ---------------------------------------------------------------------------

    # JSON output
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"\n[INFO] JSON: {JSON_OUT} ({len(records)} records)")

    # CSV output (flatten for tabular format)
    csv_fields = [
        "occupation_code",
        "occupation_title",
        "occupation_group",
        "sub_occupation_count",
        "employment_count",
        "employment_share_pct",
        "pay_median_monthly",
        "skill_level",
        "education_proxy",
        "demand_index",
        "demand_label",
        "description",
    ]

    with open(CSV_OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            # Flatten: only write scalar fields
            flat = {k: record.get(k) for k in csv_fields}
            # Truncate description for CSV
            if flat.get("description") and len(flat["description"]) > 500:
                flat["description"] = flat["description"][:497] + "..."
            writer.writerow(flat)
    print(f"[INFO] CSV:  {CSV_OUT} ({len(records)} records)")

    print(f"\n[INFO] Merge complete. {len(records)} occupation groups.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge normalized occupation sources.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild outputs even if they already exist.",
    )
    args = parser.parse_args()
    merge_occupations(force=args.force)
