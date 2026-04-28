"""RSI-14 factor — reversal effect in A-shares (low RSI may indicate oversold bounce)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor
from ..base import register


@register
class RSI_14(Factor):
    name = "RSI_14"
    category = "technical"
    direction = "negative"
    description = "14日RSI: A股中低RSI股票有均值回归倾向，因此方向为负"
    params = {"window": 14}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        df = daily[daily["ts_code"].isin(universe)]
        if df.empty:
            return pd.Series(dtype=float)

        use_col = "close_fwd" if "close_fwd" in df.columns else "close"
        if use_col not in df.columns:
            return pd.Series(dtype=float)

        df = df.sort_values(["ts_code", "trade_date"])
        w = self.params["window"]

        def _rsi(closes):
            if len(closes) < w + 1:
                return None
            delta = closes.diff()
            avg_gain = delta.clip(lower=0).tail(w).mean()
            avg_loss = (-delta).clip(lower=0).tail(w).mean()
            if avg_loss == 0:
                return 100.0
            return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

        return df.groupby("ts_code")[use_col].apply(_rsi).dropna()
