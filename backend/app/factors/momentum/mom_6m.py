"""6-month momentum factor (excluding last month to avoid short-term reversal)."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class MOM_6M(Factor):
    name = "MOM_6M"
    category = "momentum"
    direction = "positive"
    description = "6个月动量(扣除最近1个月): 过去T-6月至T-1月累计收益"
    params = {"period": 126, "skip": 21}  # trading days

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        df = daily[daily["ts_code"].isin(universe)]
        if df.empty:
            return pd.Series(dtype=float)

        use_col = "close_bwd" if "close_bwd" in df.columns else "close"
        if use_col not in df.columns:
            return pd.Series(dtype=float)

        result = {}
        for code in universe:
            sub = df[df["ts_code"] == code].sort_values("trade_date")
            if len(sub) < self.params["period"] + self.params["skip"]:
                continue
            start_price = sub[use_col].iloc[-(self.params["period"] + self.params["skip"])]
            end_price = sub[use_col].iloc[-self.params["skip"] - 1]
            if start_price and start_price > 0:
                result[code] = (end_price / start_price) - 1
        return pd.Series(result)
