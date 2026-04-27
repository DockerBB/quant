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

        result = {}
        for code in universe:
            sub = df[df["ts_code"] == code].sort_values("trade_date")
            if len(sub) < self.params["long_window"]:
                continue
            short_avg = sub["turnover_rate"].tail(self.params["short_window"]).mean()
            long_avg = sub["turnover_rate"].tail(self.params["long_window"]).mean()
            if long_avg and long_avg > 0:
                result[code] = (short_avg - long_avg) / long_avg
        return pd.Series(result)
