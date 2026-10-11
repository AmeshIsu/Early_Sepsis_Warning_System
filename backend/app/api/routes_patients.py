from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.patient import Patient, VitalRecord, DatasetMeta
from backend.app.models.alert import AlertEvent, ClinicalNote
from backend.app.models.ml_model import ModelRegistry
from backend.app.ml.explainability import generate_feature_contributions

router = APIRouter(prefix="/api/patients", tags=["patients"])

class PatientActionRequest(BaseModel):
    action: str # "acknowledge", "snooze", "false_alarm", "add_note"
    snooze_hours: Optional[float] = 2.0
    note_content: Optional[str] = None
    note_type: Optional[str] = "Clinical Note"
    author: Optional[str] = "Staff Clinician"

@router.get("")
def list_patients(
    risk_level: Optional[str] = None, # "ALL", "LOW", "MODERATE", "HIGH"
    unit: Optional[str] = None,
    alert_status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db)
):
    active_dataset = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first()
    if not active_dataset:
        active_dataset = db.query(DatasetMeta).first()

    if not active_dataset:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    query = db.query(Patient).filter(Patient.dataset_id == active_dataset.id)

    if risk_level and risk_level.upper() != "ALL":
        query = query.filter(Patient.current_risk_level == risk_level.upper())
    if unit and unit.upper() != "ALL":
        query = query.filter(Patient.unit == unit.upper())
    if alert_status and alert_status.upper() != "ALL":
        query = query.filter(Patient.alert_status == alert_status.upper())
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter((Patient.patient_id.ilike(search_fmt)) | (Patient.bed.ilike(search_fmt)))

    total = query.count()
    patients = query.order_by(Patient.current_risk_score.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for p in patients:
        curr_vital = db.query(VitalRecord).filter(
            VitalRecord.patient_id == p.id,
            VitalRecord.hour == p.current_sim_hour
        ).first()

        spark_hours = range(max(0, p.current_sim_hour - 7), p.current_sim_hour + 1)
        recent_v = db.query(VitalRecord.predicted_risk).filter(
            VitalRecord.patient_id == p.id,
            VitalRecord.hour.in_(spark_hours)
        ).order_by(VitalRecord.hour).all()
        sparkline = [round(float(r[0] or 0.05), 2) for r in recent_v]

        items.append({
            "id": p.id,
            "patient_id": p.patient_id,
            "bed": p.bed,
            "unit": p.unit,
            "age": p.age,
            "gender": "M" if p.gender == 1 else "F",
            "current_sim_hour": p.current_sim_hour,
            "current_risk_score": round(p.current_risk_score, 3),
            "current_risk_level": p.current_risk_level,
            "alert_status": p.alert_status,
            "last_alert_hour": p.last_alert_hour,
            "is_septic": p.is_septic,
            "sepsis_onset_hour": p.sepsis_onset_hour,
            "sparkline": sparkline,
            "vitals": {
                "hr": curr_vital.hr if curr_vital else None,
                "map": curr_vital.map if curr_vital else None,
                "sbp": curr_vital.sbp if curr_vital else None,
                "dbp": curr_vital.dbp if curr_vital else None,
                "resp": curr_vital.resp if curr_vital else None,
                "temp": curr_vital.temp if curr_vital else None,
                "spo2": curr_vital.spo2 if curr_vital else None,
                "lactate": curr_vital.lactate if curr_vital else None,
                "wbc": curr_vital.wbc if curr_vital else None,
                "sofa_score": curr_vital.sofa_score if curr_vital else 0,
                "sirs_score": curr_vital.sirs_score if curr_vital else 0,
                "qsofa_score": curr_vital.qsofa_score if curr_vital else 0,
                "news_score": curr_vital.news_score if curr_vital else 0
            }
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{patient_id}")
def get_patient_details(patient_id: int, db: Session = Depends(get_db)):
    pt = db.query(Patient).filter(Patient.id == patient_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Patient not found")

    active_model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first()
    threshold = active_model.operating_threshold if active_model else 0.35

    vitals = db.query(VitalRecord).filter(VitalRecord.patient_id == pt.id).order_by(VitalRecord.hour).all()
    alerts = db.query(AlertEvent).filter(AlertEvent.patient_id == pt.id).order_by(AlertEvent.hour.desc()).all()
    notes = db.query(ClinicalNote).filter(ClinicalNote.patient_id == pt.id).order_by(ClinicalNote.created_at.desc()).all()

    timeline = []
    labs_history = []
    for v in vitals:
        rec = {
            "hour": v.hour,
            "hr": v.hr,
            "sbp": v.sbp,
            "dbp": v.dbp,
            "map": v.map,
            "resp": v.resp,
            "temp": v.temp,
            "spo2": v.spo2,
            "predicted_risk": round(v.predicted_risk or 0.0, 3),
            "threshold": threshold,
            "sofa_score": v.sofa_score,
            "sirs_score": v.sirs_score,
            "qsofa_score": v.qsofa_score,
            "news_score": v.news_score,
            "sepsis_target_6h": v.sepsis_target_6h,
            "is_onset": v.is_onset,
            "alert_fired": bool(any(a.hour == v.hour for a in alerts))
        }
        timeline.append(rec)

        if any(x is not None for x in [v.lactate, v.wbc, v.creatinine, v.bilirubin]):
            labs_history.append({
                "hour": v.hour,
                "lactate": v.lactate,
                "wbc": v.wbc,
                "creatinine": v.creatinine,
                "bilirubin": v.bilirubin,
                "sofa_score": v.sofa_score
            })

    latest_v = db.query(VitalRecord).filter(
        VitalRecord.patient_id == pt.id,
        VitalRecord.hour == pt.current_sim_hour
    ).first()

    return {
        "patient": {
            "id": pt.id,
            "patient_id": pt.patient_id,
            "bed": pt.bed,
            "unit": pt.unit,
            "age": pt.age,
            "gender": "Male" if pt.gender == 1 else "Female",
            "los_hours": pt.los_hours,
            "current_sim_hour": pt.current_sim_hour,
            "current_risk_score": round(pt.current_risk_score, 3),
            "current_risk_level": pt.current_risk_level,
            "alert_status": pt.alert_status,
            "last_alert_hour": pt.last_alert_hour,
            "is_septic": pt.is_septic,
            "sepsis_onset_hour": pt.sepsis_onset_hour
        },
        "operating_threshold": threshold,
        "current_vitals": {
            "hr": latest_v.hr if latest_v else None,
            "map": latest_v.map if latest_v else None,
            "sbp": latest_v.sbp if latest_v else None,
            "dbp": latest_v.dbp if latest_v else None,
            "resp": latest_v.resp if latest_v else None,
            "temp": latest_v.temp if latest_v else None,
            "spo2": latest_v.spo2 if latest_v else None,
            "lactate": latest_v.lactate if latest_v else None,
            "wbc": latest_v.wbc if latest_v else None,
            "creatinine": latest_v.creatinine if latest_v else None,
            "bilirubin": latest_v.bilirubin if latest_v else None,
            "sofa_score": latest_v.sofa_score if latest_v else 0,
            "sirs_score": latest_v.sirs_score if latest_v else 0,
            "qsofa_score": latest_v.qsofa_score if latest_v else 0,
            "news_score": latest_v.news_score if latest_v else 0
        },
        "timeline": timeline,
        "labs_history": labs_history,
        "alerts": [
            {
                "id": a.id,
                "hour": a.hour,
                "risk_score": round(a.risk_score, 3),
                "threshold": round(a.threshold, 3),
                "status": a.status,
                "snoozed_until_hour": a.snoozed_until_hour,
                "action_note": a.action_note,
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M")
            } for a in alerts
        ],
        "notes": [
            {
                "id": n.id,
                "author": n.author,
                "sim_hour": n.sim_hour,
                "note_type": n.note_type,
                "content": n.content,
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
            } for n in notes
        ]
    }


@router.get("/{patient_id}/explain")
def get_patient_explainability(patient_id: int, db: Session = Depends(get_db)):
    pt = db.query(Patient).filter(Patient.id == patient_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Patient not found")

    curr_v = db.query(VitalRecord).filter(
        VitalRecord.patient_id == pt.id,
        VitalRecord.hour == pt.current_sim_hour
    ).first()

    base_v = db.query(VitalRecord).filter(
        VitalRecord.patient_id == pt.id,
        VitalRecord.hour == 0
    ).first()

    curr_dict = {
        "hr": curr_v.hr if curr_v else None,
        "map": curr_v.map if curr_v else None,
        "sbp": curr_v.sbp if curr_v else None,
        "dbp": curr_v.dbp if curr_v else None,
        "resp": curr_v.resp if curr_v else None,
        "temp": curr_v.temp if curr_v else None,
        "spo2": curr_v.spo2 if curr_v else None,
        "lactate": curr_v.lactate if curr_v else None,
        "wbc": curr_v.wbc if curr_v else None,
        "creatinine": curr_v.creatinine if curr_v else None,
        "bilirubin": curr_v.bilirubin if curr_v else None
    }
    base_dict = {
        "hr": base_v.hr if base_v else 75.0,
        "map": base_v.map if base_v else 90.0,
        "sbp": base_v.sbp if base_v else 120.0,
        "dbp": base_v.dbp if base_v else 75.0,
        "resp": base_v.resp if base_v else 16.0,
        "temp": base_v.temp if base_v else 36.8,
        "spo2": base_v.spo2 if base_v else 98.0,
        "lactate": base_v.lactate if base_v else 1.0,
        "wbc": base_v.wbc if base_v else 7.5,
        "creatinine": base_v.creatinine if base_v else 0.9,
        "bilirubin": base_v.bilirubin if base_v else 0.6
    }

    explanation = generate_feature_contributions(curr_dict, base_dict, pt.current_risk_score)
    return explanation


@router.post("/{patient_id}/actions")
def submit_patient_action(patient_id: int, req: PatientActionRequest, db: Session = Depends(get_db)):
    pt = db.query(Patient).filter(Patient.id == patient_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Patient not found")

    action_lower = req.action.lower()
    latest_alert = db.query(AlertEvent).filter(
        AlertEvent.patient_id == pt.id
    ).order_by(AlertEvent.id.desc()).first()

    now = datetime.utcnow()

    if action_lower == "acknowledge":
        pt.alert_status = "ACKNOWLEDGED"
        if latest_alert:
            latest_alert.status = "ACKNOWLEDGED"
            latest_alert.action_timestamp = now
            latest_alert.action_note = req.note_content or "Acknowledged by clinical staff"
        note_txt = f"Alert acknowledged. Clinical team actively evaluating bedside vitals."

    elif action_lower == "snooze":
        snooze_duration = req.snooze_hours or 2.0
        pt.alert_status = "SNOOZED"
        snooze_until = pt.current_sim_hour + snooze_duration
        if latest_alert:
            latest_alert.status = "SNOOZED"
            latest_alert.snoozed_until_hour = snooze_until
            latest_alert.action_timestamp = now
            latest_alert.action_note = f"Snoozed for {snooze_duration}h"
        note_txt = f"Alert snoozed for {snooze_duration} hours until simulation hour {snooze_until:.0f}."

    elif action_lower == "false_alarm":
        pt.alert_status = "FALSE_ALARM"
        if latest_alert:
            latest_alert.status = "FALSE_ALARM"
            latest_alert.action_timestamp = now
            latest_alert.action_note = req.note_content or "Marked as false alarm by clinician"
        note_txt = f"Alert marked as false alarm: {req.note_content or 'Vitals artifact or transient non-septic etiology.'}"

    elif action_lower == "add_note":
        note_txt = req.note_content or "Routine clinical note charted."
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")

    # Add clinical note entry
    new_note = ClinicalNote(
        patient_id=pt.id,
        author=req.author or "Staff Clinician",
        sim_hour=pt.current_sim_hour,
        note_type=req.note_type or "Bedside Action",
        content=note_txt
    )
    db.add(new_note)
    db.commit()

    return {"status": "success", "alert_status": pt.alert_status, "note": note_txt}
