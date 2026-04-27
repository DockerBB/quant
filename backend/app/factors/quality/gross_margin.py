"""Gross Margin factor — higher is better (quality)."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class GrossMargin(Factor):
    name = "GrossMargin_TTM"
    category = "quality"
    direction = "positive"
    description = "毛利率(TTM): (营收 - 营业成本) / 营收"
    params = {}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        latest = daily[daily["ts_code"].isin(universe)].sort_values("trade_date").groupby("ts_code").last()
        if "grossprofit_margin" in latest.columns:
            return latest["grossprofit_margin"].copy()
        return pd.Series(index=latest.index, dtype=float)
