import hashlib
import numpy as np
import torch
from torch.utils.data import Dataset
from typing import List, Dict, Any, Tuple, Optional
from backend.app.pipeline.preprocessor import ICUPreprocessor, FEATURE_NAMES

def patient_level_split(
    patients: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    STRICT PATIENT-LEVEL SPLIT:
    Patients are partitioned based on their unique patient_id.
    Guarantees 0% patient overlap across train, validation, and test splits.
    Stratified by sepsis status so prevalence remains consistent.
    """
    septic_pts = [p for p in patients if p.get("is_septic", False)]
    non_septic_pts = [p for p in patients if not p.get("is_septic", False)]

    rng = np.random.default_rng(seed)
    rng.shuffle(septic_pts)
    rng.shuffle(non_septic_pts)

    def split_group(group):
        n = len(group)
        n_train = int(round(n * train_ratio))
        n_val = int(round(n * val_ratio))
        train_p = group[:n_train]
        val_p = group[n_train:n_train + n_val]
        test_p = group[n_train + n_val:]
        return train_p, val_p, test_p

    s_train, s_val, s_test = split_group(septic_pts)
    ns_train, ns_val, ns_test = split_group(non_septic_pts)

    train_pts = s_train + ns_train
    val_pts = s_val + ns_val
    test_pts = s_test + ns_test

    rng.shuffle(train_pts)
    rng.shuffle(val_pts)
    rng.shuffle(test_pts)

    return train_pts, val_pts, test_pts


class ICUTimeSeriesDataset(Dataset):
    """
    PyTorch Dataset yielding variable-length sequence tensors:
    - x: (seq_len, num_features)
    - y: (seq_len,)
    - mask: (seq_len,)
    - patient_id: str
    """
    def __init__(self, patients: List[Dict[str, Any]], preprocessor: ICUPreprocessor, is_training: bool = False):
        self.patients = patients
        self.preprocessor = preprocessor
        self.is_training = is_training
        self.data = []

        total_pos = 0
        total_total = 0

        for pt in patients:
            X, y, hours = preprocessor.process_patient_trajectory(pt, is_training=is_training)
            if len(X) > 0:
                self.data.append({
                    "patient_id": pt["patient_id"],
                    "x": torch.from_numpy(X),
                    "y": torch.from_numpy(y),
                    "hours": hours,
                    "seq_len": len(X),
                    "is_septic": pt.get("is_septic", False),
                    "onset_hour": pt.get("sepsis_onset_hour")
                })
                total_pos += int(np.sum(y))
                total_total += len(y)

        self.pos_weight = float((total_total - total_pos) / max(1, total_pos))
        self.prevalence = float(total_pos / max(1, total_total))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]


def collate_seq_batch(batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
    """
    Pads variable-length sequences to max sequence length in batch.
    Returns:
    - x_padded: (batch_size, max_len, num_features)
    - y_padded: (batch_size, max_len)
    - mask: (batch_size, max_len) boolean mask where True = valid step
    - lengths: (batch_size,)
    """
    batch_size = len(batch)
    max_len = max(item["seq_len"] for item in batch)
    num_features = batch[0]["x"].shape[1]

    x_padded = torch.zeros((batch_size, max_len, num_features), dtype=torch.float32)
    y_padded = torch.zeros((batch_size, max_len), dtype=torch.float32)
    seq_mask = torch.zeros((batch_size, max_len), dtype=torch.bool)
    lengths = torch.tensor([item["seq_len"] for item in batch], dtype=torch.long)

    for i, item in enumerate(batch):
        l = item["seq_len"]
        x_padded[i, :l, :] = item["x"]
        y_padded[i, :l] = item["y"]
        seq_mask[i, :l] = True

    return {
        "x": x_padded,
        "y": y_padded,
        "mask": seq_mask,
        "lengths": lengths,
        "patient_ids": [b["patient_id"] for b in batch]
    }


def extract_windowed_tabular_dataset(
    patients: List[Dict[str, Any]],
    preprocessor: ICUPreprocessor,
    window_size: int = 6,
    is_training: bool = False
) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
    """
    Converts time-series into windowed tabular summary features (mean, min, max, slope)
    for Logistic Regression / Gradient Boosting.
    Leakage-safe: uses only data from (t - window_size, t].
    """
    all_X = []
    all_y = []
    metadata = []

    for pt in patients:
        X_seq, y_seq, hours = preprocessor.process_patient_trajectory(pt, is_training=is_training)
        seq_len = len(X_seq)
        num_raw_feats = len(FEATURE_NAMES)

        for t in range(seq_len):
            start_t = max(0, t - window_size + 1)
            window_slice = X_seq[start_t:t + 1] # shape (win_len, num_features)

            # Continuous normalized values are in first num_raw_feats columns
            raw_vals = window_slice[:, :num_raw_feats]

            mean_vals = np.mean(raw_vals, axis=0)
            min_vals = np.min(raw_vals, axis=0)
            max_vals = np.max(raw_vals, axis=0)

            # Slope over window
            if len(raw_vals) > 1:
                slope_vals = (raw_vals[-1] - raw_vals[0]) / float(len(raw_vals))
            else:
                slope_vals = np.zeros(num_raw_feats, dtype=np.float32)

            # Current static and score features (from the end of feature vector)
            static_scores = X_seq[t, -6:] # age, gender, sirs, qsofa, news, sofa

            row_feats = np.concatenate([mean_vals, min_vals, max_vals, slope_vals, static_scores])
            all_X.append(row_feats)
            all_y.append(y_seq[t])
            metadata.append({
                "patient_id": pt["patient_id"],
                "hour": int(hours[t]),
                "is_septic": pt.get("is_septic", False),
                "onset_hour": pt.get("sepsis_onset_hour")
            })

    return np.array(all_X, dtype=np.float32), np.array(all_y, dtype=np.float32), metadata
