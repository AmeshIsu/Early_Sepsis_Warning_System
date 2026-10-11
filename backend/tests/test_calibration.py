import numpy as np
import pytest
from backend.app.ml.calibration import ModelCalibrator, compute_ece, optimize_threshold, evaluate_alarm_fatigue_simulation

def test_ece_computation():
    y_true = np.array([0, 0, 0, 1, 1, 1, 1, 0, 1, 0])
    y_prob = np.array([0.1, 0.2, 0.15, 0.8, 0.9, 0.85, 0.75, 0.3, 0.95, 0.2])

    ece, diag = compute_ece(y_true, y_prob, n_bins=5)
    assert 0.0 <= ece <= 1.0
    assert len(diag) == 5


def test_platt_calibration():
    # Simulated overconfident raw predictions
    y_true = np.array([0]*50 + [1]*50)
    raw_scores = np.concatenate([np.random.uniform(0.1, 0.6, 50), np.random.uniform(0.4, 0.9, 50)])

    calibrator = ModelCalibrator(method="platt")
    calibrator.fit(raw_scores, y_true)
    calibrated = calibrator.predict(raw_scores)

    assert calibrated.shape == raw_scores.shape
    assert (calibrated >= 0.0).all() and (calibrated <= 1.0).all()


def test_alarm_fatigue_cooldown():
    # Patient with high risk for 4 consecutive hours (hours 0, 1, 2, 3)
    pt_preds = [{
        "patient_id": "P-TEST",
        "risk_scores": [0.8, 0.82, 0.81, 0.83],
        "is_septic": True,
        "sepsis_onset_hour": 5
    }]

    # With cooldown = 4 hours, only 1 alert should fire across hours 0..3 (since hour 1, 2, 3 are within 4h cooldown)
    res = evaluate_alarm_fatigue_simulation(pt_preds, threshold=0.5, cooldown_hours=4.0, escalation_delta=0.20)
    assert res["total_alerts"] == 1
    assert res["sensitivity"] == 1.0
