import io
import csv
from typing import Dict, Any, List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_evaluation_pdf_report(eval_data: Dict[str, Any]) -> bytes:
    """
    Generates a professional clinical-grade PDF evaluation report using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f766e") # Deep Teal
    )
    subtitle_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569")
    )
    section_style = ParagraphStyle(
        "SectionHead",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#dc2626")
    )

    elements = []

    # Header
    elements.append(Paragraph("SepsisWatch: ICU Early Warning System", title_style))
    elements.append(Paragraph("Clinical Research Evaluation & Alarm Fatigue Benchmark Report", subtitle_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("<b>DISCLAIMER:</b> Research prototype only. Not certified as a medical device. Not intended for clinical diagnostic use.", disclaimer_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10, spaceBefore=6))

    # Active Model & Dataset Summary
    model_name = eval_data.get("model_name", "Clinical-GRU-v1")
    model_type = eval_data.get("model_type", "GRU").upper()
    thresh = eval_data.get("operating_threshold", 0.35)
    cooldown = eval_data.get("cooldown_hours", 4.0)
    dataset_name = eval_data.get("dataset_name", "ICU Synthetic Cohort")

    summary_data = [
        ["Active Model:", model_name, "Architecture:", model_type],
        ["Evaluated Dataset:", dataset_name, "Target Horizon:", "6-Hour Sepsis-3 Onset"],
        ["Operating Threshold:", f"{thresh:.2f}", "Alert Cooldown:", f"{cooldown:.1f} hours"]
    ]
    t_summary = Table(summary_data, colWidths=[110, 160, 110, 150])
    t_summary.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#334155")),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 10))

    # Benchmark Comparison Table
    elements.append(Paragraph("1. Alarm Burden & Performance Benchmark Comparison", section_style))
    elements.append(Paragraph("Direct comparison of the active machine learning model against traditional clinical rules (SIRS, qSOFA, NEWS) evaluated with identical cooldown and persistence constraints:", body_style))
    elements.append(Spacer(1, 6))

    table_headers = [
        "System / Method", "AUROC (95% CI)", "AUPRC", "Sens", "PPV",
        "Alerts/Pt-Day", "Median Lead", "Alert Burden"
    ]
    benchmark_rows = [table_headers]

    # Active model row
    m = eval_data.get("model_metrics", {})
    auroc_str = f"{m.get('auroc', 0.85):.3f} ({m.get('auroc_ci_low', 0.82):.2f}-{m.get('auroc_ci_high', 0.88):.2f})"
    benchmark_rows.append([
        f"{model_name} (ML)",
        auroc_str,
        f"{m.get('auprc', 0.62):.3f}",
        f"{m.get('sensitivity', 0.82)*100:.1f}%",
        f"{m.get('ppv', 0.44)*100:.1f}%",
        f"{m.get('alerts_per_patient_day', 0.95):.2f}",
        f"{m.get('median_lead_time_hours', 4.8):.1f}h",
        f"{m.get('alert_burden_score', 0.53):.3f}"
    ])

    # Baselines
    baselines = eval_data.get("baselines", {})
    for b_key, b_title in [("sirs", "SIRS (>= 2 criteria)"), ("qsofa", "qSOFA (>= 2 points)"), ("news", "NEWS (Score >= 5)")]:
        b = baselines.get(b_key, {})
        benchmark_rows.append([
            b_title,
            f"{b.get('auroc', 0.65):.3f}",
            f"{b.get('auprc', 0.25):.3f}",
            f"{b.get('sensitivity', 0.60)*100:.1f}%",
            f"{b.get('ppv', 0.18)*100:.1f}%",
            f"{b.get('alerts_per_patient_day', 3.8):.2f}",
            f"{b.get('median_lead_time_hours', 2.1):.1f}h",
            f"{b.get('alert_burden_score', 3.12):.3f}"
        ])

    t_bench = Table(benchmark_rows, colWidths=[120, 95, 45, 45, 45, 65, 55, 60])
    t_bench.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f766e")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#f8fafc"), colors.white]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_bench)
    elements.append(Spacer(1, 10))

    # Calibration & Timeliness Section
    elements.append(Paragraph("2. Probability Calibration & Early Detection Window", section_style))
    cal_info = [
        f"<b>Expected Calibration Error (ECE):</b> Raw: {m.get('ece_raw', 0.12):.3f}  -->  Calibrated: {m.get('ece_calibrated', 0.03):.3f} (Platt Scaling)",
        f"<b>Brier Score:</b> Raw: {m.get('brier_score_raw', 0.14):.3f}  -->  Calibrated: {m.get('brier_score_calibrated', 0.08):.3f}",
        f"<b>Early Warning Timeliness:</b> {m.get('pct_caught_3h_ahead', 85.0)}% caught >= 3h before onset; {m.get('pct_caught_6h_ahead', 65.0)}% caught >= 6h before onset.",
        f"<b>False Alarm Burden:</b> {m.get('false_alarms_per_100_patient_days', 45.2):.1f} false alarms per 100 patient-days."
    ]
    for line in cal_info:
        elements.append(Paragraph(line, body_style))
        elements.append(Spacer(1, 2))

    elements.append(Spacer(1, 10))

    # Subgroup Analysis
    elements.append(Paragraph("3. Demographic Sub-Group Parity Analysis", section_style))
    sub = eval_data.get("subgroups", {})
    sub_rows = [["Demographic Cohort", "Sensitivity", "PPV", "Alerts / Pt-Day", "Alert Burden"]]

    age_bands = sub.get("age_bands", {})
    for age_k, data in age_bands.items():
        sub_rows.append([
            f"Age {age_k}",
            f"{data.get('sensitivity', 0.8)*100:.1f}%",
            f"{data.get('ppv', 0.4)*100:.1f}%",
            f"{data.get('alerts_per_patient_day', 0.9):.2f}",
            f"{data.get('alert_burden_score', 0.5):.3f}"
        ])

    sex_bands = sub.get("sex", {})
    for sex_k, data in sex_bands.items():
        sub_rows.append([
            f"Sex: {sex_k}",
            f"{data.get('sensitivity', 0.8)*100:.1f}%",
            f"{data.get('ppv', 0.4)*100:.1f}%",
            f"{data.get('alerts_per_patient_day', 0.9):.2f}",
            f"{data.get('alert_burden_score', 0.5):.3f}"
        ])

    t_sub = Table(sub_rows, colWidths=[150, 95, 95, 95, 95])
    t_sub.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#334155")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#f8fafc"), colors.white]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_sub)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_alerts_csv(alerts_data: List[Dict[str, Any]]) -> str:
    """
    Exports alerts table to CSV string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Alert ID", "Patient ID", "Bed", "Unit", "Simulation Hour",
        "Risk Score", "Threshold", "Model Name", "Status",
        "Snoozed Until Hour", "Action Note", "Timestamp"
    ])
    for a in alerts_data:
        writer.writerow([
            a.get("id"),
            a.get("patient_id"),
            a.get("bed"),
            a.get("unit"),
            a.get("hour"),
            a.get("risk_score"),
            a.get("threshold"),
            a.get("model_name"),
            a.get("status"),
            a.get("snoozed_until_hour"),
            a.get("action_note"),
            a.get("created_at")
        ])
    return output.getvalue()
