#!/usr/bin/env python3
"""Aggregate the per-screenshot OCR into a per-model time/cost comparison.

Reads screenshot-metrics.json (produced by extract_metrics.py) and groups each
directory's screenshots into sessions:

* the TUI status bar's ``$`` figure is *session-cumulative*, so a session's cost
  is the maximum value seen across its screenshots;
* each ``Turn N done`` line is per-turn wall time, so a session's duration is
  the sum of its distinct turns;
* a screenshot whose turn numbers do not advance past the running maximum
  starts a new session (the model was restarted and re-prompted).

The result is compared against ~/.jaaicode/usage.jsonl, which records the
authoritative per-request cost for every session whose cwd was inside this
repository, and both values are emitted so disagreements stay visible.

Usage:
    python3 build_comparison.py           # -> comparison-data.json
    python3 build_comparison.py --report  # also -> comparison-report.html
"""
from __future__ import annotations

import argparse
import datetime
import math
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_metrics import ATTEMPT_EXCLUDES, attempt_directories  # noqa: E402

ROOT = Path(__file__).resolve().parent
METRICS = ROOT / "screenshot-metrics.json"
QUALITY = ROOT / "quality-ratings.json"
USAGE = Path.home() / ".jaaicode" / "usage.jsonl"
DATA_OUT = ROOT / "comparison-data.json"


def _screenshot_stamp(name: str) -> str:
    """Extract the sortable 'YYYY-MM-DD HH-MM-SS' stamp from a gnome-screenshot name."""
    m = re.search(r"(\d{4}-\d{2}-\d{2}) (\d{2}-\d{2}-\d{2})", name)
    return f"{m.group(1)} {m.group(2)}" if m else name


def load_quality() -> dict:
    """Quality ratings keyed by directory, or an empty dict if not yet generated."""
    if not QUALITY.exists():
        return {}
    payload = json.loads(QUALITY.read_text(encoding="utf-8"))
    return {r["directory"]: r for r in payload.get("ratings", [])}


def _rank(values: list[float]) -> list[float]:
    """Average ranks, ties sharing the mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float | None:
    """Spearman rank correlation. Preferred over Pearson: the data is skewed,
    bounded and non-linear, and we only care whether the ordering moves together."""
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    rx, ry = _rank(xs), _rank(ys)
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return round(num / (dx * dy), 3) if dx and dy else None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    mid = len(s) // 2
    return round(s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2, 1)


def quality_stats(models: list[dict]) -> dict:
    """Relate spend and time to report quality. Descriptive, not causal: n is
    small, runs are sequential, and cost is largely a function of model price."""
    paired = [m for m in models
              if m.get("quality_score") is not None and m.get("total_cost_usd") is not None]
    by_cost = sorted(paired, key=lambda m: m["total_cost_usd"])
    third = max(1, len(by_cost) // 3)
    cheap, dear = by_cost[:third], by_cost[-third:]
    timed = [m for m in models
             if m.get("quality_score") is not None and m.get("total_elapsed_s") is not None]
    return {
        "n": len(paired),
        "spearman_cost_quality": spearman([m["total_cost_usd"] for m in paired],
                                          [m["quality_score"] for m in paired]),
        "spearman_time_quality": spearman([m["total_elapsed_s"] for m in timed],
                                          [m["quality_score"] for m in timed]) if timed else None,
        "cheapest_third_median_quality": _median([m["quality_score"] for m in cheap]),
        "dearest_third_median_quality": _median([m["quality_score"] for m in dear]),
        "cheapest_third_median_cost": _median([m["total_cost_usd"] for m in cheap]),
        "dearest_third_median_cost": _median([m["total_cost_usd"] for m in dear]),
    }


def roi_analysis(models: list[dict]) -> dict:
    """Return on investment, defined so that no arbitrary weights are needed.

    The value is the report's quality score; the investment is money and time.
    Quality points are not currency, so instead of inventing a dollar ROI we ask
    the only question a buyer can act on:

        at the quality this run achieved, what was the best deal available?

    For each run we find the cheapest run (and the fastest run) that reached at
    least its quality, and divide. That gives an *efficiency* per axis, capped at
    1.0 (1.0 means this run was itself the best deal). Efficiency alone is not
    ROI, though: it is normalised within a quality tier, so a cheap run that
    scraped a low bar would score as well as a cheap run that produced a strong
    report. Quality therefore enters again as a multiplier:

        roi_score = 100 * quality_attainment * sqrt(cost_efficiency * time_efficiency)

    where ``quality_attainment`` is the run's score over the best score achieved.
    A report at half the best quality can therefore never exceed 50, however
    cheap it was. 100 means the best report for the best available price; a low
    score means either poor quality or an expensive way to buy it.

    The score is capped at 100, quality is measured by this project's rubric
    rather than by human judgement, and cost reflects each provider's price list
    for one run, not a negotiated rate.
    """
    rows = [m for m in models
            if m.get("quality_score") is not None
            and m.get("total_cost_usd") is not None
            and m.get("total_elapsed_s")]
    if not rows:
        return {"n": 0, "models": [], "stats": {}}

    best_q = max(m["quality_score"] for m in rows)
    paid = [m for m in rows if not m.get("free_tier")]

    def _ratio(value: float, base: float) -> float | None:
        """None when the baseline is zero (a free-tier run can do that)."""
        return round(value / base, 3) if base else None

    for m in rows:
        same_or_better = [o for o in rows if o["quality_score"] >= m["quality_score"]]
        paid_or_better = [o for o in paid if o["quality_score"] >= m["quality_score"]] \
            or same_or_better
        m["cheapest_match_cost"] = min(o["total_cost_usd"] for o in same_or_better)
        m["cheapest_paid_match_cost"] = min(o["total_cost_usd"] for o in paid_or_better)
        m["fastest_match_time"] = min(o["total_elapsed_s"] for o in same_or_better)
        # A free-tier run sets a near-zero floor, so the like-for-like comparison
        # among purchasable options is the paid baseline; both are kept, because
        # "you could have used the free tier" is also true and worth seeing.
        m["cost_multiple"] = _ratio(m["total_cost_usd"], m["cheapest_match_cost"])
        m["cost_multiple_paid"] = _ratio(m["total_cost_usd"], m["cheapest_paid_match_cost"])
        m["time_multiple"] = _ratio(m["total_elapsed_s"], m["fastest_match_time"])
        cost_multiple = m["cost_multiple_paid"] or 1.0
        time_multiple = m["time_multiple"] or 1.0
        # Efficiency is capped at 1: a free-tier run can beat every paid option, but
        # that is recorded by its cost multiple, not as efficiency above the best deal.
        m["cost_efficiency"] = min(1.0, round(1 / cost_multiple, 4))
        m["time_efficiency"] = min(1.0, round(1 / time_multiple, 4))
        m["usd_per_point"] = round(m["total_cost_usd"] / m["quality_score"], 6)
        m["sec_per_point"] = round(m["total_elapsed_s"] / m["quality_score"], 3)
        m["quality_attainment"] = round(m["quality_score"] / best_q, 4)
        # ROI = quality attained x efficiency. Quality is a *multiplier*, not merely
        # a floor to clear: with a floor-only rule a cheap run that scraped a low
        # bar out-ranked a cheap run that produced a better report, which is not a
        # return on investment so much as a low price. The combined score stays the
        # geometric mean of the two factors, so each is readable on its own.
        m["roi_score_cost"] = min(100.0, round(
            100 * m["quality_attainment"] * m["cost_efficiency"], 1))
        m["roi_score_time"] = min(100.0, round(
            100 * m["quality_attainment"] * m["time_efficiency"], 1))
        m["roi_score"] = min(100.0, round(
            (m["roi_score_cost"] * m["roi_score_time"]) ** 0.5, 1))

    # Pareto frontiers, weight-free: cheapest/fastest first, keep a run only if
    # it beats the best quality seen so far.
    def frontier(key: str) -> list[str]:
        best, out = -1.0, []
        for m in sorted(rows, key=lambda r: r[key]):
            if m["quality_score"] > best:
                out.append(m["directory"])
                best = m["quality_score"]
        return out

    cost_frontier, time_frontier = frontier("total_cost_usd"), frontier("total_elapsed_s")
    for m in rows:
        m["pareto_cost"] = m["directory"] in cost_frontier
        m["pareto_time"] = m["directory"] in time_frontier
        m["on_frontier"] = m["pareto_cost"] or m["pareto_time"]

    ranked = sorted(rows, key=lambda m: -m["roi_score"])
    ranked_cost = sorted(rows, key=lambda m: -m["roi_score_cost"])
    median_q = _median([m["quality_score"] for m in rows])
    high = [m for m in ranked if m["quality_score"] >= median_q]
    high_cost = [m for m in ranked_cost if m["quality_score"] >= median_q]
    overpaid = [m for m in rows if (m["cost_multiple_paid"] or 0) >= 10]
    overpaid_all = [m for m in rows if (m["cost_multiple"] or 0) >= 10]

    # Sensitivity: does the pick survive re-weighting money against time? It must
    # use the same value function as the score itself, or it would recommend a run
    # that the ROI penalises. At w=0.5 this is exactly the ROI ordering; the other
    # weights tilt it one way or the other. Efficiencies are the capped ones used
    # by the score, so a free-tier run gets no extra credit here either.
    def tilt(r: dict, w_cost: float) -> float:
        eff_c = max(1e-6, r["cost_efficiency"] or 1.0)
        eff_t = max(1e-6, r["time_efficiency"] or 1.0)
        attainment = max(1e-6, r["quality_attainment"] or 1.0)
        return (math.log(attainment)
                + w_cost * math.log(eff_c)
                + (1 - w_cost) * math.log(eff_t))

    sensitivity = {}
    for w in (0.25, 0.5, 0.75):
        best = max(rows, key=lambda r: tilt(r, w))
        sensitivity[f"cost_weight_{w}"] = best["directory"]
    sensitivity["all_weights_agree"] = len(set(sensitivity.values())) == 1

    return {
        "n": len(rows),
        "models": [m["directory"] for m in ranked],
        "models_by_cost_roi": [m["directory"] for m in ranked_cost],
        "cost_frontier": cost_frontier,
        "time_frontier": time_frontier,
        "stats": {
            "best_roi": ranked[0]["directory"],
            "best_roi_score": ranked[0]["roi_score"],
            "best_roi_at_quality": high[0]["directory"] if high else None,
            "best_roi_at_quality_score": high[0]["roi_score"] if high else None,
            "best_roi_cost": ranked_cost[0]["directory"],
            "best_roi_cost_score": ranked_cost[0]["roi_score_cost"],
            "best_roi_cost_at_quality": high_cost[0]["directory"] if high_cost else None,
            "best_roi_cost_at_quality_score": high_cost[0]["roi_score_cost"] if high_cost else None,
            "median_roi_cost": _median([m["roi_score_cost"] for m in rows]),
            "median_roi_time": _median([m["roi_score_time"] for m in rows]),
            "median_quality": median_q,
            "median_roi_score": _median([m["roi_score"] for m in rows]),
            "overpaid_count": len(overpaid),
            "overpaid_count_vs_any_baseline": len(overpaid_all),
            "worst_cost_multiple": max((m["cost_multiple"] or 0) for m in rows),
            "worst_cost_multiple_paid": max((m["cost_multiple_paid"] or 0) for m in rows),
            # Paired with the figure above, not with worst_cost_multiple: the two
            # rankings can peak on different runs.
            "worst_cost_multiple_paid_model": max(
                rows, key=lambda m: (m["cost_multiple_paid"] or 0))["directory"],
            "worst_cost_multiple_model": max(
                rows, key=lambda m: (m["cost_multiple"] or 0))["directory"],
            # frontier_size counts the cost frontier; the scatter and the table mark
            # the union of both frontiers, so report all three to keep the wording
            # from understating what the chart shows.
            "frontier_size": len(cost_frontier),
            "time_frontier_size": len(time_frontier),
            "frontier_union_size": len(set(cost_frontier) | set(time_frontier)),
            "median_cost": _median([m["total_cost_usd"] for m in rows]),
            "frontier_max_cost": round(max(
                m["total_cost_usd"] for m in rows if m["directory"] in cost_frontier), 4),
            "frontier_all_below_median_cost": all(
                m["total_cost_usd"] <= (_median([o["total_cost_usd"] for o in rows]) or 0)
                for m in rows if m["directory"] in cost_frontier),
            "sensitivity": sensitivity,
        },
    }


def load_usage() -> list[dict]:
    """Return the usage.jsonl sessions whose cwd sits under this repository.

    A session may request more than one model (the operator can switch mid-run),
    so every model seen in a session is collected rather than just the first.
    """
    sessions: dict[str, dict] = {}
    if not USAGE.exists():
        return []
    for raw in USAGE.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        if not str(rec.get("cwd") or "").startswith(str(ROOT)):
            continue
        sid = rec.get("session_id", "")
        s = sessions.setdefault(sid, {
            "session_id": sid, "cwd": rec.get("cwd"), "provider": rec.get("provider"),
            "models": [], "cost_usd": 0.0, "prompt_tokens": 0, "eval_tokens": 0,
            "cache_read_tokens": 0, "requests": 0, "t0": None, "t1": None,
        })
        model = rec.get("model")
        if model and model not in s["models"]:
            s["models"].append(model)
        s["cost_usd"] += rec.get("cost_usd") or 0.0
        s["prompt_tokens"] += rec.get("prompt_tokens") or 0
        s["eval_tokens"] += rec.get("eval_tokens") or 0
        s["cache_read_tokens"] += rec.get("cache_read_tokens") or 0
        s["requests"] += 1
        ts = rec.get("ts_unix") or 0
        s["t0"] = ts if s["t0"] is None else min(s["t0"], ts)
        s["t1"] = ts if s["t1"] is None else max(s["t1"], ts)
    for s in sessions.values():
        s["cost_usd"] = round(s["cost_usd"], 4)
        start = datetime.datetime.fromtimestamp(s["t0"]) if s["t0"] else None
        end = datetime.datetime.fromtimestamp(s["t1"]) if s["t1"] else None
        s["date"] = start.date().isoformat() if start else None
        s["start"] = start.strftime("%H:%M:%S") if start else None
        s["end"] = end.strftime("%H:%M:%S") if end else None
        s["wall_s"] = round((s["t1"] or 0) - (s["t0"] or 0), 1) if s["t0"] else None
    return list(sessions.values())


def _seconds(hms: str | None) -> int | None:
    if not hms:
        return None
    try:
        h, m, s = (int(p) for p in hms.split(":"))
    except ValueError:
        return None
    return h * 3600 + m * 60 + s


def match_sessions_by_time(sessions: list[dict], usage: list[dict],
                           date: str | None,
                           start_tol: int = 60, end_tol: int = 150) -> list[dict]:
    """Pair screenshot sessions with the usage.jsonl session that contains them.

    The turn window of a screenshot session sits inside the usage session that
    produced it, so the rule is *containment*, not mere overlap: sessions run
    back to back, and a loose overlap test lets the previous session leak in.
    The two edges need different slack:

    * the artifact's first turn can predate the session's first logged request
      by a few seconds, so ``start`` may be up to ``start_tol`` earlier;
    * a turn's wall clock ends when the response finishes streaming, which can
      postdate the last logged request by a minute or two, so ``end`` may be up
      to ``end_tol`` later.

    Where several usage sessions qualify, the one starting closest to the
    artifact's first turn wins. One usage session may serve two directories when
    the operator switched models mid-session.
    """
    matched: dict[str, dict] = {}
    for session in sessions:
        start, end = _seconds(session.get("first_start")), _seconds(session.get("last_end"))
        if start is None or end is None:
            continue
        for u in usage:
            if date and u["date"] != date:
                continue
            u_start, u_end = _seconds(u["start"]), _seconds(u["end"])
            if u_start is None or u_end is None:
                continue
            if u_start - start > start_tol or end - u_end > end_tol:
                continue
            entry = {
                "session_id": u["session_id"], "cost_usd": u["cost_usd"],
                "wall_s": u["wall_s"], "requests": u["requests"],
                "models": u["models"], "start": u["start"], "end": u["end"],
                "offset_s": abs(u_start - start),
                "shared": len(u["models"]) > 1,
            }
            current = matched.get(session["screenshot_key"])
            if current is None or entry["offset_s"] < current["offset_s"]:
                matched[session["screenshot_key"]] = entry
    return sorted(matched.values(), key=lambda m: m["offset_s"])


def _screenshot_date(shots: list[dict]) -> str | None:
    """Local date of the last screenshot in the group."""
    stamps = [_screenshot_stamp(s["screenshot"]) for s in shots]
    return max(stamps)[:10] if stamps else None


def build_sessions(shots: list[dict]) -> list[dict]:
    """Split a directory's screenshots into restarted-prompt sessions.

    Cost is *cumulative* in the TUI: the ``$`` on a turn line equals the status
    bar at that moment (turn 3 of a session shows the same figure in both). So a
    session's cost is the largest cumulative observation, never a sum. A value
    an order of magnitude above the smallest observation is an OCR decimal-point
    loss ('$0.860' read as '860') and is discarded.
    """
    sessions: list[dict] = []
    current: dict | None = None
    for shot in sorted(shots, key=lambda s: _screenshot_stamp(s["screenshot"])):
        turns = shot.get("turn_lines") or []
        numbers = [t["turn"] for t in turns]
        status = shot.get("status") or {}
        if current is None or (numbers and min(numbers) <= current["max_turn"]):
            current = {"max_turn": 0, "turns": {}, "screenshots": [],
                       "cost_obs": [], "start": None, "end": None,
                       "screenshot_key": f"{shot['screenshot']}#{len(sessions)}"}
            sessions.append(current)
        for turn in turns:
            current["turns"][(turn["turn"], turn.get("start", ""))] = turn
            if "cost_usd" in turn:
                current["cost_obs"].append((turn["cost_usd"], f"{shot['screenshot']} turn {turn['turn']}"))
        current["max_turn"] = max(current["max_turn"], max(numbers, default=current["max_turn"]))
        current["screenshots"].append(shot["screenshot"])
        if "cost_usd" in status:
            current["cost_obs"].append((status["cost_usd"], f"{shot['screenshot']} status bar"))
        current["start"] = current["start"] or status.get("start")
    for s in sessions:
        ordered = [s["turns"][k] for k in sorted(s["turns"], key=lambda k: k[0])]
        s["turn_list"] = ordered
        s["turns"] = len(ordered)
        s["min_turn"] = ordered[0]["turn"] if ordered else None
        s["elapsed_s"] = sum(t["elapsed_s"] for t in ordered) or None
        s["first_start"] = ordered[0].get("start") if ordered else None
        s["last_end"] = ordered[-1].get("end") if ordered else None
        s["cost_usd"], s["cost_rejected"] = _session_cost(s.pop("cost_obs"))
    return sessions


def _session_cost(observations: list[tuple[float, str]]) -> tuple[float, list[str]]:
    """Pick the cumulative session cost, rejecting implausible OCR outliers."""
    if not observations:
        return 0.0, []
    values = [v for v, _ in observations]
    floor = min(v for v in values if v > 0) if any(v > 0 for v in values) else 0.0
    kept, rejected = [], []
    for value, origin in observations:
        if floor and value > floor * 10:
            rejected.append(f"{origin} reported ${value:g} (10x the smallest observed "
                            f"cost ${floor:g}); treated as an OCR decimal loss")
        else:
            kept.append(value)
    return (max(kept) if kept else 0.0), rejected


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--metrics", default=str(METRICS))
    ap.add_argument("--out", default=str(DATA_OUT))
    ap.add_argument("--report", action="store_true", help="also write the HTML report")
    args = ap.parse_args()

    metrics_path = Path(args.metrics)
    if not metrics_path.exists():
        print(f"error: {metrics_path} missing; run extract_metrics.py first", file=sys.stderr)
        return 1
    shots = json.loads(metrics_path.read_text(encoding="utf-8"))["screenshots"]
    pool = load_usage()
    quality_by_dir = load_quality()

    by_dir: dict[str, list[dict]] = {}
    for shot in shots:
        directory = shot.get("directory", "?")
        if directory in ATTEMPT_EXCLUDES:
            continue
        by_dir.setdefault(directory, []).append(shot)

    models, excluded, claimed = [], [], set()
    # Directories with no screenshot at all, or whose only screenshots failed
    # OCR, cannot contribute time/cost evidence.
    all_dirs = [p.name for p in attempt_directories()]
    for directory in all_dirs:
        if directory in by_dir:
            continue
        excluded.append({"directory": directory, "reason": "no screenshot in the directory"})

    for directory, group in sorted(by_dir.items()):
        usable = [g for g in group if not g.get("error")]
        if not usable:
            excluded.append({"directory": directory, "reason": "OCR failed for every screenshot"})
            continue
        sessions = build_sessions(usable)
        status = next((g["status"] for g in usable if g.get("status")), {}) or {}
        elapsed = [s["elapsed_s"] for s in sessions if s["elapsed_s"]]
        cost = sum(s["cost_usd"] for s in sessions) or None
        gaps = [
            f"screenshot '{g['screenshot']}' has no visible turn line"
            for g in usable if not g.get("turn_lines")
        ]
        first_turn = min((s["min_turn"] for s in sessions if s["min_turn"]), default=1)
        max_turn = max((t["turn"] for s in sessions for t in s["turn_list"]), default=1)
        if first_turn > 1:
            gaps.append(
                f"the earliest visible turn is turn {first_turn}; earlier turns "
                f"scrolled off screen, so the elapsed time is a lower bound")
        rejected = [r for s in sessions for r in s["cost_rejected"]]
        record = {
            "directory": directory,
            "model": status.get("model"),
            "provider": status.get("provider"),
            "effort": status.get("effort"),
            "free_tier": bool(cost is not None and cost < 0.01),
            "sessions": len(sessions),
            "turns_observed": sum(s["turns"] for s in sessions),
            "first_turn_observed": first_turn,
            "max_turn_observed": max_turn,
            "prompts_at_least": max_turn,
            "total_elapsed_s": sum(elapsed) if elapsed else None,
            "total_cost_usd": round(cost, 4) if cost else None,
            "tokens_per_s": status.get("tokens_per_s"),
            "sigma_in_tokens": status.get("sigma_in_tokens"),
            "sigma_out_tokens": status.get("sigma_out_tokens"),
            "ctx_pct": status.get("ctx_pct"),
            "screenshots": [g["screenshot"] for g in usable],
            "session_detail": [
                {"turns": s["turns"], "min_turn": s["min_turn"], "elapsed_s": s["elapsed_s"],
                 "cost_usd": s["cost_usd"], "start": s["first_start"], "end": s["last_end"]}
                for s in sessions
            ],
            "time_is_lower_bound": bool(gaps),
            "turn_is_lower_bound": first_turn > 1 or bool(
                [g for g in usable if not g.get("turn_lines")]),
            "cost_per_min_usd": (
                round(cost / ((sum(elapsed) / 60)) , 4)
                if cost and elapsed else None),
            "notes": gaps + rejected,
        }
        usage = match_sessions_by_time(sessions, pool, _screenshot_date(usable))
        record["usage_jsonl"] = usage or None
        claimed.update(m["session_id"] for m in usage)
        quality = quality_by_dir.get(directory)
        record["quality_score"] = quality["score"] if quality else None
        record["quality_breakdown"] = quality["breakdown"] if quality else None
        record["quality_dimensions"] = quality["dimensions"] if quality else None
        record["deliverable"] = quality.get("deliverable") if quality else None
        usage_cost = sum(m["cost_usd"] for m in usage) if usage else None
        record["usage_cost_usd"] = round(usage_cost, 4) if usage_cost is not None else None
        record["cost_agrees"] = bool(
            usage_cost is not None and cost is not None
            and abs(usage_cost - cost) <= 0.01)
        if any(m["shared"] for m in usage):
            record["notes"].append(
                "the usage session for this run also served other models, so "
                "the usage total spans more than this artifact")
        models.append(record)

    payload = {
        "generated_by": "build_comparison.py",
        "sources": {
            "screenshots": len(shots),
            "directories": len(models),
            "ocr": _tesseract_version(),
            "metrics_sha256": hashlib.sha256(metrics_path.read_bytes()).hexdigest(),
            "usage_jsonl": str(USAGE),
            "quality_ratings": str(QUALITY) if QUALITY.exists() else None,
        },
        "models": models,
        "excluded": excluded,
        "roi": roi_analysis(models),
        "quality": [
            {"directory": d, "deliverable": q.get("deliverable"),
             "score": q.get("score"), "breakdown": q.get("breakdown"),
             "roi_score_cost": next((m["roi_score_cost"] for m in models
                                     if m["directory"] == d), None),
             "roi_score_time": next((m["roi_score_time"] for m in models
                                     if m["directory"] == d), None)}
            for d, q in sorted(quality_by_dir.items())
        ],
        "quality_stats": quality_stats(models),
        "unmatched_usage_sessions": [
            {"session_id": s["session_id"], "models": s["models"], "cost_usd": s["cost_usd"],
             "cwd": s["cwd"], "date": s["date"], "start": s["start"], "end": s["end"]}
            for s in pool if s["session_id"] not in claimed
        ],
    }
    out = Path(args.out)
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    total_cost = sum(m["total_cost_usd"] or 0 for m in models)
    total_time = sum(m["total_elapsed_s"] or 0 for m in models)
    print(f"{len(models)} models | total ${total_cost:.2f} | total {total_time/60:.0f} min")
    print(f"wrote {out}")
    orphan = payload["unmatched_usage_sessions"]
    if orphan:
        print(f"note: {len(orphan)} usage session(s) match no directory "
              f"(${sum(o['cost_usd'] for o in orphan):.2f})")

    if args.report:
        sys.path.insert(0, str(ROOT))
        from report_template import render  # local module, imported lazily
        Path(ROOT / "comparison-report.html").write_text(
            render(payload), encoding="utf-8")
        print("wrote comparison-report.html")
    return 0


def _tesseract_version() -> str:
    try:
        out = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        return out.stdout.splitlines()[0].strip() or "unknown"
    except OSError:
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
