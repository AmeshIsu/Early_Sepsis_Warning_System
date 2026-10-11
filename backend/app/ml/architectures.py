import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Dict, Any
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier


class FocalLoss(nn.Module):
    """
    Focal Loss for binary classification with severe class imbalance:
    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
    """
    def __init__(self, alpha: float = 0.75, gamma: float = 2.0, reduction: str = "mean"):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        p = torch.sigmoid(logits)
        ce_loss = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
        p_t = p * targets + (1 - p) * (1 - targets)
        loss = ce_loss * ((1 - p_t) ** self.gamma)

        if self.alpha >= 0:
            alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)
            loss = alpha_t * loss

        if mask is not None:
            loss = loss * mask.float()
            return loss.sum() / max(1.0, mask.float().sum())

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "sum":
            return loss.sum()
        return loss


class ICUSequenceModel(nn.Module):
    """
    Rolling sequence model (GRU or LSTM) that outputs a risk logit at EVERY hourly time step.
    CPU-friendly, fast convergence on clinical time-series.
    """
    def __init__(
        self,
        input_dim: int = 39,
        hidden_dim: int = 64,
        num_layers: int = 2,
        model_type: str = "gru", # "gru" or "lstm"
        dropout: float = 0.2
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.model_type = model_type.lower()

        # Input feature projection
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        if self.model_type == "lstm":
            self.rnn = nn.LSTM(
                input_size=hidden_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0
            )
        else: # default GRU
            self.rnn = nn.GRU(
                input_size=hidden_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0
            )

        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (batch_size, seq_len, input_dim)
        returns logits: (batch_size, seq_len)
        """
        projected = self.input_proj(x)
        rnn_out, _ = self.rnn(projected) # (batch_size, seq_len, hidden_dim)
        logits = self.head(rnn_out).squeeze(-1) # (batch_size, seq_len)
        return logits


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 500):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1), :]


class ICUTemporalTransformer(nn.Module):
    """
    Causal Temporal Transformer:
    Strict causal mask ensures that prediction at time t CANNOT attend to t' > t.
    """
    def __init__(
        self,
        input_dim: int = 39,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 128,
        dropout: float = 0.1
    ):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1)
        )

    def _generate_causal_mask(self, sz: int, device: torch.device) -> torch.Tensor:
        # upper triangular mask with -inf
        mask = torch.triu(torch.full((sz, sz), float('-inf'), device=device), diagonal=1)
        return mask

    def forward(self, x: torch.Tensor, key_padding_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        x: (batch_size, seq_len, input_dim)
        key_padding_mask: (batch_size, seq_len) True for valid tokens, False for padding (we invert for PyTorch)
        returns logits: (batch_size, seq_len)
        """
        b, s, _ = x.shape
        proj = self.input_proj(x)
        encoded = self.pos_encoder(proj)
        causal_mask = self._generate_causal_mask(s, x.device)

        # In PyTorch TransformerEncoder, key_padding_mask is True for padded positions to IGNORE
        pad_mask = None
        if key_padding_mask is not None:
            pad_mask = ~key_padding_mask

        out = self.transformer_encoder(
            encoded,
            mask=causal_mask,
            src_key_padding_mask=pad_mask
        )
        logits = self.head(out).squeeze(-1)
        return logits


class ICUTabularBaseline:
    """
    Windowed baseline using Logistic Regression or HistGradientBoosting.
    """
    def __init__(self, model_type: str = "gbdt"):
        self.model_type = model_type.lower()
        if self.model_type == "logistic":
            self.model = LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)
        else:
            self.model = HistGradientBoostingClassifier(
                class_weight="balanced",
                max_iter=100,
                learning_rate=0.08,
                random_state=42
            )

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]
