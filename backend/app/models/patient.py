from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

class DatasetMeta(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    source_type = Column(String, default="synthetic") # "synthetic", "psv_upload", "csv_upload"
    patient_count = Column(Integer, default=0)
    septic_count = Column(Integer, default=0)
    total_hours = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)
    description = Column(Text, nullable=True)

    patients = relationship("Patient", back_populates="dataset", cascade="all, delete-orphan")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, index=True) # e.g. "P001"
    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True)
    age = Column(Float)
    gender = Column(Integer) # 1: Male, 0: Female
    unit = Column(String, default="MICU") # MICU, SICU, CCU, CTICU
    bed = Column(String, default="BED-01")
    los_hours = Column(Integer, default=48)
    is_septic = Column(Boolean, default=False)
    sepsis_onset_hour = Column(Float, nullable=True) # None if not septic
    split = Column(String, default="train") # "train", "val", "test"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Dynamic simulation state
    current_sim_hour = Column(Integer, default=0)
    current_risk_score = Column(Float, default=0.0)
    current_risk_level = Column(String, default="LOW") # LOW, MODERATE, HIGH
    last_alert_hour = Column(Float, nullable=True)
    alert_status = Column(String, default="NONE") # NONE, ACTIVE, ACKNOWLEDGED, SNOOZED

    dataset = relationship("DatasetMeta", back_populates="patients")
    vitals = relationship("VitalRecord", back_populates="patient", cascade="all, delete-orphan", order_by="VitalRecord.hour")
    alerts = relationship("AlertEvent", back_populates="patient", cascade="all, delete-orphan")
    notes = relationship("ClinicalNote", back_populates="patient", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_patient_dataset_pid", "dataset_id", "patient_id"),
    )


class VitalRecord(Base):
    __tablename__ = "vital_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    hour = Column(Integer, index=True)

    # Vitals
    hr = Column(Float, nullable=True)
    sbp = Column(Float, nullable=True)
    dbp = Column(Float, nullable=True)
    map = Column(Float, nullable=True)
    resp = Column(Float, nullable=True)
    temp = Column(Float, nullable=True)
    spo2 = Column(Float, nullable=True)

    # Labs
    lactate = Column(Float, nullable=True)
    wbc = Column(Float, nullable=True)
    creatinine = Column(Float, nullable=True)
    bilirubin = Column(Float, nullable=True)

    # Baseline Clinical Scores
    sofa_score = Column(Float, default=0.0)
    sirs_score = Column(Integer, default=0)
    qsofa_score = Column(Integer, default=0)
    news_score = Column(Integer, default=0)

    # Sepsis target & onset indicator
    sepsis_target_6h = Column(Integer, default=0) # 1 if onset in (hour, hour + 6]
    is_onset = Column(Boolean, default=False)

    # Model predicted risk score
    predicted_risk = Column(Float, default=0.0)

    patient = relationship("Patient", back_populates="vitals")

    __table_args__ = (
        Index("ix_vital_pt_hour", "patient_id", "hour"),
    )
