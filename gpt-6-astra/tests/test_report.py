"""Standard-library checks for the report artifact and builder."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

from generate_report import ROOT, build_report


class ReportTests(unittest.TestCase):
    """Check embedded source integrity and portable delivery constraints."""

    def setUp(self) -> None:
        self.source = ROOT / "engine-comparison-summary-data.json"
        self.report = (ROOT / "engine-comparison-summary.html").read_text()

    def test_embedded_data_is_complete(self) -> None:
        match = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', self.report, re.S)
        self.assertIsNotNone(match)
        self.assertEqual(json.loads(match.group(1)), json.loads(self.source.read_text()))

    def test_fingerprint(self) -> None:
        self.assertIn(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.report)

    def test_no_external_dependencies_or_unresolved_tokens(self) -> None:
        self.assertNotRegex(self.report, r'(?:src|href)=["\'](?:https?:)?//')
        self.assertNotRegex(self.report, r'@import|url\(\s*["\']?https?://')
        self.assertNotIn('__REPORT_DATA__', self.report)
        self.assertNotIn('__SOURCE_', self.report)

    def test_rebuild_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'report.html'
            build_report(self.source, out)
            self.assertEqual(out.read_text(), self.report)

    def test_script_closing_data_is_escaped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'input.json'
            output = Path(temp) / 'report.html'
            data = json.loads(self.source.read_text())
            data['hostile_text'] = '</script><script>alert("x")</script>'
            source.write_text(json.dumps(data))
            build_report(source, output)
            text = output.read_text()
            self.assertNotIn(data['hostile_text'], text)
            embedded = re.search(r'id="report-data">(.*?)</script>', text, re.S)
            self.assertEqual(json.loads(embedded.group(1))['hostile_text'], data['hostile_text'])


if __name__ == '__main__':
    unittest.main()
