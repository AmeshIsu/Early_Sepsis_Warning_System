import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss

def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> Tuple[float, List[Dict[str, float]]]:
    """
    Computes Expected Calibration Error (ECE) and bin points for reliability diagram.
    """
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(y_prob, bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    n_total = len(y_true)
    if n_total == 0:
        return 0.0, []

    ece = 0.0
    diagram_points = []

    for b in range(n_bins):
        mask = (bin_indices == b)
        count = int(np.sum(mask))
        bin_center = (bins[b] + bins[b + 1]) / 2.0

        if count > 0:
            avg_prob = float(np.mean(y_prob[mask]))
            empirical_pos = float(np.mean(y_true[mask]))
            ece += (count / n_total) * abs(empirical_pos - avg_prob)
            diagram_points.append({
                "bin": b,
                "bin_lower": round(float(bins[b]), 3),
                "bin_upper": round(float(bins[b + 1]), 3),
                "confidence": round(avg_prob, 4),
                "accuracy": round(empirical_pos, 4),
                "count": count
            })
        else:
            diagram_points.append({
                "bin": b,
                "bin_lower": round(float(bins[b]), 3),
                "bin_upper": round(float(bins[b + 1]), 3),
                "confidence": round(float(bin_center), 4),
                "accuracy": 0.0,
                "count": 0
            })

    return round(float(ece), 4), diagram_points


class ModelCalibrator:
    """
    Probability calibration module: Platt scaling or Isotonic regression.
    Fit strictly on validation set.
    """
    def __init__(self, method: str = "platt"):
        self.method = method.lower() # "none", "platt", "isotonic"
        self.platt_model: Optional[LogisticRegression] = None
        self.isotonic_model: Optional[IsotonicRegression] = None
        self.is_fitted = False

    def fit(self, val_scores: np.ndarray, val_targets: np.ndarray):
        val_scores = np.asarray(val_scores, dtype=np.float64)
        val_targets = np.asarray(val_targets, dtype=np.float64)

        if self.method == "platt":
            # Fit univariate logistic regression on logit or score
            # Map score to logit with eps clipping
            eps = 1e-6
            clipped = np.clip(val_scores, eps, 1.0 - eps)
            logits = np.log(clipped / (1.0 - clipped)).reshape(-1, 1)

            lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=200)
            lr.fit(logits, val_targets)
            self.platt_model = lr
            self.is_fitted = True

        elif self.method == "isotonic":
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            iso.fit(val_scores, val_targets)
            self.isotonic_model = iso
            self.is_fitted = True
        else:
            self.is_fitted = True

    def predict(self, scores: np.ndarray) -> np.ndarray:
        scores = np.asarray(scores, dtype=np.float64)
        if not self.is_fitted or self.method == "none":
            return np.clip(scores, 0.0, 1.0)

        if self.method == "platt" and self.platt_model is not None:
            eps = 1e-6
            clipped = np.clip(scores, eps, 1.0 - eps)
            logits = np.log(clipped / (1.0 - clipped)).reshape(-1, 1)
            calibrated = self.platt_model.predict_proba(logits)[:, 1]
            return np.clip(calibrated, 0.0, 1.0)

        elif self.method == "isotonic" and self.isotonic_model is not None:
            calibrated = self.isotonic_model.predict(scores)
            return np.clip(calibrated, 0.0, 1.0)

        return np.clip(scores, 0.0, 1.0)


def evaluate_alarm_fatigue_simulation(
    patients_predictions: List[Dict[str, Any]],
    threshold: float,
    cooldown_hours: float = 4.0,
    consecutive_hours: int = 1,
    escalation_delta: float = 0.15
) -> Dict[str, Any]:
    """
    Simulates real-world bedside alerting with cooldown, persistence, and escalation.
    Computes true alarm-fatigue metrics across patient stays.
    """
    total_patients = len(patients_predictions)
    total_hours = sum(len(p["risk_scores"]) for p in patients_predictions)
    total_patient_days = max(0.01, total_hours / 24.0)

    total_alerts_fired = 0
    false_alarm_count = 0
    septic_patients_total = 0
    septic_patients_caught = 0
    caught_at_least_3h = 0
    caught_at_least_6h = 0
    lead_times = []

    for pt in patients_predictions:
        scores = pt["risk_scores"]
        is_septic = pt.get("is_septic", False)
        onset_hour = pt.get("sepsis_onset_hour")

        if is_septic:
            septic_patients_total += 1

        last_alert_time = -999.0
        last_alert_risk = 0.0
        consecutive_above = 0
        patient_first_alert_time = None
        patient_fired_alerts = 0

        for h, risk in enumerate(scores):
            if risk >= threshold:
                consecutive_above += 1
            else:
                consecutive_above = 0

            # Persistence check
            if consecutive_above >= consecutive_hours:
                # Cooldown / Escalation check
                hours_since_last = h - last_alert_time
                risk_escalated = (risk - last_alert_risk) >= escalation_delta

                if (hours_since_last >= cooldown_hours) or risk_escalated:
                    # FIRE ALERT
                    total_alerts_fired += 1
                    patient_fired_alerts += 1
                    last_alert_time = float(h)
                    last_alert_risk = float(risk)

                    if patient_first_alert_time is None:
                        patient_first_alert_time = float(h)

                    # Check if this alert was true or false
                    if not is_septic:
                        false_alarm_count += 1
                    else:
                        # Septic patient: if alert fired AFTER onset hour by > 2 hours, count as false/late
                        if onset_hour is not None and h > onset_hour + 2:
                            false_alarm_count += 1

        # Check timeliness for septic patient
        if is_septic and onset_hour is not None and patient_first_alert_time is not None:
            lead_time = float(onset_hour - patient_first_alert_time)
            # A valid early catch occurs before or right at onset
            if lead_time >= 0:
                septic_patients_caught += 1
                lead_times.append(lead_time)
                if lead_time >= 3.0:
                    caught_at_least_3h += 1
                if lead_time >= 6.0:
                    caught_at_least_6h += 1

    alerts_per_pt_day = round(total_alerts_fired / total_patient_days, 2)
    alerts_per_true_case = round(total_alerts_fired / max(1, septic_patients_caught), 2)
    false_alarms_per_100_pt_days = round((false_alarm_count / total_patient_days) * 100.0, 2)

    true_alerts = total_alerts_fired - false_alarm_count
    ppv = round(true_alerts / max(1, total_alerts_fired), 4) if total_alerts_fired > 0 else 0.0
    sensitivity = round(septic_patients_caught / max(1, septic_patients_total), 4) if septic_patients_total > 0 else 0.0

    median_lead_time = float(np.median(lead_times)) if len(lead_times) > 0 else 0.0
    pct_3h = round((caught_at_least_3h / max(1, septic_patients_total)) * 100.0, 1)
    pct_6h = round((caught_at_least_6h / max(1, septic_patients_total)) * 100.0, 1)

    # Composite Alert Burden Score = alerts/pt-day * (1 - PPV)
    alert_burden = round(alerts_per_pt_day * (1.0 - ppv), 3)

    return {
        "threshold": round(threshold, 4),
        "total_alerts": total_alerts_fired,
        "false_alarms": false_alarm_count,
        "alerts_per_patient_day": alerts_per_pt_day,
        "alerts_per_true_case": alerts_per_true_case,
        "false_alarms_per_100_pt_days": false_alarms_per_100_pt_days,
        "ppv": ppv,
        "sensitivity": sensitivity,
        "median_lead_time_hours": round(median_lead_time, 1),
        "lead_time_distribution": [round(float(x), 1) for x in lead_times],
        "pct_caught_3h_ahead": pct_3h,
        "pct_caught_6h_ahead": pct_6h,
        "alert_burden_score": alert_burden,
        "septic_patients_total": septic_patients_total,
        "septic_patients_caught": septic_patients_caught
    }


def optimize_threshold(
    patients_predictions: List[Dict[str, Any]],
    mode: str = "f_beta",
    beta: float = 1.0,
    target_sensitivity: float = 0.80,
    alert_cap: float = 2.0,
    cooldown_hours: float = 4.0,
    consecutive_hours: int = 1,
    escalation_delta: float = 0.15
) -> Tuple[float, Dict[str, Any], List[Dict[str, Any]]]:
    """
    Evaluates candidate thresholds along Precision-Recall spectrum to find optimal operating point.
    Returns: (best_threshold, best_metrics, pr_curve_data)
    """
    candidate_thresholds = np.linspace(0.05, 0.95, 37)
    curve_data = []

    best_thresh = 0.35
    best_objective = -999999.0
    best_metrics = {}

    for t in candidate_thresholds:
        m = evaluate_alarm_fatigue_simulation(
            patients_predictions,
            threshold=float(t),
            cooldown_hours=cooldown_hours,
            consecutive_hours=consecutive_hours,
            escalation_delta=escalation_delta
        )
        curve_data.append(m)

        sens = m["sensitivity"]
        ppv = m["ppv"]
        alerts_day = m["alerts_per_patient_day"]

        # Objective function depending on mode
        if mode == "f_beta":
            # F-beta = (1 + beta^2) * (PPV * Recall) / (beta^2 * PPV + Recall)
            if (beta**2 * ppv + sens) > 0:
                score = (1.0 + beta**2) * (ppv * sens) / (beta**2 * ppv + sens)
            else:
                score = 0.0
            if score > best_objective:
                best_objective = score
                best_thresh = float(t)
                best_metrics = m

        elif mode == "target_sensitivity":
            # Meet or exceed target_sensitivity while minimizing alert rate
            if sens >= target_sensitivity:
                # Maximize negative alerts_day
                score = -alerts_day
            else:
                score = -1000.0 + sens # penalty
            if score > best_objective:
                best_objective = score
                best_thresh = float(t)
                best_metrics = m

        elif mode == "alert_cap":
            # Cap alerts/patient-day at alert_cap while maximizing sensitivity
            if alerts_day <= alert_cap:
                score = sens + 0.1 * ppv
            else:
                score = -1000.0 - (alerts_day - alert_cap)
            if score > best_objective:
                best_objective = score
                best_thresh = float(t)
                best_metrics = m

    if not best_metrics and len(curve_data) > 0:
        best_thresh = 0.35
        best_metrics = curve_data[len(curve_data) // 2]

    return round(best_thresh, 3), best_metrics, curve_data
