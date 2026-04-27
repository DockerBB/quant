"""Parquet-based storage for OHLCV daily data and financial data.

Uses pandas + pyarrow to read/write partitioned Parquet files.
Daily data is partitioned by year-month: daily/YYYY/MM/YYYY-MM.parquet
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ...core.config import settings

DAILY_COLUMNS = [
    "ts_code", "trade_date", "open", "high", "low", "close", "pre_close",
    "change", "pct_chg", "vol", "amount", "turnover_rate",
    "adj_factor", "is_st"
]
FINANCIAL_COLUMNS = [
    "ts_code", "ann_date", "f_ann_date", "end_date", "report_type",
    "total_assets", "total_liab", "total_hldr_eqy_exc_min_int",
    "revenue", "oper_cost", "sell_exp", "admin_exp", "fin_exp",
    "n_income", "n_income_attr_p", "cash_flow_oper_act",
    "basic_eps", "diluted_eps", "bps",
    "roe", "roa", "grossprofit_margin", "netprofit_margin",
    "debt_to_assets", "current_ratio",
]


def _daily_partition_path(trade_date: str) -> Path:
    """Convert '20240115' to daily/2024/01/2024-01.parquet."""
    ym = trade_date[:6]
    year, month = ym[:4], ym[4:6]
    return settings.DAILY_DIR / year / month / f"{year}-{month}.parquet"


def write_daily(df: pd.DataFrame) -> int:
    """Write daily OHLCV data to partitioned Parquet files.

    Groups rows by year-month, writes each partition. Returns total rows written.
    """
    if df.empty:
        return 0

    df = df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")

    total = 0
    for (year, month), group in df.groupby(
        [df["trade_date"].str[:4], df["trade_date"].str[4:6]]
    ):
        out_path = settings.DAILY_DIR / year / month / f"{year}-{month}.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        existing = pd.DataFrame()
        if out_path.exists():
            existing = pd.read_parquet(out_path)

        merged = pd.concat([existing, group], ignore_index=True)
        merged = merged.drop_duplicates(subset=["ts_code", "trade_date"], keep="last")
        merged.sort_values(["trade_date", "ts_code"], inplace=True)
        merged.to_parquet(out_path, index=False, compression="zstd")
        total += len(group)
    return total


def read_daily(
    ts_codes: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Read daily data from Parquet, optionally filtered by stock / date range."""
    daily_root = settings.DAILY_DIR
    if not daily_root.exists():
        return pd.DataFrame()

    parts = []
    for pq_file in daily_root.rglob("*.parquet"):
        parts.append(pd.read_parquet(pq_file, columns=columns))

    if not parts:
        return pd.DataFrame()

    df = pd.concat(parts, ignore_index=True)

    if ts_codes:
        df = df[df["ts_code"].isin(ts_codes)]
    if start_date:
        df = df[df["trade_date"] >= start_date]
    if end_date:
        df = df[df["trade_date"] <= end_date]

    return df.reset_index(drop=True)


def write_financial(df: pd.DataFrame) -> None:
    """Write financial data, partitioned by report end_date year."""
    if df.empty:
        return
    settings.FINANCIAL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = settings.FINANCIAL_DIR / "financial.parquet"

    existing = pd.DataFrame()
    if out_path.exists():
        existing = pd.read_parquet(out_path)

    merged = pd.concat([existing, df], ignore_index=True)
    merged = merged.drop_duplicates(subset=["ts_code", "end_date", "report_type"], keep="last")
    merged.to_parquet(out_path, index=False, compression="zstd")


def read_financial(
    ts_codes: list[str] | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    out_path = settings.FINANCIAL_DIR / "financial.parquet"
    if not out_path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(out_path)
    if ts_codes:
        df = df[df["ts_code"].isin(ts_codes)]
    if end_date:
        df = df[df["end_date"] <= end_date]
    return df.reset_index(drop=True)


def get_latest_trade_date() -> str | None:
    """Get the most recent trade date in storage."""
    daily_root = settings.DAILY_DIR
    if not daily_root.exists():
        return None
    dates = []
    for pq_file in daily_root.rglob("*.parquet"):
        df = pd.read_parquet(pq_file, columns=["trade_date"])
        if not df.empty:
            dates.append(df["trade_date"].max())
    return max(dates) if dates else None


def get_stored_stock_codes() -> list[str]:
    """Return all ts_codes that have daily data stored."""
    daily_root = settings.DAILY_DIR
    if not daily_root.exists():
        return []
    codes = set()
    for pq_file in daily_root.rglob("*.parquet"):
        df = pd.read_parquet(pq_file, columns=["ts_code"])
        codes.update(df["ts_code"].unique().tolist())
    return sorted(codes)
