from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.ml_model import ModelRegistry
from backend.app.models.patient import Patient, VitalRecord, DatasetMeta
from backend.app.ml.trainer import ACTIVE_TRAINING_JOB, start_training_in_background

router = APIRouter(prefix="/api/models", tags=["models"])

class TrainModelRequest(BaseModel):
    name: str = "Trained-GRU-Model"
    model_type: str = "gru" # "gru", "lstm", "transformer", "gbdt", "logistic"
    dataset_name: Optional[str] = None
    hidden_dim: int = 64
    num_layers: int = 2
    epochs: int = 8
    lr: float = 0.002
    batch_size: int = 16
    imputation_method: str = "masked" # "masked", "locf_decay", "patient_median", "pop_median"
    loss_type: str = "weighted_bce" # "weighted_bce", "focal"
    calibration_method: str = "platt" # "platt", "isotonic", "none"
    threshold_mode: str = "f_beta" # "f_beta", "target_sensitivity", "alert_cap", "manual"
    target_f_beta: float = 1.0
    cooldown_hours: float = 4.0
    seed: int = 42
    set_active: bool = True

@router.get("")
def list_models(db: Session = Depends(get_db)):
    models = db.query(ModelRegistry).order_by(ModelRegistry.created_at.desc()).all()
    res = []
    for m in models:
        res.append({
            "id": m.id,
            "name": m.name,
            "model_type": m.model_type,
            "dataset_name": m.dataset_name,
            "hyperparameters": m.hyperparameters,
            "imputation_method": m.imputation_method,
            "loss_type": m.loss_type,
            "calibration_method": m.calibration_method,
            "operating_threshold": m.operating_threshold,
            "threshold_mode": m.threshold_mode,
            "cooldown_hours": m.cooldown_hours,
            "auroc": m.auroc,
            "auroc_ci_low": m.auroc_ci_low,
            "auroc_ci_high": m.auroc_ci_high,
            "auprc": m.auprc,
            "auprc_ci_low": m.auprc_ci_low,
            "auprc_ci_high": m.auprc_ci_high,
            "sensitivity": m.sensitivity,
            "ppv": m.ppv,
            "f1_score": m.f1_score,
            "alerts_per_patient_day": m.alerts_per_patient_day,
            "alerts_per_true_case": m.alerts_per_true_case,
            "median_lead_time_hours": m.median_lead_time_hours,
            "pct_caught_3h_ahead": m.pct_caught_3h_ahead,
            "pct_caught_6h_ahead": m.pct_caught_6h_ahead,
            "alert_burden_score": m.alert_burden_score,
            "training_duration_sec": m.training_duration_sec,
            "is_active": m.is_active,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M")
        })
    return res

@router.get("/active")
def get_active_model(db: Session = Depends(get_db)):
    m = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first()
    if not m:
        m = db.query(ModelRegistry).first()
    if not m:
        return None
    return {
        "id": m.id,
        "name": m.name,
        "model_type": m.model_type,
        "operating_threshold": m.operating_threshold,
        "cooldown_hours": m.cooldown_hours,
        "auroc": m.auroc,
        "auprc": m.auprc,
        "sensitivity": m.sensitivity,
        "ppv": m.ppv,
        "alerts_per_patient_day": m.alerts_per_patient_day,
        "alert_burden_score": m.alert_burden_score
    }

@router.post("/{id}/activate")
def activate_model(id: int, db: Session = Depends(get_db)):
    m = db.query(ModelRegistry).filter(ModelRegistry.id == id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    db.query(ModelRegistry).update({ModelRegistry.is_active: False})
    m.is_active = True
    db.commit()
    return {"status": "success", "active_model_id": m.id, "name": m.name}

@router.delete("/{id}")
def delete_model(id: int, db: Session = Depends(get_db)):
    m = db.query(ModelRegistry).filter(ModelRegistry.id == id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    if db.query(ModelRegistry).count() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the sole remaining model.")

    db.delete(m)
    remaining = db.query(ModelRegistry).first()
    if remaining and not db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first():
        remaining.is_active = True
    db.commit()
    return {"status": "success", "deleted_id": id}

@router.post("/train")
def trigger_model_training(req: TrainModelRequest, db: Session = Depends(get_db)):
    global ACTIVE_TRAINING_JOB
    if ACTIVE_TRAINING_JOB["is_running"]:
        raise HTTPException(status_code=400, detail="A training job is already in progress.")

    # Retrieve patient data from active dataset
    active_ds = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first()
    if not active_ds:
        active_ds = db.query(DatasetMeta).first()
    if not active_ds:
        raise HTTPException(status_code=400, detail="No dataset available for training. Generate or upload data first.")

    patients = db.query(Patient).filter(Patient.dataset_id == active_ds.id).all()
    if len(patients) < 10:
        raise HTTPException(status_code=400, detail="Dataset has too few patients to train (minimum 10 required).")

    # Serialize patients to raw dict format
    patients_data = []
    for p in patients:
        v_records = db.query(VitalRecord).filter(VitalRecord.patient_id == p.id).order_by(VitalRecord.hour).all()
        v_list = []
        for v in v_records:
            v_list.append({
                "hour": v.hour,
                "hr": v.hr,
                "sbp": v.sbp,
                "dbp": v.dbp,
                "map": v.map,
                "resp": v.resp,
                "temp": v.temp,
                "spo2": v.spo2,
                "lactate": v.lactate,
                "wbc": v.wbc,
                "creatinine": v.creatinine,
                "bilirubin": v.bilirubin,
                "sofa_score": v.sofa_score,
                "sirs_score": v.sirs_score,
                "qsofa_score": v.qsofa_score,
                "news_score": v.news_score,
                "sepsis_target_6h": v.sepsis_target_6h,
                "is_onset": v.is_onset
            })

        patients_data.append({
            "patient_id": p.patient_id,
            "age": p.age,
            "gender": p.gender,
            "unit": p.unit,
            "bed": p.bed,
            "los_hours": p.los_hours,
            "is_septic": p.is_septic,
            "sepsis_onset_hour": p.sepsis_onset_hour,
            "vitals": v_list
        })

    config = req.dict()
    config["dataset_name"] = active_ds.name

    start_training_in_background(config, patients_data)
    return {"status": "started", "message": f"Training initiated for {req.name} on {len(patients_data)} patients"}

@router.post("/train/stop")
def stop_training():
    global ACTIVE_TRAINING_JOB
    if ACTIVE_TRAINING_JOB["is_running"]:
        ACTIVE_TRAINING_JOB["should_stop"] = True
        return {"status": "stopping", "message": "Stop signal sent to background training worker."}
    return {"status": "idle", "message": "No active training job."}

@router.get("/train/status")
def get_training_status():
    global ACTIVE_TRAINING_JOB
    return ACTIVE_TRAINING_JOB
