"""Unit tests for the screenshot-OCR parsers.

The OCR-facing parsers are the fragile part of this pipeline: tesseract confuses
0 with O, drops decimal points, and renders the arrow and lightning glyphs as
random punctuation. The fixtures below are real OCR strings observed in this
repository, so the tests pin the behaviour that actually matters.

Headless and offline: no tesseract or browser is required.

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_comparison as bc  # noqa: E402
import extract_metrics as em  # noqa: E402


class TurnLineTests(unittest.TestCase):
    """The 'Turn N done ... in XmYYs ... $cost' line."""

    def test_parses_a_full_recent_turn(self) -> None:
        line = ("Turn 1 done 00:41:34 -> 00:48:41 in 7m07s - 1209 tokens - 95.3 t/s "
                "- ctx: 11% (976K) - 1.1Mp+48.6Ke - $3.82")
        rec = em.parse_turn_line(line)
        assert rec is not None
        self.assertEqual(rec["turn"], 1)
        self.assertEqual(rec["start"], "00:41:34")
        self.assertEqual(rec["end"], "00:48:41")
        self.assertEqual(rec["elapsed_s"], 427)
        self.assertEqual(rec["elapsed_from_clock_s"], 427)
        self.assertEqual(rec["cost_usd"], 3.82)
        self.assertEqual(rec["tokens"], 1209)
        self.assertEqual(rec["ctx_pct"], 11.0)
        self.assertEqual(rec["sigma_in_tokens"], 1_100_000)
        self.assertEqual(rec["sigma_out_tokens"], 48_600)

    def test_ocr_zero_for_letter_o_in_duration(self) -> None:
        # '7m07s' came out of tesseract as '7mO7s'.
        line = "Turn 1 done 00:41:34 - 00:48:41 in 7mO7s - 1209 tokens - $3.82"
        rec = em.parse_turn_line(line)
        assert rec is not None
        self.assertEqual(rec["elapsed_s"], 427)

    def test_ocr_substitutes_letters_for_digits_in_duration(self) -> None:
        # '8m21s' arrived as '8m21is' in one band and '8m21s' in another.
        self.assertEqual(em._stated_seconds("8m21s"), 501)
        self.assertEqual(em._stated_seconds("1m01s"), 61)
        self.assertEqual(em._stated_seconds("50.1s"), 50)

    def test_clock_difference_is_the_fallback(self) -> None:
        # No usable 'in XmYYs' token: the two stamps still give the elapsed time.
        line = "Turn 2 done 14:11:19 -> 14:12:09 + 521 tokens + $0.05"
        rec = em.parse_turn_line(line)
        assert rec is not None
        self.assertEqual(rec["elapsed_s"], 50)

    def test_wrapped_turn_line_still_parses_core_fields(self) -> None:
        # Wide screens wrap the line, splitting the duration onto its own line.
        line = "Turn 3 done 15:26:40 > 15:29:48 in 3m08s + 366 tokens + $1.40"
        rec = em.parse_turn_line(line)
        assert rec is not None
        self.assertEqual(rec["turn"], 3)
        self.assertEqual(rec["elapsed_s"], 188)

    def test_free_tier_turn_line_has_no_dollar_cost(self) -> None:
        line = "Turn 2 done 14:11:19 > 14:12:09 in 50.1s + 521 tokens + 63.0 t/s"
        rec = em.parse_turn_line(line)
        assert rec is not None
        self.assertEqual(rec["elapsed_s"], 50)
        self.assertNotIn("cost_usd", rec)

    def test_non_turn_lines_are_ignored(self) -> None:
        self.assertIsNone(em.parse_turn_line("wrote engine-comparison-report.html"))
        self.assertIsNone(em.parse_turn_line("$14.54 | ctx 21% (976K)"))


class StatusBarTests(unittest.TestCase):
    """The 'folder | provider | model (effort) | ... | $cost | ctx' bar."""

    def test_parses_model_effort_and_cost(self) -> None:
        bar = ("model-comparison | openrouter | anthropic/claude-opus-5.5 (medium) | "
               "1,209 tok | 1.07Mp+48.6Ke | 95.3 t/s | $3.82 | ctx 11% (976K)")
        rec = em.parse_status_line(bar)
        assert rec is not None
        self.assertEqual(rec["model"], "anthropic/claude-opus-5.5")
        self.assertEqual(rec["effort"], "medium")
        self.assertEqual(rec["provider"], "openrouter")
        self.assertEqual(rec["cost_usd"], 3.82)
        self.assertEqual(rec["tokens"], 1209)
        self.assertEqual(rec["ctx_pct"], 11.0)

    def test_free_tier_cost_has_no_dollar_sign(self) -> None:
        # The bolt glyph replaces '$'; the cost sits just before the ctx field.
        bar = ("somemodel | openrouter | openrouter/free (medium) | 521 tok | "
               "765.1Kp+15.6Ke | 63.0 t/s | 0.0009 | ctx 10% (500K)")
        rec = em.parse_status_line(bar)
        assert rec is not None
        self.assertEqual(rec["model"], "openrouter/free")
        self.assertAlmostEqual(rec["cost_usd"], 0.0009)

    def test_leading_ocr_glyph_is_stripped_from_the_folder(self) -> None:
        bar = ("\u201c somemodel | openrouter | z-ai/glm-5.3 (medium) | 538 tok | "
               "5.3Mp+61.8Ke | 103.3 t/s | $1.76 | ctx 49% (195K)")
        rec = em.parse_status_line(bar)
        assert rec is not None
        self.assertEqual(rec["folder"], "somemodel")

    def test_non_status_lines_are_ignored(self) -> None:
        self.assertIsNone(em.parse_status_line("just some prose"))
        self.assertIsNone(em.parse_status_line("a | b | c"))


class SessionCostTests(unittest.TestCase):
    """Cost is cumulative per session: take the max, reject OCR decimal loss."""

    def test_takes_the_largest_cumulative_observation(self) -> None:
        value, rejected = bc._session_cost([(0.209, "a"), (0.412, "b"), (0.779, "c")])
        self.assertEqual(value, 0.779)
        self.assertEqual(rejected, [])

    def test_discards_a_decimal_point_lost_to_ocr(self) -> None:
        # kimi-k3's status bar rendered '$0.860' as '860'.
        value, rejected = bc._session_cost([(0.86, "turn 1"), (860.0, "status bar")])
        self.assertEqual(value, 0.86)
        self.assertEqual(len(rejected), 1)
        self.assertIn("decimal loss", rejected[0])

    def test_missing_cost_is_zero_and_recorded(self) -> None:
        value, rejected = bc._session_cost([])
        self.assertEqual(value, 0.0)
        self.assertEqual(rejected, [])


class UsageMatchingTests(unittest.TestCase):
    """Screenshot sessions are matched to usage.jsonl by wall-clock containment."""

    def setUp(self) -> None:
        self.usage = [
            {"session_id": "sess-prev", "date": "2026-09-26", "start": "09:04:50",
             "end": "09:16:04", "cost_usd": 0.6011, "wall_s": 681.0, "requests": 35,
             "models": ["deepseek/deepseek-v4-pro"]},
            {"session_id": "sess-kimi", "date": "2026-09-26", "start": "09:19:03",
             "end": "09:25:02", "cost_usd": 0.8598, "wall_s": 359.0, "requests": 22,
             "models": ["moonshotai/kimi-k3"]},
        ]

    def _session(self, key: str, start: str, end: str) -> dict:
        return {"screenshot_key": key, "first_start": start, "last_end": end}

    def test_matches_the_containing_session_not_the_adjacent_one(self) -> None:
        sessions = [self._session("a", "09:19:01", "09:25:02")]
        matches = bc.match_sessions_by_time(sessions, self.usage, "2026-09-26")
        self.assertEqual([m["session_id"] for m in matches], ["sess-kimi"])

    def test_ignores_sessions_from_another_day(self) -> None:
        sessions = [self._session("a", "09:19:01", "09:25:02")]
        self.assertEqual(bc.match_sessions_by_time(sessions, self.usage, "2026-09-25"), [])

    def test_flags_a_session_shared_by_two_models(self) -> None:
        usage = [dict(self.usage[1], models=["anthropic/claude-sonnet-5", "openai/gpt-6-luna-pro"])]
        sessions = [self._session("a", "09:19:01", "09:25:02")]
        matches = bc.match_sessions_by_time(sessions, usage, "2026-09-26")
        self.assertTrue(matches[0]["shared"])

    def test_no_match_without_a_full_turn_window(self) -> None:
        # A screenshot with no visible turn line cannot be placed in time.
        self.assertEqual(
            bc.match_sessions_by_time([{"screenshot_key": "a"}], self.usage, "2026-09-26"), [])

    def test_seconds_helper(self) -> None:
        self.assertEqual(bc._seconds("01:02:03"), 3723)
        self.assertIsNone(bc._seconds(None))
        self.assertIsNone(bc._seconds("nonsense"))


class SessionSplitTests(unittest.TestCase):
    """Screenshot sessions are split only when the turn counter restarts."""

    def test_advancing_turns_stay_in_one_session(self) -> None:
        # Real case, grok-build-0.1: turn 1 scrolled off, so turns 2 and 3 are
        # consecutive prompts of a single session whose cost accumulates.
        shots = [
            {"screenshot": "X 19-41-22.png", "status": {"cost_usd": 0.196},
             "turn_lines": [{"turn": 2, "start": "19:36:38", "end": "19:40:12", "elapsed_s": 214}]},
            {"screenshot": "X 19-47-38.png", "status": {"cost_usd": 0.434},
             "turn_lines": [{"turn": 3, "start": "19:41:53", "end": "19:46:16", "elapsed_s": 262}]},
        ]
        sessions = bc.build_sessions(shots)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["turns"], 2)
        self.assertEqual(sessions[0]["elapsed_s"], 476)
        self.assertEqual(sessions[0]["cost_usd"], 0.434)
        self.assertEqual(sessions[0]["min_turn"], 2)

    def test_restarting_turn_numbers_start_a_new_session(self) -> None:
        # A restarted app shows turn 1 again; its cost must not be maxed with
        # the previous session's.
        shots = [
            {"screenshot": "Y 10-00-00.png", "status": {"cost_usd": 2.0},
             "turn_lines": [{"turn": 5, "start": "09:50:00", "end": "09:59:00", "elapsed_s": 540}]},
            {"screenshot": "Y 10-05-00.png", "status": {"cost_usd": 0.3},
             "turn_lines": [{"turn": 1, "start": "10:01:00", "end": "10:04:00", "elapsed_s": 180}]},
        ]
        sessions = bc.build_sessions(shots)
        self.assertEqual(len(sessions), 2)
        self.assertEqual([s["cost_usd"] for s in sessions], [2.0, 0.3])
        self.assertEqual([s["elapsed_s"] for s in sessions], [540, 180])

    def test_deduplicates_a_turn_seen_in_two_ocr_bands(self) -> None:
        turn = {"turn": 1, "start": "00:41:34", "end": "00:48:41", "elapsed_s": 427}
        shots = [
            {"screenshot": "Z 00-50-42.png", "status": {"cost_usd": 3.82},
             "turn_lines": [dict(turn), dict(turn, elapsed_from_clock_s=427)]},
        ]
        sessions = bc.build_sessions(shots)
        self.assertEqual(sessions[0]["turns"], 1)
        self.assertEqual(sessions[0]["elapsed_s"], 427)


if __name__ == "__main__":
    unittest.main()
