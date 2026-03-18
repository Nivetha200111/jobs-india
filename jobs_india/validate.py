#!/usr/bin/env python3
"""Repository validation helpers for production-ready builds."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINAL_DATA_PATH = ROOT / "data" / "final" / "occupations_india.json"
SITE_DATA_PATH = ROOT / "site" / "data-india.json"
SITE_INDEX_PATH = ROOT / "site" / "index.html"
SITE_METHOD_PATH = ROOT / "site" / "methodology.html"
SITE_FAVICON_PATH = ROOT / "site" / "favicon.svg"

CODE_RE = re.compile(r"^\d{2}$")


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_records(records: list[dict], source: str) -> list[str]:
    errors: list[str] = []
    seen_codes: set[str] = set()

    for record in records:
        code = record.get("occupation_code")
        if not isinstance(code, str) or not CODE_RE.match(code):
            errors.append(f"{source}: invalid occupation_code {code!r}")
            continue
        if code in seen_codes:
            errors.append(f"{source}: duplicate occupation_code {code}")
        seen_codes.add(code)

        if not record.get("occupation_title"):
            errors.append(f"{source}: {code} missing occupation_title")
        if not record.get("occupation_group"):
            errors.append(f"{source}: {code} missing occupation_group")
        elif str(record["occupation_group"]).startswith("NCO-"):
            errors.append(f"{source}: {code} still uses placeholder occupation_group")

    return errors


def validate_outputs(root: Path | None = None) -> list[str]:
    root = root or ROOT
    errors: list[str] = []

    required_paths = [
        root / FINAL_DATA_PATH.relative_to(ROOT),
        root / SITE_DATA_PATH.relative_to(ROOT),
        root / SITE_INDEX_PATH.relative_to(ROOT),
        root / SITE_METHOD_PATH.relative_to(ROOT),
        root / SITE_FAVICON_PATH.relative_to(ROOT),
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(root)}")

    if errors:
        return errors

    final_records = load_json(root / FINAL_DATA_PATH.relative_to(ROOT))
    site_records = load_json(root / SITE_DATA_PATH.relative_to(ROOT))

    if not isinstance(final_records, list):
        errors.append("data/final/occupations_india.json must be a JSON array")
        return errors
    if not isinstance(site_records, list):
        errors.append("site/data-india.json must be a JSON array")
        return errors

    if not final_records:
        errors.append("data/final/occupations_india.json is empty")
    if not site_records:
        errors.append("site/data-india.json is empty")

    errors.extend(_validate_records(final_records, "final"))
    errors.extend(_validate_records(site_records, "site"))

    final_codes = {record["occupation_code"] for record in final_records if "occupation_code" in record}
    site_codes = {record["occupation_code"] for record in site_records if "occupation_code" in record}
    if final_codes != site_codes:
        errors.append("site/data-india.json does not match data/final/occupations_india.json code set")
    if len(final_records) != len(site_records):
        errors.append("final/site record counts do not match")

    for record in final_records:
        code = record["occupation_code"]
        for key in ("employment_count", "pay_median_monthly", "skill_level", "description"):
            if record.get(key) is None:
                errors.append(f"final: {code} missing {key}")
        skill_level = record.get("skill_level")
        if not isinstance(skill_level, int) or skill_level not in {1, 2, 3, 4}:
            errors.append(f"final: {code} has invalid skill_level {skill_level!r}")

    for record in site_records:
        code = record["occupation_code"]
        for key in (
            "employment_count",
            "pay_median_monthly",
            "skill_level",
            "demand_index",
            "ai_exposure",
            "description",
        ):
            if record.get(key) is None:
                errors.append(f"site: {code} missing {key}")
        ai_exposure = record.get("ai_exposure")
        if not isinstance(ai_exposure, (int, float)) or not (0 <= ai_exposure <= 10):
            errors.append(f"site: {code} has invalid ai_exposure {ai_exposure!r}")
        skill_level = record.get("skill_level")
        if not isinstance(skill_level, int) or skill_level not in {1, 2, 3, 4}:
            errors.append(f"site: {code} has invalid skill_level {skill_level!r}")

    index_html = (root / SITE_INDEX_PATH.relative_to(ROOT)).read_text(encoding="utf-8")
    if "alert(" in index_html:
        errors.append("site/index.html still uses alert() for methodology")
    if 'href="methodology.html"' not in index_html:
        errors.append("site/index.html is missing a methodology page link")
    if 'rel="icon"' not in index_html:
        errors.append("site/index.html is missing a favicon link")
    if "Monthly Pay (median)" in index_html or "Pay (Monthly Median)" in index_html:
        errors.append("site/index.html still labels PLFS pay as median")

    return errors


def main() -> int:
    errors = validate_outputs()
    if errors:
        print("[ERROR] Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    final_records = load_json(FINAL_DATA_PATH)
    site_records = load_json(SITE_DATA_PATH)
    print(
        f"[OK] Validation passed: {len(final_records)} final records, "
        f"{len(site_records)} site records."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
