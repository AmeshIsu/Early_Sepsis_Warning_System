import pytest
from backend.app.ml.baselines import compute_sirs, compute_qsofa, compute_news, compute_sofa_components

def test_sirs_calculation():
    # Normal vitals -> SIRS 0
    assert compute_sirs(hr=75, resp=16, temp=36.8, wbc=7.0) == 0

    # Tachycardia (>90) and Tachypnea (>20) -> SIRS 2 (positive)
    assert compute_sirs(hr=95, resp=22, temp=36.8, wbc=7.0) == 2

    # High temp (>38.0) and high WBC (>12.0) -> SIRS 2
    assert compute_sirs(hr=75, resp=16, temp=38.5, wbc=14.0) == 2

    # All 4 criteria
    assert compute_sirs(hr=110, resp=24, temp=39.0, wbc=15.0) == 4


def test_qsofa_calculation():
    # Normal -> qSOFA 0
    assert compute_qsofa(resp=16, sbp=120) == 0

    # Resp >= 22 -> 1 point
    assert compute_qsofa(resp=23, sbp=120) == 1

    # Resp >= 22 and SBP <= 100 -> 2 points (positive)
    assert compute_qsofa(resp=23, sbp=95) == 2

    # Altered mental status adds 1 point
    assert compute_qsofa(resp=23, sbp=95, altered_mental=True) == 3


def test_news_score():
    # Normal vitals
    assert compute_news(hr=72, sbp=120, resp=16, temp=36.8, spo2=98) == 0

    # Severe vitals
    score = compute_news(hr=135, sbp=85, resp=26, temp=39.2, spo2=90)
    # hr 135 -> 3, sbp 85 -> 3, resp 26 -> 3, temp 39.2 -> 2, spo2 90 -> 3 => total = 14
    assert score >= 10


def test_sofa_components():
    sofa = compute_sofa_components(map_val=60.0, creatinine=2.5, bilirubin=3.0, spo2=88)
    assert sofa["cardiovascular"] == 1.0
    assert sofa["renal"] == 2.0
    assert sofa["liver"] == 2.0
    assert sofa["respiration"] == 2.0
    assert sofa["total"] == 7.0
