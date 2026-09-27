"""Build a portable engine-comparison report using only the Python standard library."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build_report(source: Path, destination: Path) -> None:
    """Embed the original dataset and source fingerprint into the report template."""
    raw = source.read_bytes()
    data = json.loads(raw)
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    encoded = encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    template = (ROOT / "report.template.html").read_text(encoding="utf-8")
    result = template.replace("__SOURCE_NAME__", html.escape(source.name))
    result = result.replace("__JSON_HASH__", hashlib.sha256(raw).hexdigest())
    result = result.replace("__SOURCE_HASH__", html.escape(str(data["sha256"])))
    result = result.replace("__SOURCE_DOCUMENT__", html.escape(data["source"]))
    result = result.replace("__REPORT_DATA__", encoded)
    destination.write_text(result, encoding="utf-8")
    logging.info("Wrote %s (%s bytes)", destination, destination.stat().st_size)


def main() -> None:
    """Parse optional source and destination paths and generate the report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "engine-comparison-summary-data.json")
    parser.add_argument("--output", type=Path, default=ROOT / "engine-comparison-summary.html")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    build_report(args.source, args.output)


if __name__ == "__main__":
    main()
