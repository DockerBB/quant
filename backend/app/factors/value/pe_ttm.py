"""PE-TTM factor — lower is better (value)."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class PE_TTM(Factor):
    name = "PE_TTM"
    category = "value"
    direction = "negative"
    description = "市盈率(TTM): 总市值 / 近4个季度净利润合计"
    params = {}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        df = daily[daily["ts_code"].isin(universe)]
        if df.empty:
            return pd.Series(dtype=float)

        latest = df.sort_values("trade_date").groupby("ts_code").last()

        # PE = price / earnings_per_share
        if "basic_eps" in latest.columns and "close" in latest.columns:
            pe = latest["close"] / latest["basic_eps"].replace(0, pd.NA)
            return pe
        if "pe" in latest.columns:
            return latest["pe"].copy()
        return pd.Series(index=latest.index, dtype=float)
