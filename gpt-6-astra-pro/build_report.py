#!/usr/bin/env python3
"""Build a portable, offline engine-comparison report using only the standard library."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build_report() -> Path:
    """Embed the complete source dataset into the HTML template without script injection."""
    source = ROOT / "engine-comparison-summary-data.json"
    raw = source.read_bytes()
    data = json.loads(raw)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    template = (ROOT / "report-template.html").read_text(encoding="utf-8")
    result = template.replace("__SOURCE_JSON__", payload).replace("__JSON_SHA256__", hashlib.sha256(raw).hexdigest())
    target = ROOT / "engine-comparison-report.html"
    target.write_text(result, encoding="utf-8")
    return target


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.info("Created %s", build_report())
