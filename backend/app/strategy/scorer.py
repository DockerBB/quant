"""Factor scorer — computes weighted composite scores from individual factor values."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..factors.registry import create as create_factor


class Scorer:
    def __init__(self, factor_weights: dict[str, float]):
        """
        Args:
            factor_weights: {factor_name: weight}
                Positive weight = higher factor is better
                Negative weight = lower factor is better
        """
        self.factor_weights = factor_weights

    def score(
        self,
        universe: list[str],
        daily: pd.DataFrame,
        preprocessing: dict | None = None,
        financial: pd.DataFrame | None = None,
    ) -> pd.Series:
        if not self.factor_weights:
            return pd.Series(index=universe, dtype=float)

        prep = preprocessing or {}
        scores = pd.DataFrame(index=universe, dtype=float)

        for factor_name, weight in self.factor_weights.items():
            factor = create_factor(factor_name)
            if factor is None:
                continue

            kwargs = {}
            if financial is not None:
                kwargs["financial"] = financial
            raw = factor.compute(universe, daily, **kwargs)
            if raw is None or raw.empty:
                continue

            processed = self._preprocess(raw, prep, weight)
            if processed is not None:
                scores[factor_name] = processed

        if scores.empty:
            return pd.Series(index=universe, dtype=float)

        composite = pd.Series(0.0, index=universe)
        total_weight = 0.0
        for factor_name, weight in self.factor_weights.items():
            if factor_name not in scores.columns:
                continue
            abs_w = abs(weight)
            composite = composite.add(scores[factor_name] * weight, fill_value=0)
            total_weight += abs_w

        if total_weight > 0:
            composite = composite / total_weight

        return composite.sort_values(ascending=False)

    def _preprocess(
        self,
        series: pd.Series,
        prep: dict,
        weight: float,
    ) -> pd.Series | None:
        s = series.dropna()
        if s.empty:
            return None

        pct_low, pct_high = prep.get("winsorize_pct", (1, 99))
        lo = np.percentile(s, pct_low)
        hi = np.percentile(s, pct_high)
        s = s.clip(lo, hi)

        method = prep.get("standardize_method", "zscore")
        if method == "zscore":
            std = s.std()
            if std and std > 0:
                s = (s - s.mean()) / std
        elif method == "rank":
            s = s.rank(pct=True)

        if weight < 0:
            s = -s

        return s.reindex(series.index)
