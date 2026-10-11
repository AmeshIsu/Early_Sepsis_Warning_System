# SepsisWatch: ICU Early Warning System

> **A clinical research and portfolio early warning system for adult intensive care units (ICUs) that ingests irregular, streaming vitals and labs, produces a continuously updated 6-hour-ahead sepsis risk trajectory, and evaluates models where alarm fatigue is a first-class optimization metric.**

---

## 1. Clinical Context & Motivation

### The Sepsis Problem
Sepsis is the leading cause of in-hospital mortality, accounting for over 1 in 3 hospital deaths in the United States and over 11 million deaths worldwide annually. Early clinical signs of sepsis (subtle heart rate elevation, trending hypotension, rising serum lactate, and widening respiratory rate) are frequently missed in noisy intensive care monitor telemetry. For every hour of delayed antimicrobial therapy after the onset of septic shock, patient mortality increases by approximately 7.6% (Kumar et al., *Crit Care Med* 2006).

### Limitations of Existing Systems
1. **Rule-Based Screening (SIRS / qSOFA / NEWS)**: Fixed-threshold scores suffer from severe false-positive rates (low positive predictive value ~15-20%), lack personalization against patient baselines, and frequently sound alerts after irreversible organ damage has already begun.
2. **Academic Binary Classification**: Many academic machine learning publications treat sepsis as static binary classification ("did the patient develop sepsis during their stay?"), ignoring the continuous, sequential nature of bedside monitoring.
3. **The Epic Sepsis Model (ESM) Cautionary Tale**: In external prospective evaluations (Wong et al., *JAMA Intern Med* 2021), the proprietary Epic Sepsis Model missed over 67% of sepsis cases while sounding alerts on 18% of all hospitalized patients, creating massive alert fatigue that led clinicians to ignore warnings.

### SepsisWatch Design Principles
- **6-Hour Prediction Horizon**: Predicts sepsis onset within $(t, t+6\text{h}]$, giving clinicians sufficient lead time for blood cultures, antibiotic administration, and fluid resuscitation prior to septic shock.
- **Alarm Fatigue as a First-Class Metric**: Evaluates alerting burden via alerts per patient-day, alerts per true positive case, positive predictive value (PPV), median lead time, and composite alert burden score.
- **Suppressing Spurious Alerts**: Incorporates post-alert cooldown windows (4 hours default) and persistence rules (consecutive hourly confirmations) to eliminate duplicate alarms.
- **Adult ICU Scope Only**: Strictly designed for adult ICUs using Sepsis-3 definitions (acute change in SOFA score $\ge 2$ points consequent to infection). Pediatric and general ward care are out of scope. Alerts only; treatment recommendations are never generated.

---

## 2. System Architecture

```
                          [ ICU Patient Data Sources ]
                         /                            \
        Synthetic Cohort Generator          PhysioNet Challenge 2019 PSV / CSV
          (100 - 5000 patients)                  (Upload & Ingestion)
                         \                            /
                          v                          v
                      [ SQLite Database (SQLAlchemy Core) ]
                                      |
                     [ Data Pipeline & Resampling Engine ]
                       - 1-hour regular grid resampling
                       - Observation masks & elapsed delta-t features
                       - Imputation: Masked (default), LOCF decay, Medians
                       - Leakage-safe 6h forward windowing: (t, t+6h]
                       - Strict patient-level train/val/test splits (0% overlap)
                                      |
                     [ Modeling Layer & Baselines ]
       +--------------------+---------------------+--------------------+
       |                    |                     |                    |
   PyTorch GRU/LSTM     Temporal Transformer   Windowed GBDT/LR   Rule Baselines
   (Rolling continuous)  (Causal attention)   (Feature summary)  (SIRS, qSOFA, NEWS)
       +--------------------+---------------------+--------------------+
                                      |
                      [ Validation Calibration & Alerting ]
                       - Platt scaling (sigmoidal) / Isotonic regression
                       - Precision-Recall threshold optimization (F-beta, target sens, cap)
                       - Post-alert cooldown window & persistence filtering
                                      |
               +----------------------+----------------------+
               |                                             |
     [ REST API (FastAPI) ]                       [ WebSocket Hub ]
       - Telemetry & bed endpoints                  - Live bedside monitor stream
       - Background training worker                 - Playback speed (1x - 60x)
       - Evaluation & bootstrap CIs                 - Real-time alert triggers
       - PDF & CSV clinical export                  - Explainability drivers
               |                                             |
               +----------------------+----------------------+
                                      |
                      [ Frontend: React + TypeScript + Vite ]
       - 1. Command Center (ICU Bed Grid, Sparklines, Stream Controls)
       - 2. Patient Monitor (High-Res Vitals, Trajectory, Explainability, Actions)
       - 3. Alerts Center (Audit Log, Snooze, False Alarm, Bulk Actions, CSV)
       - 4. Data Manager (Synthetic Generator, PSV Upload, Missingness Heatmap)
       - 5. Model Lab (Architecture Controls, Live Loss Curves, Model Registry)
       - 6. Calibration & Thresholds (Reliability Diagrams, PR Slider, Apply)
       - 7. Evaluation & Benchmarks (Benchmark Table, ROC/PR Curves, PDF Export)
       - 8. Settings & Methodology (Cooldown Rules, Units, Reset, Sepsis-3 Docs)
```

---

## 3. Technology Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn, SQLite via SQLAlchemy Core, PyTorch (CPU-compatible), scikit-learn, pandas, numpy, ReportLab (PDF generation), WebSockets.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS v4, Lucide-react, Recharts, React Router.
- **Testing**: PyTest for leakage validation, patient-level splits, clinical baseline calculations, and calibration.

---

## 4. Quick Start & One-Command Launch

### Prerequisites
- Python 3.11+
- Node.js v18+ and npm

### Windows (One-Click Launch)
Double-click `run.bat` or execute in PowerShell / Command Prompt:
```cmd
run.bat
```

### Linux / macOS
Make executable and run:
```bash
chmod +x run.sh
./run.sh
```

### Accessing the Web Application
Once launched:
- **Frontend User Interface**: [http://localhost:5173/](http://localhost:5173/)
- **Backend Interactive API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Database**: Automatically created at `backend/sepsiswatch.db`

*Note: On first startup, SepsisWatch automatically generates a 200-patient synthetic ICU cohort and trains a default PyTorch GRU model in the background. The dashboard will be populated within seconds, with a live progress indicator.*

---

## 5. Core Application Pages & Features

### 1. Command Center (ICU Overview)
- **Live Bed Grid**: Displays all ICU patients with bed number, unit (MICU, SICU, CCU, CTICU), current 6h sepsis risk score, risk level chip (`LOW`, `MODERATE`, `HIGH`), and rolling 8-hour sparkline.
- **KPI Metrics**: Census monitored, active pending alerts, alerts today, median lead time, and composite alert burden score.
- **Simulation Replay Controls**: Start, pause, step forward, and reset simulation clock. Replay speed selectable from 1x to 60x.
- **Search & Filters**: Search patient IDs or bed numbers; filter by risk level, ICU unit, or alert status; sort by highest risk or bed order.

### 2. Patient Monitor
- **Multi-Panel Trajectory Charts**: Continuous 6-hour risk score timeline overlaid against operating threshold, true Sepsis-3 onset marker, and alert firing points.
- **Physiological Vitals Stream**: Replays heart rate, mean arterial pressure, respiratory rate, and temperature.
- **SOFA Score & Labs Table**: Displays component breakdown (respiratory, cardiovascular, renal, liver) alongside serum lactate, WBC, and creatinine.
- **Explainability Engine**: Feature attribution breakdown displaying top physiological drivers (e.g. elevated lactate, dropping MAP) with contribution percentages and a clinical summary.
- **Bedside Clinical Actions**: Clinicians can Acknowledge, Snooze (1h, 2h, 4h), Mark False Alarm, or add custom clinical observation notes, logging timestamped entries to the audit trail.

### 3. Alerts Center
- Complete chronological audit log of all system alert events.
- Filter by status (`NEW`, `ACKNOWLEDGED`, `SNOOZED`, `FALSE_ALARM`, `CONFIRMED`) or unit.
- Bulk actions: select multiple alerts to bulk acknowledge or bulk snooze.
- CSV export button downloading full alert history.

### 4. Data Manager
- **Synthetic Cohort Generator**: Configurable patient count (100 to 5,000), sepsis prevalence (5% to 30%), and random seed.
- **Real-World Importer**: Upload PhysioNet Challenge 2019 format `.psv` files or `.zip` archives, or generic CSV files with column mapping.
- **Data Quality Report**: Missingness heatmap displaying charted percentages and average drawing intervals per feature.
- **MIMIC Credentialing Notice**: Prominent documentation noting that protected health datasets (MIMIC-III/IV) require PhysioNet credentialing and Data Use Agreements.

### 5. Model Lab
- **Training Form**: Configure model architecture (GRU, LSTM, Temporal Transformer, GBDT, Logistic Regression), hidden dimensions, layers, epochs, learning rate, batch size, loss type (Weighted BCE, Focal Loss), and imputation strategy.
- **Live Metric Curves**: Live stream of training loss, validation loss, and validation AUPRC.
- **Model Registry**: Compare saved models side-by-side on AUROC (95% CI), AUPRC, alerts per patient-day, lead time, and alert burden score.

### 6. Calibration & Threshold Optimization
- **Probability Calibration**: Platt scaling and Isotonic regression fit strictly on the validation set. Reliability diagrams with decile bins, Brier score, and Expected Calibration Error (ECE) before vs after.
- **Precision-Recall Optimization Modes**:
  1. *Maximize F-Beta*: User sets $\beta$ (e.g., $\beta=1.0$ or $\beta=2.0$ prioritizing recall).
  2. *Target Sensitivity*: Meet target sensitivity (e.g., 85%) while minimizing alert frequency.
  3. *Cap Alerts/Patient-Day*: Restrict alerts to manageable clinician burden while maximizing sensitivity.
  4. *Manual Slider*: Real-time recalculation of alarm metrics across the threshold spectrum.
- **Apply to Active Model**: Persists operating threshold and cooldown parameters to the live monitoring pipeline.

### 7. Evaluation & Benchmarks
- **Head-to-Head Comparison Table**: Active ML model vs SIRS ($\ge 2$), qSOFA ($\ge 2$), and NEWS ($\ge 5$) evaluated under identical 4-hour cooldown constraints.
- **Discrimination & Diagnostics**: AUROC and AUPRC with 1,000-sample bootstrap 95% confidence intervals, ROC curve, PR curve, confusion matrix, and lead-time distribution histogram.
- **Demographic Fairness Analysis**: Subgroup performance breakdown across age bands (18-49, 50-64, 65-74, 75+) and biological sex.
- **Report Exports**: One-click download of full evaluation results as CSV and clinical research evaluation report as PDF.

### 8. Settings & Clinical Methodology
- Configure alert cooldown window, persistence rule, escalation delta, and clinical units.
- Complete clinical methodology documentation on Sepsis-3 definition, 6-hour prediction horizon, and alarm fatigue philosophy.
- Application reset button with confirmation modal.

---

## 6. Running Tests

Run the complete backend test suite:
```bash
python -m pytest backend/tests/ -v
```

Verified test coverage includes:
- `test_patient_level_split_no_overlap`: Proves 0% patient overlap across train, val, and test splits.
- `test_leakage_safe_windowing`: Proves features at time $t$ strictly use data at or before $t$, and targets adhere to $(t, t+6\text{h}]$.
- `test_sirs_calculation`, `test_qsofa_calculation`, `test_news_score`, `test_sofa_components`: Validates clinical scoring criteria.
- `test_ece_computation`, `test_platt_calibration`: Validates calibration metrics.
- `test_alarm_fatigue_cooldown`: Verifies alert suppression within cooldown windows.

---

## 7. Known Scope & Research Limitations

1. **Adult ICU Only**: Model was developed and calibrated exclusively for adult ICU patients. Pediatric and neonatal physiology exhibit fundamentally different vital patterns and are out of scope.
2. **Surveillance & Early Warning Only**: The system is designed strictly to detect and alert; it does not generate treatment, fluid dosing, or antibiotic recommendations.
3. **Research Prototype**: SepsisWatch is a research and portfolio prototype. It is not certified as a medical device and is not intended for unsupervised clinical diagnostic use without institutional IRB approval and prospective clinical validation.
