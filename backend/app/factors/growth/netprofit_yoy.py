"""Net profit YoY growth factor — higher is better."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class NetProfitYoY(Factor):
    name = "NetProfit_YoY"
    category = "growth"
    direction = "positive"
    description = "净利润同比增长率"
    params = {}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        latest = daily[daily["ts_code"].isin(universe)].sort_values("trade_date").groupby("ts_code").last()
        if "n_income_yoy" in latest.columns:
            return latest["n_income_yoy"].copy()
        return pd.Series(index=latest.index, dtype=float)
