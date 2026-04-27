"""Stock universe builder — filters for valid tradable stocks.

Handles A-share specific rules: ST exclusion, new stock exclusion,
suspension detection, delisting, limit-up/down exclusion.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from ..core.config import settings
from .limit_rules import get_limit_thresholds_batch


def build_universe(
    stock_info: pd.DataFrame,
    trade_date: str,
    daily_snapshot: pd.DataFrame | None = None,
    exclude_st: bool | None = None,
    exclude_new_days: int | None = None,
    exclude_suspended: bool = True,
    exclude_limit: bool = False,
) -> list[str]:
    """Build the investable stock universe for a given trade date.

    Args:
        stock_info: DataFrame from stock_info table (ts_code, list_date, delist_date, status)
        trade_date: Target date string 'YYYYMMDD'
        daily_snapshot: Optional daily data for the date (for suspension / limit checks)
        exclude_st: Override ST exclusion (default from settings)
        exclude_new_days: Override new stock min days (default from settings)
        exclude_suspended: Exclude suspended stocks
        exclude_limit: Exclude stocks at limit-up (can't buy) or limit-down (can't sell)

    Returns:
        List of valid ts_codes
    """
    if exclude_st is None:
        exclude_st = settings.EXCLUDE_ST
    if exclude_new_days is None:
        exclude_new_days = settings.EXCLUDE_NEW_STOCK_DAYS

    si = stock_info.copy()
    si["list_date"] = pd.to_datetime(si["list_date"], errors="coerce")
    si["delist_date"] = pd.to_datetime(si["delist_date"], errors="coerce")
    trade_dt = pd.to_datetime(trade_date)

    mask = pd.Series(True, index=si.index)

    # Exclude ST / *ST
    if exclude_st and "status" in si.columns:
        mask &= ~si["status"].str.upper().str.contains("ST", na=False)

    # Exclude delisted
    if "delist_date" in si.columns:
        mask &= (si["delist_date"].isna()) | (si["delist_date"] > trade_dt)

    # Exclude not-yet-listed. If list_date is null, assume listed.
    if "list_date" in si.columns:
        known_listed = si["list_date"].isna() | (si["list_date"] <= trade_dt)
        mask &= known_listed

    # Exclude new stocks (< N trading days since listing). Skip if list_date unknown.
    if exclude_new_days > 0 and "list_date" in si.columns:
        listed_mask = si["list_date"].notna()
        if listed_mask.any():
            days_listed = (trade_dt - si["list_date"]).dt.days
            new_mask = listed_mask & (days_listed >= exclude_new_days) | ~listed_mask
            mask &= new_mask

    candidates = si.loc[mask, "ts_code"].tolist()

    # Apply daily snapshot filters
    if daily_snapshot is not None and not daily_snapshot.empty:
        snap = daily_snapshot[daily_snapshot["ts_code"].isin(candidates)]

        # Exclude suspended (volume = 0 or price unchanged with zero volume)
        if exclude_suspended:
            if "vol" in snap.columns:
                suspended = snap[snap["vol"] <= 0]["ts_code"].tolist()
                candidates = [c for c in candidates if c not in suspended]

        # Exclude limit-up / limit-down (per-board thresholds)
        if exclude_limit and "pct_chg" in snap.columns:
            thresholds = get_limit_thresholds_batch(snap["ts_code"].tolist(), tolerance=True)
            limit_codes = [
                row["ts_code"]
                for _, row in snap.iterrows()
                if abs(row["pct_chg"]) >= thresholds.get(row["ts_code"], 9.8)
            ]
            candidates = [c for c in candidates if c not in limit_codes]

    return candidates


def detect_suspended(
    daily_snapshot: pd.DataFrame,
) -> list[str]:
    """Detect suspended stocks in a daily snapshot (vol == 0 or NaN)."""
    if daily_snapshot.empty or "vol" not in daily_snapshot.columns:
        return []
    return daily_snapshot.loc[
        daily_snapshot["vol"].fillna(0) <= 0, "ts_code"
    ].tolist()


def detect_limit_hit(
    daily_snapshot: pd.DataFrame,
    direction: str = "up",
    threshold: float | None = None,
) -> list[str]:
    """Detect stocks that hit price limit.

    Args:
        direction: 'up' for limit-up, 'down' for limit-down
        threshold: Optional fixed threshold. If None, uses per-board rules.
    """
    if daily_snapshot.empty or "pct_chg" not in daily_snapshot.columns:
        return []
    if threshold is not None:
        if direction == "up":
            return daily_snapshot.loc[
                daily_snapshot["pct_chg"] >= threshold, "ts_code"
            ].tolist()
        return daily_snapshot.loc[
            daily_snapshot["pct_chg"] <= -threshold, "ts_code"
        ].tolist()
    from .limit_rules import get_limit_threshold
    result = []
    for _, row in daily_snapshot.iterrows():
        t = get_limit_threshold(row["ts_code"], tolerance=True)
        if direction == "up" and row["pct_chg"] >= t:
            result.append(row["ts_code"])
        elif direction == "down" and row["pct_chg"] <= -t:
            result.append(row["ts_code"])
    return result
