from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base

class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    hour = Column(Integer, index=True)
    risk_score = Column(Float)
    threshold = Column(Float)
    model_name = Column(String, default="Active Model")
    status = Column(String, default="NEW") # NEW, ACKNOWLEDGED, SNOOZED, FALSE_ALARM, CONFIRMED
    snoozed_until_hour = Column(Float, nullable=True)
    action_note = Column(Text, nullable=True)
    action_timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="alerts")


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    author = Column(String, default="Staff Clinician")
    sim_hour = Column(Integer, default=0)
    note_type = Column(String, default="Observation") # "Observation", "Alert Review", "Intervention"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="notes")
