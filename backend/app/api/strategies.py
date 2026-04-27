"""API routes for strategy CRUD and execution."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import yaml
from fastapi import APIRouter, HTTPException, Query

from ..core.database import sqlite_session
from ..data.adjust import compute_adjust_factor
from ..data.store.parquet_store import read_daily, read_financial
from ..data.store.sqlite_store import (
    get_stock_info,
    read_signals,
    write_signals,
)
from ..data.universe import build_universe
from ..models.schemas import StrategyConfig, StrategyRunRequest
from ..strategy.config_loader import load_strategy_from_yaml
from ..strategy.scorer import Scorer
from ..strategy.signal_generator import SignalGenerator


MERGE_COLUMNS = [
    "roe", "grossprofit_margin", "netprofit_margin",
    "n_income", "n_income_attr_p", "cash_flow_oper_act",
    "total_assets", "total_liab", "total_hldr_eqy_exc_min_int",
    "revenue", "oper_cost", "basic_eps", "bps",
    "debt_to_assets", "current_ratio",
]


def _enrich_with_financial(
    daily: pd.DataFrame,
    financial: pd.DataFrame,
    trade_date: str,
) -> pd.DataFrame:
    """Merge latest financial report columns into daily rows for each stock."""
    if financial.empty:
        return daily
    fin = financial[financial["end_date"] <= trade_date]
    if fin.empty:
        return daily
    latest_fin = fin.sort_values("end_date").groupby("ts_code").last().reset_index()
    merge_cols = ["ts_code"] + [c for c in MERGE_COLUMNS if c in latest_fin.columns]
    return daily.merge(latest_fin[merge_cols], on="ts_code", how="left")

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("/")
def list_strategies():
    with sqlite_session() as conn:
        rows = conn.execute(
            "SELECT id, name, description, is_active, created_at, updated_at FROM strategies ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/")
def create_strategy(config: StrategyConfig):
    try:
        yaml.safe_load(config.config_yaml)  # Validate YAML
    except yaml.YAMLError as e:
        raise HTTPException(400, f"Invalid YAML: {e}")

    with sqlite_session() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO strategies (id, name, description, config_yaml, is_active, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (config.id, config.name, config.description, config.config_yaml,
             1 if config.is_active else 0, datetime.now().isoformat()),
        )
    return {"status": "ok", "id": config.id}


@router.get("/{strategy_id}")
def get_strategy(strategy_id: str):
    with sqlite_session() as conn:
        row = conn.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Strategy not found")
    return dict(row)


@router.put("/{strategy_id}")
def update_strategy(strategy_id: str, config: StrategyConfig):
    with sqlite_session() as conn:
        row = conn.execute("SELECT id FROM strategies WHERE id = ?", (strategy_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Strategy not found")
        conn.execute(
            """UPDATE strategies SET name=?, description=?, config_yaml=?, is_active=?, updated_at=? WHERE id=?""",
            (config.name, config.description, config.config_yaml,
             1 if config.is_active else 0, datetime.now().isoformat(), strategy_id),
        )
    return {"status": "ok", "id": strategy_id}


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: str):
    with sqlite_session() as conn:
        conn.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))
        conn.execute("DELETE FROM signals WHERE strategy_id = ?", (strategy_id,))
    return {"status": "ok", "id": strategy_id}


@router.post("/{strategy_id}/run")
def run_strategy(strategy_id: str, req: StrategyRunRequest | None = None):
    with sqlite_session() as conn:
        row = conn.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Strategy not found")

    trade_date = (req.trade_date if req and req.trade_date
                  else datetime.now().strftime("%Y%m%d"))

    # Load strategy from YAML
    strategy = load_strategy_from_yaml(row["config_yaml"])

    # Get universe
    stock_info = get_stock_info()
    if stock_info.empty:
        raise HTTPException(500, "No stock info available. Run data refresh first.")

    universe = build_universe(
        stock_info, trade_date,
        exclude_st=strategy.get("universe", {}).get("exclude_ST", True),
        exclude_new_days=strategy.get("universe", {}).get("exclude_new_stock_days", 60),
    )

    if not universe:
        return {"strategy_id": strategy_id, "trade_date": trade_date,
                "signals_count": 0, "buy_count": 0, "sell_count": 0, "status": "empty_universe"}

    # --- Data Loading ---
    # Load enough history for all factors (max: Residual_Momentum ~252 trading days)
    lookback_days = 420
    start_dt = datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=lookback_days)
    start_date = start_dt.strftime("%Y%m%d")

    daily = read_daily(ts_codes=universe, start_date=start_date, end_date=trade_date)
    if daily.empty:
        return {"strategy_id": strategy_id, "trade_date": trade_date,
                "signals_count": 0, "buy_count": 0, "sell_count": 0, "status": "no_daily_data"}

    daily = compute_adjust_factor(daily)

    financial = read_financial(ts_codes=universe, end_date=trade_date)
    if not financial.empty:
        daily = _enrich_with_financial(daily, financial, trade_date)

    daily_snapshot = daily[daily["trade_date"] == trade_date].copy()

    # --- Compute factor scores ---
    scorer = Scorer(strategy.get("factor_weights", {}))
    preprocessing = strategy.get("preprocessing", {})
    scores = scorer.score(universe, daily, preprocessing=preprocessing,
                          financial=financial if not financial.empty else None)

    # Generate signals
    signal_config = strategy.get("signals", {})
    gen = SignalGenerator(signal_config)
    signals = gen.generate(scores, daily_snapshot)

    # Store signals
    write_signals(strategy_id, trade_date, signals)

    buys = sum(1 for s in signals if s["signal_type"] == "buy")
    sells = sum(1 for s in signals if s["signal_type"] == "sell")

    return {
        "strategy_id": strategy_id,
        "trade_date": trade_date,
        "signals_count": len(signals),
        "buy_count": buys,
        "sell_count": sells,
        "status": "ok",
    }


@router.post("/{strategy_id}/validate")
def validate_strategy(strategy_id: str):
    """Validate strategy configuration."""
    with sqlite_session() as conn:
        row = conn.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Strategy not found")

    try:
        strategy = load_strategy_from_yaml(row["config_yaml"])
    except Exception as e:
        return {"valid": False, "error": str(e)}

    errors = []
    warnings = []

    # Check factor weights
    weights = strategy.get("factor_weights", {})
    if len(weights) > 15:
        warnings.append("超过15个因子，建议减少以避免过拟合")

    from ..factors.registry import list_all
    available = {f["name"] for f in list_all()}
    for name in weights:
        if name not in available:
            errors.append(f"未知因子: {name}")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
