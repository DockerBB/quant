"""Revenue YoY growth factor — higher is better."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class RevenueYoY(Factor):
    name = "Revenue_YoY"
    category = "growth"
    direction = "positive"
    description = "营收同比增长率"
    params = {}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        latest = daily[daily["ts_code"].isin(universe)].sort_values("trade_date").groupby("ts_code").last()
        if "revenue_yoy" in latest.columns:
            return latest["revenue_yoy"].copy()
        return pd.Series(index=latest.index, dtype=float)
