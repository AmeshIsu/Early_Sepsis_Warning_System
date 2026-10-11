import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

FEATURE_NAMES = [
    "hr", "sbp", "dbp", "map", "resp", "temp", "spo2",
    "lactate", "wbc", "creatinine", "bilirubin"
]

POPULATION_DEFAULTS = {
    "hr": 75.0,
    "sbp": 120.0,
    "dbp": 75.0,
    "map": 90.0,
    "resp": 16.0,
    "temp": 36.8,
    "spo2": 98.0,
    "lactate": 1.1,
    "wbc": 7.5,
    "creatinine": 0.9,
    "bilirubin": 0.6
}

NORMALIZATION_STATS = {
    "hr": (75.0, 18.0),
    "sbp": (120.0, 22.0),
    "dbp": (75.0, 14.0),
    "map": (90.0, 16.0),
    "resp": (16.0, 5.0),
    "temp": (36.8, 0.8),
    "spo2": (98.0, 2.5),
    "lactate": (1.2, 1.5),
    "wbc": (8.0, 4.5),
    "creatinine": (1.0, 0.8),
    "bilirubin": (0.7, 0.9),
    "age": (62.0, 14.0)
}

class ICUPreprocessor:
    def __init__(self, imputation_method: str = "masked", decay_lambda: float = 0.1):
        self.imputation_method = imputation_method # "masked", "locf_decay", "patient_median", "pop_median"
        self.decay_lambda = decay_lambda
        self.pop_medians = POPULATION_DEFAULTS.copy()

    def fit_population_medians(self, patients_data: List[Dict[str, Any]]):
        """Calculates true population medians from training split."""
        values = {feat: [] for feat in FEATURE_NAMES}
        for pt in patients_data:
            for v in pt["vitals"]:
                for feat in FEATURE_NAMES:
                    val = v.get(feat)
                    if val is not None and not np.isnan(val):
                        values[feat].append(val)

        for feat in FEATURE_NAMES:
            if len(values[feat]) > 0:
                self.pop_medians[feat] = float(np.median(values[feat]))

    def process_patient_trajectory(
        self,
        pt: Dict[str, Any],
        is_training: bool = False
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Takes raw patient trajectory and produces:
        - X: feature matrix of shape (seq_len, num_features)
        - y: target vector of shape (seq_len,)
        - hours: array of hourly timestamps (seq_len,)

        LEAKAGE-SAFE:
        Features at index t are computed using strictly data observed at or before t.
        If patient developed sepsis, observations after onset hour are excluded from training
        to prevent post-onset artifact contamination.
        """
        vitals = pt["vitals"]
        los = len(vitals)
        is_septic = pt.get("is_septic", False)
        onset_hour = pt.get("sepsis_onset_hour")

        # In training mode, truncate after onset hour to prevent post-onset leakage
        max_h = los
        if is_training and is_septic and onset_hour is not None:
            max_h = min(los, int(onset_hour) + 1)

        # Precompute patient medians for "patient_median" method
        pt_medians = {}
        if self.imputation_method == "patient_median":
            for feat in FEATURE_NAMES:
                observed = [v[feat] for v in vitals[:max_h] if v.get(feat) is not None and not np.isnan(v[feat])]
                pt_medians[feat] = float(np.median(observed)) if len(observed) > 0 else self.pop_medians[feat]

        num_raw = len(FEATURE_NAMES)
        # Features will include:
        # 1. Imputed value (normalized) [num_raw]
        # 2. Measurement mask (1 if observed at hour t, else 0) [num_raw]
        # 3. Delta-t (hours elapsed since last observation) [num_raw]
        # 4. Demographic features: Age, Gender [2]
        # 5. Baseline clinical scores: SIRS, qSOFA, NEWS, SOFA [4]
        # Total features: 11*3 + 2 + 4 = 39 features

        feature_matrix = []
        target_vector = []
        hour_vector = []

        last_observed_val = {feat: self.pop_medians[feat] for feat in FEATURE_NAMES}
        last_observed_hour = {feat: -1 for feat in FEATURE_NAMES}

        age_norm = (pt.get("age", 60.0) - NORMALIZATION_STATS["age"][0]) / NORMALIZATION_STATS["age"][1]
        gender_feat = float(pt.get("gender", 1))

        for idx in range(max_h):
            rec = vitals[idx]
            h = rec["hour"]

            imputed_vals = []
            masks = []
            delta_ts = []

            for feat in FEATURE_NAMES:
                val = rec.get(feat)
                is_obs = (val is not None and not np.isnan(val))

                if is_obs:
                    last_observed_val[feat] = val
                    last_observed_hour[feat] = h
                    dt = 0.0
                    mask = 1.0
                else:
                    mask = 0.0
                    dt = float(h - last_observed_hour[feat]) if last_observed_hour[feat] >= 0 else 24.0

                # Imputation strategy
                if is_obs:
                    curr_val = val
                else:
                    if self.imputation_method == "masked":
                        # Standard LOCF; model uses mask & delta-t to learn decay
                        curr_val = last_observed_val[feat]
                    elif self.imputation_method == "locf_decay":
                        # Exponential decay towards population median
                        mu = self.pop_medians[feat]
                        curr_val = mu + (last_observed_val[feat] - mu) * np.exp(-self.decay_lambda * dt)
                    elif self.imputation_method == "patient_median":
                        curr_val = pt_medians[feat]
                    elif self.imputation_method == "pop_median":
                        curr_val = self.pop_medians[feat]
                    else:
                        curr_val = last_observed_val[feat]

                # Normalize continuous value
                mean_f, std_f = NORMALIZATION_STATS[feat]
                norm_val = (curr_val - mean_f) / std_f

                imputed_vals.append(norm_val)
                masks.append(mask)
                delta_ts.append(min(dt / 24.0, 2.0)) # bounded normalized dt

            # Clinical baseline scores normalized
            sirs_norm = float(rec.get("sirs_score", 0)) / 4.0
            qsofa_norm = float(rec.get("qsofa_score", 0)) / 3.0
            news_norm = float(rec.get("news_score", 0)) / 20.0
            sofa_norm = float(rec.get("sofa_score", 0)) / 12.0

            # Target 6-hour forward window:
            # 1 if onset in (h, h + 6]
            y_val = 0
            if is_septic and onset_hour is not None:
                if h < onset_hour <= (h + 6):
                    y_val = 1

            row = imputed_vals + masks + delta_ts + [age_norm, gender_feat, sirs_norm, qsofa_norm, news_norm, sofa_norm]
            feature_matrix.append(row)
            target_vector.append(y_val)
            hour_vector.append(h)

        return np.array(feature_matrix, dtype=np.float32), np.array(target_vector, dtype=np.float32), np.array(hour_vector, dtype=np.int32)
