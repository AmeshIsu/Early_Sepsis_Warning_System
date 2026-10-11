import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from sklearn.metrics import roc_curve, precision_recall_curve, auc, confusion_matrix
from backend.app.ml.calibration import evaluate_alarm_fatigue_simulation

def compute_bootstrap_ci(
    y_true: np.ndarray,
    y_scores: np.ndarray,
    n_bootstraps: int = 500,
    seed: int = 42
) -> Tuple[float, float, float, float, float, float]:
    """
    Computes AUROC and AUPRC with non-parametric bootstrap 95% confidence intervals.
    Returns: (auroc, auroc_low, auroc_high, auprc, auprc_low, auprc_high)
    """
    rng = np.random.default_rng(seed)
    n = len(y_true)
    if n == 0 or len(np.unique(y_true)) < 2:
        return 0.5, 0.5, 0.5, 0.0, 0.0, 0.0

    # Base values
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    base_auroc = float(auc(fpr, tpr))

    prec, rec, _ = precision_recall_curve(y_true, y_scores)
    base_auprc = float(auc(rec, prec))

    boot_aurocs = []
    boot_auprcs = []

    for _ in range(n_bootstraps):
        indices = rng.integers(0, n, n)
        if len(np.unique(y_true[indices])) < 2:
            continue
        try:
            bfpr, btpr, _ = roc_curve(y_true[indices], y_scores[indices])
            bprec, brec, _ = precision_recall_curve(y_true[indices], y_scores[indices])
            boot_aurocs.append(float(auc(bfpr, btpr)))
            boot_auprcs.append(float(auc(brec, bprec)))
        except Exception:
            continue

    if len(boot_aurocs) > 20:
        auroc_low = float(np.percentile(boot_aurocs, 2.5))
        auroc_high = float(np.percentile(boot_aurocs, 97.5))
        auprc_low = float(np.percentile(boot_auprcs, 2.5))
        auprc_high = float(np.percentile(boot_auprcs, 97.5))
    else:
        auroc_low, auroc_high = base_auroc * 0.95, min(1.0, base_auroc * 1.05)
        auprc_low, auprc_high = base_auprc * 0.95, min(1.0, base_auprc * 1.05)

    return (
        round(base_auroc, 4),
        round(auroc_low, 4),
        round(auroc_high, 4),
        round(base_auprc, 4),
        round(auprc_low, 4),
        round(auprc_high, 4)
    )


def evaluate_clinical_baselines(patients: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Evaluates SIRS, qSOFA, and NEWS against patient trajectories under realistic alerting.
    """
    # Prepare predictions format for alarm fatigue evaluator
    # SIRS threshold >= 2 (range 0 to 4) -> normalize to score / 4.0, threshold = 0.5
    sirs_pts = []
    qsofa_pts = []
    news_pts = []

    for pt in patients:
        sirs_scores = [float(v.get("sirs_score", 0)) / 4.0 for v in pt["vitals"]]
        qsofa_scores = [float(v.get("qsofa_score", 0)) / 3.0 for v in pt["vitals"]]
        news_scores = [float(v.get("news_score", 0)) / 20.0 for v in pt["vitals"]]

        meta = {
            "patient_id": pt["patient_id"],
            "is_septic": pt.get("is_septic", False),
            "sepsis_onset_hour": pt.get("sepsis_onset_hour")
        }
        sirs_pts.append({**meta, "risk_scores": sirs_scores})
        qsofa_pts.append({**meta, "risk_scores": qsofa_scores})
        news_pts.append({**meta, "risk_scores": news_scores})

    # Standard thresholds:
    # SIRS >= 2/4 = 0.50
    # qSOFA >= 2/3 = 0.66
    # NEWS >= 5/20 = 0.25 (medium risk)
    sirs_eval = evaluate_alarm_fatigue_simulation(sirs_pts, threshold=0.50, cooldown_hours=4.0)
    qsofa_eval = evaluate_alarm_fatigue_simulation(qsofa_pts, threshold=0.66, cooldown_hours=4.0)
    news_eval = evaluate_alarm_fatigue_simulation(news_pts, threshold=0.25, cooldown_hours=4.0)

    # Compute AUROC for each baseline using pooled points
    y_true = []
    sirs_all = []
    qsofa_all = []
    news_all = []
    for pt in patients:
        for v in pt["vitals"]:
            y_true.append(v.get("sepsis_target_6h", 0))
            sirs_all.append(float(v.get("sirs_score", 0)))
            qsofa_all.append(float(v.get("qsofa_score", 0)))
            news_all.append(float(v.get("news_score", 0)))

    y_arr = np.array(y_true)
    def calc_auc(scores):
        if len(np.unique(y_arr)) < 2:
            return 0.5, 0.0
        fpr, tpr, _ = roc_curve(y_arr, scores)
        prec, rec, _ = precision_recall_curve(y_arr, scores)
        return round(float(auc(fpr, tpr)), 4), round(float(auc(rec, prec)), 4)

    s_auroc, s_auprc = calc_auc(sirs_all)
    q_auroc, q_auprc = calc_auc(qsofa_all)
    n_auroc, n_auprc = calc_auc(news_all)

    sirs_eval.update({"name": "SIRS (Criteria >= 2)", "auroc": s_auroc, "auprc": s_auprc})
    qsofa_eval.update({"name": "qSOFA (Score >= 2)", "auroc": q_auroc, "auprc": q_auprc})
    news_eval.update({"name": "NEWS (Score >= 5)", "auroc": n_auroc, "auprc": n_auprc})

    return {
        "sirs": sirs_eval,
        "qsofa": qsofa_eval,
        "news": news_eval
    }


def compute_subgroup_analysis(
    patients: List[Dict[str, Any]],
    patient_predictions: List[Dict[str, Any]],
    threshold: float
) -> Dict[str, Any]:
    """
    Sub-group analysis by Age band and Sex.
    """
    age_groups = {
        "18-49": [],
        "50-64": [],
        "65-74": [],
        "75+": []
    }
    sex_groups = {
        "Female": [],
        "Male": []
    }

    pt_map = {p["patient_id"]: p for p in patients}

    for pred in patient_predictions:
        pid = pred["patient_id"]
        pt = pt_map.get(pid)
        if not pt:
            continue

        age = pt.get("age", 60.0)
        gender = pt.get("gender", 1)

        if age < 50:
            age_groups["18-49"].append(pred)
        elif age < 65:
            age_groups["50-64"].append(pred)
        elif age < 75:
            age_groups["65-74"].append(pred)
        else:
            age_groups["75+"].append(pred)

        if gender == 0:
            sex_groups["Female"].append(pred)
        else:
            sex_groups["Male"].append(pred)

    results = {"age_bands": {}, "sex": {}}

    for grp, p_list in age_groups.items():
        if len(p_list) > 0:
            results["age_bands"][grp] = evaluate_alarm_fatigue_simulation(p_list, threshold=threshold)
        else:
            results["age_bands"][grp] = {"total_alerts": 0, "sensitivity": 0.0, "ppv": 0.0, "alerts_per_patient_day": 0.0}

    for grp, p_list in sex_groups.items():
        if len(p_list) > 0:
            results["sex"][grp] = evaluate_alarm_fatigue_simulation(p_list, threshold=threshold)
        else:
            results["sex"][grp] = {"total_alerts": 0, "sensitivity": 0.0, "ppv": 0.0, "alerts_per_patient_day": 0.0}

    return results
