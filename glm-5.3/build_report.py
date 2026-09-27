#!/usr/bin/env python3
"""Build the self-contained engine comparison HTML report.

Embeds engine-comparison-summary-data.json into report_template.html at the
__DATA_JSON__ placeholder. No third-party packages.
"""
import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(HERE / "engine-comparison-summary-data.json"))
    ap.add_argument("--template", default=str(HERE / "report_template.html"))
    ap.add_argument("--out", default=str(HERE / "engine-comparison-report.html"))
    args = ap.parse_args()

    data_path = pathlib.Path(args.data)
    tpl_path = pathlib.Path(args.template)
    out_path = pathlib.Path(args.out)

    raw = data_path.read_bytes()
    json_sha = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw.decode("utf-8"))
    # the sha256 field in the data refers to the source document, not the JSON
    src_sha = data.get("sha256") or "n/a"

    tpl = tpl_path.read_text(encoding="utf-8")
    if "__DATA_JSON__" not in tpl:
        print("error: template missing __DATA_JSON__ placeholder", file=sys.stderr)
        return 1

    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    # safety: the payload lives inside a <script> tag
    payload = payload.replace("</", "<\\/")

    html = tpl.replace("__DATA_JSON__", payload)
    html = html.replace("__SRC_SHA256__", src_sha)
    html = html.replace("__JSON_SHA256__", json_sha)
    html = html.replace("__SOURCE__", data.get("source", "n/a"))

    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({out_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
