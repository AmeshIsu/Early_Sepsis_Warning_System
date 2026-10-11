import io
import csv
import numpy as np
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sklearn.metrics import roc_curve, precision_recall_curve, confusion_matrix
from backend.app.database import get_db
from backend.app.models.ml_model import ModelRegistry
from backend.app.models.patient import Patient, VitalRecord, DatasetMeta
from backend.app.ml.evaluation import evaluate_clinical_baselines, compute_subgroup_analysis, compute_bootstrap_ci
from backend.app.ml.calibration import evaluate_alarm_fatigue_simulation
from backend.app.services.export_service import generate_evaluation_pdf_report

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

@router.get("/benchmark")
def get_benchmark_evaluation(
    model_id: Optional[int] = None,
    dataset_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if model_id:
        model = db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()
    else:
        model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first()
        if not model:
            model = db.query(ModelRegistry).first()

    if not model:
        raise HTTPException(status_code=404, detail="No trained model found.")

    if dataset_id:
        dataset = db.query(DatasetMeta).filter(DatasetMeta.id == dataset_id).first()
    else:
        dataset = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first()
        if not dataset:
            dataset = db.query(DatasetMeta).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="No dataset found.")

    patients = db.query(Patient).filter(Patient.dataset_id == dataset.id).all()
    if not patients:
        raise HTTPException(status_code=400, detail="Dataset has no patients.")

    # Prepare patient trajectories
    pt_preds = []
    raw_pt_list = []
    y_true_all = []
    y_scores_all = []

    for p in patients:
        vitals = db.query(VitalRecord).filter(VitalRecord.patient_id == p.id).order_by(VitalRecord.hour).all()
        scores = [v.predicted_risk or 0.05 for v in vitals]
        pt_preds.append({
            "patient_id": p.patient_id,
            "risk_scores": scores,
            "is_septic": p.is_septic,
            "sepsis_onset_hour": p.sepsis_onset_hour
        })
        v_list = []
        for v in vitals:
            y_true_all.append(v.sepsis_target_6h)
            y_scores_all.append(v.predicted_risk or 0.05)
            v_list.append({
                "hour": v.hour,
                "hr": v.hr,
                "map": v.map,
                "resp": v.resp,
                "temp": v.temp,
                "spo2": v.spo2,
                "lactate": v.lactate,
                "wbc": v.wbc,
                "creatinine": v.creatinine,
                "bilirubin": v.bilirubin,
                "sirs_score": v.sirs_score,
                "qsofa_score": v.qsofa_score,
                "news_score": v.news_score,
                "sofa_score": v.sofa_score,
                "sepsis_target_6h": v.sepsis_target_6h
            })

        raw_pt_list.append({
            "patient_id": p.patient_id,
            "age": p.age,
            "gender": p.gender,
            "is_septic": p.is_septic,
            "sepsis_onset_hour": p.sepsis_onset_hour,
            "vitals": v_list
        })

    # Evaluate ML Model
    thresh = model.operating_threshold
    cooldown = model.cooldown_hours or 4.0
    ml_alarm = evaluate_alarm_fatigue_simulation(pt_preds, threshold=thresh, cooldown_hours=cooldown)

    # Evaluate Baselines: SIRS, qSOFA, NEWS
    baselines = evaluate_clinical_baselines(raw_pt_list)

    # ROC & PR curves for ML Model
    y_true_arr = np.array(y_true_all)
    y_scores_arr = np.array(y_scores_all)

    fpr, tpr, _ = roc_curve(y_true_arr, y_scores_arr)
    prec, rec, pr_thresh = precision_recall_curve(y_true_arr, y_scores_arr)

    # Downsample curves to 50 points for fast rendering in Recharts
    def downsample_curve(x_arr, y_arr, n=50):
        idx = np.linspace(0, len(x_arr) - 1, min(n, len(x_arr))).astype(int)
        return [{"x": round(float(x_arr[i]), 4), "y": round(float(y_arr[i]), 4)} for i in idx]

    roc_curve_pts = downsample_curve(fpr, tpr)
    pr_curve_pts = downsample_curve(rec, prec)

    # Confusion Matrix
    y_pred_binary = (y_scores_arr >= thresh).astype(int)
    cm = confusion_matrix(y_true_arr, y_pred_binary)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

    # Lead-time Histogram bins (0h to 12h)
    lead_times = ml_alarm.get("lead_time_distribution", [])
    lead_hist = []
    for h_bin in range(0, 13, 2):
        count = sum(1 for lt in lead_times if h_bin <= lt < h_bin + 2)
        lead_hist.append({
            "bin": f"{h_bin}-{h_bin+2}h",
            "count": count
        })

    subgroups = compute_subgroup_analysis(raw_pt_list, pt_preds, threshold=thresh)

    return {
        "model": {
            "id": model.id,
            "name": model.name,
            "model_type": model.model_type.upper(),
            "operating_threshold": thresh,
            "cooldown_hours": cooldown,
            "auroc": model.auroc,
            "auroc_ci_low": model.auroc_ci_low,
            "auroc_ci_high": model.auroc_ci_high,
            "auprc": model.auprc,
            "auprc_ci_low": model.auprc_ci_low,
            "auprc_ci_high": model.auprc_ci_high,
            "metrics": ml_alarm
        },
        "baselines": baselines,
        "roc_curve": roc_curve_pts,
        "pr_curve": pr_curve_pts,
        "confusion_matrix": {
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn)
        },
        "lead_time_histogram": lead_hist,
        "subgroups": subgroups
    }

@router.get("/subgroups")
def get_subgroups_endpoint(db: Session = Depends(get_db)):
    active_model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first() or db.query(ModelRegistry).first()
    active_ds = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first() or db.query(DatasetMeta).first()

    if not active_model or not active_ds:
        return {"age_bands": {}, "sex": {}}

    patients = db.query(Patient).filter(Patient.dataset_id == active_ds.id).all()
    pt_preds = []
    raw_pt_list = []
    for p in patients:
        vitals = db.query(VitalRecord).filter(VitalRecord.patient_id == p.id).order_by(VitalRecord.hour).all()
        scores = [v.predicted_risk or 0.05 for v in vitals]
        pt_preds.append({
            "patient_id": p.patient_id,
            "risk_scores": scores,
            "is_septic": p.is_septic,
            "sepsis_onset_hour": p.sepsis_onset_hour
        })
        raw_pt_list.append({
            "patient_id": p.patient_id,
            "age": p.age,
            "gender": p.gender,
            "is_septic": p.is_septic
        })

    subgroups = compute_subgroup_analysis(raw_pt_list, pt_preds, threshold=active_model.operating_threshold)
    return subgroups

@router.get("/export/pdf")
def export_pdf_report(db: Session = Depends(get_db)):
    active_model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first() or db.query(ModelRegistry).first()
    active_ds = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first() or db.query(DatasetMeta).first()

    patients = db.query(Patient).filter(Patient.dataset_id == active_ds.id).all()
    pt_preds = []
    raw_pt_list = []
    for p in patients:
        vitals = db.query(VitalRecord).filter(VitalRecord.patient_id == p.id).order_by(VitalRecord.hour).all()
        scores = [v.predicted_risk or 0.05 for v in vitals]
        pt_preds.append({
            "patient_id": p.patient_id,
            "risk_scores": scores,
            "is_septic": p.is_septic,
            "sepsis_onset_hour": p.sepsis_onset_hour
        })
        v_list = [{"sirs_score": v.sirs_score, "qsofa_score": v.qsofa_score, "news_score": v.news_score, "sepsis_target_6h": v.sepsis_target_6h} for v in vitals]
        raw_pt_list.append({
            "patient_id": p.patient_id,
            "age": p.age,
            "gender": p.gender,
            "is_septic": p.is_septic,
            "sepsis_onset_hour": p.sepsis_onset_hour,
            "vitals": v_list
        })

    ml_alarm = evaluate_alarm_fatigue_simulation(pt_preds, threshold=active_model.operating_threshold)
    baselines = evaluate_clinical_baselines(raw_pt_list)
    subgroups = compute_subgroup_analysis(raw_pt_list, pt_preds, threshold=active_model.operating_threshold)

    eval_data = {
        "model_name": active_model.name,
        "model_type": active_model.model_type,
        "operating_threshold": active_model.operating_threshold,
        "cooldown_hours": active_model.cooldown_hours,
        "dataset_name": active_ds.name,
        "model_metrics": {
            **ml_alarm,
            "auroc": active_model.auroc,
            "auroc_ci_low": active_model.auroc_ci_low,
            "auroc_ci_high": active_model.auroc_ci_high,
            "auprc": active_model.auprc,
            "brier_score_raw": active_model.brier_score_raw,
            "brier_score_calibrated": active_model.brier_score_calibrated,
            "ece_raw": active_model.ece_raw,
            "ece_calibrated": active_model.ece_calibrated
        },
        "baselines": baselines,
        "subgroups": subgroups
    }

    pdf_bytes = generate_evaluation_pdf_report(eval_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=SepsisWatch_Evaluation_Report.pdf"}
    )

@router.get("/export/csv")
def export_benchmark_csv(db: Session = Depends(get_db)):
    active_model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first() or db.query(ModelRegistry).first()
    active_ds = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first() or db.query(DatasetMeta).first()

    patients = db.query(Patient).filter(Patient.dataset_id == active_ds.id).all()
    pt_preds = [{"patient_id": p.patient_id, "risk_scores": [v.predicted_risk or 0.05 for v in p.vitals], "is_septic": p.is_septic, "sepsis_onset_hour": p.sepsis_onset_hour} for p in patients]
    raw_pt_list = [{"patient_id": p.patient_id, "is_septic": p.is_septic, "sepsis_onset_hour": p.sepsis_onset_hour, "vitals": [{"sirs_score": v.sirs_score, "qsofa_score": v.qsofa_score, "news_score": v.news_score, "sepsis_target_6h": v.sepsis_target_6h} for v in p.vitals]} for p in patients]

    ml_alarm = evaluate_alarm_fatigue_simulation(pt_preds, threshold=active_model.operating_threshold)
    baselines = evaluate_clinical_baselines(raw_pt_list)

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Method", "AUROC", "AUPRC", "Sensitivity", "PPV", "Alerts_Per_Patient_Day", "Median_Lead_Time_Hours", "Alert_Burden_Score"])

    writer.writerow([
        active_model.name,
        active_model.auroc,
        active_model.auprc,
        ml_alarm["sensitivity"],
        ml_alarm["ppv"],
        ml_alarm["alerts_per_patient_day"],
        ml_alarm["median_lead_time_hours"],
        ml_alarm["alert_burden_score"]
    ])
    for b_key, b in baselines.items():
        writer.writerow([
            b.get("name", b_key),
            b.get("auroc"),
            b.get("auprc"),
            b.get("sensitivity"),
            b.get("ppv"),
            b.get("alerts_per_patient_day"),
            b.get("median_lead_time_hours"),
            b.get("alert_burden_score")
        ])

    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sepsiswatch_benchmark.csv"}
    )
