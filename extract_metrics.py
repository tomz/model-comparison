#!/usr/bin/env python3
"""Extract generation time and cost per model from the TUI screenshots.

Each attempt directory holds one or more gnome-screenshots of the finished
jaaicode TUI session. Every screenshot carries, near the bottom, the per-turn
stat line and a status bar:

    Turn 1 done 00:41:34 -> 00:48:41 in 7m07s - 1209 tokens - 95.3 t/s
        - ctx: 11% (976K) - 1.1Mp+48.6Ke - $3.82

    model-comparison | openrouter | anthropic/claude-opus-5.5 (medium)
        | 1,209 tok | 1.07Mp+48.6Ke | 95.3 t/s | $3.82 | ctx 11% (976K)

This script OCRs the bottom strip of every PNG (tesseract, light-on-dark text)
and parses those two lines into screenshot-metrics.json. It never mutates the
screenshots or the model directories. Tesseract is an external binary; the
script fails loudly if it is missing.

Usage:
    python3 extract_metrics.py                  # OCR all screenshots
    python3 extract_metrics.py --dirs glm-5.3   # limit to some directories
    python3 extract_metrics.py --dump-raw       # keep OCR text for inspection
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "screenshot-metrics.json"

# Directories that belong to this tooling, not to a model attempt. Without this
# the report's own verification screenshots would be counted as a model.
ATTEMPT_EXCLUDES = frozenset({"verification", "tests", "graphify-out", "__pycache__"})


def attempt_directories() -> list[Path]:
    """The model-attempt directories that may contain screenshots."""
    return sorted(
        p for p in ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in ATTEMPT_EXCLUDES
    )

# The turn line(s) and status bar live near the bottom of the window. Two
# passes are needed: psm 4 over a tall band catches earlier turns, psm 6 over
# a tight band reads the newest turn line and the status bar cleanly.
TURN_BANDS = ((0.60, 1.00, 4), (0.72, 0.93, 6))
STATUS_BAND = (0.905, 1.00, 6)
UPSCALE = 2
# Vertical offsets differ between the 2446 px and 2770 px window heights, so
# bands are expressed as fractions of image height.

TIME_RE = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})")
DURATION_RE = re.compile(r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?")
TURN_RE = re.compile(r"Turn\s+([0-9O]+)\s+done", re.IGNORECASE)
# OCR renders zero as 'O' often enough that the time pattern must accept it.
CLOCK_RE = re.compile(r"([0-9O]{1,2}):([0-9O]{2}):([0-9O]{2})")
STATED_RE = re.compile(r"\bin\b\s*([0-9OhmsilsOHMSIL\s]{1,14})")
STATUS_SPLIT_RE = re.compile(r"\s*[|]\s*")
COST_RE = re.compile(r"\$\s*(\d+(?:\.\d+)?)")
# Free (lightning-bolt) requests print the cost without a '$', so the status
# bar is parsed positionally as a fallback: the field before 'ctx N%'.
BARE_COST_RE = re.compile(r"^[^\d]*(\d+(?:\.\d+)?)$")
TOKENS_RE = re.compile(r"([\d,]+)\s*tok(?:ens)?\b", re.IGNORECASE)
TPS_RE = re.compile(r"([\d.]+)\s*t/s", re.IGNORECASE)
CTX_RE = re.compile(r"ctx[:.]?\s*(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
SIGMA_RE = re.compile(r"([\d.]+)\s*([KM])\s*p\s*\+\s*([\d.]+)\s*([KM])\s*e", re.IGNORECASE)
MODEL_RE = re.compile(r"^(?P<model>.+?)\s*\((?P<effort>[a-z]+)\)\s*$", re.IGNORECASE)


def normalise(text: str) -> str:
    """Fold the glyphs tesseract renders inconsistently into plain ASCII."""
    out = text
    for src, dst in (
        ("\u2192", "-"), ("\u2014", "-"), ("\u2013", "-"), ("\u2022", "-"),
        ("\u00b7", "-"), ("\u03a3", "S"), ("\u26a1", "$"), ("\u2713", "-"),
    ):
        out = out.replace(src, dst)
    return out


def ocr(image_path: Path, top_f: float, bot_f: float, psm: int) -> str:
    """OCR a horizontal band of the image, upscaled, in the given tesseract mode."""
    with Image.open(image_path) as im:
        grey = im.convert("L")
    width, height = grey.size
    box = (0, int(height * top_f), width, int(height * bot_f))
    crop = grey.crop(box)
    crop = crop.resize((crop.width * UPSCALE, crop.height * UPSCALE), Image.LANCZOS)
    tmp = Path("/tmp") / f"ocr-{abs(hash((image_path.name, top_f, psm)))}.png"
    crop.save(tmp)
    proc = subprocess.run(
        ["tesseract", str(tmp), "stdout", "--psm", str(psm)],
        capture_output=True, text=True,
    )
    tmp.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"tesseract failed on {image_path}: {proc.stderr.strip()}")
    return normalise(proc.stdout)


def _clock(group: tuple[str, str, str]) -> int:
    return int(group[0]) * 3600 + int(group[1]) * 60 + int(group[2])


def _stated_seconds(fragment: str) -> int | None:
    """Parse an OCR'd duration such as '7mO7s', '50.1s' or '1h02m03s' into seconds."""
    f = (fragment.replace("O", "0").replace("o", "0")
         .replace("I", "1").replace("l", "1"))
    h = re.search(r"(\d+(?:\.\d+)?)\s*h", f)
    m = re.search(r"(\d+(?:\.\d+)?)\s*m", f)
    s = re.search(r"(\d+(?:\.\d+)?)\s*s", f)
    if not any((h, m, s)):
        return None
    return int(float(h.group(1)) if h else 0) * 3600 + \
           int(float(m.group(1)) if m else 0) * 60 + \
           int(float(s.group(1)) if s else 0)


def parse_turn_line(line: str) -> dict | None:
    """Parse one 'Turn N done HH:MM:SS -> HH:MM:SS in XmYYs ... $cost' line.

    Elapsed time prefers the app-printed duration (``in XmYYs``), which the TUI
    computes from its own clocks; the two wall-clock stamps are kept as a
    cross-check (``elapsed_from_clock_s``), since OCR occasionally misreads a
    single digit in one of the stamps.
    """
    m = TURN_RE.search(line)
    if not m:
        return None
    rest = line[m.end():].replace("O", "0")
    times = [(int(a) * 3600 + int(b) * 60 + int(c), ":".join((a, b, c)))
             for a, b, c in CLOCK_RE.findall(rest)]
    rec: dict = {"turn": int(m.group(1))}
    if len(times) >= 2:
        (start_s, start), (end_s, end) = times[0], times[1]
        rec["start"], rec["end"] = start, end
        rec["elapsed_from_clock_s"] = (end_s - start_s) % 86400
    stated_frag = STATED_RE.search(line[m.end():])
    if stated_frag:
        if stated := _stated_seconds(stated_frag.group(1)):
            rec["elapsed_s"] = stated
    if "elapsed_s" not in rec:
        if "elapsed_from_clock_s" in rec:
            rec["elapsed_s"] = rec["elapsed_from_clock_s"]
        else:
            return None
    if cost := COST_RE.search(rest):
        rec["cost_usd"] = float(cost.group(1))
    if tok := TOKENS_RE.search(rest):
        rec["tokens"] = int(tok.group(1).replace(",", ""))
    if tps := TPS_RE.search(rest):
        rec["tokens_per_s"] = float(tps.group(1))
    if ctx := CTX_RE.search(rest):
        rec["ctx_pct"] = float(ctx.group(1))
    if sigma := SIGMA_RE.search(rest):
        rec["sigma_in_tokens"] = _scaled(sigma.group(1), sigma.group(2))
        rec["sigma_out_tokens"] = _scaled(sigma.group(3), sigma.group(4))
    return rec


def _scaled(value: str, unit: str) -> int:
    return int(float(value) * (1000 if unit.upper() == "K" else 1_000_000))


def parse_status_line(line: str) -> dict | None:
    """Parse the 'folder | provider | model (effort) | ... | $cost | ctx' bar."""
    parts = [p for p in STATUS_SPLIT_RE.split(line.strip()) if p.strip()]
    if len(parts) < 4:
        return None
    rec: dict = {
        "folder": re.sub(r"^[^A-Za-z0-9._-]+", "", parts[0].strip()).strip(),
        "provider": parts[1].strip(),
    }
    model_field = parts[2].strip()
    if mm := MODEL_RE.match(model_field):
        rec["model"] = mm.group("model").strip()
        rec["effort"] = mm.group("effort").strip().lower()
    else:
        rec["model"] = model_field
    tail = " | ".join(parts[3:])
    if tok := TOKENS_RE.search(tail):
        rec["tokens"] = int(tok.group(1).replace(",", ""))
    if tps := TPS_RE.search(tail):
        rec["tokens_per_s"] = float(tps.group(1))
    if cost := COST_RE.search(tail):
        rec["cost_usd"] = float(cost.group(1))
    elif (bare := BARE_COST_RE.match(parts[-2].strip())) and CTX_RE.search(parts[-1]):
        # free providers print the cost without a '$' (a lightning bolt instead)
        rec["cost_usd"] = float(bare.group(1))
    if ctx := CTX_RE.search(tail):
        rec["ctx_pct"] = float(ctx.group(1))
    if sigma := SIGMA_RE.search(tail):
        rec["sigma_in_tokens"] = _scaled(sigma.group(1), sigma.group(2))
        rec["sigma_out_tokens"] = _scaled(sigma.group(3), sigma.group(4))
    return rec


def parse_ocr(text: str) -> dict:
    """Pull every turn line and the status bar out of one screenshot's OCR."""
    turns: dict[tuple[int, str], dict] = {}
    status = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if (turn := parse_turn_line(line)) is not None:
            key = (turn["turn"], turn.get("start", ""))
            if key not in turns or len(turn) > len(turns[key]):
                turns[key] = turn
        elif CTX_RE.search(line) and STATUS_SPLIT_RE.search(line):
            candidate = parse_status_line(line)
            if candidate and candidate.get("model") and (
                status is None or len(candidate) > len(status)
            ):
                status = candidate
    ordered = [turns[k] for k in sorted(turns, key=lambda k: (k[1], k[0]))]
    return {"turns": ordered, "status": status}


def extract_image(path: Path) -> dict:
    chunks = [ocr(path, *band) for band in TURN_BANDS]
    chunks.append(ocr(path, *STATUS_BAND))
    parsed = parse_ocr("\n".join(chunks))
    turns = parsed["turns"]
    return {
        "screenshot": path.name,
        "turn_lines": turns,
        "status": parsed["status"],
        "total_elapsed_s": sum(t["elapsed_s"] for t in turns) or None,
        "total_cost_usd": _turn_cost(turns, parsed["status"]),
        "ocr_text": "\n".join(chunks),
    }


def _turn_cost(turns: list[dict], status: dict | None) -> float | None:
    per_turn = [t["cost_usd"] for t in turns if "cost_usd" in t]
    if per_turn:
        return round(sum(per_turn), 6)
    if status and "cost_usd" in status:
        return status["cost_usd"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dirs", nargs="*", default=None, help="attempt directories to scan")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--dump-raw", action="store_true", help="keep per-image OCR text")
    args = ap.parse_args()

    if shutil.which("tesseract") is None:
        print("error: tesseract not on PATH (apt-get install tesseract-ocr)", file=sys.stderr)
        return 1

    targets = [ROOT / d for d in args.dirs] if args.dirs else attempt_directories()
    records = []
    for directory in targets:
        if not directory.is_dir():
            continue
        for png in sorted(directory.glob("*.png")):
            try:
                rec = extract_image(png)
            except Exception as exc:  # keep going; report the failure in the JSON
                rec = {"screenshot": png.name, "error": f"{type(exc).__name__}: {exc}"}
            rec["directory"] = directory.name
            records.append(rec)
            turns = len(rec.get("turn_lines") or [])
            print(f"{directory.name:32} {png.name[-24:]:24} turns={turns} "
                  f"t={rec.get('total_elapsed_s')} cost={rec.get('total_cost_usd')}")

    if not args.dump_raw:
        for rec in records:
            rec.pop("ocr_text", None)
    out = Path(args.out)
    out.write_text(json.dumps({"screenshots": records}, indent=1), encoding="utf-8")
    print(f"\nwrote {out} ({len(records)} screenshots)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
