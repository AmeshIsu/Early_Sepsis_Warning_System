import random
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from backend.app.ml.baselines import compute_sirs, compute_qsofa, compute_news, compute_sofa_components

UNITS = ["MICU", "SICU", "CCU", "CTICU"]

def generate_patient_trajectory(
    pid_idx: int,
    is_septic: bool,
    sepsis_prevalence: float = 0.10,
    rng: Optional[np.random.Generator] = None
) -> Dict[str, Any]:
    if rng is None:
        rng = np.random.default_rng()

    patient_id = f"PAT-{pid_idx:04d}"
    age = float(np.clip(rng.normal(62, 14), 18, 89))
    gender = int(rng.choice([0, 1])) # 0: Female, 1: Male
    unit = str(rng.choice(UNITS))
    bed = f"BED-{(pid_idx % 24) + 1:02d}"

    # ICU stay length in hours (between 36 and 72 hours)
    los_hours = int(rng.integers(36, 73))

    # Patient baseline vitals
    base_hr = rng.normal(74, 8)
    base_sbp = rng.normal(122, 10)
    base_dbp = rng.normal(74, 7)
    base_map = (2 * base_dbp + base_sbp) / 3.0
    base_resp = rng.normal(16, 2)
    base_temp = rng.normal(36.8, 0.25)
    base_spo2 = rng.normal(97.5, 1.0)

    # Patient baseline labs
    base_lactate = rng.normal(1.1, 0.25)
    base_wbc = rng.normal(7.8, 1.5)
    base_creat = rng.normal(0.9, 0.2)
    base_bili = rng.normal(0.6, 0.2)

    # Determine sepsis onset if septic
    onset_hour = None
    drift_start_hour = None
    if is_septic:
        # Onset occurs between hour 14 and los_hours - 6
        onset_hour = int(rng.integers(14, max(16, los_hours - 5)))
        drift_hours = int(rng.integers(6, 11)) # 6 to 10 hours prior to onset
        drift_start_hour = max(2, onset_hour - drift_hours)

    # Non-septic confounders (e.g. transient fever/pain/tachycardia episode)
    has_confounder = (not is_septic) and (rng.random() < 0.28)
    confounder_start = int(rng.integers(8, max(10, los_hours - 12))) if has_confounder else -1
    confounder_duration = int(rng.integers(4, 9)) if has_confounder else 0

    vitals_history = []
    # Lab draw schedules (labs drawn periodically, e.g. every 8-16h)
    lab_hours = set(range(0, los_hours, int(rng.integers(8, 14))))
    lab_hours.add(0) # baseline draw
    if is_septic and onset_hour is not None:
        lab_hours.add(max(0, onset_hour - 3))
        lab_hours.add(onset_hour)

    for h in range(los_hours):
        # Auto-regressive small random walk for vitals
        noise_hr = rng.normal(0, 2.5)
        noise_sbp = rng.normal(0, 3.5)
        noise_dbp = rng.normal(0, 2.5)
        noise_resp = rng.normal(0, 1.2)
        noise_temp = rng.normal(0, 0.12)
        noise_spo2 = rng.normal(0, 0.5)

        curr_hr = base_hr + noise_hr
        curr_sbp = base_sbp + noise_sbp
        curr_dbp = base_dbp + noise_dbp
        curr_resp = base_resp + noise_resp
        curr_temp = base_temp + noise_temp
        curr_spo2 = base_spo2 + noise_spo2

        # Sepsis drift trajectory
        if is_septic and onset_hour is not None:
            if h >= drift_start_hour:
                # Progress fraction from drift start to onset
                prog = min(1.0, (h - drift_start_hour) / max(1.0, (onset_hour - drift_start_hour)))
                # Subtle physiological collapse: HR up, BP down, RR up, Temp changes, SpO2 dips
                curr_hr += prog * rng.uniform(22, 38)
                curr_sbp -= prog * rng.uniform(20, 34)
                curr_dbp -= prog * rng.uniform(12, 22)
                curr_resp += prog * rng.uniform(6, 12)
                curr_temp += prog * rng.uniform(1.2, 2.2) # septic fever
                curr_spo2 -= prog * rng.uniform(3.5, 7.0)

        # Confounder trajectory (transient tachycardia / fever, then recovery)
        elif has_confounder and (confounder_start <= h < confounder_start + confounder_duration):
            conf_prog = np.sin(np.pi * (h - confounder_start) / confounder_duration)
            curr_hr += conf_prog * rng.uniform(18, 28)
            curr_temp += conf_prog * rng.uniform(0.8, 1.4)
            curr_resp += conf_prog * rng.uniform(3, 6)

        # Compute MAP
        curr_map = (2 * curr_dbp + curr_sbp) / 3.0

        # Physical biological limits
        curr_hr = float(np.clip(curr_hr, 35, 185))
        curr_sbp = float(np.clip(curr_sbp, 55, 230))
        curr_dbp = float(np.clip(curr_dbp, 30, 140))
        curr_map = float(np.clip(curr_map, 35, 160))
        curr_resp = float(np.clip(curr_resp, 6, 45))
        curr_temp = float(np.clip(curr_temp, 34.5, 41.5))
        curr_spo2 = float(np.clip(curr_spo2, 75, 100))

        # Labs: sampled only during lab draw hours
        obs_lactate = None
        obs_wbc = None
        obs_creat = None
        obs_bili = None

        if h in lab_hours:
            curr_lactate = base_lactate + rng.normal(0, 0.15)
            curr_wbc = base_wbc + rng.normal(0, 0.6)
            curr_creat = base_creat + rng.normal(0, 0.1)
            curr_bili = base_bili + rng.normal(0, 0.1)

            if is_septic and onset_hour is not None and h >= drift_start_hour:
                prog = min(1.2, (h - drift_start_hour) / max(1.0, (onset_hour - drift_start_hour)))
                curr_lactate += prog * rng.uniform(1.8, 4.2)
                curr_wbc += prog * rng.uniform(4.5, 9.5)
                curr_creat += prog * rng.uniform(0.7, 1.8)
                curr_bili += prog * rng.uniform(0.5, 1.5)

            obs_lactate = round(float(np.clip(curr_lactate, 0.4, 15.0)), 2)
            obs_wbc = round(float(np.clip(curr_wbc, 1.5, 40.0)), 1)
            obs_creat = round(float(np.clip(curr_creat, 0.3, 10.0)), 2)
            obs_bili = round(float(np.clip(curr_bili, 0.1, 15.0)), 2)

        # Missingness on vitals (realistic charting gaps)
        obs_hr = round(curr_hr, 1) if rng.random() > 0.15 else None
        obs_sbp = round(curr_sbp, 1) if rng.random() > 0.18 else None
        obs_dbp = round(curr_dbp, 1) if rng.random() > 0.18 else None
        obs_map = round(curr_map, 1) if (obs_sbp is not None and obs_dbp is not None) else None
        obs_resp = round(curr_resp, 1) if rng.random() > 0.20 else None
        obs_temp = round(curr_temp, 2) if rng.random() > 0.45 else None
        obs_spo2 = round(curr_spo2, 1) if rng.random() > 0.15 else None

        # Clinical Baseline scores (use current values for calculation)
        sirs = compute_sirs(
            hr=obs_hr or curr_hr,
            resp=obs_resp or curr_resp,
            temp=obs_temp or curr_temp,
            wbc=obs_wbc or base_wbc
        )
        qsofa = compute_qsofa(
            resp=obs_resp or curr_resp,
            sbp=obs_sbp or curr_sbp,
            altered_mental=(curr_map < 65.0)
        )
        news = compute_news(
            hr=obs_hr or curr_hr,
            sbp=obs_sbp or curr_sbp,
            resp=obs_resp or curr_resp,
            temp=obs_temp or curr_temp,
            spo2=obs_spo2 or curr_spo2
        )
        sofa_dict = compute_sofa_components(
            map_val=obs_map or curr_map,
            creatinine=obs_creat or base_creat,
            bilirubin=obs_bili or base_bili,
            spo2=obs_spo2 or curr_spo2
        )

        # Target 6-hour forward horizon:
        # sepsis_target_6h = 1 if onset in (h, h + 6]
        is_target_6h = 0
        is_onset_now = False
        if is_septic and onset_hour is not None:
            if h < onset_hour <= (h + 6):
                is_target_6h = 1
            if h == onset_hour:
                is_onset_now = True

        vitals_history.append({
            "hour": h,
            "hr": obs_hr,
            "sbp": obs_sbp,
            "dbp": obs_dbp,
            "map": obs_map,
            "resp": obs_resp,
            "temp": obs_temp,
            "spo2": obs_spo2,
            "lactate": obs_lactate,
            "wbc": obs_wbc,
            "creatinine": obs_creat,
            "bilirubin": obs_bili,
            "sofa_score": sofa_dict["total"],
            "sirs_score": sirs,
            "qsofa_score": qsofa,
            "news_score": news,
            "sepsis_target_6h": is_target_6h,
            "is_onset": is_onset_now,
            # Ground truth latent values (for fallback / test verification)
            "_true_hr": round(curr_hr, 1),
            "_true_map": round(curr_map, 1),
            "_true_resp": round(curr_resp, 1),
            "_true_temp": round(curr_temp, 2),
            "_true_spo2": round(curr_spo2, 1),
        })

    return {
        "patient_id": patient_id,
        "age": age,
        "gender": gender,
        "unit": unit,
        "bed": bed,
        "los_hours": los_hours,
        "is_septic": is_septic,
        "sepsis_onset_hour": onset_hour,
        "vitals": vitals_history
    }


def generate_synthetic_cohort(
    num_patients: int = 200,
    sepsis_prevalence: float = 0.12,
    seed: int = 42
) -> List[Dict[str, Any]]:
    """
    Generates a full synthetic ICU patient cohort with realistic irregular vitals/labs,
    missingness, confounders, and Sepsis-3 labels.
    """
    rng = np.random.default_rng(seed)
    patients = []

    # Assign sepsis labels to guarantee prevalence
    num_septic = max(1, int(round(num_patients * sepsis_prevalence)))
    septic_flags = [True] * num_septic + [False] * (num_patients - num_septic)
    rng.shuffle(septic_flags)

    for i in range(num_patients):
        pt = generate_patient_trajectory(
            pid_idx=i + 1,
            is_septic=septic_flags[i],
            sepsis_prevalence=sepsis_prevalence,
            rng=rng
        )
        patients.append(pt)

    return patients
