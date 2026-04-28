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

    # ST detection from name (akshare includes ST/*ST prefix in stock name)
    # Detect ST/*ST from name prefix (akshare names: "ST某某" or "*ST某某")
    df["status"] = df["name"].apply(
        lambda n: "ST" if n and str(n).upper().replace(" ", "").startswith(("*ST", "ST")) else "normal"
    )
    if "list_date" not in df.columns:
        df["list_date"] = None
    if "delist_date" not in df.columns:
        df["delist_date"] = None
    if "area" not in df.columns:
        df["area"] = None
    if "industry" not in df.columns:
        df["industry"] = None
    if "asset_type" not in df.columns:
        df["asset_type"] = "stock"
    if "market" not in df.columns:
        df["market"] = df["ts_code"].apply(lambda x: "SZ" if ".SZ" in str(x) else "SH")
    if "symbol" not in df.columns:
        df["symbol"] = df["ts_code"].str.split(".").str[0]

    # Sync industry from financial Parquet (survives stock list refreshes)
    try:
        from .store.parquet_store import read_financial
        fin = read_financial()
        if not fin.empty and "industry" in fin.columns:
            ind = fin[fin["industry"].notna()].sort_values("end_date").groupby("ts_code").last().reset_index()
            ind = ind[["ts_code", "industry"]]
            # Drop existing industry column to avoid _x/_y suffix from merge
            if "industry" in df.columns:
                df = df.drop(columns=["industry"])
            df = df.merge(ind, on="ts_code", how="left")
    except Exception:
        pass

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

    # Use akshare's batch financial API (东方财富业绩报表) — much faster than per-stock
    try:
        import akshare as ak
        import re

        today = datetime.now()
        current_year = today.year
        # Fetch last 4 quarters
        frames = []
        for year in [current_year, current_year - 1]:
            for date_str in [f"{year}0331", f"{year}0630", f"{year}0930", f"{year}1231"]:
                if date_str > today.strftime("%Y%m%d"):
                    continue
                try:
                    df = ak.stock_yjbb_em(date=date_str)
                    if df is None or df.empty:
                        continue
                    # Rename Chinese columns to English
                    rename = {
                        "股票代码": "symbol",
                        "每股收益": "basic_eps",
                        "营业总收入-营业总收入": "revenue",
                        "营业总收入-同比增长": "revenue_yoy",
                        "净利润-净利润": "n_income",
                        "净利润-同比增长": "netprofit_yoy",
                        "每股净资产": "bps",
                        "净资产收益率": "roe",
                        "销售毛利率": "grossprofit_margin",
                        "每股经营现金流量": "cash_flow_oper_act",
                        "所处行业": "industry",
                        "最新公告日期": "ann_date",
                    }
                    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
                    # Convert symbol to ts_code
                    def _em_to_ts_code(code):
                        c = str(code)
                        if c.startswith(("0", "3")): return f"{c}.SZ"
                        if c.startswith(("6", "9")): return f"{c}.SH"
                        if c.startswith(("4", "8", "92")): return f"{c}.BJ"
                        return c
                    if "symbol" in df.columns:
                        df["ts_code"] = df["symbol"].apply(_em_to_ts_code)
                        df = df.drop(columns=["symbol"])
                    df["end_date"] = date_str
                    df["report_type"] = {"0331": "Q1", "0630": "Q2", "0930": "Q3", "1231": "Q4"}.get(date_str[4:], "Q4")
                    # Filter to A-shares only (include BSE 920xxx.BJ)
                    df = df[df["ts_code"].str.match(r"^\d{6}\.(SZ|SH|BJ)$")]
                    frames.append(df)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"[pipeline] financial batch {date_str} error: {e}")

        if not frames:
            _log_update(today.strftime("%Y%m%d"), "financial", "failed", 0, "No data")
            return 0

        big = pd.concat(frames, ignore_index=True)
        # Filter to requested ts_codes if specified
        if ts_codes:
            big = big[big["ts_code"].isin(ts_codes)]
        write_financial(big)

        # Sync industry info to stock_info table
        if "industry" in big.columns:
            ind_df = big[big["industry"].notna()][["ts_code", "industry"]].drop_duplicates("ts_code")
            if not ind_df.empty:
                from ..core.database import sqlite_session
                with sqlite_session() as conn:
                    for _, row in ind_df.iterrows():
                        conn.execute(
                            "UPDATE stock_info SET industry = ?, updated_at = ? WHERE ts_code = ?",
                            (row["industry"], today.isoformat(), row["ts_code"]),
                        )

        _log_update(today.strftime("%Y%m%d"), "financial", "success", len(big))
        return len(big)

    except Exception as e:
        _log_update(datetime.now().strftime("%Y%m%d"), "financial", "failed", 0, str(e))
        print(f"[pipeline] refresh_financial_batch error: {e}")
        return 0


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
