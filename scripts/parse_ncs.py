#!/usr/bin/env python3
"""
Parses raw NCS HTML files into structured data.

Reads HTML from data/raw/ncs_html/, extracts occupation details using
BeautifulSoup, and produces:
  - Markdown files in data/intermediate/ncs_pages/<nco_code>.md
  - Structured JSON at data/intermediate/ncs_data.json
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "data" / "raw" / "ncs_html"
MD_DIR = ROOT / "data" / "intermediate" / "ncs_pages"
JSON_OUT = ROOT / "data" / "intermediate" / "ncs_data.json"


def clean_text(text: str) -> str:
    """Collapse whitespace and strip."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def extract_section(soup: BeautifulSoup, heading_text: str) -> str | None:
    """Find a section by its heading text and return the following content."""
    # Try finding headings (h2, h3, h4, strong, span) that contain the text
    for tag in soup.find_all(re.compile(r"^(h[1-6]|strong|b|span|div|label)")):
        if heading_text.lower() in (tag.get_text() or "").lower():
            # Collect sibling text until next heading
            parts = []
            sibling = tag.find_next_sibling()
            while sibling:
                if sibling.name and re.match(r"^h[1-6]$", sibling.name):
                    break
                txt = clean_text(sibling.get_text())
                if txt:
                    parts.append(txt)
                sibling = sibling.find_next_sibling()
            if parts:
                return "\n".join(parts)
    return None


def extract_list_section(soup: BeautifulSoup, heading_text: str) -> list[str]:
    """Extract a list of items from a section identified by heading text."""
    for tag in soup.find_all(re.compile(r"^(h[1-6]|strong|b|span|div|label)")):
        if heading_text.lower() in (tag.get_text() or "").lower():
            # Look for a <ul> or <ol> nearby
            sibling = tag.find_next_sibling()
            while sibling:
                if sibling.name in ("ul", "ol"):
                    return [
                        clean_text(li.get_text())
                        for li in sibling.find_all("li")
                        if clean_text(li.get_text())
                    ]
                if sibling.name and re.match(r"^h[1-6]$", sibling.name):
                    break
                sibling = sibling.find_next_sibling()
    return []


def parse_html(html_path: Path) -> dict | None:
    """Parse a single NCS HTML file into a structured dict."""
    html = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    # Try to extract the title from the page
    title = None
    for sel in [
        'span[id*="lblOccupation"]',
        'span[id*="lblTitle"]',
        "h1",
        "h2",
        ".occupation-title",
    ]:
        el = soup.select_one(sel)
        if el:
            title = clean_text(el.get_text())
            if title:
                break

    # If we got an essentially empty page, skip
    body_text = clean_text(soup.get_text())
    if len(body_text) < 100:
        return None

    # Extract fields
    description = extract_section(soup, "description") or extract_section(
        soup, "about"
    )
    tasks = extract_list_section(soup, "task") or extract_list_section(
        soup, "duties"
    )
    sectors = extract_list_section(soup, "sector") or extract_list_section(
        soup, "industry"
    )
    related = extract_list_section(soup, "related") or extract_list_section(
        soup, "similar"
    )

    # Fallback: try to grab the main content area
    if not description:
        main = soup.select_one("#MainContent, .main-content, #content, .content")
        if main:
            description = clean_text(main.get_text())[:2000]

    return {
        "title": title,
        "description": description,
        "tasks": tasks if tasks else None,
        "sectors": sectors if sectors else None,
        "related_occupations": related if related else None,
    }


def to_markdown(code: str, data: dict) -> str:
    """Convert parsed occupation data to Markdown."""
    lines = [f"# NCO {code}: {data.get('title') or 'Unknown'}"]
    lines.append("")
    if data.get("description"):
        lines.append("## Description")
        lines.append(data["description"])
        lines.append("")
    if data.get("tasks"):
        lines.append("## Tasks")
        for t in data["tasks"]:
            lines.append(f"- {t}")
        lines.append("")
    if data.get("sectors"):
        lines.append("## Sectors")
        for s in data["sectors"]:
            lines.append(f"- {s}")
        lines.append("")
    if data.get("related_occupations"):
        lines.append("## Related Occupations")
        for r in data["related_occupations"]:
            lines.append(f"- {r}")
        lines.append("")
    return "\n".join(lines)


def parse_all():
    """Parse all NCS HTML files."""
    if not HTML_DIR.exists():
        print(f"[WARN] HTML directory not found: {HTML_DIR}")
        print("       Run scrape_ncs.py first, or place HTML files manually.")
        return

    html_files = sorted(HTML_DIR.glob("*.html"))
    if not html_files:
        print(f"[WARN] No HTML files found in {HTML_DIR}")
        return

    print(f"[INFO] Found {len(html_files)} HTML files to parse.")

    MD_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)

    # Load existing JSON data if present (for incremental updates)
    existing: dict[str, dict] = {}
    if JSON_OUT.exists():
        try:
            with open(JSON_OUT, "r", encoding="utf-8") as f:
                existing_list = json.load(f)
            if isinstance(existing_list, list):
                for item in existing_list:
                    if "nco_code" in item:
                        existing[item["nco_code"]] = item
            elif isinstance(existing_list, dict):
                existing = existing_list
        except Exception:
            pass

    all_data: dict[str, dict] = dict(existing)
    parsed_count = 0
    skipped_count = 0

    for html_path in html_files:
        code = html_path.stem
        md_path = MD_DIR / f"{code}.md"

        # Skip if already parsed
        if code in all_data and md_path.exists():
            skipped_count += 1
            continue

        print(f"  Parsing {code} ...")
        try:
            result = parse_html(html_path)
            if result is None:
                print(f"  [WARN] No usable content in {html_path.name}")
                continue

            record = {"nco_code": code, **result}
            all_data[code] = record

            # Write Markdown
            md_content = to_markdown(code, result)
            md_path.write_text(md_content, encoding="utf-8")

            parsed_count += 1
        except Exception as exc:
            print(f"  [ERROR] {code}: {exc}")

    # Write combined JSON (as a list)
    output_list = list(all_data.values())
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(output_list, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Parsed {parsed_count} new, skipped {skipped_count} existing.")
    print(f"[INFO] Total records: {len(output_list)}")
    print(f"[INFO] JSON output: {JSON_OUT}")
    print(f"[INFO] Markdown dir: {MD_DIR}")


if __name__ == "__main__":
    parse_all()
