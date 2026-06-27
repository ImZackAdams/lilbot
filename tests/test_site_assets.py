from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SiteAssetTests(unittest.TestCase):
    def test_static_sales_page_contains_paid_workflow(self) -> None:
        html = (PROJECT_ROOT / "site" / "index.html").read_text(encoding="utf-8")
        css = (PROJECT_ROOT / "site" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("Lilbot Pro", html)
        self.assertIn("lilbot pro audit .", html)
        self.assertIn("lilbot pro launch-pack", html)
        self.assertIn("lilbot license start-trial", html)
        self.assertIn("https://example.com/lilbot-pro-checkout", html)
        self.assertIn(".hero", css)
