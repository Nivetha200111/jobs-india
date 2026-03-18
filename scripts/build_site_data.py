#!/usr/bin/env python3
"""
Merges occupations + AI exposure scores into compact frontend dataset.

Reads:
  - data/final/occupations_india.json
  - data/final/india_scores.json

Outputs:
  - site/data-india.json (compact, only fields needed by frontend)

If scores file doesn't exist, the builder will reuse AI fields from an
existing site/data-india.json when available; otherwise ai_exposure and
ai_rationale are set to null.
"""

import argparse
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
OCCUPATIONS_PATH = ROOT / "data" / "final" / "occupations_india.json"
SCORES_PATH = ROOT / "data" / "final" / "india_scores.json"
SITE_OUT = ROOT / "site" / "data-india.json"


def load_json(path: Path) -> list | dict | None:
    """Load JSON file if it exists."""
    if not path.exists():
        print(f"  [SKIP] {path.name} not found")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"  [ERR]  {path.name}: {exc}")
        return None


def load_scores_from_site(path: Path) -> dict[str, dict]:
    """Load existing site data as a fallback score source."""
    existing = load_json(path)
    if not isinstance(existing, list):
        return {}

    scores_map = {}
    for entry in existing:
        code = entry.get("occupation_code", "")
        if not code:
            continue
        if entry.get("ai_exposure") is None and not entry.get("ai_rationale"):
            continue
        scores_map[code] = {
            "occupation_code": code,
            "ai_exposure": entry.get("ai_exposure"),
            "ai_rationale": entry.get("ai_rationale"),
        }
    return scores_map


def build_site_data(force: bool = False):
    """Main function to build frontend data."""
    if not force and SITE_OUT.exists():
        print(f"[INFO] Output already exists: {SITE_OUT}")
        print("       Delete it to regenerate. Skipping.")
        return

    SITE_OUT.parent.mkdir(parents=True, exist_ok=True)

    print("[INFO] Loading input files ...")

    # Load occupations (required)
    occupations_raw = load_json(OCCUPATIONS_PATH)
    if not occupations_raw:
        print("[ERROR] Occupations file is required. Run merge_occupations.py first.")
        return

    if not isinstance(occupations_raw, list):
        print("[ERROR] Expected occupations to be a JSON array.")
        return

    print(f"  [OK]   {len(occupations_raw)} occupation records loaded")

    # Load scores (optional)
    scores_raw = load_json(SCORES_PATH)
    scores_map: dict[str, dict] = {}

    if scores_raw:
        if isinstance(scores_raw, dict):
            scores_map = scores_raw
        elif isinstance(scores_raw, list):
            for entry in scores_raw:
                code = entry.get("occupation_code", "")
                if code:
                    scores_map[code] = entry
        print(f"  [OK]   {len(scores_map)} score records loaded")
    else:
        scores_map = load_scores_from_site(SITE_OUT)
        if scores_map:
            print(f"  [OK]   {len(scores_map)} legacy site score records loaded")
        else:
            print("  [INFO] No scores file; ai_exposure/ai_rationale will be null")

    # Build compact frontend records
    site_records = []
    for occ in occupations_raw:
        code = occ.get("occupation_code", "")
        score_entry = scores_map.get(code, {})

        record = {
            "occupation_code": code,
            "occupation_title": occ.get("occupation_title"),
            "occupation_group": occ.get("occupation_group"),
            "employment_count": occ.get("employment_count"),
            "pay_median_monthly": occ.get("pay_median_monthly"),
            "skill_level": occ.get("skill_level"),
            "demand_index": occ.get("demand_index"),
            "ai_exposure": score_entry.get("ai_exposure"),
            "ai_rationale": score_entry.get("ai_rationale"),
            "description": occ.get("description"),
        }

        site_records.append(record)

    # Sort by occupation code
    site_records.sort(key=lambda r: r.get("occupation_code", ""))

    with open(SITE_OUT, "w", encoding="utf-8") as f:
        json.dump(site_records, f, indent=2, ensure_ascii=False)

    # Summary stats
    scored = sum(1 for r in site_records if r.get("ai_exposure") is not None)
    with_employment = sum(1 for r in site_records if r.get("employment_count") is not None)
    with_pay = sum(1 for r in site_records if r.get("pay_median_monthly") is not None)

    print(f"\n[INFO] Built site data with {len(site_records)} occupation records:")
    print(f"       AI scores:  {scored}/{len(site_records)}")
    print(f"       Employment: {with_employment}/{len(site_records)}")
    print(f"       Pay data:   {with_pay}/{len(site_records)}")
    print(f"       Output:     {SITE_OUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build compact frontend data.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild site data even if the output already exists.",
    )
    args = parser.parse_args()
    build_site_data(force=args.force)
