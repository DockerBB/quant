"""Backfill historical daily data for all stocks using baostock.
Single-threaded with batched parquet writes — reliable and optimized.

Usage:
    python scripts/backfill_history.py              # all stocks, from 2024-01-01
    python scripts/backfill_history.py --limit 500  # first 500 stocks
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import baostock as bs
import pandas as pd

from app.core.config import settings


def fetch(bs_code: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    """Fetch one stock, return DataFrame or None on failure."""
    sd = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
    ed = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,open,high,low,close,preclose,volume,amount,turn,tradestatus,isST",
        start_date=sd, end_date=ed, frequency="d", adjustflag="2",
    )
    if rs is None:
        return None
    rows = []
    while rs.next():
        rows.append(rs.get_row_data())
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[
        "trade_date", "open", "high", "low", "close", "pre_close",
        "vol", "amount", "turnover_rate", "trade_status", "is_st"
    ])
    numeric = ["open", "high", "low", "close", "pre_close", "vol", "amount", "turnover_rate"]
    df[numeric] = df[numeric].apply(pd.to_numeric, errors="coerce")
    df["adj_factor"] = 1.0
    df["is_st"] = df["is_st"].apply(lambda x: 1 if x == "1" else 0)
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
    keep = ["ts_code", "trade_date", "open", "high", "low", "close",
            "pre_close", "vol", "amount", "turnover_rate",
            "adj_factor", "trade_status", "is_st"]
    return df[[c for c in keep if c in df.columns]]


def write_parquet(frames: list[pd.DataFrame]) -> int:
    """Batch write DataFrames to partitioned parquet."""
    if not frames:
        return 0
    big = pd.concat(frames, ignore_index=True)
    total = 0
    for (year, month), group in big.groupby(
        [big["trade_date"].str[:4], big["trade_date"].str[4:6]]
    ):
        out_path = settings.DAILY_DIR / year / month / f"{year}-{month}.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists():
            existing = pd.read_parquet(out_path)
            group = pd.concat([existing, group], ignore_index=True)
        group = group.drop_duplicates(subset=["ts_code", "trade_date"], keep="last")
        group.sort_values(["trade_date", "ts_code"], inplace=True)
        group.to_parquet(out_path, index=False, compression="zstd")
        total += len(group)
    return total


def main():
    parser = argparse.ArgumentParser(description="Backfill historical daily data")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--from", dest="start", default="20240101")
    parser.add_argument("--batch", type=int, default=300)
    args = parser.parse_args()

    end_date = datetime.now().strftime("%Y%m%d")

    from app.core.database import sqlite_session
    with sqlite_session() as conn:
        rows = conn.execute(
            "SELECT ts_code FROM stock_info WHERE status='normal' ORDER BY ts_code"
        ).fetchall()

    all_codes = [r["ts_code"] for r in rows]
    if args.limit:
        all_codes = all_codes[:args.limit]

    print(f"Target: {len(all_codes)} stocks, {args.start} ~ {end_date}")
    print("=" * 60)

    lg = bs.login()
    if lg.error_code != "0":
        print(f"Login failed: {lg.error_msg}")
        sys.exit(1)

    success = 0
    empty = 0
    errors = 0
    batch_frames: list[pd.DataFrame] = []
    t0 = time.time()

    for i, ts_code in enumerate(all_codes):
        num, mkt = ts_code.split(".")
        bs_code = f"{mkt.lower()}.{num}"

        df = None
        for retry in range(3):
            df = fetch(bs_code, args.start, end_date)
            if df is not None:
                break
            time.sleep(0.5)

        if df is None:
            errors += 1
        elif df.empty:
            empty += 1
        else:
            df["ts_code"] = ts_code
            batch_frames.append(df)
            success += 1

        # Flush batch
        if len(batch_frames) >= args.batch:
            write_parquet(batch_frames)
            batch_frames = []

        # Progress
        if (i + 1) % args.batch == 0 or i == len(all_codes) - 1:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(all_codes) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{len(all_codes)}] ok={success} empty={empty} err={errors} "
                  f"| {rate:.1f} stk/s | ETA {eta:.0f}s")

        time.sleep(0.03)

    # Final flush
    if batch_frames:
        write_parquet(batch_frames)

    bs.logout()

    elapsed = time.time() - t0
    print("=" * 60)
    print(f"Done! {success} stocks, {empty} empty, {errors} errors")
    print(f"Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")

    from app.data.store.parquet_store import read_daily
    daily = read_daily()
    print(f"Total rows: {len(daily)}, stocks: {daily['ts_code'].nunique()}")
    print(f"Date range: {daily['trade_date'].min()} ~ {daily['trade_date'].max()}")


if __name__ == "__main__":
    main()
