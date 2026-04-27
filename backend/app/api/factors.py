"""API routes for factor discovery and analysis."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from ..data.adjust import compute_adjust_factor
from ..factors.registry import get, create, list_all

router = APIRouter(prefix="/api/factors", tags=["factors"])


@router.get("/")
def list_factors_route(category: str | None = Query(None)):
    factors = list_all()
    if category:
        factors = [f for f in factors if f["category"] == category]
    return factors


@router.get("/{factor_name}")
def get_factor(factor_name: str):
    meta = get(factor_name)
    if meta is None:
        return {"error": f"Factor '{factor_name}' not found"}
    return meta


@router.get("/{factor_name}/values")
def get_factor_values(
    factor_name: str,
    trade_date: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    inst = create(factor_name)
    if inst is None:
        return {"error": f"Factor '{factor_name}' not found"}

    from ..data.store.parquet_store import read_daily, read_financial
    from ..data.store.sqlite_store import get_stock_info
    from ..data.universe import build_universe

    date = trade_date or datetime.now().strftime("%Y%m%d")
    stock_info = get_stock_info()
    if stock_info.empty:
        return []

    universe = build_universe(stock_info, date)

    lookback_days = 420
    start_dt = datetime.strptime(date, "%Y%m%d") - timedelta(days=lookback_days)
    start_date = start_dt.strftime("%Y%m%d")

    daily = read_daily(ts_codes=universe, start_date=start_date, end_date=date)
    if daily.empty:
        return []

    daily = compute_adjust_factor(daily)

    financial = read_financial(ts_codes=universe, end_date=date)
    if not financial.empty:
        fin = financial[financial["end_date"] <= date]
        if not fin.empty:
            latest_fin = fin.sort_values("end_date").groupby("ts_code").last().reset_index()
            merge_cols = ["ts_code"] + [c for c in [
                "roe", "grossprofit_margin", "netprofit_margin",
                "n_income", "cash_flow_oper_act", "total_assets",
                "revenue", "basic_eps", "bps",
            ] if c in latest_fin.columns]
            daily = daily.merge(latest_fin[merge_cols], on="ts_code", how="left")

    kwargs = {}
    if financial is not None and not financial.empty:
        kwargs["financial"] = financial

    df = inst.compute(universe, daily, **kwargs)
    if df is None or df.empty:
        return []

    result = df.nlargest(limit).reset_index()
    result.columns = ["ts_code", "value"]
    return result.to_dict(orient="records")
