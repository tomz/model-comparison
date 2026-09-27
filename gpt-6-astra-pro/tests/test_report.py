"""Standard-library acceptance tests for the portable artifact."""
from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReportParser(HTMLParser):
    """Collect markup evidence and embedded source data."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.links: list[str] = []
        self.external: list[str] = []
        self.in_data = False
        self.data = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(str(attributes["id"]))
        if tag == "a" and attributes.get("href", "").startswith("#"):
            self.links.append(str(attributes["href"])[1:])
        if tag in {"script", "img", "link", "iframe"}:
            for key in ("src", "href"):
                if attributes.get(key):
                    self.external.append(str(attributes[key]))
        if tag == "script" and attributes.get("id") == "report-data":
            self.in_data = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.in_data = False

    def handle_data(self, data: str) -> None:
        if self.in_data:
            self.data += data


class ReportTests(unittest.TestCase):
    """Check data fidelity, local navigation, and portability."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "engine-comparison-report.html").read_text()
        cls.source_bytes = (ROOT / "engine-comparison-summary-data.json").read_bytes()
        cls.source = json.loads(cls.source_bytes)
        cls.parser = ReportParser()
        cls.parser.feed(cls.html)

    def test_embedded_source_is_lossless(self) -> None:
        self.assertEqual(json.loads(self.parser.data), self.source)

    def test_no_external_assets(self) -> None:
        self.assertEqual(self.parser.external, [])
        self.assertNotIn("@import", self.html)
        self.assertNotIn("fetch(", self.html)

    def test_unique_ids_and_valid_links(self) -> None:
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))
        self.assertTrue(set(self.parser.links).issubset(self.parser.ids))

    def test_input_hash_and_no_template_tokens(self) -> None:
        self.assertIn(hashlib.sha256(self.source_bytes).hexdigest(), self.html)
        self.assertNotIn("__SOURCE_JSON__", self.html)
        self.assertNotIn("__JSON_SHA256__", self.html)

    def test_missing_cluster_coverage_is_preserved(self) -> None:
        rows = self.source["clusterQueries"]["10000"]
        unpaired = [row["q"] for row in rows if row["r"] is None or row["g"] is None]
        self.assertEqual(unpaired, [23, 39, 67, 78, 95])
        self.assertEqual(len(rows), 99)

    def test_baseline_ratios_are_consistent(self) -> None:
        for rows in self.source["totals"].values():
            for row in rows:
                baseline = next(r for r in rows if r["sf"] == row["sf"] and r["engine"] == "DuckDB 1.5.5")
                self.assertAlmostEqual(row["ratio"], row["time"] / baseline["time"], places=5)


if __name__ == "__main__":
    unittest.main()
