#!/usr/bin/env python3
"""Inline engine-comparison-summary-data.json into the report template.

Produces a single self-contained HTML file with no network dependencies.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "engine-comparison-summary-data.json"
TEMPLATE = ROOT / "report.template.html"
OUT = ROOT / "engine-comparison-summary.html"
PLACEHOLDER = "/*__DATA__*/"


def embed(raw: str) -> str:
    """Make JSON safe inside an HTML <script> element without altering values."""
    return raw.replace("</", "<\\/").replace("<!--", "<\\!--")


def main() -> None:
    raw = DATA.read_text(encoding="utf-8")
    data = json.loads(raw)  # validate
    compact = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    html = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise SystemExit(f"placeholder {PLACEHOLDER} missing from {TEMPLATE.name}")
    html = html.replace(PLACEHOLDER, embed(compact))
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.name}  {OUT.stat().st_size:,} bytes")
    print(f"embedded payload {len(compact):,} chars")
    print(f"json sha256      {hashlib.sha256(raw.encode()).hexdigest()}")
    # data['sha256'] is the digest of the upstream source document, not of this JSON.
    print(f"source doc       {data['source']} @ {data['sha256'][:16]}...")


if __name__ == "__main__":
    main()
