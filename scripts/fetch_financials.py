"""Fetch financial data for all A-share stocks using batch APIs.

Uses akshare's 东方财富 batch endpoints — fetches all stocks in one call per quarter.
MUCH faster than per-stock queries (~10s per quarter vs hours).

Usage:
    python scripts/fetch_financials.py
    python scripts/fetch_financials.py --from 2023
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import akshare as ak
import pandas as pd

from app.core.config import settings
from app.data.store.parquet_store import write_financial


def ts_code_from_em(code: str) -> str:
    """Convert 东方财富 code to standard ts_code (e.g. '000001' -> '000001.SZ')."""
    c = str(code).zfill(6)
    if c.startswith(('0', '3')):
        return f"{c}.SZ"
    if c.startswith(('6', '9')):
        return f"{c}.SH"
    if c.startswith(('4', '8')):
        return f"{c}.BJ"
    return c


def fetch_quarter(date_str: str) -> pd.DataFrame:
    """Fetch 业绩报表 for a given YYYYMMDD reporting date."""
    df = ak.stock_yjbb_em(date=date_str)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={
        "股票代码": "symbol",
        "股票简称": "name",
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
    })
    df["ts_code"] = df["symbol"].apply(ts_code_from_em)
    df["end_date"] = date_str
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="start_year", type=int, default=2023)
    args = parser.parse_args()

    now = datetime.now()
    end_year = now.year

    # Build list of quarter-end dates
    quarters = []
    for y in range(args.start_year, end_year + 1):
        for m in ["0331", "0630", "0930", "1231"]:
            date_str = f"{y}{m}"
            if date_str > now.strftime("%Y%m%d"):
                break
            quarters.append(date_str)

    print(f"Fetching {len(quarters)} quarters: {quarters[0]} ~ {quarters[-1]}")
    print("=" * 60)

    all_frames = []
    t0 = time.time()

    for q in quarters:
        try:
            df = fetch_quarter(q)
            if df.empty:
                print(f"  {q}: empty")
            else:
                all_frames.append(df)
                elapsed = time.time() - t0
                print(f"  {q}: {len(df)} stocks | {elapsed:.0f}s elapsed")
            time.sleep(0.5)
        except Exception as e:
            print(f"  {q}: ERROR - {e}")
            time.sleep(1)

    elapsed = time.time() - t0
    print("=" * 60)

    if not all_frames:
        print("No data fetched!")
        sys.exit(1)

    big = pd.concat(all_frames, ignore_index=True)

    # Keep only A-share stocks (codes we recognize)
    big = big[big["ts_code"].str.match(r"^\d{6}\.(SZ|SH|BJ)$")]
    print(f"Total financial records: {len(big)}")
    print(f"Unique stocks: {big['ts_code'].nunique()}")
    print(f"Quarters: {sorted(big['end_date'].unique())}")

    # Select and order columns
    keep = ["ts_code", "end_date", "revenue", "revenue_yoy", "n_income",
            "netprofit_yoy", "roe", "grossprofit_margin", "bps", "basic_eps",
            "cash_flow_oper_act", "industry"]
    big = big[[c for c in keep if c in big.columns]]

    # Convert numeric
    for col in ["revenue", "n_income", "roe", "grossprofit_margin", "bps",
                "basic_eps", "cash_flow_oper_act", "revenue_yoy", "netprofit_yoy"]:
        if col in big.columns:
            big[col] = pd.to_numeric(big[col], errors="coerce")

    # Merge with existing data — preserve history
    settings.FINANCIAL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = settings.FINANCIAL_DIR / "financial.parquet"
    if out_path.exists():
        existing = pd.read_parquet(out_path)
        big = pd.concat([existing, big], ignore_index=True)

    # Keep latest per ts_code + end_date
    big = big.drop_duplicates(subset=["ts_code", "end_date"], keep="last")
    big.to_parquet(out_path, index=False, compression="zstd")
    print(f"Written to {out_path} ({len(big)} records total)")
    print(f"Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")


if __name__ == "__main__":
    main()
