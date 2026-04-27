"""Signal generator — converts composite scores to buy/sell/hold signals.

Applies A-share specific rules:
- T+1: buy signal means tradable next day
- Limit-up: exclude from buy candidates (can't buy at limit-up)
- Limit-down: exclude from sell candidates (can't sell at limit-down)
"""

from __future__ import annotations

import pandas as pd


class SignalGenerator:
    def __init__(self, config: dict):
        self.buy_top_pct = config.get("buy_top_pct", 0.2)
        self.sell_bottom_pct = config.get("sell_bottom_pct", 0.2)
        self.max_holdings = config.get("max_holdings", 20)
        self.min_holding_days = config.get("min_holding_days", 1)
        self.stop_loss = config.get("stop_loss", {})

    def generate(
        self,
        scores: pd.Series,
        daily: pd.DataFrame,
    ) -> list[dict]:
        """Generate signals from composite scores.

        Args:
            scores: Series indexed by ts_code with composite scores (desc = better)
            daily: Daily snapshot DataFrame for the target date

        Returns:
            List of signal dicts: [{ts_code, signal_type, score, percentile, detail}, ...]
        """
        if scores.empty:
            return []

        valid_scores = scores.dropna()
        if valid_scores.empty:
            return []

        n = len(valid_scores)
        buy_threshold = valid_scores.quantile(1 - self.buy_top_pct)
        sell_threshold = valid_scores.quantile(self.sell_bottom_pct)

        # Build daily snapshot lookup
        daily_idx = pd.Series()
        if not daily.empty and "close" in daily.columns and "pct_chg" in daily.columns:
            snap = daily.set_index("ts_code")
            daily_idx = snap

        signals = []
        for ts_code, score in valid_scores.items():
            pct = (valid_scores < score).mean()

            # Check limit constraints (per-board thresholds)
            is_limit_up = False
            is_limit_down = False
            if ts_code in daily_idx.index:
                pct_chg = daily_idx.loc[ts_code, "pct_chg"]
                if isinstance(pct_chg, pd.Series):
                    pct_chg = pct_chg.iloc[0]
                from ..data.limit_rules import get_limit_threshold
                limit_pct = get_limit_threshold(ts_code, tolerance=True)
                is_limit_up = float(pct_chg) >= limit_pct if pd.notna(pct_chg) else False
                is_limit_down = float(pct_chg) <= -limit_pct if pd.notna(pct_chg) else False

            if score >= buy_threshold and not is_limit_up:
                sig_type = "buy"
            elif score <= sell_threshold and not is_limit_down:
                sig_type = "sell"
            else:
                sig_type = "hold"

            signals.append({
                "ts_code": ts_code,
                "signal_type": sig_type,
                "score": round(float(score), 4),
                "percentile": round(float(pct), 4),
                "detail": {
                    "is_limit_up": is_limit_up,
                    "is_limit_down": is_limit_down,
                },
            })

        # Sort: buys first (high score), then holds, then sells
        order_key = {"buy": 0, "hold": 1, "sell": 2}
        signals.sort(key=lambda s: (order_key.get(s["signal_type"], 9), -s.get("score", 0)))

        # Cap max holdings for buy signals
        buy_count = 0
        for s in signals:
            if s["signal_type"] == "buy":
                buy_count += 1
                if buy_count > self.max_holdings:
                    s["signal_type"] = "hold"

        return signals
