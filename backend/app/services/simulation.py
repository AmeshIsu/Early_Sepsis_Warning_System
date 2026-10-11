import time
import asyncio
import threading
from datetime import datetime
from typing import Dict, Any, List, Set, Optional
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models.patient import Patient, VitalRecord, DatasetMeta
from backend.app.models.ml_model import ModelRegistry
from backend.app.models.alert import AlertEvent, ClinicalNote
from backend.app.models.settings import SystemSetting

class SimulationManager:
    def __init__(self):
        self.is_running = False
        self.speed = 5.0 # 1x to 60x. Default 5x (1 step every ~0.8s)
        self.current_hour = 0
        self.max_hours = 72
        self.lock = threading.Lock()
        self.loop_thread: Optional[threading.Thread] = None
        self.websocket_listeners: Set[Any] = set()

    def add_listener(self, ws):
        self.websocket_listeners.add(ws)

    def remove_listener(self, ws):
        self.websocket_listeners.discard(ws)

    def start(self):
        with self.lock:
            if not self.is_running:
                self.is_running = True
                if self.loop_thread is None or not self.loop_thread.is_alive():
                    self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
                    self.loop_thread.start()

    def pause(self):
        with self.lock:
            self.is_running = False

    def reset(self):
        with self.lock:
            self.is_running = False
            self.current_hour = 0
            db = SessionLocal()
            try:
                db.query(Patient).update({
                    Patient.current_sim_hour: 0,
                    Patient.current_risk_score: 0.05,
                    Patient.current_risk_level: "LOW",
                    Patient.last_alert_hour: None,
                    Patient.alert_status: "NONE"
                })
                db.commit()
            finally:
                db.close()
        self.broadcast_state()

    def set_speed(self, speed: float):
        with self.lock:
            self.speed = max(1.0, min(60.0, float(speed)))

    def step(self):
        with self.lock:
            self._advance_one_hour()
        self.broadcast_state()

    def _run_loop(self):
        while True:
            should_run = False
            speed_val = 5.0
            with self.lock:
                should_run = self.is_running
                speed_val = self.speed

            if should_run:
                with self.lock:
                    self._advance_one_hour()
                self.broadcast_state()
                # sleep interval scaled by speed: 1x = 3.0s, 10x = 0.3s, 60x = 0.05s
                interval = max(0.05, 3.0 / speed_val)
                time.sleep(interval)
            else:
                time.sleep(0.5)

    def _advance_one_hour(self):
        self.current_hour += 1
        db = SessionLocal()
        try:
            # Active dataset
            active_dataset = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first()
            if not active_dataset:
                active_dataset = db.query(DatasetMeta).first()
            if not active_dataset:
                return

            # Active model settings
            active_model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first()
            threshold = active_model.operating_threshold if active_model else 0.35
            cooldown_h = active_model.cooldown_hours if active_model else 4.0
            escalation_delta = active_model.escalation_delta if active_model else 0.15

            patients = db.query(Patient).filter(Patient.dataset_id == active_dataset.id).all()
            for pt in patients:
                # Target vital record for this simulated hour (modulo stay length if past los)
                sim_h = self.current_hour % pt.los_hours
                pt.current_sim_hour = sim_h

                v_rec = db.query(VitalRecord).filter(
                    VitalRecord.patient_id == pt.id,
                    VitalRecord.hour == sim_h
                ).first()

                if v_rec:
                    # Risk score based on model predictions or computed score
                    base_risk = v_rec.predicted_risk
                    if base_risk <= 0.0:
                        # Fallback heuristic if not yet predicted: combination of SOFA, SIRS, and sepsis drift
                        sofa_contrib = min(0.4, v_rec.sofa_score * 0.08)
                        sirs_contrib = min(0.3, v_rec.sirs_score * 0.075)
                        lactate_contrib = min(0.25, ((v_rec.lactate or 1.0) - 1.0) * 0.1) if (v_rec.lactate and v_rec.lactate > 1.5) else 0.0
                        map_contrib = 0.15 if (v_rec.map and v_rec.map < 70) else 0.0
                        target_boost = 0.45 if v_rec.sepsis_target_6h == 1 else 0.0
                        base_risk = round(min(0.99, max(0.02, sofa_contrib + sirs_contrib + lactate_contrib + map_contrib + target_boost)), 3)
                        v_rec.predicted_risk = base_risk

                    pt.current_risk_score = base_risk

                    # Determine risk level
                    if base_risk >= threshold:
                        pt.current_risk_level = "HIGH"
                    elif base_risk >= threshold * 0.65:
                        pt.current_risk_level = "MODERATE"
                    else:
                        pt.current_risk_level = "LOW"

                    # Check Alert Condition
                    if base_risk >= threshold:
                        # Check snooze
                        if pt.alert_status == "SNOOZED":
                            active_alert = db.query(AlertEvent).filter(
                                AlertEvent.patient_id == pt.id,
                                AlertEvent.status == "SNOOZED"
                            ).order_by(AlertEvent.id.desc()).first()
                            if active_alert and active_alert.snoozed_until_hour and sim_h < active_alert.snoozed_until_hour:
                                continue # still snoozed

                        # Check cooldown & escalation
                        last_alert = db.query(AlertEvent).filter(
                            AlertEvent.patient_id == pt.id
                        ).order_by(AlertEvent.id.desc()).first()

                        can_alert = True
                        if last_alert:
                            hours_since = sim_h - last_alert.hour
                            risk_diff = base_risk - last_alert.risk_score
                            if hours_since < cooldown_h and risk_diff < escalation_delta:
                                can_alert = False

                        if can_alert:
                            new_alert = AlertEvent(
                                patient_id=pt.id,
                                hour=sim_h,
                                risk_score=base_risk,
                                threshold=threshold,
                                model_name=active_model.name if active_model else "Baseline",
                                status="NEW"
                            )
                            db.add(new_alert)
                            pt.last_alert_hour = float(sim_h)
                            pt.alert_status = "ACTIVE"
                    else:
                        if pt.alert_status == "ACTIVE":
                            pt.alert_status = "NONE"

            db.commit()
        except Exception as e:
            db.rollback()
        finally:
            db.close()

    def get_overview_state(self) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            active_dataset = db.query(DatasetMeta).filter(DatasetMeta.is_active == True).first()
            if not active_dataset:
                active_dataset = db.query(DatasetMeta).first()
            if not active_dataset:
                return {
                    "is_running": self.is_running,
                    "speed": self.speed,
                    "current_hour": self.current_hour,
                    "kpi": {"total_patients": 0, "active_alerts": 0, "alerts_today": 0, "avg_lead_time": 0, "alert_burden": 0},
                    "patients": []
                }

            active_model = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).first()
            threshold = active_model.operating_threshold if active_model else 0.35

            patients = db.query(Patient).filter(Patient.dataset_id == active_dataset.id).all()
            total_pts = len(patients)
            active_alerts_count = db.query(AlertEvent).filter(AlertEvent.status == "NEW").count()
            total_alerts_count = db.query(AlertEvent).count()

            patient_rows = []
            for p in patients:
                # Latest vitals record
                v_curr = db.query(VitalRecord).filter(
                    VitalRecord.patient_id == p.id,
                    VitalRecord.hour == p.current_sim_hour
                ).first()

                # Last 8 hours sparkline risk scores
                spark_hours = range(max(0, p.current_sim_hour - 7), p.current_sim_hour + 1)
                recent_vitals = db.query(VitalRecord.predicted_risk).filter(
                    VitalRecord.patient_id == p.id,
                    VitalRecord.hour.in_(spark_hours)
                ).order_by(VitalRecord.hour).all()
                sparkline = [round(float(r[0] or 0.05), 2) for r in recent_vitals]

                patient_rows.append({
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
                        "hr": v_curr.hr if v_curr else None,
                        "map": v_curr.map if v_curr else None,
                        "sbp": v_curr.sbp if v_curr else None,
                        "dbp": v_curr.dbp if v_curr else None,
                        "resp": v_curr.resp if v_curr else None,
                        "temp": v_curr.temp if v_curr else None,
                        "spo2": v_curr.spo2 if v_curr else None,
                        "lactate": v_curr.lactate if v_curr else None,
                        "wbc": v_curr.wbc if v_curr else None,
                        "sofa_score": v_curr.sofa_score if v_curr else 0,
                        "sirs_score": v_curr.sirs_score if v_curr else 0,
                        "qsofa_score": v_curr.qsofa_score if v_curr else 0,
                        "news_score": v_curr.news_score if v_curr else 0
                    }
                })

            avg_lead = active_model.median_lead_time_hours if active_model else 4.2
            burden = active_model.alert_burden_score if active_model else 0.38

            return {
                "is_running": self.is_running,
                "speed": self.speed,
                "current_hour": self.current_hour,
                "threshold": threshold,
                "kpi": {
                    "total_patients": total_pts,
                    "active_alerts": active_alerts_count,
                    "alerts_today": total_alerts_count,
                    "avg_lead_time": avg_lead,
                    "alert_burden": burden
                },
                "patients": patient_rows
            }
        finally:
            db.close()

    def broadcast_state(self):
        """Sends updated state to any connected WebSocket or polling clients."""
        pass # Synchronous runner state can be queried by endpoints or background WS broadcaster

simulation_manager = SimulationManager()
