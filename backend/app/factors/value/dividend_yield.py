"""Dividend Yield factor — higher is better."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class DividendYield(Factor):
    name = "DYield"
    category = "value"
    direction = "positive"
    description = "股息率: 过去12个月每股分红 / 当前股价"
    params = {}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        df = daily[daily["ts_code"].isin(universe)]
        if df.empty:
            return pd.Series(dtype=float)
        latest = df.sort_values("trade_date").groupby("ts_code").last()
        if "dv_ratio" in latest.columns:
            return latest["dv_ratio"].copy()
        return pd.Series(index=latest.index, dtype=float)
