"""Transparent generic inverse-variance meta-analysis (DerSimonian-Laird RE)."""

from __future__ import annotations

import math
import statistics
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

from .errors import InsufficientEvidenceError, ValidationError


@dataclass(slots=True)
class StudyEffect:
    study_id: str
    effect: float
    standard_error: float
    outcome_id: str
    effect_measure: str = "generic"
    direction: str = "higher_is_more"
    unit: str | None = None
    source_ids: list[str] | None = None


def binary_log_odds_ratio(study_id: str, *, event_treatment: int, total_treatment: int,
                          event_control: int, total_control: int, outcome_id: str,
                          continuity_correction: float | None = None) -> StudyEffect:
    vals = (event_treatment, total_treatment, event_control, total_control)
    if any(not isinstance(x, int) for x in vals) or min(vals) < 0:
        raise ValidationError("Binary counts must be non-negative integers")
    if total_treatment <= 0 or total_control <= 0 or event_treatment > total_treatment or event_control > total_control:
        raise ValidationError("Binary outcome counts are inconsistent")
    cells = [event_treatment, total_treatment - event_treatment, event_control, total_control - event_control]
    if any(x == 0 for x in cells):
        if continuity_correction is None or continuity_correction <= 0:
            raise ValidationError("Zero cells require an explicit positive continuity correction; none was applied automatically")
        cells = [x + continuity_correction for x in cells]
    a, b, c, d = cells
    effect = math.log((a * d) / (b * c))
    se = math.sqrt(sum(1 / x for x in cells))
    return StudyEffect(study_id, effect, se, outcome_id, "log_odds_ratio", "higher_is_more")


def continuous_mean_difference(study_id: str, *, mean_treatment: float, sd_treatment: float,
                               n_treatment: int, mean_control: float, sd_control: float,
                               n_control: int, outcome_id: str, unit: str | None = None,
                               direction: str = "higher_is_more") -> StudyEffect:
    if min(n_treatment, n_control) < 2 or sd_treatment < 0 or sd_control < 0:
        raise ValidationError("Continuous outcome requires group sizes >=2 and non-negative SDs")
    values = (mean_treatment, sd_treatment, mean_control, sd_control)
    if not all(math.isfinite(x) for x in values):
        raise ValidationError("Continuous outcome values must be finite")
    se = math.sqrt((sd_treatment ** 2) / n_treatment + (sd_control ** 2) / n_control)
    if se <= 0:
        raise ValidationError("Continuous outcome standard error must be positive")
    return StudyEffect(study_id, mean_treatment - mean_control, se, outcome_id,
                       "mean_difference", direction, unit)


def analyze(effects: list[StudyEffect], *, model: str = "random", confidence: float = 0.95,
            estimator: str = "DL", outcome_id: str | None = None,
            prediction_interval: bool = True) -> dict[str, Any]:
    if model not in {"fixed", "random"}:
        raise ValidationError("model must be fixed or random")
    if not 0 < confidence < 1:
        raise ValidationError("confidence must be strictly between 0 and 1")
    if estimator != "DL":
        raise ValidationError("Only DerSimonian-Laird tau-squared estimation is implemented")
    if len(effects) < 2:
        raise InsufficientEvidenceError("At least two independent studies are required for pooling")
    ids = [item.study_id for item in effects]
    if len(ids) != len(set(ids)):
        raise ValidationError("Duplicate study_id values: reports from one study must not be double-counted")
    outcomes = {item.outcome_id for item in effects}
    if outcome_id is None and len(outcomes) != 1:
        raise ValidationError("Incompatible outcome_id values; do not pool without a justified harmonization")
    if outcome_id and outcomes != {outcome_id}:
        raise ValidationError("Every study must match the requested outcome_id")
    for item in effects:
        if not all(math.isfinite(x) for x in (item.effect, item.standard_error)) or item.standard_error <= 0:
            raise ValidationError(f"Invalid effect/standard error in study {item.study_id}")
    if len({item.effect_measure for item in effects}) != 1 or len({item.direction for item in effects}) != 1:
        raise ValidationError("Effect measures and effect directions must match before pooling")
    if len({item.unit for item in effects}) != 1:
        raise ValidationError("Effect units must match before pooling")
    signs = {math.copysign(1, item.effect) for item in effects if item.effect != 0}
    warnings = []
    if len(signs) > 1:
        warnings.append("Studies have effects in opposing directions; verify harmonization and clinical interpretation.")
    zcrit = statistics.NormalDist().inv_cdf(0.5 + confidence / 2)
    fixed_w = [1 / (e.standard_error ** 2) for e in effects]
    fixed_mu = sum(w * e.effect for w, e in zip(fixed_w, effects)) / sum(fixed_w)
    q = sum(w * (e.effect - fixed_mu) ** 2 for w, e in zip(fixed_w, effects))
    df = len(effects) - 1
    c = sum(fixed_w) - sum(w * w for w in fixed_w) / sum(fixed_w)
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
    weights = fixed_w if model == "fixed" else [1 / (e.standard_error ** 2 + tau2) for e in effects]
    pooled = sum(w * e.effect for w, e in zip(weights, effects)) / sum(weights)
    se = math.sqrt(1 / sum(weights))
    ci = [pooled - zcrit * se, pooled + zcrit * se]
    i2 = max(0.0, (q - df) / q) * 100 if q > 0 else 0.0
    pi = None
    if model == "random" and prediction_interval and len(effects) >= 3:
        # Approximate normal-theory interval; small-k uncertainty is not fully represented.
        pred_se = math.sqrt(tau2 + se * se)
        pi = [pooled - zcrit * pred_se, pooled + zcrit * pred_se]
        warnings.append("Prediction interval uses a normal approximation; small-k uncertainty is not fully represented.")
    if q > df:
        warnings.append("Between-study heterogeneity is present; investigate sources and whether pooling is clinically meaningful.")
    if model == "fixed":
        warnings.append("Fixed-effect result assumes one common underlying effect; this is a substantive model assumption.")
    return {"status": "calculated_requires_human_review", "model": model, "estimator": estimator,
            "n_studies": len(effects), "outcome_id": outcome_id or next(iter(outcomes)),
            "effect_measure": effects[0].effect_measure, "effect_direction": effects[0].direction,
            "pooled_effect": pooled, "standard_error": se, "confidence_level": confidence,
            "confidence_interval": ci, "Q": q, "Q_df": df, "tau_squared_DL": tau2,
            "I_squared_percent": i2, "prediction_interval_normal_approx": pi,
            "study_weights": {item.study_id: weight / sum(weights) for item, weight in zip(effects, weights)},
            "study_effects": [{"study_id": e.study_id, "effect": e.effect, "standard_error": e.standard_error,
                               "ci": [e.effect-zcrit*e.standard_error, e.effect+zcrit*e.standard_error],
                               "weight": w/sum(weights), "source_ids": e.source_ids or []} for e, w in zip(effects, weights)],
            "warnings": warnings,
            "clinical_importance_assessed": False,
            "provenance": {"formula": "generic inverse variance; DerSimonian-Laird moment estimator",
                           "pooled_data_inputs": len(effects), "requires_reproducible_input_file": True}}


def forest_plot_svg(result: dict[str, Any], *, width: int = 800) -> str:
    """Generate a dependency-free SVG forest plot from a calculated result."""
    rows = result["study_effects"]
    height = max(180, 70 + 42 * len(rows))
    all_ci = [v for row in rows for v in row["ci"]] + result["confidence_interval"]
    lo, hi = min(all_ci), max(all_ci)
    pad = max((hi - lo) * 0.12, 0.1)
    lo, hi = lo - pad, hi + pad
    x0, x1 = 300, width - 40
    scale = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    root = ET.Element("svg", xmlns="http://www.w3.org/2000/svg", width=str(width), height=str(height), viewBox=f"0 0 {width} {height}")
    ET.SubElement(root, "text", x="20", y="25", **{"font-size": "16"}).text = f"Forest plot ({result['model']} effect)"
    null = 0.0 if result["effect_measure"] in {"mean_difference", "log_odds_ratio", "standardized_mean_difference", "generic"} else 1.0
    xnull = scale(null)
    ET.SubElement(root, "line", x1=str(xnull), x2=str(xnull), y1="38", y2=str(height-25), stroke="#888", **{"stroke-dasharray": "4 4"})
    for i, row in enumerate(rows):
        y = 60 + i * 42
        ET.SubElement(root, "text", x="20", y=str(y+5), **{"font-size": "12"}).text = row["study_id"]
        ET.SubElement(root, "line", x1=str(scale(row["ci"][0])), x2=str(scale(row["ci"][1])), y1=str(y), y2=str(y), stroke="#245d8f", **{"stroke-width": "2"})
        ET.SubElement(root, "rect", x=str(scale(row["effect"])-4), y=str(y-4), width="8", height="8", fill="#245d8f")
    py = height - 28
    ET.SubElement(root, "polygon", points=f"{scale(result['pooled_effect'])},{py-7} {scale(result['confidence_interval'][1])},{py} {scale(result['pooled_effect'])},{py+7} {scale(result['confidence_interval'][0])},{py}", fill="#aa4e28")
    ET.SubElement(root, "text", x="20", y=str(py+4), **{"font-size": "12"}).text = "Pooled"
    return ET.tostring(root, encoding="unicode")
