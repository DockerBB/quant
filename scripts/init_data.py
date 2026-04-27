#!/usr/bin/env python
"""Initialize all data: stock list, daily history, financial, trade calendar.

Usage:
    python scripts/init_data.py              # full init
    python scripts/init_data.py --daily      # daily data only
    python scripts/init_data.py --financial  # financial data only
"""

import argparse
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import settings
from app.core.database import init_metadata_tables
from app.data.pipeline import (
    refresh_daily,
    refresh_financial_batch,
    refresh_stock_list,
    refresh_trade_calendar,
    run_daily_pipeline,
)


def main():
    parser = argparse.ArgumentParser(description="Initialize quant system data")
    parser.add_argument("--daily", action="store_true", help="Initialize daily data only")
    parser.add_argument("--financial", action="store_true", help="Initialize financial data only")
    parser.add_argument("--full", action="store_true", help="Full initialization (default)")
    args = parser.parse_args()

    # Ensure directories exist
    settings.ensure_dirs()
    init_metadata_tables()

    if not any([args.daily, args.financial]):
        args.full = True

    print("=" * 50)
    print("Quant System Data Initialization")
    print("=" * 50)

    if args.full:
        print("\n[1/4] Initializing stock list...")
        stock_df = refresh_stock_list()
        print(f"  -> {len(stock_df)} stocks loaded")

        print("\n[2/4] Initializing trade calendar...")
        cal_count = refresh_trade_calendar()
        print(f"  -> {cal_count} calendar entries loaded")

        print("\n[3/4] Initializing daily data (this may take a while)...")
        daily_count = refresh_daily()
        print(f"  -> {daily_count} daily records loaded")

        print("\n[4/4] Initializing financial data (this may take several minutes)...")
        fin_count = refresh_financial_batch()
        print(f"  -> {fin_count} financial records loaded")

    if args.daily:
        print("\nInitializing daily data...")
        count = refresh_daily()
        print(f"  -> {count} daily records loaded")

    if args.financial:
        print("\nInitializing financial data...")
        count = refresh_financial_batch()
        print(f"  -> {count} financial records loaded")

    print("\n" + "=" * 50)
    print("Data initialization complete!")
    print("=" * 50)
    print(f"Data directory: {settings.DATA_DIR}")
    print(f"SQLite database: {settings.SQLITE_PATH}")


if __name__ == "__main__":
    main()
