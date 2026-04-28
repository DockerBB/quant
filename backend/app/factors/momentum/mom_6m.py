"""6-month momentum factor (excluding last month to avoid short-term reversal)."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class MOM_6M(Factor):
    name = "MOM_6M"
    category = "momentum"
    direction = "positive"
    description = "6个月动量(扣除最近1个月): 过去T-6月至T-1月累计收益"
    params = {"period": 126, "skip": 21}  # trading days

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        df = daily[daily["ts_code"].isin(universe)]
        if df.empty:
            return pd.Series(dtype=float)

        use_col = "close_bwd" if "close_bwd" in df.columns else "close"
        if use_col not in df.columns:
            return pd.Series(dtype=float)

        df = df.sort_values(["ts_code", "trade_date"])
        p = self.params["period"] + self.params["skip"]  # 147
        s = self.params["skip"]  # 21

        def _mom(closes):
            if len(closes) < p:
                return None
            start = closes.iloc[-p]
            end = closes.iloc[-s - 1]
            if start and start > 0:
                return (end / start) - 1
            return None

        return df.groupby("ts_code")[use_col].apply(_mom).dropna()
