from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class SiteAssetsTest(unittest.TestCase):
    def test_index_points_to_methodology_page(self):
        index_html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="methodology.html"', index_html)
        self.assertNotIn("alert(", index_html)

    def test_methodology_page_exists(self):
        self.assertTrue((ROOT / "site" / "methodology.html").exists())

    def test_favicon_exists(self):
        self.assertTrue((ROOT / "site" / "favicon.svg").exists())
