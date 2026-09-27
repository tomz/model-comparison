#!/usr/bin/env python3
"""Build a self-contained HTML report from engine-comparison-summary-data.json.

Usage:
    python3 build_report.py [--data PATH] [--template PATH] [--out PATH]

The template contains a single ``__DATA_JSON__`` placeholder inside a
``<script type="application/json">`` block. The JSON is minified and escaped so
that it can never terminate the script element early.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path

log = logging.getLogger("build_report")

HERE = Path(__file__).resolve().parent


def embed_json(payload: object) -> str:
    """Serialise ``payload`` for safe inclusion inside a <script> element."""
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    # Prevent "</script>" or HTML comment openers from ending the block.
    return text.replace("</", "<\\/").replace("<!--", "<\\!--")


def build(data_path: Path, template_path: Path, out_path: Path) -> None:
    raw = data_path.read_bytes()
    data = json.loads(raw)
    file_sha = hashlib.sha256(raw).hexdigest()
    data.setdefault("_meta", {})
    data["_meta"]["json_file"] = data_path.name
    data["_meta"]["json_sha256"] = file_sha

    template = template_path.read_text(encoding="utf-8")
    if template.count("__DATA_JSON__") != 1:
        raise SystemExit("template must contain exactly one __DATA_JSON__ placeholder")
    html = template.replace("__DATA_JSON__", embed_json(data))
    out_path.write_text(html, encoding="utf-8")
    log.info("wrote %s (%d bytes)", out_path, len(html.encode("utf-8")))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=HERE.parent / "engine-comparison-summary-data.json")
    ap.add_argument("--template", type=Path, default=HERE / "report_template.html")
    ap.add_argument("--out", type=Path, default=HERE / "engine-comparison-report.html")
    args = ap.parse_args()
    build(args.data, args.template, args.out)


if __name__ == "__main__":
    main()
