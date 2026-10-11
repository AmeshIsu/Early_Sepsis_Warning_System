import os
import io
import zipfile
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from backend.app.ml.baselines import compute_sirs, compute_qsofa, compute_news, compute_sofa_components

MIMIC_DISCLAIMER_NOTE = (
    "Note on Clinical Data: MIMIC-III, MIMIC-IV, and PhysioNet Challenge 2019 raw datasets "
    "are protected health research resources that cannot be redistributed publicly without "
    "credentialing, CITI 'Data or Specimens Only Research' certification, and signed Data Use Agreements. "
    "Users must obtain their own authorized files from PhysioNet (physionet.org) before uploading here."
)

PHYSIONET_COL_MAP = {
    "hr": "HR",
    "spo2": "O2Sat",
    "temp": "Temp",
    "sbp": "SBP",
    "map": "MAP",
    "dbp": "DBP",
    "resp": "Resp",
    "lactate": "Lactate",
    "wbc": "WBC",
    "creatinine": "Creatinine",
    "bilirubin": "Bilirubin_total",
    "age": "Age",
    "gender": "Gender",
    "iculor": "ICULOS",
    "sepsis_label": "SepsisLabel"
}

def parse_single_psv(content_str: str, filename: str) -> Dict[str, Any]:
    """
    Parses a single PhysioNet 2019 .psv string.
    Returns patient metadata and list of hourly records.
    """
    df = pd.read_csv(io.StringIO(content_str), sep="|")

    # Patient ID from filename, e.g. p012345.psv -> P-012345
    pt_id_str = os.path.splitext(os.path.basename(filename))[0].upper()
    if not pt_id_str.startswith("P"):
        pt_id_str = f"P-{pt_id_str}"

    age = float(df["Age"].dropna().iloc[0]) if "Age" in df and not df["Age"].dropna().empty else 60.0
    gender = int(df["Gender"].dropna().iloc[0]) if "Gender" in df and not df["Gender"].dropna().empty else 1
    unit = "MICU"
    if "Unit1" in df and "Unit2" in df:
        u1 = df["Unit1"].dropna().iloc[0] if not df["Unit1"].dropna().empty else 0
        unit = "MICU" if u1 == 1 else "SICU"

    los_hours = len(df)
    sepsis_series = df["SepsisLabel"] if "SepsisLabel" in df else pd.Series([0]*los_hours)
    is_septic = bool((sepsis_series == 1).any())
    sepsis_onset_hour = None
    if is_septic:
        onset_idx = (sepsis_series == 1).idxmax()
        sepsis_onset_hour = int(onset_idx)

    vitals = []
    for h in range(los_hours):
        row = df.iloc[h]
        hr = float(row["HR"]) if "HR" in row and not pd.isna(row["HR"]) else None
        sbp = float(row["SBP"]) if "SBP" in row and not pd.isna(row["SBP"]) else None
        dbp = float(row["DBP"]) if "DBP" in row and not pd.isna(row["DBP"]) else None
        map_val = float(row["MAP"]) if "MAP" in row and not pd.isna(row["MAP"]) else None
        resp = float(row["Resp"]) if "Resp" in row and not pd.isna(row["Resp"]) else None
        temp = float(row["Temp"]) if "Temp" in row and not pd.isna(row["Temp"]) else None
        spo2 = float(row["O2Sat"]) if "O2Sat" in row and not pd.isna(row["O2Sat"]) else None

        lactate = float(row["Lactate"]) if "Lactate" in row and not pd.isna(row["Lactate"]) else None
        wbc = float(row["WBC"]) if "WBC" in row and not pd.isna(row["WBC"]) else None
        creat = float(row["Creatinine"]) if "Creatinine" in row and not pd.isna(row["Creatinine"]) else None
        bili = float(row["Bilirubin_total"]) if "Bilirubin_total" in row and not pd.isna(row["Bilirubin_total"]) else None

        sirs = compute_sirs(hr, resp, temp, wbc)
        qsofa = compute_qsofa(resp, sbp, altered_mental=(map_val is not None and map_val < 65))
        news = compute_news(hr, sbp, resp, temp, spo2)
        sofa_dict = compute_sofa_components(map_val, creat, bili, spo2)

        is_target_6h = 0
        if is_septic and sepsis_onset_hour is not None:
            if h < sepsis_onset_hour <= (h + 6):
                is_target_6h = 1

        vitals.append({
            "hour": h,
            "hr": hr,
            "sbp": sbp,
            "dbp": dbp,
            "map": map_val,
            "resp": resp,
            "temp": temp,
            "spo2": spo2,
            "lactate": lactate,
            "wbc": wbc,
            "creatinine": creat,
            "bilirubin": bili,
            "sofa_score": sofa_dict["total"],
            "sirs_score": sirs,
            "qsofa_score": qsofa,
            "news_score": news,
            "sepsis_target_6h": is_target_6h,
            "is_onset": (is_septic and h == sepsis_onset_hour)
        })

    return {
        "patient_id": pt_id_str,
        "age": age,
        "gender": gender,
        "unit": unit,
        "bed": f"BED-{(len(pt_id_str) % 24) + 1:02d}",
        "los_hours": los_hours,
        "is_septic": is_septic,
        "sepsis_onset_hour": sepsis_onset_hour,
        "vitals": vitals
    }


def parse_generic_csv(
    csv_str: str,
    column_mapping: Dict[str, str],
    dataset_name: str = "custom_csv"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parses generic CSV with custom column mapping.
    column_mapping format: {"patient_id": "subject_id", "hour": "charttime_hour", "hr": "heart_rate", ...}
    """
    df = pd.read_csv(io.StringIO(csv_str))

    pid_col = column_mapping.get("patient_id", "patient_id")
    hour_col = column_mapping.get("hour", "hour")
    label_col = column_mapping.get("sepsis_label", "sepsis_label")

    if pid_col not in df.columns:
        raise ValueError(f"Patient ID column '{pid_col}' not found in CSV. Available columns: {list(df.columns)}")

    patients = []
    errors = []

    grouped = df.groupby(pid_col)
    for pid_val, group in grouped:
        try:
            pt_id = f"PAT-{str(pid_val)}"
            if hour_col in group.columns:
                group = group.sort_values(hour_col)

            los = len(group)
            is_septic = False
            onset_hour = None
            if label_col in group.columns:
                labels = group[label_col].fillna(0).astype(int).values
                if (labels == 1).any():
                    is_septic = True
                    onset_hour = int(np.where(labels == 1)[0][0])

            vitals = []
            for h in range(los):
                row = group.iloc[h]
                def get_val(key):
                    c = column_mapping.get(key)
                    if c and c in row and not pd.isna(row[c]):
                        try:
                            return float(row[c])
                        except Exception:
                            return None
                    return None

                hr = get_val("hr")
                sbp = get_val("sbp")
                dbp = get_val("dbp")
                map_val = get_val("map")
                if map_val is None and sbp is not None and dbp is not None:
                    map_val = (2 * dbp + sbp) / 3.0
                resp = get_val("resp")
                temp = get_val("temp")
                spo2 = get_val("spo2")
                lactate = get_val("lactate")
                wbc = get_val("wbc")
                creat = get_val("creatinine")
                bili = get_val("bilirubin")

                sirs = compute_sirs(hr, resp, temp, wbc)
                qsofa = compute_qsofa(resp, sbp)
                news = compute_news(hr, sbp, resp, temp, spo2)
                sofa_d = compute_sofa_components(map_val, creat, bili, spo2)

                is_target_6h = 1 if (is_septic and onset_hour is not None and h < onset_hour <= h + 6) else 0

                vitals.append({
                    "hour": h,
                    "hr": hr,
                    "sbp": sbp,
                    "dbp": dbp,
                    "map": map_val,
                    "resp": resp,
                    "temp": temp,
                    "spo2": spo2,
                    "lactate": lactate,
                    "wbc": wbc,
                    "creatinine": creat,
                    "bilirubin": bili,
                    "sofa_score": sofa_d["total"],
                    "sirs_score": sirs,
                    "qsofa_score": qsofa,
                    "news_score": news,
                    "sepsis_target_6h": is_target_6h,
                    "is_onset": (is_septic and h == onset_hour)
                })

            age = get_val("age") or 60.0
            gender = int(get_val("gender") or 1)

            patients.append({
                "patient_id": pt_id,
                "age": age,
                "gender": gender,
                "unit": "MICU",
                "bed": f"BED-{(len(patients) % 24) + 1:02d}",
                "los_hours": los,
                "is_septic": is_septic,
                "sepsis_onset_hour": onset_hour,
                "vitals": vitals
            })
        except Exception as e:
            errors.append(f"Patient {pid_val}: {str(e)}")

    summary = {
        "total_parsed": len(patients),
        "errors_count": len(errors),
        "errors": errors[:10],
        "preview": patients[:3] if patients else []
    }
    return patients, summary


def parse_psv_archive_or_files(files_dict: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Accepts dictionary of {filename: content_str} and parses all .psv files.
    """
    results = []
    for fname, content in files_dict.items():
        if fname.endswith(".psv") or fname.endswith(".txt"):
            try:
                pt_data = parse_single_psv(content, fname)
                results.append(pt_data)
            except Exception as e:
                continue
    return results
