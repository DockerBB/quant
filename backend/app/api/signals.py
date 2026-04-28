"""API routes for signal queries."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from ..data.store.sqlite_store import read_signals

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/")
def get_signals(
    strategy_id: str | None = Query(None),
    date: str | None = Query(None),
    signal_type: str | None = Query(None),
    ts_code: str | None = Query(None),
):
    df = read_signals(
        strategy_id=strategy_id,
        date_str=date or datetime.now().strftime("%Y%m%d"),
        signal_type=signal_type,
        ts_code=ts_code,
    )
    if df.empty:
        return []
    return df.to_dict(orient="records")


@router.get("/{strategy_id}/current")
def get_current_signals(strategy_id: str):
    from ..core.database import sqlite_session

    with sqlite_session() as conn:
        row = conn.execute(
            "SELECT MAX(date) FROM signals WHERE strategy_id = ?", (strategy_id,)
        ).fetchone()
        latest_date = row[0] if row else None

        if not latest_date:
            return {"date": None, "buys": [], "sells": [], "holds": []}

        # Join with stock_info to get industry
        rows = conn.execute(
            """SELECT s.ts_code, s.signal_type, s.score, s.percentile, s.date,
                      si.industry
               FROM signals s
               LEFT JOIN stock_info si ON s.ts_code = si.ts_code
               WHERE s.strategy_id = ? AND s.date = ?
               ORDER BY s.score DESC""",
            (strategy_id, latest_date),
        ).fetchall()

    buys, sells, holds = [], [], []
    for r in rows:
        item = {"ts_code": r["ts_code"], "signal_type": r["signal_type"],
                "score": r["score"], "percentile": r["percentile"], "date": r["date"],
                "industry": r["industry"] or ""}
        if r["signal_type"] == "buy":
            buys.append(item)
        elif r["signal_type"] == "sell":
            sells.append(item)
        else:
            holds.append(item)

    return {"date": latest_date, "buys": buys, "sells": sells, "holds": holds}


@router.get("/{strategy_id}/summary")
def get_signal_summary(strategy_id: str):
    current = get_current_signals(strategy_id)
    return {
        "strategy_id": strategy_id,
        "date": current["date"],
        "buy_count": len(current["buys"]),
        "sell_count": len(current["sells"]),
        "hold_count": len(current["holds"]),
    }


@router.get("/{strategy_id}/history")
def get_signal_history(
    strategy_id: str,
    start_date: str = Query("20200101"),
    end_date: str | None = Query(None),
):
    df = read_signals(
        strategy_id=strategy_id,
        date_str=None,  # all dates
    )
    if df.empty:
        return []
    if start_date:
        df = df[df["date"] >= start_date]
    if end_date:
        df = df[df["date"] <= end_date]
    return df.to_dict(orient="records")
