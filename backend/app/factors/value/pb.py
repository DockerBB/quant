"""PB factor — price to book. Lower is better (value)."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class PB(Factor):
    name = "PB"
    category = "value"
    direction = "negative"
    description = "市净率: 总市值 / 净资产"
    params = {}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        df = daily[daily["ts_code"].isin(universe)]
        if df.empty:
            return pd.Series(dtype=float)
        latest = df.sort_values("trade_date").groupby("ts_code").last()
        # PB = price / book_value_per_share
        if "bps" in latest.columns and "close" in latest.columns:
            pb = latest["close"] / latest["bps"].replace(0, pd.NA)
            return pb
        if "pb" in latest.columns:
            return latest["pb"].copy()
        return pd.Series(index=latest.index, dtype=float)
