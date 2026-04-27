"""API routes for data: stock list, daily bars, financial, refresh, status."""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query

from ..data.pipeline import (
    refresh_daily,
    refresh_stock_list,
    refresh_trade_calendar,
    run_daily_pipeline,
)
from ..data.store.parquet_store import (
    get_latest_trade_date,
    get_stored_stock_codes,
    read_daily,
    read_financial,
)
from ..data.store.sqlite_store import get_stock_info, is_trade_day
from ..models.schemas import DataRefreshRequest, DataRefreshStatus, StockInfo

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/stock-list", response_model=List[StockInfo])
def get_stock_list(
    status: str = Query("normal", description="normal | st | delisted | all"),
    industry: str | None = Query(None, description="Industry filter"),
):
    df = get_stock_info()
    if df.empty:
        return []

    if status != "all":
        if status == "st":
            df = df[df["status"].str.upper().str.contains("ST", na=False)]
        elif status == "delisted":
            df = df[df["status"].str.contains("delist", case=False, na=False)]
        else:
            df = df[~df["status"].str.upper().str.contains("ST", na=False)]
            df = df[~df["status"].str.contains("delist", case=False, na=False)]

    if industry:
        df = df[df.get("industry", "") == industry]

    return df.to_dict(orient="records")


@router.get("/daily/{ts_code}")
def get_daily(
    ts_code: str,
    start_date: str = Query("20200101"),
    end_date: str | None = Query(None),
    adjust: str = Query("bwd", description="bwd | fwd | none"),
    columns: str | None = Query(None, description="Comma-separated column list"),
):
    col_list = columns.split(",") if columns else None
    df = read_daily(
        ts_codes=[ts_code],
        start_date=start_date,
        end_date=end_date or datetime.now().strftime("%Y%m%d"),
        columns=col_list,
    )
    if df.empty:
        return []
    return df.to_dict(orient="records")


@router.get("/financial/{ts_code}")
def get_financial(ts_code: str, end_date: str | None = Query(None)):
    df = read_financial(ts_codes=[ts_code], end_date=end_date)
    if df.empty:
        return []
    return df.to_dict(orient="records")


@router.get("/trade-days")
def get_trade_days(
    start_date: str = Query("20200101"),
    end_date: str | None = Query(None),
):
    from ..core.database import sqlite_session

    ed = end_date or datetime.now().strftime("%Y%m%d")
    with sqlite_session() as conn:
        rows = conn.execute(
            "SELECT cal_date FROM trade_calendar WHERE cal_date BETWEEN ? AND ? AND is_open=1 ORDER BY cal_date",
            (start_date, ed),
        ).fetchall()
    return [r["cal_date"] for r in rows]


@router.post("/refresh")
def trigger_refresh(req: DataRefreshRequest):
    try:
        results = {}
        if req.data_type == "all":
            results = run_daily_pipeline(req.date)
        elif req.data_type == "daily":
            count = refresh_daily(req.date)
            results["daily"] = {"count": count, "status": "ok" if count > 0 else "empty"}
        elif req.data_type == "stock_list":
            df = refresh_stock_list()
            results["stock_list"] = {"count": len(df), "status": "ok" if len(df) > 0 else "empty"}
        elif req.data_type == "calendar":
            count = refresh_trade_calendar()
            results["calendar"] = {"count": count, "status": "ok" if count > 0 else "empty"}
        elif req.data_type == "financial":
            from ..data.pipeline import refresh_financial_batch
            count = refresh_financial_batch()
            results["financial"] = {"count": count, "status": "ok" if count > 0 else "empty"}
        else:
            raise HTTPException(400, f"Unknown data_type: {req.data_type}")
        return {"status": "ok", "results": results}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/status")
def get_data_status():
    from ..core.database import sqlite_session

    items = {}
    with sqlite_session() as conn:
        rows = conn.execute(
            """SELECT data_type, MAX(date) as last_date, COUNT(*) as cnt,
                      MAX(finished_at) as last_finished
               FROM daily_update_log WHERE status='success'
               GROUP BY data_type"""
        ).fetchall()
        for r in rows:
            items[r["data_type"]] = DataRefreshStatus(
                data_type=r["data_type"],
                last_updated=r["last_date"],
                record_count=r["cnt"],
                status="healthy" if r["last_date"] else "empty",
            )
    return items
