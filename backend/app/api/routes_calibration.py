import numpy as np
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.ml_model import ModelRegistry
from backend.app.models.patient import Patient, VitalRecord, DatasetMeta
from backend.app.ml.calibration import (
    ModelCalibrator,
    compute_ece,
    optimize_threshold,
    evaluate_alarm_fatigue_simulation
)

router = APIRouter(prefix="/api/calibration", tags=["calibration"])

class OptimizeThresholdRequest(BaseModel):
    mode: str = "f_beta" # "f_beta", "target_sensitivity", "alert_cap", "manual"
    manual_threshold: Optional[float] = 0.35
    beta: Optional[float] = 1.0
    target_sensitivity: Optional[float] = 0.80
    alert_cap: Optional[float] = 1.5
    cooldown_hours: Optional[float] = 4.0
    consecutive_hours: Optional[int] = 1
    calibration_method: Optional[str] = "platt"

class ApplyThresholdRequest(BaseModel):
    model_id: Optional[int] = None
    threshold: float
    mode: str = "manual"
    cooldown_hours: float = 4.0
    consecutive_hours: int = 1
    escalation_delta: float = 0.15
    calibration_method: str = "platt"

@router.get("/current")
def get_current_calibration(db: Session = Depends(get_db)):
    active_model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first()
    if not active_model:
        active_model = db.query(ModelRegistry).first()
    if not active_model:
        raise HTTPException(status_code=404, detail="No trained model found.")

    active_ds = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first()
    if not active_ds:
        active_ds = db.query(DatasetMeta).first()

    # Generate patient prediction timelines for PR simulation
    patients = db.query(Patient).filter(Patient.dataset_id == active_ds.id).all()
    pt_preds = []
    y_true_all = []
    y_scores_raw = []

    for p in patients:
        vitals = db.query(VitalRecord).filter(VitalRecord.patient_id == p.id).order_by(VitalRecord.hour).all()
        scores = [v.predicted_risk or 0.05 for v in vitals]
        pt_preds.append({
            "patient_id": p.patient_id,
            "risk_scores": scores,
            "is_septic": p.is_septic,
            "sepsis_onset_hour": p.sepsis_onset_hour
        })
        for v in vitals:
            y_true_all.append(v.sepsis_target_6h)
            y_scores_raw.append(v.predicted_risk or 0.05)

    y_true_arr = np.array(y_true_all)
    y_scores_arr = np.array(y_scores_raw)

    # Compute reliability diagram points (raw vs calibrated)
    ece_raw, diag_raw = compute_ece(y_true_arr, y_scores_arr, n_bins=10)

    calibrator = ModelCalibrator(method=active_model.calibration_method or "platt")
    calibrator.fit(y_scores_arr, y_true_arr)
    y_scores_calib = calibrator.predict(y_scores_arr)
    ece_calib, diag_calib = compute_ece(y_true_arr, y_scores_calib, n_bins=10)

    # Compute PR curve over thresholds
    best_t, best_m, pr_curve = optimize_threshold(
        pt_preds,
        mode=active_model.threshold_mode or "f_beta",
        beta=active_model.target_f_beta or 1.0,
        cooldown_hours=active_model.cooldown_hours or 4.0
    )

    # Metrics at current active threshold
    current_metrics = evaluate_alarm_fatigue_simulation(
        pt_preds,
        threshold=active_model.operating_threshold,
        cooldown_hours=active_model.cooldown_hours or 4.0
    )

    return {
        "model_id": active_model.id,
        "model_name": active_model.name,
        "calibration_method": active_model.calibration_method,
        "operating_threshold": active_model.operating_threshold,
        "cooldown_hours": active_model.cooldown_hours,
        "brier_score_raw": active_model.brier_score_raw,
        "brier_score_calibrated": active_model.brier_score_calibrated,
        "ece_raw": ece_raw,
        "ece_calibrated": ece_calib,
        "reliability_raw": diag_raw,
        "reliability_calibrated": diag_calib,
        "current_metrics": current_metrics,
        "pr_curve": pr_curve
    }

@router.post("/optimize")
def run_threshold_optimization(req: OptimizeThresholdRequest, db: Session = Depends(get_db)):
    active_ds = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first()
    if not active_ds:
        active_ds = db.query(DatasetMeta).first()

    patients = db.query(Patient).filter(Patient.dataset_id == active_ds.id).all()
    pt_preds = []
    for p in patients:
        vitals = db.query(VitalRecord).filter(VitalRecord.patient_id == p.id).order_by(VitalRecord.hour).all()
        scores = [v.predicted_risk or 0.05 for v in vitals]
        pt_preds.append({
            "patient_id": p.patient_id,
            "risk_scores": scores,
            "is_septic": p.is_septic,
            "sepsis_onset_hour": p.sepsis_onset_hour
        })

    cooldown_h = req.cooldown_hours or 4.0
    consec = req.consecutive_hours or 1

    if req.mode == "manual":
        thresh = float(req.manual_threshold or 0.35)
        metrics = evaluate_alarm_fatigue_simulation(
            pt_preds,
            threshold=thresh,
            cooldown_hours=cooldown_h,
            consecutive_hours=consec
        )
        _, _, pr_curve = optimize_threshold(pt_preds, mode="f_beta", cooldown_hours=cooldown_h)
        return {
            "mode": "manual",
            "threshold": thresh,
            "metrics": metrics,
            "pr_curve": pr_curve
        }
    else:
        best_t, best_metrics, pr_curve = optimize_threshold(
            pt_preds,
            mode=req.mode,
            beta=req.beta or 1.0,
            target_sensitivity=req.target_sensitivity or 0.80,
            alert_cap=req.alert_cap or 1.5,
            cooldown_hours=cooldown_h,
            consecutive_hours=consec
        )
        return {
            "mode": req.mode,
            "threshold": best_t,
            "metrics": best_metrics,
            "pr_curve": pr_curve
        }

@router.post("/apply")
def apply_threshold_to_model(req: ApplyThresholdRequest, db: Session = Depends(get_db)):
    if req.model_id:
        model = db.query(ModelRegistry).filter(ModelRegistry.id == req.model_id).first()
    else:
        model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first()

    if not model:
        model = db.query(ModelRegistry).first()
    if not model:
        raise HTTPException(status_code=404, detail="No model found to update.")

    model.operating_threshold = round(req.threshold, 3)
    model.threshold_mode = req.mode
    model.cooldown_hours = req.cooldown_hours
    model.consecutive_hours = req.consecutive_hours
    model.escalation_delta = req.escalation_delta
    model.calibration_method = req.calibration_method

    db.commit()
    return {
        "status": "success",
        "model_id": model.id,
        "name": model.name,
        "operating_threshold": model.operating_threshold,
        "cooldown_hours": model.cooldown_hours
    }
