#!/usr/bin/env python3
"""
Playwright-based scraper for NCS (National Career Service) occupation pages.

Takes NCO codes from data/raw/nco_2015.json, navigates to the NCS content
repository for each occupation, and saves raw HTML to data/raw/ncs_html/.
"""

import json
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
NCO_PATH = ROOT / "data" / "raw" / "nco_2015.json"
HTML_DIR = ROOT / "data" / "raw" / "ncs_html"
NCS_URL = "https://www.ncs.gov.in/content-repository/Pages/ViewNcoDetails.aspx"

DELAY_SECONDS = 2  # polite scraping delay


def load_nco_codes(path: Path) -> list[dict]:
    """Load NCO code entries from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Expect a list of dicts; each should have at minimum a 'code' (or 'nco_code') and 'title' field
    if isinstance(data, list):
        return data
    # If it's a dict with a top-level key wrapping a list, try common keys
    for key in ("occupations", "codes", "data", "nco"):
        if key in data and isinstance(data[key], list):
            return data[key]
    raise ValueError(f"Cannot interpret NCO data structure in {path}")


def get_code(entry: dict) -> str:
    """Extract the NCO code string from an entry dict."""
    for key in ("code", "nco_code", "nco", "Code", "NCO_Code"):
        if key in entry:
            return str(entry[key]).strip()
    raise KeyError(f"No code field found in entry: {entry}")


def get_title(entry: dict) -> str:
    """Extract the occupation title from an entry dict."""
    for key in ("title", "occupation", "name", "Title", "Occupation"):
        if key in entry:
            return str(entry[key]).strip()
    return ""


def scrape_all():
    """Main scraping loop using Playwright."""
    if not NCO_PATH.exists():
        print(f"[ERROR] NCO input file not found: {NCO_PATH}")
        print("        Please ensure data/raw/nco_2015.json exists before running.")
        return

    entries = load_nco_codes(NCO_PATH)
    print(f"[INFO] Loaded {len(entries)} NCO entries from {NCO_PATH}")

    HTML_DIR.mkdir(parents=True, exist_ok=True)

    # Count how many are already done
    already = sum(1 for e in entries if (HTML_DIR / f"{get_code(e)}.html").exists())
    print(f"[INFO] {already}/{len(entries)} already scraped — will skip those.")

    from playwright.sync_api import sync_playwright  # noqa: late import

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for i, entry in enumerate(entries, start=1):
            code = get_code(entry)
            title = get_title(entry)
            out_path = HTML_DIR / f"{code}.html"

            if out_path.exists():
                continue  # skip already-scraped

            label = f"[{i}/{len(entries)}]"
            print(f"{label} Scraping NCO {code}: {title} ...")

            try:
                # Navigate to the NCS page
                page.goto(NCS_URL, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)

                # Try to find and fill a search/input box for the NCO code
                # NCS pages typically have a search input; try common selectors
                search_selectors = [
                    'input[id*="txtSearch"]',
                    'input[id*="txtNco"]',
                    'input[name*="search"]',
                    'input[type="text"]',
                ]
                filled = False
                for sel in search_selectors:
                    try:
                        el = page.query_selector(sel)
                        if el:
                            el.fill(code)
                            filled = True
                            break
                    except Exception:
                        continue

                if filled:
                    # Try clicking a search/submit button
                    btn_selectors = [
                        'input[type="submit"]',
                        'button[id*="btnSearch"]',
                        'a[id*="btnSearch"]',
                        'button[type="submit"]',
                        "#btnSearch",
                    ]
                    for sel in btn_selectors:
                        try:
                            btn = page.query_selector(sel)
                            if btn:
                                btn.click()
                                page.wait_for_load_state("networkidle", timeout=15000)
                                break
                        except Exception:
                            continue

                # Save whatever page content we got
                html = page.content()
                out_path.write_text(html, encoding="utf-8")
                print(f"{label} Saved {out_path.name} ({len(html)} bytes)")

            except Exception as exc:
                print(f"{label} ERROR scraping {code}: {exc}")

            time.sleep(DELAY_SECONDS)

        browser.close()

    print("[INFO] Scraping complete.")


if __name__ == "__main__":
    scrape_all()
