"""Scheduled task definitions for daily data refresh and strategy execution."""

from datetime import datetime

from ..core.config import settings
from ..data.pipeline import run_daily_pipeline


def daily_data_refresh():
    """Daily task: refresh all data after market close."""
    trade_date = datetime.now().strftime("%Y%m%d")
    return run_daily_pipeline(trade_date)


def daily_strategy_run():
    """Daily task: run all active strategies."""
    from ..core.database import sqlite_session
    from ..api.strategies import run_strategy
    from ..models.schemas import StrategyRunRequest

    trade_date = datetime.now().strftime("%Y%m%d")

    with sqlite_session() as conn:
        rows = conn.execute(
            "SELECT id FROM strategies WHERE is_active = 1"
        ).fetchall()

    results = {}
    for row in rows:
        try:
            result = run_strategy(row["id"], StrategyRunRequest(trade_date=trade_date))
            results[row["id"]] = result
        except Exception as e:
            results[row["id"]] = {"error": str(e)}

    return results
