"""ROE-TTM factor — higher is better (quality)."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class ROE_TTM(Factor):
    name = "ROE_TTM"
    category = "quality"
    direction = "positive"
    description = "净资产收益率(TTM): 近4季净利润 / 净资产"
    params = {}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        latest = daily[daily["ts_code"].isin(universe)].sort_values("trade_date").groupby("ts_code").last()
        if "roe" in latest.columns:
            return latest["roe"].copy()
        return pd.Series(index=latest.index, dtype=float)
