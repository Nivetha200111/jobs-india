#!/usr/bin/env python3
"""
Scrapes/parses NSDC qualification packs and maps them to NCO codes.

Attempts live scraping from NSDC website, falls back to embedded data
mapping NCO 2-digit groups to typical education/training requirements.

Outputs: data/intermediate/nsdc_skills.json
"""

import json
import re
from pathlib import Path

try:
    import httpx
    from bs4 import BeautifulSoup
    HAS_SCRAPE_DEPS = True
except ImportError:
    HAS_SCRAPE_DEPS = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
NCO_PATH = ROOT / "data" / "raw" / "nco_2015.json"
OUTPUT_PATH = ROOT / "data" / "intermediate" / "nsdc_skills.json"
NSDC_URL = "https://nsdcindia.org/national-occupational-standards"

# ---------------------------------------------------------------------------
# Embedded fallback: NCO 2-digit group -> education/training requirements
# Covers all NCO 2-digit codes (01-96) with reasonable proxies.
# ---------------------------------------------------------------------------
FALLBACK_SKILLS: dict[str, dict] = {
    "11": {
        "group_title": "Chief Executives, Senior Officials and Legislators",
        "education_proxy": "Postgraduate degree or equivalent; MBA/MPA common",
        "training_context": "Extensive management experience (15+ years); leadership development programs; policy and governance training",
        "key_competencies": ["Strategic planning", "Policy formulation", "Stakeholder management", "Governance", "Decision-making"],
    },
    "12": {
        "group_title": "Administrative and Commercial Managers",
        "education_proxy": "Bachelor's or postgraduate degree in business/management",
        "training_context": "5-10 years managerial experience; professional certifications (PMP, Six Sigma); industry-specific training",
        "key_competencies": ["Operations management", "Financial planning", "Human resource management", "Business development", "Compliance"],
    },
    "13": {
        "group_title": "Production and Specialised Services Managers",
        "education_proxy": "Bachelor's degree in engineering/technology or relevant field",
        "training_context": "Technical management training; sector-specific certifications; 5+ years in production/operations",
        "key_competencies": ["Production planning", "Quality management", "Supply chain management", "Technical oversight", "Safety management"],
    },
    "14": {
        "group_title": "Hospitality, Retail and Other Services Managers",
        "education_proxy": "Bachelor's degree in hotel management/business; diploma acceptable",
        "training_context": "Customer service training; hospitality management programs; 3-5 years experience",
        "key_competencies": ["Customer service", "Revenue management", "Staff supervision", "Inventory management", "Marketing"],
    },
    "21": {
        "group_title": "Science and Engineering Professionals",
        "education_proxy": "Bachelor's or Master's in science/engineering (B.Tech/M.Tech/M.Sc)",
        "training_context": "Research methodology; laboratory techniques; professional engineering certifications; continuing education",
        "key_competencies": ["Research and analysis", "Technical design", "Problem-solving", "Data analysis", "Scientific methodology"],
    },
    "22": {
        "group_title": "Health Professionals",
        "education_proxy": "MBBS/BDS/BAMS/BHMS or equivalent professional degree; postgraduate specialization common",
        "training_context": "Internship and residency (1-3 years); continuing medical education; professional registration with Medical Council of India",
        "key_competencies": ["Clinical diagnosis", "Patient care", "Medical procedures", "Health counselling", "Emergency response"],
    },
    "23": {
        "group_title": "Teaching Professionals",
        "education_proxy": "Bachelor's degree + B.Ed; Master's/PhD for higher education",
        "training_context": "Teacher training certification (B.Ed/D.El.Ed); CTET/state TET qualification; pedagogy workshops",
        "key_competencies": ["Curriculum design", "Classroom management", "Student assessment", "Pedagogical skills", "Subject expertise"],
    },
    "24": {
        "group_title": "Business and Administration Professionals",
        "education_proxy": "Bachelor's or Master's degree in commerce/business (B.Com/MBA/CA/CS)",
        "training_context": "Professional certification (CA, CS, CMA, CFA); articleship; continuing professional development",
        "key_competencies": ["Financial analysis", "Accounting", "Business consulting", "Regulatory compliance", "Strategic planning"],
    },
    "25": {
        "group_title": "Information and Communications Technology Professionals",
        "education_proxy": "Bachelor's in computer science/IT (B.Tech/BCA/MCA)",
        "training_context": "Technology certifications (AWS, Azure, Cisco); coding bootcamps; agile/DevOps training; continuous learning",
        "key_competencies": ["Software development", "System design", "Database management", "Cybersecurity", "Cloud computing"],
    },
    "26": {
        "group_title": "Legal, Social and Cultural Professionals",
        "education_proxy": "Bachelor's or Master's degree (LLB, MA, MSW); professional registration",
        "training_context": "Bar council enrollment (law); field practicum (social work); creative portfolio development",
        "key_competencies": ["Legal analysis", "Social research", "Creative expression", "Advocacy", "Cultural literacy"],
    },
    "31": {
        "group_title": "Science and Engineering Associate Professionals",
        "education_proxy": "Diploma in engineering/technology (polytechnic); some hold B.Tech",
        "training_context": "Industrial training; apprenticeship programs; sector skill council certifications",
        "key_competencies": ["Technical drawing", "Equipment operation", "Quality testing", "Fieldwork", "Technical troubleshooting"],
    },
    "32": {
        "group_title": "Health Associate Professionals",
        "education_proxy": "Diploma or bachelor's in nursing/pharmacy/allied health (GNM/B.Sc Nursing/D.Pharm)",
        "training_context": "Clinical training; state nursing/pharmacy council registration; continuing education",
        "key_competencies": ["Patient care", "Medication administration", "Diagnostic procedures", "Health education", "Record keeping"],
    },
    "33": {
        "group_title": "Business and Administration Associate Professionals",
        "education_proxy": "Bachelor's degree or diploma in commerce/business",
        "training_context": "On-the-job training; short-term professional courses; banking/insurance certifications",
        "key_competencies": ["Data entry and processing", "Customer relations", "Bookkeeping", "Sales support", "Administrative coordination"],
    },
    "34": {
        "group_title": "Legal, Social, Cultural and Related Associate Professionals",
        "education_proxy": "Diploma or bachelor's degree in relevant field",
        "training_context": "Fieldwork training; community engagement programs; media production training",
        "key_competencies": ["Community mobilization", "Documentation", "Event coordination", "Media production", "Counselling"],
    },
    "35": {
        "group_title": "Information and Communications Technicians",
        "education_proxy": "Diploma in IT/electronics; ITI certificate; BCA",
        "training_context": "Hardware/networking certifications; vendor-specific training (Microsoft, Cisco); apprenticeships",
        "key_competencies": ["Network setup", "Hardware maintenance", "User support", "System administration", "Troubleshooting"],
    },
    "41": {
        "group_title": "General and Keyboard Clerks",
        "education_proxy": "Higher secondary (12th pass); typing/computer certificate",
        "training_context": "Basic computer training; typing proficiency; office procedures training",
        "key_competencies": ["Data entry", "Filing and documentation", "Word processing", "Office administration", "Record maintenance"],
    },
    "42": {
        "group_title": "Customer Services Clerks",
        "education_proxy": "Higher secondary or bachelor's degree",
        "training_context": "Customer service training; communication skills; product knowledge training",
        "key_competencies": ["Customer interaction", "Information provision", "Complaint handling", "Cash handling", "Telephone etiquette"],
    },
    "43": {
        "group_title": "Numerical and Material Recording Clerks",
        "education_proxy": "Higher secondary with commerce; diploma in accounting",
        "training_context": "Accounting software training (Tally); inventory management systems; basic bookkeeping courses",
        "key_competencies": ["Accounting", "Inventory tracking", "Data recording", "Statistical compilation", "Financial documentation"],
    },
    "44": {
        "group_title": "Other Clerical Support Workers",
        "education_proxy": "Higher secondary (12th pass); basic computer literacy",
        "training_context": "On-the-job training; office skills programs; postal/sorting procedures",
        "key_competencies": ["Mail handling", "Coding and sorting", "Proofreading", "Library management", "Administrative support"],
    },
    "51": {
        "group_title": "Personal Service Workers",
        "education_proxy": "Secondary (10th pass) to higher secondary; vocational certificates",
        "training_context": "Vocational training in hospitality/beauty/wellness; short-term skill courses; NSDC certifications",
        "key_competencies": ["Personal grooming services", "Food service", "Travel assistance", "Housekeeping", "Customer care"],
    },
    "52": {
        "group_title": "Sales Workers",
        "education_proxy": "Secondary to higher secondary; often informal training",
        "training_context": "Product knowledge training; sales techniques; shop floor experience; some have retail management diplomas",
        "key_competencies": ["Salesmanship", "Product display", "Customer persuasion", "Cash handling", "Inventory awareness"],
    },
    "53": {
        "group_title": "Personal Care Workers",
        "education_proxy": "Secondary education; short-term care training",
        "training_context": "Healthcare assistant training; childcare/eldercare certifications; first aid training",
        "key_competencies": ["Patient assistance", "Child care", "Elder care", "Health monitoring", "Empathy and communication"],
    },
    "54": {
        "group_title": "Protective Services Workers",
        "education_proxy": "Secondary to higher secondary; police/military training",
        "training_context": "Police academy training; fire service training; private security certification (PSARA); physical fitness",
        "key_competencies": ["Law enforcement", "Crowd management", "Emergency response", "Physical fitness", "Surveillance"],
    },
    "61": {
        "group_title": "Market-oriented Skilled Agricultural Workers",
        "education_proxy": "Primary to secondary education; agricultural extension training",
        "training_context": "Krishi Vigyan Kendra (KVK) training; state agricultural university extension; practical farming experience",
        "key_competencies": ["Crop cultivation", "Soil management", "Irrigation", "Pest control", "Harvest and storage"],
    },
    "62": {
        "group_title": "Market-oriented Skilled Forestry, Fishery and Hunting Workers",
        "education_proxy": "Primary to secondary education; some vocational training",
        "training_context": "Fishery training institutes; forestry extension programs; traditional knowledge transfer",
        "key_competencies": ["Fish cultivation", "Forest produce collection", "Animal husbandry", "Sustainable harvesting", "Equipment maintenance"],
    },
    "63": {
        "group_title": "Subsistence Farmers, Fishers, Hunters and Gatherers",
        "education_proxy": "Primary education or below; informal/traditional learning",
        "training_context": "Intergenerational knowledge transfer; minimal formal training; some government scheme participation",
        "key_competencies": ["Traditional farming", "Foraging", "Basic animal rearing", "Weather reading", "Self-sufficiency"],
    },
    "71": {
        "group_title": "Building and Related Trades Workers (excluding Electricians)",
        "education_proxy": "Primary to secondary education; ITI certificate in some cases",
        "training_context": "Apprenticeship under master craftsmen; PMKVY construction sector courses; on-site training",
        "key_competencies": ["Masonry", "Carpentry", "Plumbing", "Painting", "Blueprint reading"],
    },
    "72": {
        "group_title": "Metal, Machinery and Related Trades Workers",
        "education_proxy": "ITI/ITC certificate; secondary education",
        "training_context": "ITI courses (fitter, turner, welder, machinist); apprenticeship under Apprentices Act; NSDC certifications",
        "key_competencies": ["Welding", "Machining", "Sheet metal work", "Tool maintenance", "Quality inspection"],
    },
    "73": {
        "group_title": "Handicraft and Printing Workers",
        "education_proxy": "Primary to secondary; traditional craft training",
        "training_context": "Master craftsperson training; DC Handicrafts programs; printing technology diplomas",
        "key_competencies": ["Artisan craftsmanship", "Pattern making", "Printing operations", "Material selection", "Design execution"],
    },
    "74": {
        "group_title": "Electrical and Electronic Trades Workers",
        "education_proxy": "ITI certificate in electrician/electronics; diploma",
        "training_context": "ITI electrician course (2 years); apprenticeship; wireman licensing; safety training",
        "key_competencies": ["Electrical installation", "Circuit repair", "Electronics troubleshooting", "Safety protocols", "Equipment testing"],
    },
    "75": {
        "group_title": "Food Processing, Wood Working, Garment and Other Craft Workers",
        "education_proxy": "Primary to secondary; vocational training",
        "training_context": "Food technology diplomas; tailoring/garment courses; NSDC sector skill council training",
        "key_competencies": ["Food preparation", "Garment construction", "Wood crafting", "Quality control", "Machine operation"],
    },
    "81": {
        "group_title": "Stationary Plant and Machine Operators",
        "education_proxy": "Secondary education; ITI in relevant trade",
        "training_context": "Machine-specific operator training; boiler attendant certification; industrial safety courses",
        "key_competencies": ["Machine operation", "Process monitoring", "Basic maintenance", "Safety compliance", "Production logging"],
    },
    "82": {
        "group_title": "Assemblers",
        "education_proxy": "Secondary education; some ITI training",
        "training_context": "Assembly line training; quality control procedures; lean manufacturing basics",
        "key_competencies": ["Component assembly", "Quality checking", "Manual dexterity", "Production tracking", "Team coordination"],
    },
    "83": {
        "group_title": "Drivers and Mobile Plant Operators",
        "education_proxy": "Primary to secondary education; valid driving license",
        "training_context": "Driving school certification; heavy vehicle license training; transport authority permit",
        "key_competencies": ["Vehicle operation", "Route navigation", "Vehicle maintenance", "Traffic law compliance", "Cargo handling"],
    },
    "91": {
        "group_title": "Cleaners and Helpers",
        "education_proxy": "Primary education or below; minimal formal requirements",
        "training_context": "On-the-job training; basic sanitation/hygiene courses; some municipal training",
        "key_competencies": ["Cleaning procedures", "Waste management", "Sanitation", "Equipment use", "Physical stamina"],
    },
    "92": {
        "group_title": "Agricultural, Forestry and Fishery Labourers",
        "education_proxy": "Primary education or below",
        "training_context": "Informal on-farm training; seasonal agricultural labour; MGNREGA skilling",
        "key_competencies": ["Manual harvesting", "Field preparation", "Carrying and loading", "Basic tool use", "Physical endurance"],
    },
    "93": {
        "group_title": "Labourers in Mining, Construction, Manufacturing and Transport",
        "education_proxy": "Primary education or below",
        "training_context": "On-site safety induction; manual labour experience; no formal certification typically required",
        "key_competencies": ["Heavy lifting", "Construction assistance", "Material transport", "Basic tool operation", "Safety awareness"],
    },
    "94": {
        "group_title": "Food Preparation Assistants",
        "education_proxy": "Primary to secondary education",
        "training_context": "On-the-job kitchen training; basic food safety/hygiene; FSSAI awareness",
        "key_competencies": ["Food preparation assistance", "Kitchen cleaning", "Ingredient sorting", "Basic cooking", "Hygiene maintenance"],
    },
    "95": {
        "group_title": "Street and Related Sales and Service Workers",
        "education_proxy": "Primary education or below; minimal formal requirements",
        "training_context": "Self-taught or family-taught; informal apprenticeship; micro-enterprise experience",
        "key_competencies": ["Street vending", "Customer interaction", "Cash management", "Product sourcing", "Weather resilience"],
    },
    "96": {
        "group_title": "Refuse Workers and Other Elementary Workers",
        "education_proxy": "Primary education or below",
        "training_context": "Municipal training where applicable; waste segregation awareness; minimal formal training",
        "key_competencies": ["Waste collection", "Sorting and segregation", "Physical labour", "Basic sanitation", "Route adherence"],
    },
    # Additional codes that may appear in some NCO taxonomies
    "01": {
        "group_title": "Commissioned Armed Forces Officers",
        "education_proxy": "Bachelor's degree; military academy training (NDA/IMA/OTA)",
        "training_context": "National Defence Academy or Indian Military Academy; officer training 1-3 years; specialization courses",
        "key_competencies": ["Military tactics", "Leadership", "Strategic planning", "Physical fitness", "Crisis management"],
    },
    "02": {
        "group_title": "Non-commissioned Armed Forces Officers",
        "education_proxy": "Higher secondary; military training",
        "training_context": "Basic military training; NCO academy; specialized technical courses",
        "key_competencies": ["Squad leadership", "Tactical operations", "Equipment handling", "Training supervision", "Discipline enforcement"],
    },
    "03": {
        "group_title": "Armed Forces Occupations, Other Ranks",
        "education_proxy": "Secondary education (10th pass)",
        "training_context": "Basic military training (6-12 months); arms training; physical conditioning",
        "key_competencies": ["Combat readiness", "Weapon handling", "Physical endurance", "Discipline", "Team operations"],
    },
}


def try_live_scrape() -> dict | None:
    """
    Attempt to scrape NSDC qualification packs from the website.
    Returns a dict mapping titles to skill data, or None if scraping fails.
    """
    if not HAS_SCRAPE_DEPS:
        print("[WARN] httpx/beautifulsoup4 not installed, skipping live scrape.")
        return None
    print("[INFO] Attempting live scrape of NSDC qualification packs ...")
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(NSDC_URL)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for qualification pack data in tables or structured elements
        results = {}
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    title = cells[0].get_text(strip=True)
                    if title and len(title) > 3:
                        details = " | ".join(
                            c.get_text(strip=True) for c in cells[1:]
                        )
                        results[title] = {"raw_details": details}

        if results:
            print(f"[INFO] Live scrape found {len(results)} entries.")
            return results
        else:
            print("[WARN] Live scrape returned no structured data.")
            return None

    except Exception as exc:
        print(f"[WARN] Live scrape failed: {exc}")
        return None


def fuzzy_match_score(s1: str, s2: str) -> float:
    """Simple fuzzy matching score based on shared words."""
    words1 = set(re.findall(r"\w+", s1.lower()))
    words2 = set(re.findall(r"\w+", s2.lower()))
    if not words1 or not words2:
        return 0.0
    # Remove common stop words
    stop = {"and", "the", "of", "in", "for", "a", "an", "or", "to", "with", "not", "other"}
    words1 -= stop
    words2 -= stop
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


def load_nco_taxonomy() -> list[dict]:
    """Load NCO taxonomy from nco_2015.json if available."""
    if not NCO_PATH.exists():
        return []
    with open(NCO_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    for key in ("occupations", "codes", "data", "nco"):
        if key in data and isinstance(data[key], list):
            return data[key]
    return []


def get_nco_code(entry: dict) -> str:
    for key in ("code", "nco_code", "nco", "Code", "NCO_Code"):
        if key in entry:
            return str(entry[key]).strip()
    return ""


def get_nco_title(entry: dict) -> str:
    for key in ("title", "occupation", "name", "Title", "Occupation"):
        if key in entry:
            return str(entry[key]).strip()
    return ""


def build_skills():
    """Main function to build skills data."""
    if OUTPUT_PATH.exists():
        print(f"[INFO] Output already exists: {OUTPUT_PATH}")
        print("       Delete it to regenerate. Skipping.")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Try live scraping first
    live_data = try_live_scrape()

    # Load NCO taxonomy for mapping
    taxonomy = load_nco_taxonomy()
    print(f"[INFO] Loaded {len(taxonomy)} NCO entries from taxonomy.")

    # Build the skills dataset
    skills_records = []

    # If we have live data, try to match it to NCO codes
    matched_live = {}
    if live_data and taxonomy:
        print("[INFO] Attempting fuzzy matching of NSDC data to NCO codes ...")
        for nco_entry in taxonomy:
            code = get_nco_code(nco_entry)
            title = get_nco_title(nco_entry)
            if not code or not title:
                continue

            best_match = None
            best_score = 0.3  # minimum threshold
            for nsdc_title, nsdc_data in live_data.items():
                score = fuzzy_match_score(title, nsdc_title)
                if score > best_score:
                    best_score = score
                    best_match = (nsdc_title, nsdc_data)

            if best_match:
                matched_live[code] = {
                    "nsdc_title": best_match[0],
                    "match_score": round(best_score, 3),
                    **best_match[1],
                }

        print(f"[INFO] Matched {len(matched_live)} NCO codes to NSDC data.")

    # Build final output: combine live data with fallback
    # Process all 2-digit groups from fallback to ensure full coverage
    for group_code, fallback in FALLBACK_SKILLS.items():
        record = {
            "nco_2digit": group_code,
            "group_title": fallback["group_title"],
            "education_proxy": fallback["education_proxy"],
            "training_context": fallback["training_context"],
            "key_competencies": fallback["key_competencies"],
            "source": "fallback_embedded",
        }

        # If we have live-matched data for any code in this group, enrich
        live_enrichments = {
            code: data
            for code, data in matched_live.items()
            if code[:2] == group_code
        }
        if live_enrichments:
            record["nsdc_matches"] = live_enrichments
            record["source"] = "live_scrape+fallback"

        skills_records.append(record)
        print(f"  NCO {group_code}: {fallback['group_title']} [{record['source']}]")

    # Sort by code
    skills_records.sort(key=lambda r: r["nco_2digit"])

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(skills_records, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Wrote {len(skills_records)} skill records to {OUTPUT_PATH}")


if __name__ == "__main__":
    build_skills()
