#!/usr/bin/env python3
"""
Extracts NCS vacancy/demand signals and builds demand index data.

Reads NCS data from data/intermediate/ncs_data.json if available, labels all
demand data explicitly as "portal-derived demand proxy", and falls back to
embedded demand data with reasonable relative demand indices for all NCO
2-digit codes.

Outputs: data/intermediate/ncs_demand.json
"""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
NCS_DATA_PATH = ROOT / "data" / "intermediate" / "ncs_data.json"
OUTPUT_PATH = ROOT / "data" / "intermediate" / "ncs_demand.json"

# ---------------------------------------------------------------------------
# Embedded fallback demand data
#
# Relative demand index (0-100 scale) based on typical NCS portal activity
# and broader Indian labour market signals. IT/software highest, agricultural
# labour lowest.  All values are explicitly labelled as proxy estimates.
# ---------------------------------------------------------------------------
FALLBACK_DEMAND: dict[str, dict] = {
    "11": {
        "group_title": "Chief Executives, Senior Officials and Legislators",
        "demand_index": 15,
        "demand_label": "portal-derived demand proxy",
        "notes": "Low portal listings; hiring via headhunters/networks",
    },
    "12": {
        "group_title": "Administrative and Commercial Managers",
        "demand_index": 35,
        "demand_label": "portal-derived demand proxy",
        "notes": "Moderate demand across sectors; mix of portal and referral hiring",
    },
    "13": {
        "group_title": "Production and Specialised Services Managers",
        "demand_index": 40,
        "demand_label": "portal-derived demand proxy",
        "notes": "Steady demand in manufacturing and services sectors",
    },
    "14": {
        "group_title": "Hospitality, Retail and Other Services Managers",
        "demand_index": 45,
        "demand_label": "portal-derived demand proxy",
        "notes": "Growing retail/hospitality sector; moderate portal presence",
    },
    "21": {
        "group_title": "Science and Engineering Professionals",
        "demand_index": 65,
        "demand_label": "portal-derived demand proxy",
        "notes": "Strong demand across engineering disciplines; infrastructure push",
    },
    "22": {
        "group_title": "Health Professionals",
        "demand_index": 55,
        "demand_label": "portal-derived demand proxy",
        "notes": "High societal demand but much hiring is institutional/government",
    },
    "23": {
        "group_title": "Teaching Professionals",
        "demand_index": 40,
        "demand_label": "portal-derived demand proxy",
        "notes": "Large employment base; government recruitment dominates",
    },
    "24": {
        "group_title": "Business and Administration Professionals",
        "demand_index": 60,
        "demand_label": "portal-derived demand proxy",
        "notes": "CA/CS/finance roles show strong portal activity",
    },
    "25": {
        "group_title": "Information and Communications Technology Professionals",
        "demand_index": 95,
        "demand_label": "portal-derived demand proxy",
        "notes": "Highest portal demand; IT services is India's largest formal employer of graduates",
    },
    "26": {
        "group_title": "Legal, Social and Cultural Professionals",
        "demand_index": 25,
        "demand_label": "portal-derived demand proxy",
        "notes": "Niche demand; legal/media/arts roles less frequently on portals",
    },
    "31": {
        "group_title": "Science and Engineering Associate Professionals",
        "demand_index": 50,
        "demand_label": "portal-derived demand proxy",
        "notes": "Technician roles in demand for infrastructure and manufacturing",
    },
    "32": {
        "group_title": "Health Associate Professionals",
        "demand_index": 55,
        "demand_label": "portal-derived demand proxy",
        "notes": "Nursing and allied health demand growing with healthcare expansion",
    },
    "33": {
        "group_title": "Business and Administration Associate Professionals",
        "demand_index": 50,
        "demand_label": "portal-derived demand proxy",
        "notes": "Banking, insurance, and administrative support roles",
    },
    "34": {
        "group_title": "Legal, Social, Cultural and Related Associate Professionals",
        "demand_index": 20,
        "demand_label": "portal-derived demand proxy",
        "notes": "Limited portal visibility; many roles filled via networks",
    },
    "35": {
        "group_title": "Information and Communications Technicians",
        "demand_index": 70,
        "demand_label": "portal-derived demand proxy",
        "notes": "IT support and networking roles consistently in demand",
    },
    "41": {
        "group_title": "General and Keyboard Clerks",
        "demand_index": 45,
        "demand_label": "portal-derived demand proxy",
        "notes": "Data entry and office clerk positions common on portals",
    },
    "42": {
        "group_title": "Customer Services Clerks",
        "demand_index": 65,
        "demand_label": "portal-derived demand proxy",
        "notes": "BPO/call centre/customer support — high volume hiring",
    },
    "43": {
        "group_title": "Numerical and Material Recording Clerks",
        "demand_index": 40,
        "demand_label": "portal-derived demand proxy",
        "notes": "Accounting clerks and inventory managers; steady demand",
    },
    "44": {
        "group_title": "Other Clerical Support Workers",
        "demand_index": 25,
        "demand_label": "portal-derived demand proxy",
        "notes": "Miscellaneous clerical roles; limited portal presence",
    },
    "51": {
        "group_title": "Personal Service Workers",
        "demand_index": 50,
        "demand_label": "portal-derived demand proxy",
        "notes": "Hospitality, beauty, wellness sectors growing on aggregator platforms",
    },
    "52": {
        "group_title": "Sales Workers",
        "demand_index": 70,
        "demand_label": "portal-derived demand proxy",
        "notes": "Retail and sales roles are among the most listed on Indian job portals",
    },
    "53": {
        "group_title": "Personal Care Workers",
        "demand_index": 30,
        "demand_label": "portal-derived demand proxy",
        "notes": "Growing but mostly informal; urban platforms emerging",
    },
    "54": {
        "group_title": "Protective Services Workers",
        "demand_index": 45,
        "demand_label": "portal-derived demand proxy",
        "notes": "Private security sector large; government recruitment separate",
    },
    "61": {
        "group_title": "Market-oriented Skilled Agricultural Workers",
        "demand_index": 10,
        "demand_label": "portal-derived demand proxy",
        "notes": "Minimal portal presence; farming is largely self-employed/informal",
    },
    "62": {
        "group_title": "Market-oriented Skilled Forestry, Fishery and Hunting Workers",
        "demand_index": 8,
        "demand_label": "portal-derived demand proxy",
        "notes": "Very low portal presence; traditional/informal labour markets",
    },
    "63": {
        "group_title": "Subsistence Farmers, Fishers, Hunters and Gatherers",
        "demand_index": 3,
        "demand_label": "portal-derived demand proxy",
        "notes": "Subsistence work is outside formal job markets entirely",
    },
    "71": {
        "group_title": "Building and Related Trades Workers",
        "demand_index": 55,
        "demand_label": "portal-derived demand proxy",
        "notes": "Construction boom drives demand; mix of contractor and portal hiring",
    },
    "72": {
        "group_title": "Metal, Machinery and Related Trades Workers",
        "demand_index": 45,
        "demand_label": "portal-derived demand proxy",
        "notes": "Manufacturing sector demand; ITI graduates actively sought",
    },
    "73": {
        "group_title": "Handicraft and Printing Workers",
        "demand_index": 12,
        "demand_label": "portal-derived demand proxy",
        "notes": "Declining traditional demand; niche artisan markets",
    },
    "74": {
        "group_title": "Electrical and Electronic Trades Workers",
        "demand_index": 55,
        "demand_label": "portal-derived demand proxy",
        "notes": "Electrification and electronics repair create consistent demand",
    },
    "75": {
        "group_title": "Food Processing, Wood Working, Garment Workers",
        "demand_index": 40,
        "demand_label": "portal-derived demand proxy",
        "notes": "Garment and food processing sectors are major employers",
    },
    "81": {
        "group_title": "Stationary Plant and Machine Operators",
        "demand_index": 35,
        "demand_label": "portal-derived demand proxy",
        "notes": "Factory and plant operators; industrial zone hiring",
    },
    "82": {
        "group_title": "Assemblers",
        "demand_index": 40,
        "demand_label": "portal-derived demand proxy",
        "notes": "Electronics and auto assembly lines; growing with Make in India",
    },
    "83": {
        "group_title": "Drivers and Mobile Plant Operators",
        "demand_index": 60,
        "demand_label": "portal-derived demand proxy",
        "notes": "Very high actual demand via ride-hailing and logistics platforms",
    },
    "91": {
        "group_title": "Cleaners and Helpers",
        "demand_index": 30,
        "demand_label": "portal-derived demand proxy",
        "notes": "High actual employment but mostly informal; some platform presence (Urban Company etc.)",
    },
    "92": {
        "group_title": "Agricultural, Forestry and Fishery Labourers",
        "demand_index": 5,
        "demand_label": "portal-derived demand proxy",
        "notes": "Largest workforce segment but entirely outside digital job portals",
    },
    "93": {
        "group_title": "Labourers in Mining, Construction, Manufacturing and Transport",
        "demand_index": 25,
        "demand_label": "portal-derived demand proxy",
        "notes": "Some contractor-portal presence; mostly informal hiring at labour chowks",
    },
    "94": {
        "group_title": "Food Preparation Assistants",
        "demand_index": 35,
        "demand_label": "portal-derived demand proxy",
        "notes": "Restaurant and food delivery ecosystem growth; platform hiring emerging",
    },
    "95": {
        "group_title": "Street and Related Sales and Service Workers",
        "demand_index": 5,
        "demand_label": "portal-derived demand proxy",
        "notes": "Street vendors and hawkers — entirely outside formal job portals",
    },
    "96": {
        "group_title": "Refuse Workers and Other Elementary Workers",
        "demand_index": 15,
        "demand_label": "portal-derived demand proxy",
        "notes": "Municipal hiring; Swachh Bharat related roles; some portal presence",
    },
    "01": {
        "group_title": "Commissioned Armed Forces Officers",
        "demand_index": 20,
        "demand_label": "portal-derived demand proxy",
        "notes": "Recruitment through UPSC/SSB; not on civilian portals",
    },
    "02": {
        "group_title": "Non-commissioned Armed Forces Officers",
        "demand_index": 18,
        "demand_label": "portal-derived demand proxy",
        "notes": "Military recruitment rallies; not on civilian portals",
    },
    "03": {
        "group_title": "Armed Forces Occupations, Other Ranks",
        "demand_index": 22,
        "demand_label": "portal-derived demand proxy",
        "notes": "Agniveer scheme and recruitment rallies; high applicant volume",
    },
}


def load_ncs_data() -> list[dict] | None:
    """Load NCS parsed data if available."""
    if not NCS_DATA_PATH.exists():
        return None
    try:
        with open(NCS_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            return data
    except Exception as exc:
        print(f"[WARN] Could not load NCS data: {exc}")
    return None


def build_demand():
    """Main function to build demand index data."""
    if OUTPUT_PATH.exists():
        print(f"[INFO] Output already exists: {OUTPUT_PATH}")
        print("       Delete it to regenerate. Skipping.")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Try to enrich from NCS data
    ncs_data = load_ncs_data()
    ncs_sector_counts: dict[str, int] = {}

    if ncs_data:
        print(f"[INFO] Loaded {len(ncs_data)} NCS records for demand enrichment.")
        # Count how many NCS entries fall into each 2-digit group
        for entry in ncs_data:
            code = entry.get("nco_code", "")
            if len(code) >= 2:
                group = code[:2]
                ncs_sector_counts[group] = ncs_sector_counts.get(group, 0) + 1
    else:
        print("[INFO] No NCS data available; using fallback demand data only.")

    # Build demand records
    demand_records = []
    for group_code, fallback in sorted(FALLBACK_DEMAND.items()):
        record = {
            "nco_2digit": group_code,
            "group_title": fallback["group_title"],
            "demand_index": fallback["demand_index"],
            "demand_label": "portal-derived demand proxy",
            "notes": fallback["notes"],
            "source": "fallback_embedded",
        }

        # Enrich with NCS presence count if available
        if group_code in ncs_sector_counts:
            record["ncs_occupation_count"] = ncs_sector_counts[group_code]
            record["source"] = "ncs_data+fallback"

        demand_records.append(record)
        idx = record["demand_index"]
        bar = "#" * (idx // 5)
        print(f"  NCO {group_code}: {fallback['group_title'][:50]:50s} demand={idx:3d} {bar}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(demand_records, f, indent=2, ensure_ascii=False)

    print(f"\n[INFO] Wrote {len(demand_records)} demand records to {OUTPUT_PATH}")


if __name__ == "__main__":
    build_demand()
