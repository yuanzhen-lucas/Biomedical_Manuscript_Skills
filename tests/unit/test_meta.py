import math
from unittest import TestCase

from biomedical_manuscript.errors import InsufficientEvidenceError, ValidationError
from biomedical_manuscript.meta import (StudyEffect, analyze, binary_log_odds_ratio,
                                       continuous_mean_difference, forest_plot_svg)


class MetaAnalysisTests(TestCase):
    def test_random_effects_golden_values(self):
        effects = [StudyEffect("s1", 0.2, 0.1, "mortality", "mean_difference", unit="points"),
                   StudyEffect("s2", 0.5, 0.2, "mortality", "mean_difference", unit="points")]
        result = analyze(effects, model="random", prediction_interval=False)
        self.assertAlmostEqual(result["Q"], 1.8, places=10)
        self.assertAlmostEqual(result["tau_squared_DL"], 0.02, places=10)
        self.assertAlmostEqual(result["pooled_effect"], 0.3, places=10)
        self.assertAlmostEqual(result["standard_error"], math.sqrt(0.02), places=10)
        self.assertAlmostEqual(result["I_squared_percent"], 44.4444444444, places=7)

    def test_fixed_effect_golden_values(self):
        result = analyze([StudyEffect("s1", 0.2, 0.1, "o"), StudyEffect("s2", 0.5, 0.2, "o")],
                         model="fixed", prediction_interval=False)
        self.assertAlmostEqual(result["pooled_effect"], 0.26, places=10)
        self.assertAlmostEqual(result["standard_error"], math.sqrt(1 / 125), places=10)

    def test_binary_zero_cell_requires_explicit_correction(self):
        with self.assertRaises(ValidationError):
            binary_log_odds_ratio("s1", event_treatment=0, total_treatment=10,
                                  event_control=1, total_control=10, outcome_id="o")
        result = binary_log_odds_ratio("s1", event_treatment=10, total_treatment=100,
                                       event_control=20, total_control=100, outcome_id="o")
        self.assertAlmostEqual(result.effect, math.log(800 / 1800), places=10)
        self.assertEqual(result.effect_measure, "log_odds_ratio")

    def test_continuous_mean_difference(self):
        result = continuous_mean_difference("s1", mean_treatment=8, sd_treatment=2, n_treatment=25,
                                            mean_control=10, sd_control=3, n_control=25,
                                            outcome_id="score", unit="points")
        self.assertEqual(result.effect, -2)
        self.assertAlmostEqual(result.standard_error, math.sqrt(0.52), places=10)

    def test_reject_duplicate_studies_and_mismatched_outcomes(self):
        with self.assertRaises(ValidationError):
            analyze([StudyEffect("s1", .1, .2, "a"), StudyEffect("s1", .2, .2, "a")])
        with self.assertRaises(ValidationError):
            analyze([StudyEffect("s1", .1, .2, "a"), StudyEffect("s2", .2, .2, "b")])

    def test_reject_mismatched_units(self):
        with self.assertRaises(ValidationError):
            analyze([StudyEffect("s1", .1, .2, "a", "mean_difference", unit="mg"),
                     StudyEffect("s2", .2, .2, "a", "mean_difference", unit="ug")])

    def test_reject_one_study_and_bad_confidence(self):
        with self.assertRaises(InsufficientEvidenceError):
            analyze([StudyEffect("s1", .1, .2, "a")])
        with self.assertRaises(ValidationError):
            analyze([StudyEffect("s1", .1, .2, "a"), StudyEffect("s2", .2, .2, "a")], confidence=1)

    def test_svg_generated_from_result(self):
        result = analyze([StudyEffect("s1", .1, .2, "a"), StudyEffect("s2", .2, .2, "a")])
        self.assertIn("<svg", forest_plot_svg(result))
