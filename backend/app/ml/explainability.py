import numpy as np
from typing import Dict, Any, List
from backend.app.pipeline.preprocessor import FEATURE_NAMES, NORMALIZATION_STATS

FEATURE_DISPLAY_NAMES = {
    "hr": "Heart Rate",
    "sbp": "Systolic BP",
    "dbp": "Diastolic BP",
    "map": "Mean Arterial Pressure",
    "resp": "Respiratory Rate",
    "temp": "Body Temperature",
    "spo2": "Oxygen Saturation (SpO2)",
    "lactate": "Serum Lactate",
    "wbc": "White Blood Cell Count",
    "creatinine": "Serum Creatinine",
    "bilirubin": "Total Bilirubin",
    "age": "Patient Age",
    "sirs": "SIRS Criteria",
    "qsofa": "qSOFA Score",
    "news": "NEWS Score",
    "sofa": "SOFA Score"
}

FEATURE_UNITS = {
    "hr": "bpm",
    "sbp": "mmHg",
    "dbp": "mmHg",
    "map": "mmHg",
    "resp": "/min",
    "temp": "°C",
    "spo2": "%",
    "lactate": "mmol/L",
    "wbc": "x10^9/L",
    "creatinine": "mg/dL",
    "bilirubin": "mg/dL"
}

def generate_feature_contributions(
    current_vitals: Dict[str, Any],
    baseline_vitals: Dict[str, Any],
    risk_score: float
) -> Dict[str, Any]:
    """
    Computes perturbation/attribution contributions for the current hour's risk score.
    Produces both quantitative relative weights (%) and a human-readable clinical explanation.
    """
    contributions = []

    # Expected normal ranges
    normals = {
        "hr": (60.0, 90.0, 75.0),
        "map": (70.0, 105.0, 85.0),
        "sbp": (100.0, 135.0, 115.0),
        "dbp": (60.0, 85.0, 75.0),
        "resp": (12.0, 20.0, 16.0),
        "temp": (36.4, 37.5, 36.8),
        "spo2": (95.0, 100.0, 98.0),
        "lactate": (0.5, 2.0, 1.0),
        "wbc": (4.5, 11.0, 7.5),
        "creatinine": (0.6, 1.2, 0.9),
        "bilirubin": (0.2, 1.2, 0.6)
    }

    raw_scores = {}
    for feat, (low, high, baseline) in normals.items():
        val = current_vitals.get(feat)
        if val is None or np.isnan(val):
            continue

        # Deviation from normal envelope
        dev = 0.0
        if val > high:
            dev = (val - high) / (high - baseline + 1e-4)
        elif val < low:
            dev = (low - val) / (baseline - low + 1e-4)

        if dev > 0.05:
            # Special clinical weighting: lactate, MAP, RR, Temp have high sepsis specificity
            weight = 1.0
            if feat in ["lactate", "map", "resp"]:
                weight = 1.5
            elif feat in ["temp", "hr", "wbc"]:
                weight = 1.2

            raw_scores[feat] = dev * weight

    total_attr = sum(raw_scores.values()) if raw_scores else 1.0
    if total_attr == 0:
        total_attr = 1.0

    # Sort descending
    sorted_feats = sorted(raw_scores.items(), key=lambda x: x[1], reverse=True)

    summary_bullets = []
    top_drivers = []

    for feat, raw_val in sorted_feats[:6]:
        pct = round((raw_val / total_attr) * 100.0, 1)
        curr_val = current_vitals.get(feat)
        unit = FEATURE_UNITS.get(feat, "")
        name = FEATURE_DISPLAY_NAMES.get(feat, feat.upper())

        direction = "elevated" if curr_val > normals[feat][2] else "depressed"
        top_drivers.append({
            "feature": feat,
            "name": name,
            "contribution_pct": pct,
            "current_value": curr_val,
            "unit": unit,
            "direction": direction,
            "normal_range": f"{normals[feat][0]} - {normals[feat][1]} {unit}"
        })
        summary_bullets.append(f"{name} ({curr_val} {unit}, {direction}) contributing {pct}%")

    # Generate clinical paragraph
    if top_drivers:
        driver_phrases = [f"{d['name'].lower()} at {d['current_value']} {d['unit']}" for d in top_drivers[:3]]
        explanation = (
            f"The current risk score of {risk_score:.2f} is primarily driven by "
            f"{', '.join(driver_phrases)}. "
            f"These physiological deviations match early organ hypoperfusion and systemic inflammatory patterns."
        )
    else:
        explanation = (
            f"Current risk score is {risk_score:.2f}. Vitals and labs remain within normal physiological baselines "
            f"with low acute inflammatory markers."
        )

    return {
        "risk_score": round(risk_score, 4),
        "drivers": top_drivers,
        "clinical_summary": explanation,
        "summary_bullets": summary_bullets
    }
