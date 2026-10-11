from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database import get_db, Base, engine
from backend.app.models.patient import Patient, VitalRecord, DatasetMeta
from backend.app.models.ml_model import ModelRegistry
from backend.app.models.alert import AlertEvent, ClinicalNote
from backend.app.models.settings import SystemSetting
from backend.app.services.seed_service import seed_database_if_empty
from backend.app.pipeline.psv_importer import MIMIC_DISCLAIMER_NOTE

router = APIRouter(prefix="/api/settings", tags=["settings"])

class UpdateSettingsRequest(BaseModel):
    cooldown_hours: Optional[float] = 4.0
    consecutive_hours: Optional[int] = 1
    escalation_delta: Optional[float] = 0.15
    simulation_speed: Optional[float] = 5.0
    temperature_unit: Optional[str] = "C" # "C" or "F"
    blood_pressure_unit: Optional[str] = "mmHg"

class ResetAppRequest(BaseModel):
    confirm_reset: bool

DEFAULT_SETTINGS = {
    "cooldown_hours": 4.0,
    "consecutive_hours": 1,
    "escalation_delta": 0.15,
    "simulation_speed": 5.0,
    "temperature_unit": "C",
    "blood_pressure_unit": "mmHg"
}

@router.get("")
def get_settings(db: Session = Depends(get_db)):
    settings_records = db.query(SystemSetting).all()
    s_map = DEFAULT_SETTINGS.copy()
    for s in settings_records:
        if s.value_float is not None:
            s_map[s.key] = s.value_float
        elif s.value_int is not None:
            s_map[s.key] = s.value_int
        elif s.value_str is not None:
            s_map[s.key] = s.value_str

    return s_map

@router.post("")
def update_settings(req: UpdateSettingsRequest, db: Session = Depends(get_db)):
    updates = req.dict(exclude_unset=True)
    for key, val in updates.items():
        record = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not record:
            record = SystemSetting(key=key)
            db.add(record)
        if isinstance(val, float):
            record.value_float = val
        elif isinstance(val, int):
            record.value_int = val
        elif isinstance(val, str):
            record.value_str = val

    # Also sync cooldown to active model if changed
    if "cooldown_hours" in updates or "consecutive_hours" in updates or "escalation_delta" in updates:
        active_m = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first()
        if active_m:
            if "cooldown_hours" in updates:
                active_m.cooldown_hours = updates["cooldown_hours"]
            if "consecutive_hours" in updates:
                active_m.consecutive_hours = updates["consecutive_hours"]
            if "escalation_delta" in updates:
                active_m.escalation_delta = updates["escalation_delta"]

    db.commit()
    return {"status": "success", "settings": updates}

@router.post("/reset")
def reset_application(req: ResetAppRequest, db: Session = Depends(get_db)):
    if not req.confirm_reset:
        raise HTTPException(status_code=400, detail="Confirmation required to reset application.")

    # Drop all data and recreate tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Re-seed with clean default cohort and baseline model
    seed_database_if_empty()

    return {"status": "success", "message": "Application database successfully reset and re-seeded."}

@router.get("/about")
def get_about_documentation():
    return {
        "title": "SepsisWatch: ICU Early Warning System",
        "version": "1.0.0 (Research Prototype)",
        "disclaimer": "Research prototype only. Not certified for clinical diagnostic use.",
        "sepsis_3_definition": (
            "Sepsis is defined under Sepsis-3 (Singer et al., JAMA 2016) as life-threatening organ dysfunction "
            "caused by a dysregulated host response to infection. Clinically operationalized in ICU settings as an acute "
            "change in total SOFA score >= 2 points consequent to infection (identified via blood cultures and antibiotic administration)."
        ),
        "prediction_horizon": (
            "The model predicts sepsis onset within a forward-looking 6-hour window: target = 1 if onset in (t, t + 6h]. "
            "This provides critical lead time for antimicrobial stewardship, fluid resuscitation, and blood cultures "
            "prior to irreversible septic shock."
        ),
        "alarm_fatigue_philosophy": (
            "Hospital alerting systems like the Epic Sepsis Model (Wong et al., JAMA Int Med 2021) have suffered from "
            "massive false positive rates, alerting on large proportions of uninfected patients and causing clinician alert desensitization. "
            "SepsisWatch treats alarm burden as a first-class optimization metric: combining Platt/isotonic calibration, "
            "F-beta precision-recall threshold optimization, post-alert cooldown windows (4h default), and persistence rules."
        ),
        "mimic_compliance": MIMIC_DISCLAIMER_NOTE,
        "scope_limitations": [
            "Adult ICU inpatients only (pediatric and neonatal physiology out of scope).",
            "Non-ICU general ward alerting is out of scope due to vastly different monitoring cadences.",
            "Alerting only: treatment, antibiotic selection, and fluid dosing recommendations are strictly out of scope.",
            "Models require validation against external prospective cohorts before any clinical translation."
        ]
    }
