"""Residual momentum — stock return residual after regressing on market return."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor
from ..base import register


@register
class ResidualMomentum(Factor):
    name = "Residual_MOM"
    category = "momentum"
    direction = "positive"
    description = "残差动量: 相对于市场的超额收益(252日Beta调整后)"
    params = {"period": 252}

    def compute(self, universe: list[str], daily: pd.DataFrame, **kwargs) -> pd.Series:
        df = daily[daily["ts_code"].isin(universe)]
        if df.empty:
            return pd.Series(dtype=float)

        use_col = "close_bwd" if "close_bwd" in df.columns else "close"
        if use_col not in df.columns:
            return pd.Series(dtype=float)

        # Compute market return from all stocks
        mkt_ret = (
            df.groupby("trade_date")[use_col]
            .mean()
            .pct_change()
            .dropna()
        )

        result = {}
        for code in universe:
            sub = df[df["ts_code"] == code].set_index("trade_date").sort_index()
            ret = sub[use_col].pct_change().dropna()
            common = ret.index.intersection(mkt_ret.index)
            if len(common) < 60:
                continue
            r = ret[common].tail(self.params["period"])
            m = mkt_ret[common].tail(self.params["period"])
            # Simple OLS: beta = Cov(r, m) / Var(m)
            cov = np.cov(r, m)[0, 1] if len(r) > 1 else 0
            var = np.var(m) if len(m) > 1 else 1
            beta = cov / var if var != 0 else 0
            # Alpha = mean excess return
            alpha = (r - beta * m).mean()
            result[code] = alpha

        return pd.Series(result)
