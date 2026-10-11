from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.alert import AlertEvent, ClinicalNote
from backend.app.models.patient import Patient
from backend.app.services.export_service import generate_alerts_csv

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

class AlertActionRequest(BaseModel):
    action: str # "acknowledge", "snooze", "false_alarm", "confirm"
    snooze_hours: Optional[float] = 2.0
    note: Optional[str] = None
    author: Optional[str] = "Staff Clinician"

class BulkAlertActionRequest(BaseModel):
    alert_ids: List[int]
    action: str
    snooze_hours: Optional[float] = 2.0
    note: Optional[str] = None

@router.get("")
def list_alerts(
    status: Optional[str] = None, # ALL, NEW, ACKNOWLEDGED, SNOOZED, FALSE_ALARM, CONFIRMED
    unit: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(AlertEvent).join(Patient, AlertEvent.patient_id == Patient.id)

    if status and status.upper() != "ALL":
        query = query.filter(AlertEvent.status == status.upper())
    if unit and unit.upper() != "ALL":
        query = query.filter(Patient.unit == unit.upper())
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter((Patient.patient_id.ilike(search_fmt)) | (Patient.bed.ilike(search_fmt)))

    total = query.count()
    alerts = query.order_by(AlertEvent.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for a in alerts:
        p = a.patient
        items.append({
            "id": a.id,
            "patient_db_id": p.id if p else None,
            "patient_id": p.patient_id if p else "UNKNOWN",
            "bed": p.bed if p else "-",
            "unit": p.unit if p else "-",
            "hour": a.hour,
            "risk_score": round(a.risk_score, 3),
            "threshold": round(a.threshold, 3),
            "model_name": a.model_name,
            "status": a.status,
            "snoozed_until_hour": a.snoozed_until_hour,
            "action_note": a.action_note,
            "action_timestamp": a.action_timestamp.strftime("%Y-%m-%d %H:%M:%S") if a.action_timestamp else None,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/{alert_id}/action")
def update_alert_action(alert_id: int, req: AlertActionRequest, db: Session = Depends(get_db)):
    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    act = req.action.lower()
    now = datetime.utcnow()

    if act == "acknowledge":
        alert.status = "ACKNOWLEDGED"
        alert.action_note = req.note or "Alert acknowledged"
    elif act == "snooze":
        alert.status = "SNOOZED"
        snooze_dur = req.snooze_hours or 2.0
        alert.snoozed_until_hour = alert.hour + snooze_dur
        alert.action_note = f"Snoozed for {snooze_dur}h"
    elif act == "false_alarm":
        alert.status = "FALSE_ALARM"
        alert.action_note = req.note or "Marked as false alarm"
    elif act == "confirm":
        alert.status = "CONFIRMED"
        alert.action_note = req.note or "Confirmed sepsis suspicion"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    alert.action_timestamp = now

    # Also update patient status
    if alert.patient:
        alert.patient.alert_status = alert.status

    # Add clinical note
    if req.note:
        note_entry = ClinicalNote(
            patient_id=alert.patient_id,
            author=req.author or "Staff Clinician",
            sim_hour=alert.hour,
            note_type="Alert Audit Action",
            content=f"Alert #{alert.id} ({alert.status}): {req.note}"
        )
        db.add(note_entry)

    db.commit()
    return {"status": "success", "alert_status": alert.status}


@router.post("/bulk-action")
def bulk_alert_action(req: BulkAlertActionRequest, db: Session = Depends(get_db)):
    alerts = db.query(AlertEvent).filter(AlertEvent.id.in_(req.alert_ids)).all()
    act = req.action.lower()
    now = datetime.utcnow()

    for a in alerts:
        if act == "acknowledge":
            a.status = "ACKNOWLEDGED"
            a.action_note = req.note or "Bulk acknowledged"
        elif act == "snooze":
            a.status = "SNOOZED"
            snooze_dur = req.snooze_hours or 2.0
            a.snoozed_until_hour = a.hour + snooze_dur
            a.action_note = f"Bulk snoozed for {snooze_dur}h"
        elif act == "false_alarm":
            a.status = "FALSE_ALARM"
            a.action_note = req.note or "Bulk false alarm"
        elif act == "confirm":
            a.status = "CONFIRMED"
            a.action_note = req.note or "Bulk confirmed"
        a.action_timestamp = now
        if a.patient:
            a.patient.alert_status = a.status

    db.commit()
    return {"status": "success", "updated_count": len(alerts)}


@router.get("/export/csv")
def export_alerts_csv_file(db: Session = Depends(get_db)):
    alerts = db.query(AlertEvent).join(Patient).order_by(AlertEvent.id.desc()).all()
    export_rows = []
    for a in alerts:
        p = a.patient
        export_rows.append({
            "id": a.id,
            "patient_id": p.patient_id if p else "-",
            "bed": p.bed if p else "-",
            "unit": p.unit if p else "-",
            "hour": a.hour,
            "risk_score": a.risk_score,
            "threshold": a.threshold,
            "model_name": a.model_name,
            "status": a.status,
            "snoozed_until_hour": a.snoozed_until_hour,
            "action_note": a.action_note,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    csv_data = generate_alerts_csv(export_rows)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sepsiswatch_alerts.csv"}
    )
