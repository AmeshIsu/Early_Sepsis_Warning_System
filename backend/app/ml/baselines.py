import numpy as np
from typing import Dict, Any, Optional

def compute_sirs(hr: Optional[float], resp: Optional[float], temp: Optional[float], wbc: Optional[float]) -> int:
    """
    SIRS criteria (Systemic Inflammatory Response Syndrome):
    - Temp > 38.0 C or < 36.0 C
    - Heart Rate > 90 bpm
    - Respiratory Rate > 20 breaths/min
    - WBC > 12.0 x 10^9/L or < 4.0 x 10^9/L
    Positive threshold: >= 2 criteria
    """
    criteria = 0
    if temp is not None and not np.isnan(temp):
        if temp > 38.0 or temp < 36.0:
            criteria += 1
    if hr is not None and not np.isnan(hr):
        if hr > 90.0:
            criteria += 1
    if resp is not None and not np.isnan(resp):
        if resp > 20.0:
            criteria += 1
    if wbc is not None and not np.isnan(wbc):
        if wbc > 12.0 or wbc < 4.0:
            criteria += 1
    return criteria


def compute_qsofa(resp: Optional[float], sbp: Optional[float], altered_mental: bool = False) -> int:
    """
    quick SOFA (qSOFA) criteria:
    - Respiratory Rate >= 22 breaths/min
    - Systolic BP <= 100 mmHg
    - Altered mental status (GCS < 15)
    Positive threshold: >= 2 criteria
    """
    criteria = 0
    if resp is not None and not np.isnan(resp):
        if resp >= 22.0:
            criteria += 1
    if sbp is not None and not np.isnan(sbp):
        if sbp <= 100.0:
            criteria += 1
    if altered_mental:
        criteria += 1
    return criteria


def compute_news(
    hr: Optional[float],
    sbp: Optional[float],
    resp: Optional[float],
    temp: Optional[float],
    spo2: Optional[float]
) -> int:
    """
    National Early Warning Score (NEWS) simplified standard table:
    Aggregated score: >= 5 is medium risk, >= 7 is high risk
    """
    score = 0

    # Respiration Rate
    if resp is not None and not np.isnan(resp):
        if resp <= 8:
            score += 3
        elif 9 <= resp <= 11:
            score += 1
        elif 12 <= resp <= 20:
            score += 0
        elif 21 <= resp <= 24:
            score += 2
        else: # >= 25
            score += 3

    # SpO2
    if spo2 is not None and not np.isnan(spo2):
        if spo2 <= 91:
            score += 3
        elif 92 <= spo2 <= 93:
            score += 2
        elif 94 <= spo2 <= 95:
            score += 1
        else:
            score += 0

    # Systolic BP
    if sbp is not None and not np.isnan(sbp):
        if sbp <= 90:
            score += 3
        elif 91 <= sbp <= 100:
            score += 2
        elif 101 <= sbp <= 110:
            score += 1
        elif 111 <= sbp <= 219:
            score += 0
        else: # >= 220
            score += 3

    # Heart Rate
    if hr is not None and not np.isnan(hr):
        if hr <= 40:
            score += 3
        elif 41 <= hr <= 50:
            score += 1
        elif 51 <= hr <= 90:
            score += 0
        elif 91 <= hr <= 110:
            score += 1
        elif 111 <= hr <= 130:
            score += 2
        else: # >= 131
            score += 3

    # Temperature
    if temp is not None and not np.isnan(temp):
        if temp <= 35.0:
            score += 3
        elif 35.1 <= temp <= 36.0:
            score += 1
        elif 36.1 <= temp <= 38.0:
            score += 0
        elif 38.1 <= temp <= 39.0:
            score += 1
        else: # >= 39.1
            score += 2

    return score


def compute_sofa_components(
    map_val: Optional[float],
    creatinine: Optional[float],
    bilirubin: Optional[float],
    spo2: Optional[float] = None
) -> Dict[str, float]:
    """
    Computes available component scores for Sequential Organ Failure Assessment (SOFA).
    Total acute change >= 2 points with suspected infection defines Sepsis-3.
    """
    cardio_score = 0.0
    if map_val is not None and not np.isnan(map_val):
        if map_val < 70.0:
            cardio_score = 1.0

    renal_score = 0.0
    if creatinine is not None and not np.isnan(creatinine):
        if creatinine >= 5.0:
            renal_score = 4.0
        elif creatinine >= 3.5:
            renal_score = 3.0
        elif creatinine >= 2.0:
            renal_score = 2.0
        elif creatinine >= 1.2:
            renal_score = 1.0

    liver_score = 0.0
    if bilirubin is not None and not np.isnan(bilirubin):
        if bilirubin >= 12.0:
            liver_score = 4.0
        elif bilirubin >= 6.0:
            liver_score = 3.0
        elif bilirubin >= 2.0:
            liver_score = 2.0
        elif bilirubin >= 1.2:
            liver_score = 1.0

    resp_score = 0.0
    if spo2 is not None and not np.isnan(spo2):
        if spo2 < 90:
            resp_score = 2.0
        elif spo2 < 94:
            resp_score = 1.0

    total_sofa = cardio_score + renal_score + liver_score + resp_score

    return {
        "cardiovascular": cardio_score,
        "renal": renal_score,
        "liver": liver_score,
        "respiration": resp_score,
        "total": total_sofa
    }
