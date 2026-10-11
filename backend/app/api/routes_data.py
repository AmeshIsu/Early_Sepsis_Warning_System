import json
import zipfile
import io
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.patient import Patient, VitalRecord, DatasetMeta
from backend.app.pipeline.generator import generate_synthetic_cohort
from backend.app.pipeline.psv_importer import (
    parse_single_psv,
    parse_generic_csv,
    parse_psv_archive_or_files,
    MIMIC_DISCLAIMER_NOTE
)

router = APIRouter(prefix="/api/data", tags=["data"])

class GenerateCohortRequest(BaseModel):
    name: str = "Synthetic Cohort"
    num_patients: int = 200 # 100 to 5000
    sepsis_prevalence: float = 0.12 # 0.05 to 0.30
    seed: int = 42
    set_active: bool = True

@router.get("/mimic-note")
def get_mimic_notice():
    return {"note": MIMIC_DISCLAIMER_NOTE}

@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(DatasetMeta).order_by(DatasetMeta.created_at.desc()).all()
    res = []
    for d in datasets:
        res.append({
            "id": d.id,
            "name": d.name,
            "source_type": d.source_type,
            "patient_count": d.patient_count,
            "septic_count": d.septic_count,
            "total_hours": d.total_hours,
            "is_active": d.is_active,
            "description": d.description,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M")
        })
    return res

@router.post("/datasets/{id}/activate")
def activate_dataset(id: int, db: Session = Depends(get_db)):
    ds = db.query(DatasetMeta).filter(DatasetMeta.id == id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.query(DatasetMeta).update({DatasetMeta.is_active: False})
    ds.is_active = True
    db.commit()
    return {"status": "success", "active_dataset_id": ds.id, "name": ds.name}

@router.delete("/datasets/{id}")
def delete_dataset(id: int, db: Session = Depends(get_db)):
    ds = db.query(DatasetMeta).filter(DatasetMeta.id == id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    # Don't delete if it's the only dataset
    if db.query(DatasetMeta).count() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the sole remaining dataset.")

    db.delete(ds)
    # Ensure at least one dataset is active
    remaining = db.query(DatasetMeta).first()
    if remaining and not db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first():
        remaining.is_active = True
    db.commit()
    return {"status": "success", "deleted_id": id}

@router.get("/datasets/{id}/preview")
def preview_dataset(id: int, db: Session = Depends(get_db)):
    ds = db.query(DatasetMeta).filter(DatasetMeta.id == id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    patients = db.query(Patient).filter(Patient.dataset_id == ds.id).limit(5).all()
    preview_data = []
    for p in patients:
        sample_vitals = db.query(VitalRecord).filter(VitalRecord.patient_id == p.id).limit(6).all()
        preview_data.append({
            "patient_id": p.patient_id,
            "bed": p.bed,
            "age": p.age,
            "gender": "M" if p.gender == 1 else "F",
            "is_septic": p.is_septic,
            "onset_hour": p.sepsis_onset_hour,
            "vitals_sample": [
                {
                    "hour": v.hour,
                    "hr": v.hr,
                    "map": v.map,
                    "resp": v.resp,
                    "temp": v.temp,
                    "spo2": v.spo2,
                    "lactate": v.lactate,
                    "wbc": v.wbc,
                    "sirs": v.sirs_score,
                    "qsofa": v.qsofa_score,
                    "sofa": v.sofa_score
                } for v in sample_vitals
            ]
        })
    return {"dataset": ds.name, "preview": preview_data}

@router.post("/generate")
def generate_cohort_endpoint(req: GenerateCohortRequest, db: Session = Depends(get_db)):
    n_pts = max(10, min(5000, req.num_patients))
    prev = max(0.01, min(0.50, req.sepsis_prevalence))

    # Avoid duplicate name
    existing_count = db.query(DatasetMeta).filter(DatasetMeta.name == req.name).count()
    ds_name = req.name if existing_count == 0 else f"{req.name} ({existing_count + 1})"

    patients_raw = generate_synthetic_cohort(
        num_patients=n_pts,
        sepsis_prevalence=prev,
        seed=req.seed
    )

    septic_count = sum(1 for p in patients_raw if p["is_septic"])
    total_hours = sum(p["los_hours"] for p in patients_raw)

    if req.set_active:
        db.query(DatasetMeta).update({DatasetMeta.is_active: False})

    ds = DatasetMeta(
        name=ds_name,
        source_type="synthetic",
        patient_count=len(patients_raw),
        septic_count=septic_count,
        total_hours=total_hours,
        is_active=req.set_active,
        description=f"Generated synthetic cohort of {n_pts} adult ICU patients (prevalence: {prev*100:.1f}%, seed: {req.seed})"
    )
    db.add(ds)
    db.flush()

    for pt_data in patients_raw:
        p_orm = Patient(
            patient_id=pt_data["patient_id"],
            dataset_id=ds.id,
            age=pt_data["age"],
            gender=pt_data["gender"],
            unit=pt_data["unit"],
            bed=pt_data["bed"],
            los_hours=pt_data["los_hours"],
            is_septic=pt_data["is_septic"],
            sepsis_onset_hour=pt_data["sepsis_onset_hour"],
            current_sim_hour=0,
            current_risk_score=0.05,
            current_risk_level="LOW"
        )
        db.add(p_orm)
        db.flush()

        v_list = []
        for v in pt_data["vitals"]:
            v_orm = VitalRecord(
                patient_id=p_orm.id,
                hour=v["hour"],
                hr=v["hr"],
                sbp=v["sbp"],
                dbp=v["dbp"],
                map=v["map"],
                resp=v["resp"],
                temp=v["temp"],
                spo2=v["spo2"],
                lactate=v["lactate"],
                wbc=v["wbc"],
                creatinine=v["creatinine"],
                bilirubin=v["bilirubin"],
                sofa_score=v["sofa_score"],
                sirs_score=v["sirs_score"],
                qsofa_score=v["qsofa_score"],
                news_score=v["news_score"],
                sepsis_target_6h=v["sepsis_target_6h"],
                is_onset=v["is_onset"],
                predicted_risk=0.0
            )
            v_list.append(v_orm)
        db.bulk_save_objects(v_list)

    db.commit()
    return {"status": "success", "dataset_id": ds.id, "name": ds.name, "patient_count": ds.patient_count}

@router.post("/upload-psv")
async def upload_psv_endpoint(
    files: List[UploadFile] = File(...),
    dataset_name: str = Form("PhysioNet Ingested Cohort"),
    db: Session = Depends(get_db)
):
    """
    Ingests PhysioNet 2019 .psv files or a .zip archive of psv files.
    """
    parsed_files = {}

    for file in files:
        contents = await file.read()
        filename = file.filename or "unknown.psv"

        if filename.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(contents)) as z:
                for z_name in z.namelist():
                    if z_name.endswith(".psv") or z_name.endswith(".txt"):
                        with z.open(z_name) as zf:
                            parsed_files[z_name] = zf.read().decode("utf-8", errors="ignore")
        elif filename.endswith(".psv") or filename.endswith(".txt"):
            parsed_files[filename] = contents.decode("utf-8", errors="ignore")

    if not parsed_files:
        raise HTTPException(status_code=400, detail="No valid .psv or .zip files found.")

    patients_raw = parse_psv_archive_or_files(parsed_files)
    if not patients_raw:
        raise HTTPException(status_code=400, detail="Could not parse patient trajectories from provided files.")

    septic_count = sum(1 for p in patients_raw if p["is_septic"])
    total_hours = sum(p["los_hours"] for p in patients_raw)

    db.query(DatasetMeta).update({DatasetMeta.is_active: False})
    ds = DatasetMeta(
        name=dataset_name,
        source_type="psv_upload",
        patient_count=len(patients_raw),
        septic_count=septic_count,
        total_hours=total_hours,
        is_active=True,
        description=f"PhysioNet Challenge 2019 format cohort ({len(patients_raw)} patients)"
    )
    db.add(ds)
    db.flush()

    for pt_data in patients_raw:
        p_orm = Patient(
            patient_id=pt_data["patient_id"],
            dataset_id=ds.id,
            age=pt_data["age"],
            gender=pt_data["gender"],
            unit=pt_data["unit"],
            bed=pt_data["bed"],
            los_hours=pt_data["los_hours"],
            is_septic=pt_data["is_septic"],
            sepsis_onset_hour=pt_data["sepsis_onset_hour"],
            current_sim_hour=0,
            current_risk_score=0.05,
            current_risk_level="LOW"
        )
        db.add(p_orm)
        db.flush()

        v_list = []
        for v in pt_data["vitals"]:
            v_orm = VitalRecord(
                patient_id=p_orm.id,
                hour=v["hour"],
                hr=v["hr"],
                sbp=v["sbp"],
                dbp=v["dbp"],
                map=v["map"],
                resp=v["resp"],
                temp=v["temp"],
                spo2=v["spo2"],
                lactate=v["lactate"],
                wbc=v["wbc"],
                creatinine=v["creatinine"],
                bilirubin=v["bilirubin"],
                sofa_score=v["sofa_score"],
                sirs_score=v["sirs_score"],
                qsofa_score=v["qsofa_score"],
                news_score=v["news_score"],
                sepsis_target_6h=v["sepsis_target_6h"],
                is_onset=v["is_onset"],
                predicted_risk=0.0
            )
            v_list.append(v_orm)
        db.bulk_save_objects(v_list)

    db.commit()
    return {"status": "success", "dataset_id": ds.id, "patient_count": len(patients_raw)}

@router.post("/upload-csv")
async def upload_generic_csv_endpoint(
    file: UploadFile = File(...),
    column_mapping_json: str = Form(...),
    dataset_name: str = Form("Custom CSV Cohort"),
    db: Session = Depends(get_db)
):
    try:
        col_map = json.loads(column_mapping_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON column mapping")

    content = await file.read()
    csv_str = content.decode("utf-8", errors="ignore")

    patients_raw, summary = parse_generic_csv(csv_str, col_map, dataset_name)
    if not patients_raw:
        raise HTTPException(status_code=400, detail=f"No patients parsed. Errors: {summary.get('errors')}")

    septic_count = sum(1 for p in patients_raw if p["is_septic"])
    total_hours = sum(p["los_hours"] for p in patients_raw)

    db.query(DatasetMeta).update({DatasetMeta.is_active: False})
    ds = DatasetMeta(
        name=dataset_name,
        source_type="csv_upload",
        patient_count=len(patients_raw),
        septic_count=septic_count,
        total_hours=total_hours,
        is_active=True,
        description=f"Generic CSV mapped cohort ({len(patients_raw)} patients)"
    )
    db.add(ds)
    db.flush()

    for pt_data in patients_raw:
        p_orm = Patient(
            patient_id=pt_data["patient_id"],
            dataset_id=ds.id,
            age=pt_data["age"],
            gender=pt_data["gender"],
            unit=pt_data["unit"],
            bed=pt_data["bed"],
            los_hours=pt_data["los_hours"],
            is_septic=pt_data["is_septic"],
            sepsis_onset_hour=pt_data["sepsis_onset_hour"],
            current_sim_hour=0,
            current_risk_score=0.05,
            current_risk_level="LOW"
        )
        db.add(p_orm)
        db.flush()

        v_list = []
        for v in pt_data["vitals"]:
            v_orm = VitalRecord(
                patient_id=p_orm.id,
                hour=v["hour"],
                hr=v["hr"],
                sbp=v["sbp"],
                dbp=v["dbp"],
                map=v["map"],
                resp=v["resp"],
                temp=v["temp"],
                spo2=v["spo2"],
                lactate=v["lactate"],
                wbc=v["wbc"],
                creatinine=v["creatinine"],
                bilirubin=v["bilirubin"],
                sofa_score=v["sofa_score"],
                sirs_score=v["sirs_score"],
                qsofa_score=v["qsofa_score"],
                news_score=v["news_score"],
                sepsis_target_6h=v["sepsis_target_6h"],
                is_onset=v["is_onset"],
                predicted_risk=0.0
            )
            v_list.append(v_orm)
        db.bulk_save_objects(v_list)

    db.commit()
    return {"status": "success", "dataset_id": ds.id, "summary": summary}

@router.get("/quality-report")
def get_data_quality_report(db: Session = Depends(get_db)):
    active_dataset = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first()
    if not active_dataset:
        active_dataset = db.query(DatasetMeta).first()

    if not active_dataset:
        return {"features": [], "total_measurements": 0, "missingness_pct": {}}

    patients = db.query(Patient).filter(Patient.dataset_id == active_dataset.id).all()
    patient_ids = [p.id for p in patients]

    total_records = db.query(VitalRecord).filter(VitalRecord.patient_id.in_(patient_ids)).count()
    if total_records == 0:
        return {"features": [], "total_measurements": 0}

    features = ["hr", "map", "sbp", "dbp", "resp", "temp", "spo2", "lactate", "wbc", "creatinine", "bilirubin"]
    missing_data = []

    for f in features:
        col = getattr(VitalRecord, f)
        observed = db.query(VitalRecord).filter(VitalRecord.patient_id.in_(patient_ids), col != None).count()
        missing = total_records - observed
        pct = round((missing / total_records) * 100.0, 1)

        # Expected sampling interval in hours
        sampling_interval = 1.0
        if f in ["hr", "map", "resp", "spo2"]:
            sampling_interval = 1.2
        elif f in ["temp"]:
            sampling_interval = 2.4
        elif f in ["lactate", "wbc", "creatinine", "bilirubin"]:
            sampling_interval = 12.0

        missing_data.append({
            "feature": f.upper(),
            "observed_count": observed,
            "missing_count": missing,
            "missingness_pct": pct,
            "avg_sampling_interval_hours": sampling_interval
        })

    return {
        "dataset_name": active_dataset.name,
        "total_patients": len(patients),
        "total_patient_hours": total_records,
        "missingness": missing_data
    }
