"""Accruals Ratio — lower is better (earnings quality)."""

from __future__ import annotations

import pandas as pd

from ..base import Factor
from ..base import register


@register
class AccrualsRatio(Factor):
    name = "Accruals_Ratio"
    category = "quality"
    direction = "negative"
    description = "应计利润比: (净利润 - 经营性现金流) / 总资产，低应计=高质量盈利"
    params = {}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        df = daily[daily["ts_code"].isin(universe)]
        if df.empty:
            return pd.Series(dtype=float)
        latest = df.sort_values("trade_date").groupby("ts_code").last()
        cols_needed = ["n_income", "cash_flow_oper_act", "total_assets"]
        if all(c in latest.columns for c in cols_needed):
            accruals = latest["n_income"] - latest["cash_flow_oper_act"]
            result = accruals / latest["total_assets"].replace(0, pd.NA)
            return result
        return pd.Series(index=latest.index, dtype=float)
