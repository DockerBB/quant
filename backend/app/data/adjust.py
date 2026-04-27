"""Price adjustment (复权) for A-share stocks.

Handles forward-adjusted and backward-adjusted price computation
using cumulative adjustment factors from dividend/split/rights-issue events.
"""

import pandas as pd


def compute_adjust_factor(
    daily: pd.DataFrame,
) -> pd.DataFrame:
    """Compute cumulative adjustment factor for each stock from raw OHLCV data.

    The adj_factor column represents the multiplier to convert raw prices
    to backward-adjusted prices. If adj_factor is not available in the source,
    we default to 1.0 (no adjustment needed).

    Args:
        daily: DataFrame with columns [ts_code, trade_date, close, adj_factor]

    Returns:
        DataFrame with added columns: adj_factor_filled, close_bwd, close_fwd
    """
    df = daily.copy()
    df = df.sort_values(["ts_code", "trade_date"])

    if "adj_factor" not in df.columns:
        df["adj_factor"] = 1.0

    # Forward-fill missing adj_factor within each stock
    df["adj_factor"] = df.groupby("ts_code")["adj_factor"].ffill().fillna(1.0)

    # Backward-adjusted close (true total return)
    df["close_bwd"] = df["close"] * df["adj_factor"]

    # Forward-adjusted close (latest price = actual)
    latest_adj = df.groupby("ts_code")["adj_factor"].transform("last")
    df["close_fwd"] = df["close"] * df["adj_factor"] / latest_adj.replace(0, 1.0)

    # Apply to all OHLC columns
    for col in ["open", "high", "low"]:
        if col in df.columns:
            df[f"{col}_bwd"] = df[col] * df["adj_factor"]
            df[f"{col}_fwd"] = df[col] * df["adj_factor"] / latest_adj.replace(0, 1.0)

    return df


def get_adjusted_price(
    daily: pd.DataFrame,
    method: str = "bwd",
) -> pd.Series:
    """Extract adjusted close prices from a daily dataframe.

    Args:
        daily: Must have columns [ts_code, trade_date, close, adj_factor] or pre-computed close_bwd/close_fwd
        method: 'bwd' for backward-adjusted, 'fwd' for forward-adjusted
    """
    col = f"close_{method}"
    if col in daily.columns:
        return daily.set_index(["ts_code", "trade_date"])[col]
    df = compute_adjust_factor(daily)
    return df.set_index(["ts_code", "trade_date"])[f"close_{method}"]
