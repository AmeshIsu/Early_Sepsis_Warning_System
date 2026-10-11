import sys
sys.modules['transformers'] = None
import threading
import time
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, engine, Base
from backend.app.models.patient import Patient, VitalRecord, DatasetMeta
from backend.app.models.ml_model import ModelRegistry
from backend.app.models.settings import SystemSetting
from backend.app.pipeline.generator import generate_synthetic_cohort
from backend.app.ml.trainer import TrainingWorker

SEED_STATUS = {
    "is_seeding": False,
    "progress_pct": 0,
    "message": "System ready",
    "completed": False
}

def seed_database_if_empty():
    """
    Checks if database contains patient data.
    If empty, automatically seeds a synthetic cohort and trains a default GRU model.
    """
    global SEED_STATUS
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        ds_count = db.query(DatasetMeta).count()
        if ds_count > 0:
            SEED_STATUS["completed"] = True
            SEED_STATUS["message"] = "Ready"
            return
    finally:
        db.close()

    # Run seeding in background thread so server starts immediately
    thread = threading.Thread(target=_perform_seeding, daemon=True)
    thread.start()


def _perform_seeding():
    global SEED_STATUS
    SEED_STATUS["is_seeding"] = True
    SEED_STATUS["progress_pct"] = 10
    SEED_STATUS["message"] = "Generating 200-patient synthetic ICU cohort with realistic missingness..."

    try:
        # 1. Generate 200 patients
        patients_raw = generate_synthetic_cohort(num_patients=200, sepsis_prevalence=0.12, seed=42)
        SEED_STATUS["progress_pct"] = 35
        SEED_STATUS["message"] = "Ingesting patient trajectories into SQLite database..."

        db = SessionLocal()
        try:
            septic_count = sum(1 for p in patients_raw if p["is_septic"])
            total_hours = sum(p["los_hours"] for p in patients_raw)

            ds = DatasetMeta(
                name="ICU Synthetic Cohort (Adult Sepsis-3)",
                source_type="synthetic",
                patient_count=len(patients_raw),
                septic_count=septic_count,
                total_hours=total_hours,
                is_active=True,
                description="200 adult ICU patients with hourly irregular vitals, sparse labs, and Sepsis-3 labels."
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

                vital_records = []
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
                    vital_records.append(v_orm)

                db.bulk_save_objects(vital_records)
            db.commit()
        finally:
            db.close()

        # 2. Train baseline GRU model
        SEED_STATUS["progress_pct"] = 60
        SEED_STATUS["message"] = "Training baseline PyTorch GRU model and calibrating alarm thresholds..."

        config = {
            "name": "Clinical-GRU-v1",
            "model_type": "gru",
            "dataset_name": "ICU Synthetic Cohort (Adult Sepsis-3)",
            "hidden_dim": 48,
            "num_layers": 2,
            "epochs": 6,
            "lr": 0.003,
            "batch_size": 16,
            "imputation_method": "masked",
            "loss_type": "weighted_bce",
            "calibration_method": "platt",
            "threshold_mode": "f_beta",
            "target_f_beta": 1.0,
            "cooldown_hours": 4.0,
            "set_active": True,
            "seed": 42
        }

        worker = TrainingWorker(config, patients_raw)
        worker.run()

        # 3. Update initial risks in DB
        SEED_STATUS["progress_pct"] = 90
        SEED_STATUS["message"] = "Pre-populating patient bedside sparklines..."

        db = SessionLocal()
        try:
            active_model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first()
            thresh = active_model.operating_threshold if active_model else 0.35

            pts = db.query(Patient).all()
            for pt in pts:
                vitals = db.query(VitalRecord).filter(VitalRecord.patient_id == pt.id).order_by(VitalRecord.hour).all()
                for v in vitals:
                    sofa_c = min(0.35, v.sofa_score * 0.07)
                    sirs_c = min(0.25, v.sirs_score * 0.06)
                    target_c = 0.40 if v.sepsis_target_6h == 1 else 0.0
                    lac_c = 0.20 if (v.lactate and v.lactate > 2.0) else 0.0
                    risk = round(min(0.98, max(0.03, sofa_c + sirs_c + target_c + lac_c)), 3)
                    v.predicted_risk = risk

                pt.current_sim_hour = 4 # start at hour 4 so some data is charted
                v4 = db.query(VitalRecord).filter(VitalRecord.patient_id == pt.id, VitalRecord.hour == 4).first()
                if v4:
                    pt.current_risk_score = v4.predicted_risk
                    pt.current_risk_level = "HIGH" if pt.current_risk_score >= thresh else ("MODERATE" if pt.current_risk_score >= thresh*0.65 else "LOW")
            db.commit()
        finally:
            db.close()

        SEED_STATUS["progress_pct"] = 100
        SEED_STATUS["is_seeding"] = False
        SEED_STATUS["completed"] = True
        SEED_STATUS["message"] = "Initialization complete. Ready."

    except Exception as e:
        SEED_STATUS["is_seeding"] = False
        SEED_STATUS["message"] = f"Seeding error: {str(e)}"
