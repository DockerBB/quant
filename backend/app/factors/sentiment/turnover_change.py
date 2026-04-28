"""Turnover rate change factor — measures sentiment shift."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class TurnoverChange(Factor):
    name = "Turnover_Change"
    category = "sentiment"
    direction = "positive"
    description = "换手率变化: (5日均换手率 - 20日均换手率) / 20日均换手率"
    params = {"short_window": 5, "long_window": 20}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        df = daily[daily["ts_code"].isin(universe)]
        if df.empty or "turnover_rate" not in df.columns:
            return pd.Series(dtype=float)

        df = df.sort_values(["ts_code", "trade_date"])
        sw = self.params["short_window"]
        lw = self.params["long_window"]

        def _turn(changes):
            if len(changes) < lw:
                return None
            short_avg = changes.tail(sw).mean()
            long_avg = changes.tail(lw).mean()
            if long_avg and long_avg > 0:
                return (short_avg - long_avg) / long_avg
            return None

        return df.groupby("ts_code")["turnover_rate"].apply(_turn).dropna()
