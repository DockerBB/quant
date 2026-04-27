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

        result = {}
        for code in universe:
            sub = df[df["ts_code"] == code].sort_values("trade_date")
            if len(sub) < self.params["window"] + 1:
                continue
            closes = sub[use_col]
            delta = closes.diff()
            gains = delta.clip(lower=0)
            losses = (-delta).clip(lower=0)

            avg_gain = gains.tail(self.params["window"]).mean()
            avg_loss = losses.tail(self.params["window"]).mean()

            if avg_loss == 0:
                result[code] = 100.0
            else:
                rs = avg_gain / avg_loss
                result[code] = 100.0 - (100.0 / (1.0 + rs))

        return pd.Series(result)
