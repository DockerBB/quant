"""Backfill historical daily data for ETFs using akshare.
Uses the AkshareFetcher._fetch_etf_daily() method which calls fund_etf_hist_em.
Single-threaded with batched parquet writes.

Usage:
    python scripts/backfill_etf_history.py              # all ETFs, from 2024-01-01
    python scripts/backfill_etf_history.py --limit 100  # first 100 ETFs
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pandas as pd

from app.core.config import settings
from app.data.fetcher.akshare_fetcher import AkshareFetcher


fetcher = AkshareFetcher()


def fetch_one_etf(symbol: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    """Fetch a single ETF via akshare, return standardized DataFrame or None."""
    try:
        df = fetcher._fetch_etf_daily(symbol, start_date, end_date)
        if df is None or df.empty:
            return pd.DataFrame()
        # Add standard columns expected by the pipeline
        df["adj_factor"] = 1.0
        df["is_st"] = 0
        if "pre_close" not in df.columns:
            df["pre_close"] = None
        return df
    except Exception:
        return None


def write_parquet(frames: list[pd.DataFrame]) -> int:
    """Batch write DataFrames to partitioned parquet (same as backfill_history.py)."""
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
    parser = argparse.ArgumentParser(description="Backfill ETF historical daily data")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--from", dest="start", default="20240101")
    parser.add_argument("--batch", type=int, default=300)
    args = parser.parse_args()

    end_date = datetime.now().strftime("%Y%m%d")

    from app.core.database import sqlite_session
    with sqlite_session() as conn:
        rows = conn.execute(
            "SELECT ts_code, symbol FROM stock_info WHERE status='normal' AND asset_type='etf' ORDER BY ts_code"
        ).fetchall()

    all_codes = [(r["symbol"], r["ts_code"]) for r in rows]
    if args.limit:
        all_codes = all_codes[:args.limit]

    print(f"Target: {len(all_codes)} ETFs, {args.start} ~ {end_date}")
    print("=" * 60)

    success = 0
    empty = 0
    errors = 0
    batch_frames: list[pd.DataFrame] = []
    t0 = time.time()

    for i, (symbol, ts_code) in enumerate(all_codes):
        df = None
        for retry in range(3):
            df = fetch_one_etf(symbol, args.start, end_date)
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
        if (i + 1) % 100 == 0 or i == len(all_codes) - 1:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(all_codes) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{len(all_codes)}] ok={success} empty={empty} err={errors} "
                  f"| {rate:.1f} etf/s | ETA {eta:.0f}s")

        time.sleep(0.3)  # Rate limiting for akshare

    # Final flush
    if batch_frames:
        write_parquet(batch_frames)

    elapsed = time.time() - t0
    print("=" * 60)
    print(f"Done! {success} ETFs, {empty} empty, {errors} errors")
    print(f"Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")

    from app.data.store.parquet_store import read_daily

    daily = read_daily()
    print(f"Total rows: {len(daily):,}, codes: {daily['ts_code'].nunique():,}")
    print(f"Date range: {daily['trade_date'].min()} ~ {daily['trade_date'].max()}")


if __name__ == "__main__":
    main()
