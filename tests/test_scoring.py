"""Unit tests for the quality-rubric statistics.

The rank correlation is what the report quotes as evidence about spend and
quality, so it is tested against hand-checkable cases rather than trusted.
Offline: no browser, no OCR.

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_comparison as bc  # noqa: E402
import rate_quality as rq  # noqa: E402


class RankTests(unittest.TestCase):
    def test_ranks_are_one_based_positions(self) -> None:
        self.assertEqual(bc._rank([30, 10, 20]), [3.0, 1.0, 2.0])

    def test_ties_share_the_mean_rank(self) -> None:
        # 10, 10 occupy ranks 1 and 2 -> both get 1.5
        self.assertEqual(bc._rank([10, 10, 20]), [1.5, 1.5, 3.0])
        self.assertEqual(bc._rank([5, 5, 5]), [2.0, 2.0, 2.0])


class SpearmanTests(unittest.TestCase):
    def test_perfect_monotonic_increase(self) -> None:
        self.assertEqual(bc.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)

    def test_perfect_monotonic_decrease(self) -> None:
        self.assertEqual(bc.spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)

    def test_monotonic_but_non_linear_is_still_one(self) -> None:
        # Rank correlation must ignore the shape of the curve.
        self.assertEqual(bc.spearman([1, 2, 3, 4], [1, 100, 10_000, 5_000_000]), 1.0)

    def test_known_intermediate_value(self) -> None:
        # ranks are identical to the inputs, so sum(d^2)=36 and
        # rho = 1 - 6*36/(5*(25-1)) = -0.8
        self.assertAlmostEqual(bc.spearman([1, 2, 3, 4, 5], [5, 3, 4, 1, 2]), -0.8, places=3)

    def test_constant_series_has_no_correlation(self) -> None:
        self.assertIsNone(bc.spearman([1, 1, 1, 1], [1, 2, 3, 4]))

    def test_too_few_points(self) -> None:
        self.assertIsNone(bc.spearman([1, 2], [3, 4]))
        self.assertIsNone(bc.spearman([1, 2, 3], [1, 2]))


class MedianTests(unittest.TestCase):
    def test_odd_and_even_counts(self) -> None:
        self.assertEqual(bc._median([3, 1, 2]), 2)
        self.assertEqual(bc._median([1, 2, 3, 4]), 2.5)

    def test_empty(self) -> None:
        self.assertIsNone(bc._median([]))


class QualityStatsTests(unittest.TestCase):
    def _models(self):
        # Costs and scores rise together, so both correlations should be positive.
        return [
            {"directory": f"m{i}", "total_cost_usd": c, "total_elapsed_s": c * 10,
             "quality_score": q}
            for i, (c, q) in enumerate([(0.1, 50.0), (0.5, 60.0), (1.0, 70.0),
                                        (3.0, 80.0), (9.0, 90.0)])
        ]

    def test_reports_n_and_positive_correlations(self) -> None:
        stats = bc.quality_stats(self._models())
        self.assertEqual(stats["n"], 5)
        self.assertEqual(stats["spearman_cost_quality"], 1.0)
        self.assertEqual(stats["spearman_time_quality"], 1.0)

    def test_thirds_compare_cheap_and_dear(self) -> None:
        stats = bc.quality_stats(self._models())
        self.assertLess(stats["cheapest_third_median_quality"],
                        stats["dearest_third_median_quality"])
        self.assertLess(stats["cheapest_third_median_cost"],
                        stats["dearest_third_median_cost"])

    def test_missing_quality_is_excluded_not_zeroed(self) -> None:
        models = self._models()
        models.append({"directory": "unrated", "total_cost_usd": 2.0,
                       "total_elapsed_s": 20.0, "quality_score": None})
        stats = bc.quality_stats(models)
        self.assertEqual(stats["n"], 5)


class RoiAnalysisTests(unittest.TestCase):
    """ROI is defined against the best deal at equal-or-better quality."""

    def _models(self):
        # four runs. cheap-high is the best deal; free-mid is free but only
        # clears a lower bar, so it does not dominate cheap-high.
        return [
            {"directory": "cheap-low", "quality_score": 50.0, "total_cost_usd": 0.01,
             "total_elapsed_s": 100, "free_tier": False},
            {"directory": "cheap-high", "quality_score": 90.0, "total_cost_usd": 0.10,
             "total_elapsed_s": 200, "free_tier": False},
            {"directory": "dear-high", "quality_score": 90.0, "total_cost_usd": 10.00,
             "total_elapsed_s": 400, "free_tier": False},
            {"directory": "free-mid", "quality_score": 60.0, "total_cost_usd": 0.0,
             "total_elapsed_s": 300, "free_tier": True},
        ]

    def test_frontier_is_the_cheap_high_run(self) -> None:
        roi = bc.roi_analysis(self._models())
        self.assertEqual(roi["cost_frontier"], ["free-mid", "cheap-high"])

    def test_frontier_run_scores_full_marks(self) -> None:
        models = self._models()
        bc.roi_analysis(models)
        by = {m["directory"]: m for m in models}
        self.assertEqual(by["cheap-high"]["roi_score"], 100.0)
        self.assertTrue(by["cheap-high"]["pareto_cost"])

    def test_dominated_run_is_penalised(self) -> None:
        models = self._models()
        bc.roi_analysis(models)
        by = {m["directory"]: m for m in models}
        dear = by["dear-high"]
        # 100x the cheapest run at equal-or-better quality, and twice the fastest
        self.assertEqual(dear["cost_multiple_paid"], 100.0)
        self.assertLess(dear["roi_score"], 20.0)
        self.assertFalse(dear["on_frontier"])

    def test_paid_baseline_ignores_the_free_run(self) -> None:
        models = self._models()
        bc.roi_analysis(models)
        by = {m["directory"]: m for m in models}
        # free-mid has zero cost, so the paid baseline must come from cheap-high
        self.assertEqual(by["dear-high"]["cheapest_paid_match_cost"], 0.10)

    def test_score_is_capped_at_one_hundred(self) -> None:
        models = self._models()
        bc.roi_analysis(models)
        by = {m["directory"]: m for m in models}
        self.assertLessEqual(by["free-mid"]["roi_score"], 100.0)

    def test_low_quality_can_never_out_rank_high_quality(self) -> None:
        """The rule the analysis must not break: quality caps the score.

        A run that reached half the best quality must not score above 50 no matter
        how cheap or fast it was, so being cheap alone cannot buy a top rating.
        """
        models = [
            {"directory": "best-but-dear", "quality_score": 96.0, "total_cost_usd": 5.0,
             "total_elapsed_s": 900, "free_tier": False},
            {"directory": "cheap-and-weak", "quality_score": 48.0, "total_cost_usd": 0.01,
             "total_elapsed_s": 60, "free_tier": False},
        ]
        bc.roi_analysis(models)
        by = {m["directory"]: m for m in models}
        weak, best = by["cheap-and-weak"], by["best-but-dear"]
        # half the best quality caps the score at exactly 50, so even at full
        # efficiency on both axes the weak run cannot pass it
        self.assertLessEqual(weak["roi_score"], 50.0)
        self.assertGreater(best["roi_score"], weak["roi_score"])
        self.assertAlmostEqual(weak["quality_attainment"], 0.5, places=3)

    def test_score_never_exceeds_quality_attainment(self) -> None:
        models = self._models()
        bc.roi_analysis(models)
        for m in models:
            cap = 100 * m["quality_attainment"] + 0.1
            self.assertLessEqual(m["roi_score"], cap,
                                 msg=f"{m['directory']} scored {m['roi_score']} above its "
                                     f"quality cap {cap:.1f}")

    def test_empty_input_is_handled(self) -> None:
        roi = bc.roi_analysis([])
        self.assertEqual(roi["n"], 0)
        self.assertEqual(roi["models"], [])

    def test_models_without_quality_are_excluded(self) -> None:
        models = self._models() + [{"directory": "unrated", "quality_score": None,
                                    "total_cost_usd": 1.0, "total_elapsed_s": 10}]
        roi = bc.roi_analysis(models)
        self.assertEqual(roi["n"], 4)

    def test_cost_only_and_time_only_factors_multiply_to_the_combined(self) -> None:
        models = self._models()
        bc.roi_analysis(models)
        for m in models:
            combined = (m["roi_score_cost"] * m["roi_score_time"]) ** 0.5
            self.assertAlmostEqual(m["roi_score"], min(100.0, combined), delta=0.6,
                                   msg=f"{m['directory']}: {m['roi_score']} vs sqrt("
                                       f"{m['roi_score_cost']}*{m['roi_score_time']})")

    def test_cost_only_roi_matches_cost_multiple(self) -> None:
        models = self._models()
        bc.roi_analysis(models)
        by = {m["directory"]: m for m in models}
        # dear-high costs 100x the cheapest at >= quality -> 1% efficiency
        self.assertAlmostEqual(by["dear-high"]["roi_score_cost"], 1.0, places=1)
        # cheap-high is the cheapest at its own quality -> full marks
        self.assertEqual(by["cheap-high"]["roi_score_cost"], 100.0)

    def test_cost_only_ranking_is_reported_separately(self) -> None:
        roi = bc.roi_analysis(self._models())
        self.assertEqual(set(roi["models_by_cost_roi"]), set(roi["models"]))
        self.assertIn("best_roi_cost", roi["stats"])
        self.assertIn("median_roi_cost", roi["stats"])

    def test_sensitivity_is_reported_for_both_weightings(self) -> None:
        roi = bc.roi_analysis(self._models())
        keys = set(roi["stats"]["sensitivity"]) - {"all_weights_agree"}
        self.assertEqual(keys, {"cost_weight_0.25", "cost_weight_0.5", "cost_weight_0.75"})

    def test_worst_overpayer_name_matches_the_worst_figure(self) -> None:
        # The two cost multiples can peak on different runs, so the named run must
        # be the one holding the quoted figure, or the report misattributes it.
        models = self._models()
        roi = bc.roi_analysis(models)
        stats = roi["stats"]
        by = {m["directory"]: m for m in models}
        self.assertEqual(stats["worst_cost_multiple_paid_model"], "dear-high")
        self.assertAlmostEqual(stats["worst_cost_multiple_paid"],
                              by["dear-high"]["cost_multiple_paid"], places=3)
        # the uncapped multiple is a different ranking, and is named separately
        self.assertAlmostEqual(
            stats["worst_cost_multiple"],
            max(m["cost_multiple"] or 0 for m in models), places=3)

    def test_frontier_counts_distinguish_cost_time_and_union(self) -> None:
        # The chart marks the union, so the count quoted next to it must not be the
        # cost frontier alone.
        models = self._models()
        roi = bc.roi_analysis(models)
        stats = roi["stats"]
        union = set(roi["cost_frontier"]) | set(roi["time_frontier"])
        self.assertEqual(stats["frontier_size"], len(roi["cost_frontier"]))
        self.assertEqual(stats["time_frontier_size"], len(roi["time_frontier"]))
        self.assertEqual(stats["frontier_union_size"], len(union))
        self.assertGreaterEqual(stats["frontier_union_size"], stats["frontier_size"])

    def test_sensitivity_pick_matches_the_roi_winner_at_even_weights(self) -> None:
        # The re-weighted comparison must use the same value function as the
        # score, or it could recommend a run the ROI itself penalises.
        roi = bc.roi_analysis(self._models())
        self.assertEqual(roi["stats"]["sensitivity"]["cost_weight_0.5"],
                         roi["stats"]["best_roi"])


class RubricShapeTests(unittest.TestCase):
    """The rubric weights are the contract quoted in the report."""

    def test_fact_groups_are_non_empty_regexes(self) -> None:
        for name, patterns in rq.FACT_GROUPS.items():
            self.assertTrue(patterns, f"{name} has no patterns")
            for p in patterns:
                re.compile(p)  # raises if malformed

    def _max_dom(self) -> dict:
        return {
            "terms": {k: True for k in
                      ("canonical", "matched", "markers", "nulls", "limitations", "units",
                       "ratios", "wins")},
            "sections": {k: True for k in
                         ("summary", "single", "cluster", "perquery", "method", "provenance")},
            "engines": 5, "tpch": True, "tpcds": True, "rows": 100, "th": 50,
            "svg": 2, "canvas": 0, "cssbars": 5, "tables": 4,
            "buttons": 3, "selects": 1, "inputs": 0, "details": 2, "sortable": 4,
            "aria": 10, "anchors": 5, "h2": 5, "h3": 5, "chars": 9000,
            "hasDark": True, "hasPrint": True, "hasMono": True, "hasResponsive": True,
            "hasTable": True, "fact_hits": 2,
            "fact_detail": {"single-node figures": True, "cluster figures": True},
        }

    def test_weights_sum_to_one_hundred(self) -> None:
        src = {"embeds_dataset": True, "placeholder_left": False, "bytes": 10, "has_sha": True}
        dirs = {"builder": True, "template": True, "readme": True, "tests": True, "verify": True}
        result = rq.score(self._max_dom(), src, dirs, [], [])
        maxes = sum(d["max"] for d in result["dimensions"].values())
        self.assertEqual(maxes, 100, "rubric weights must total 100")

    def test_every_check_is_boolean_reportable(self) -> None:
        src = {"embeds_dataset": True, "placeholder_left": False, "bytes": 10, "has_sha": True}
        dirs = {"builder": True, "template": True, "readme": True, "tests": True, "verify": True}
        result = rq.score(self._max_dom(), src, dirs, [], [])
        self.assertEqual(result["score"], 100.0)
        self.assertEqual(set(result["breakdown"]),
                         {"data_fidelity", "coverage", "analysis", "caveats",
                          "presentation", "usability", "provenance"})

    def test_empty_report_scores_low(self) -> None:
        dom = {
            "terms": {k: False for k in
                      ("canonical", "matched", "markers", "nulls", "limitations", "units",
                       "ratios", "wins")},
            "sections": {k: False for k in
                         ("summary", "single", "cluster", "perquery", "method", "provenance")},
            "engines": 0, "tpch": False, "tpcds": False, "rows": 0, "th": 0,
            "svg": 0, "canvas": 0, "cssbars": 0, "tables": 0,
            "buttons": 0, "selects": 0, "inputs": 0, "details": 0, "sortable": 0,
            "aria": 0, "anchors": 0, "h2": 0, "h3": 0, "chars": 0,
            "hasDark": False, "hasPrint": False, "hasMono": False, "hasResponsive": False,
            "hasTable": False, "fact_hits": 0,
            "fact_detail": {"single-node figures": False, "cluster figures": False},
        }
        src = {"embeds_dataset": False, "placeholder_left": True, "bytes": 10, "has_sha": False}
        dirs = {"builder": False, "template": False, "readme": False,
                "tests": False, "verify": False}
        result = rq.score(dom, src, dirs, ["boom"], [])
        self.assertEqual(result["score"], 0.0)


if __name__ == "__main__":
    unittest.main()
