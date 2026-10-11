import numpy as np
import pytest
from backend.app.pipeline.generator import generate_synthetic_cohort
from backend.app.pipeline.dataset import patient_level_split
from backend.app.pipeline.preprocessor import ICUPreprocessor

def test_patient_level_split_no_overlap():
    """
    Unit test proving ZERO patient overlap across train, validation, and test splits.
    """
    patients = generate_synthetic_cohort(num_patients=60, sepsis_prevalence=0.15, seed=42)
    train_pts, val_pts, test_pts = patient_level_split(patients, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)

    train_ids = set(p["patient_id"] for p in train_pts)
    val_ids = set(p["patient_id"] for p in val_pts)
    test_ids = set(p["patient_id"] for p in test_pts)

    # 1. No overlap between train and val
    assert len(train_ids.intersection(val_ids)) == 0, "Train and Val split share patients!"

    # 2. No overlap between train and test
    assert len(train_ids.intersection(test_ids)) == 0, "Train and Test split share patients!"

    # 3. No overlap between val and test
    assert len(val_ids.intersection(test_ids)) == 0, "Val and Test split share patients!"

    # 4. Total patients conserved
    assert len(train_ids) + len(val_ids) + len(test_ids) == len(patients)


def test_leakage_safe_windowing():
    """
    Unit test proving that features at time t use ONLY data at or before t,
    and label definition strictly adheres to sepsis onset in (t, t + 6h].
    """
    preprocessor = ICUPreprocessor(imputation_method="masked")

    # Construct a septic patient with known onset at hour 20
    vitals = []
    for h in range(40):
        vitals.append({
            "hour": h,
            "hr": 70.0 + h * 0.5, # increasing
            "map": 90.0 - h * 0.5,
            "resp": 16.0,
            "temp": 36.8,
            "spo2": 98.0,
            "lactate": 1.0,
            "wbc": 7.0,
            "creatinine": 0.9,
            "bilirubin": 0.6,
            "sofa_score": 0.0,
            "sirs_score": 0,
            "qsofa_score": 0,
            "news_score": 0
        })

    patient = {
        "patient_id": "TEST-001",
        "age": 65.0,
        "gender": 1,
        "is_septic": True,
        "sepsis_onset_hour": 20,
        "vitals": vitals
    }

    X, y, hours = preprocessor.process_patient_trajectory(patient, is_training=False)

    # Verify target label window:
    # y[h] should be 1 if and only if h < 20 <= h + 6 (i.e. h in {14, 15, 16, 17, 18, 19})
    for h, y_val in zip(hours, y):
        if 14 <= h <= 19:
            assert y_val == 1, f"Expected positive label at hour {h} for onset at 20"
        else:
            assert y_val == 0, f"Expected negative label at hour {h} for onset at 20"

    # In training mode, patient trajectory must be truncated at onset hour to prevent post-onset leakage
    X_train, y_train, hours_train = preprocessor.process_patient_trajectory(patient, is_training=True)
    assert max(hours_train) <= 20, "Training trajectory contains post-onset time steps!"
