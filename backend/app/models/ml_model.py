from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, JSON
from backend.app.database import Base

class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    model_type = Column(String) # "gru", "lstm", "transformer", "gbdt", "logistic"
    dataset_name = Column(String, default="default_cohort")
    hyperparameters = Column(JSON, default=dict)
    imputation_method = Column(String, default="masked") # "masked", "locf_decay", "patient_median", "pop_median"
    loss_type = Column(String, default="weighted_bce") # "weighted_bce", "focal"

    # Calibration settings
    calibration_method = Column(String, default="platt") # "none", "platt", "isotonic"
    calibration_params = Column(JSON, default=dict) # Platt slope/intercept or isotonic step points
    brier_score_raw = Column(Float, default=0.0)
    brier_score_calibrated = Column(Float, default=0.0)
    ece_raw = Column(Float, default=0.0)
    ece_calibrated = Column(Float, default=0.0)

    # Threshold & Alert Fatigue Settings
    operating_threshold = Column(Float, default=0.35)
    threshold_mode = Column(String, default="f_beta") # "f_beta", "target_sensitivity", "alert_cap", "manual"
    target_f_beta = Column(Float, default=1.0)
    cooldown_hours = Column(Float, default=4.0)
    consecutive_hours = Column(Integer, default=1)
    escalation_delta = Column(Float, default=0.15)

    # Performance Metrics
    auroc = Column(Float, default=0.0)
    auroc_ci_low = Column(Float, default=0.0)
    auroc_ci_high = Column(Float, default=0.0)
    auprc = Column(Float, default=0.0)
    auprc_ci_low = Column(Float, default=0.0)
    auprc_ci_high = Column(Float, default=0.0)
    sensitivity = Column(Float, default=0.0)
    specificity = Column(Float, default=0.0)
    ppv = Column(Float, default=0.0)
    npv = Column(Float, default=0.0)
    f1_score = Column(Float, default=0.0)

    # Alarm fatigue metrics
    alerts_per_patient_day = Column(Float, default=0.0)
    alerts_per_true_case = Column(Float, default=0.0)
    false_alarms_per_100_patient_days = Column(Float, default=0.0)
    median_lead_time_hours = Column(Float, default=0.0)
    pct_caught_3h_ahead = Column(Float, default=0.0)
    pct_caught_6h_ahead = Column(Float, default=0.0)
    alert_burden_score = Column(Float, default=0.0)

    # State & file
    is_active = Column(Boolean, default=False)
    file_path = Column(String, nullable=True) # Serialized weights or joblib
    training_duration_sec = Column(Float, default=0.0)
    training_history = Column(JSON, default=list) # [{epoch, train_loss, val_loss, val_auprc}]
    subgroup_metrics = Column(JSON, default=dict) # metrics by age group & sex
    created_at = Column(DateTime, default=datetime.utcnow)
