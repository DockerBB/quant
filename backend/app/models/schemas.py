"""Pydantic models for API request/response schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---- Data ----

class StockInfo(BaseModel):
    ts_code: str
    symbol: str
    name: str
    area: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    list_date: Optional[str] = None
    status: str = "normal"


class DailyBar(BaseModel):
    ts_code: str
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    pre_close: Optional[float] = None
    change: Optional[float] = None
    pct_chg: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    turnover_rate: Optional[float] = None


class DataRefreshRequest(BaseModel):
    data_type: str = "all"
    date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class DataRefreshStatus(BaseModel):
    data_type: str
    last_updated: Optional[str]
    record_count: int
    status: str


# ---- Factors ----

class FactorInfo(BaseModel):
    name: str
    category: str
    description: str
    direction: str = "positive"
    params: Dict[str, Any] = Field(default_factory=dict)


class FactorValue(BaseModel):
    ts_code: str
    factor_name: str
    value: float
    date: str


# ---- Strategies ----

class StrategyConfig(BaseModel):
    id: str
    name: str
    description: str = ""
    is_active: bool = True
    config_yaml: str


class StrategyRunRequest(BaseModel):
    trade_date: Optional[str] = None


class StrategyRunResult(BaseModel):
    strategy_id: str
    trade_date: str
    signals_count: int
    buy_count: int
    sell_count: int
    status: str


# ---- Signals ----

class Signal(BaseModel):
    strategy_id: str
    date: str
    ts_code: str
    signal_type: str
    score: Optional[float] = None
    percentile: Optional[float] = None
    detail: Optional[Dict[str, Any]] = None


class SignalSummary(BaseModel):
    strategy_id: str
    date: str
    buy_count: int
    sell_count: int
    hold_count: int
    top_stocks: List[Signal] = Field(default_factory=list)


# ---- Scheduler ----

class ScheduledTask(BaseModel):
    id: str
    name: str
    task_type: str
    cron_expr: Optional[str] = None
    is_active: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


# ---- Health ----

class HealthCheck(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
