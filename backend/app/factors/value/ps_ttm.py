"""PS-TTM factor — price to sales."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class PS_TTM(Factor):
    name = "PS_TTM"
    category = "value"
    direction = "negative"
    description = "市销率(TTM): 总市值 / 近4季度营收合计"
    params = {}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        latest = daily[daily["ts_code"].isin(universe)].sort_values("trade_date").groupby("ts_code").last()
        if "circ_mv" in latest.columns and "revenue" in latest.columns:
            return latest["circ_mv"] / latest["revenue"].replace(0, pd.NA)
        # Fallback: estimate from EPS and total profit → shares → market cap → PS
        # PS = (close × n_income / basic_eps) / revenue
        if all(c in latest.columns for c in ["close", "n_income", "basic_eps", "revenue"]):
            shares = latest["n_income"] / latest["basic_eps"].replace(0, pd.NA)
            market_cap = latest["close"] * shares
            return market_cap / latest["revenue"].replace(0, pd.NA)
        return pd.Series(index=latest.index, dtype=float)
