"""ETL Pipeline — orchestrates data fetching, validation, adjustment, and storage."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Callable

import pandas as pd

from ..core.config import settings
from ..core.database import sqlite_session
from .adjust import compute_adjust_factor
try:
    from .fetcher.akshare_fetcher import AkshareFetcher
    _has_akshare = True
except ImportError:
    _has_akshare = False
    AkshareFetcher = None

from .fetcher.baostock_fetcher import BaostockFetcher
from .store.parquet_store import write_daily, write_financial, get_latest_trade_date
from .store.sqlite_store import upsert_stock_info, upsert_trade_calendar


def _get_fetcher(source: str):
    if source == "akshare":
        if not _has_akshare:
            print("[pipeline] akshare not installed, falling back to baostock")
            return BaostockFetcher()
        return AkshareFetcher()
    return BaostockFetcher()


def _log_update(date_str: str, data_type: str, status: str, count: int = 0, message: str = ""):
    with sqlite_session() as conn:
        conn.execute(
            """INSERT INTO daily_update_log (date, data_type, status, record_count, message, started_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (date_str, data_type, status, count, message, datetime.now().isoformat()),
        )


def refresh_stock_list() -> pd.DataFrame:
    """Fetch and store the full stock list."""
    primary = _get_fetcher(settings.PRIMARY_SOURCE)
    df = primary.fetch_stock_list()
    if df.empty and settings.FALLBACK_SOURCE != "none":
        fallback = _get_fetcher(settings.FALLBACK_SOURCE)
        df = fallback.fetch_stock_list()

    if df.empty:
        _log_update(datetime.now().strftime("%Y%m%d"), "stock_list", "failed", 0, "Empty result")
        return df

    df["status"] = "normal"
    if "list_date" not in df.columns:
        df["list_date"] = None
    if "delist_date" not in df.columns:
        df["delist_date"] = None
    if "area" not in df.columns:
        df["area"] = None
    if "industry" not in df.columns:
        df["industry"] = None
    if "market" not in df.columns:
        df["market"] = df["ts_code"].apply(lambda x: "SZ" if ".SZ" in str(x) else "SH")
    if "symbol" not in df.columns:
        df["symbol"] = df["ts_code"].str.split(".").str[0]

    upsert_stock_info(df)
    _log_update(datetime.now().strftime("%Y%m%d"), "stock_list", "success", len(df))
    return df


def refresh_daily(trade_date: str | None = None) -> int:
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y%m%d")

    fetcher = _get_fetcher(settings.PRIMARY_SOURCE)
    df = fetcher.fetch_all_daily(trade_date)

    if df.empty:
        if settings.FALLBACK_SOURCE != "none":
            fallback = _get_fetcher(settings.FALLBACK_SOURCE)
            df = fallback.fetch_all_daily(trade_date)
        if df.empty:
            _log_update(trade_date, "daily", "failed", 0, "No data returned")
            return 0

    if "adj_factor" not in df.columns:
        df["adj_factor"] = 1.0
    if "pre_close" not in df.columns:
        if "pct_chg" in df.columns and "close" in df.columns:
            df["pre_close"] = (df["close"] / (1 + df["pct_chg"] / 100)).round(2)

    df = _validate_daily(df)
    df = compute_adjust_factor(df)

    count = write_daily(df)
    _log_update(trade_date, "daily", "success", count)
    return count


def refresh_financial_batch(ts_codes: list[str] | None = None) -> int:
    from .store.parquet_store import get_stored_stock_codes

    if ts_codes is None:
        ts_codes = get_stored_stock_codes()
    if not ts_codes:
        _log_update(datetime.now().strftime("%Y%m%d"), "financial", "failed", 0, "No stock codes")
        return 0

    primary = _get_fetcher(settings.PRIMARY_SOURCE)
    frames = []

    for ts_code in ts_codes:
        df = primary.fetch_financial(ts_code, "20100101", datetime.now().strftime("%Y%m%d"))
        if not df.empty:
            frames.append(df)
        time.sleep(0.1)

    if not frames:
        _log_update(datetime.now().strftime("%Y%m%d"), "financial", "failed", 0, "No data")
        return 0

    big = pd.concat(frames, ignore_index=True)
    write_financial(big)
    _log_update(datetime.now().strftime("%Y%m%d"), "financial", "success", len(big))
    return len(big)


def refresh_trade_calendar(start_date: str = "20100101", end_date: str | None = None) -> int:
    if end_date is None:
        end_date = (datetime.now() + pd.DateOffset(years=1)).strftime("%Y%m%d")

    fetcher = _get_fetcher(settings.FALLBACK_SOURCE if settings.FALLBACK_SOURCE != "none" else settings.PRIMARY_SOURCE)
    df = fetcher.fetch_trade_calendar(start_date, end_date)

    if df.empty:
        fetcher = _get_fetcher(settings.PRIMARY_SOURCE)
        df = fetcher.fetch_trade_calendar(start_date, end_date)

    if df.empty:
        _log_update(datetime.now().strftime("%Y%m%d"), "calendar", "failed", 0, "No data")
        return 0

    upsert_trade_calendar(df)
    _log_update(datetime.now().strftime("%Y%m%d"), "calendar", "success", len(df))
    return len(df)


def run_daily_pipeline(trade_date: str | None = None) -> dict:
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y%m%d")

    results = {}

    stock_df = refresh_stock_list()
    results["stock_list"] = {"status": "ok" if len(stock_df) > 0 else "empty", "count": len(stock_df)}

    cal_count = refresh_trade_calendar()
    results["calendar"] = {"status": "ok" if cal_count > 0 else "empty", "count": cal_count}

    daily_count = refresh_daily(trade_date)
    results["daily"] = {"status": "ok" if daily_count > 0 else "empty", "count": daily_count}

    return results


def _validate_daily(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    d = df.copy()

    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        if col in d.columns:
            d = d[d[col].notna() & (d[col] > 0)]

    if "vol" in d.columns:
        d = d[d["vol"] >= 0]

    if all(c in d.columns for c in ["high", "low", "open", "close"]):
        bad_high = d["high"] < d[["open", "close"]].max(axis=1)
        bad_low = d["low"] > d[["open", "close"]].min(axis=1)
        d = d[~(bad_high | bad_low)]

    return d.reset_index(drop=True)
