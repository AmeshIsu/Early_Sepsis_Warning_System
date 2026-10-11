export interface VitalsSummary {
  hr: number | null;
  map: number | null;
  sbp: number | null;
  dbp: number | null;
  resp: number | null;
  temp: number | null;
  spo2: number | null;
  lactate: number | null;
  wbc: number | null;
  creatinine?: number | null;
  bilirubin?: number | null;
  sofa_score: number;
  sirs_score: number;
  qsofa_score: number;
  news_score: number;
}

export interface PatientOverview {
  id: number;
  patient_id: string;
  bed: string;
  unit: string;
  age: number;
  gender: string;
  current_sim_hour: number;
  current_risk_score: number;
  current_risk_level: 'LOW' | 'MODERATE' | 'HIGH';
  alert_status: 'NONE' | 'ACTIVE' | 'ACKNOWLEDGED' | 'SNOOZED' | 'FALSE_ALARM' | 'CONFIRMED';
  last_alert_hour: number | null;
  is_septic: boolean;
  sepsis_onset_hour: number | null;
  sparkline: number[];
  vitals: VitalsSummary;
}

export interface PatientDetailTimelineRecord {
  hour: number;
  hr: number | null;
  sbp: number | null;
  dbp: number | null;
  map: number | null;
  resp: number | null;
  temp: number | null;
  spo2: number | null;
  predicted_risk: number;
  threshold: number;
  sofa_score: number;
  sirs_score: number;
  qsofa_score: number;
  news_score: number;
  sepsis_target_6h: number;
  is_onset: boolean;
  alert_fired: boolean;
}

export interface LabHistoryRecord {
  hour: number;
  lactate: number | null;
  wbc: number | null;
  creatinine: number | null;
  bilirubin: number | null;
  sofa_score: number;
}

export interface AlertRecord {
  id: number;
  patient_db_id?: number;
  patient_id?: string;
  bed?: string;
  unit?: string;
  hour: number;
  risk_score: number;
  threshold: number;
  model_name: string;
  status: string;
  snoozed_until_hour: number | null;
  action_note: string | null;
  action_timestamp: string | null;
  created_at: string;
}

export interface ClinicalNoteRecord {
  id: number;
  author: string;
  sim_hour: number;
  note_type: string;
  content: string;
  created_at: string;
}

export interface FeatureDriver {
  feature: string;
  name: string;
  contribution_pct: number;
  current_value: number;
  unit: string;
  direction: 'elevated' | 'depressed';
  normal_range: string;
}

export interface ExplainabilityData {
  risk_score: number;
  drivers: FeatureDriver[];
  clinical_summary: string;
  summary_bullets: string[];
}

export interface DatasetMetaItem {
  id: number;
  name: string;
  source_type: string;
  patient_count: number;
  septic_count: number;
  total_hours: number;
  is_active: boolean;
  description: string;
  created_at: string;
}

export interface ModelRegistryItem {
  id: number;
  name: string;
  model_type: string;
  dataset_name: string;
  hyperparameters: Record<string, any>;
  imputation_method: string;
  loss_type: string;
  calibration_method: string;
  operating_threshold: number;
  threshold_mode: string;
  cooldown_hours: number;
  auroc: number;
  auroc_ci_low: number;
  auroc_ci_high: number;
  auprc: number;
  auprc_ci_low: number;
  auprc_ci_high: number;
  sensitivity: number;
  ppv: number;
  f1_score: number;
  alerts_per_patient_day: number;
  alerts_per_true_case: number;
  median_lead_time_hours: number;
  pct_caught_3h_ahead: number;
  pct_caught_6h_ahead: number;
  alert_burden_score: number;
  training_duration_sec: number;
  is_active: boolean;
  created_at: string;
}

export interface CalibrationData {
  model_id: number;
  model_name: string;
  calibration_method: string;
  operating_threshold: number;
  cooldown_hours: number;
  brier_score_raw: number;
  brier_score_calibrated: number;
  ece_raw: number;
  ece_calibrated: number;
  reliability_raw: Array<{ bin: number; confidence: number; accuracy: number; count: number }>;
  reliability_calibrated: Array<{ bin: number; confidence: number; accuracy: number; count: number }>;
  current_metrics: Record<string, any>;
  pr_curve: Array<Record<string, any>>;
}

export interface SimulationState {
  is_running: boolean;
  speed: number;
  current_hour: number;
  threshold: number;
  kpi: {
    total_patients: number;
    active_alerts: number;
    alerts_today: number;
    avg_lead_time: number;
    alert_burden: number;
  };
  patients: PatientOverview[];
}
