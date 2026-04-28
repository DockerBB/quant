"""SQLite-based storage for metadata: stock info, trade calendar, signals."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd

from ...core.database import sqlite_session


def upsert_stock_info(df: pd.DataFrame) -> int:
    with sqlite_session() as conn:
        count = 0
        for _, row in df.iterrows():
            d = row.to_dict()
            d["updated_at"] = datetime.now().isoformat()
            conn.execute(
                """INSERT OR REPLACE INTO stock_info
                   (ts_code, symbol, name, area, industry, market, list_date, delist_date, status, asset_type, updated_at)
                   VALUES (:ts_code, :symbol, :name, :area, :industry, :market,
                           :list_date, :delist_date, :status, :asset_type, :updated_at)""",
                d,
            )
            count += 1
        return count


def get_stock_info(ts_codes: list[str] | None = None) -> pd.DataFrame:
    with sqlite_session() as conn:
        if ts_codes:
            placeholders = ",".join(["?"] * len(ts_codes))
            sql = f"SELECT * FROM stock_info WHERE ts_code IN ({placeholders})"
            return pd.read_sql_query(sql, conn, params=ts_codes)
        return pd.read_sql_query("SELECT * FROM stock_info WHERE status='normal'", conn)


def upsert_trade_calendar(df: pd.DataFrame) -> None:
    with sqlite_session() as conn:
        for _, row in df.iterrows():
            conn.execute(
                "INSERT OR REPLACE INTO trade_calendar (cal_date, is_open, pretrade_date) VALUES (?,?,?)",
                (row["cal_date"], int(row.get("is_open", 1)), row.get("pretrade_date", None)),
            )


def is_trade_day(date_str: str) -> bool:
    with sqlite_session() as conn:
        row = conn.execute(
            "SELECT is_open FROM trade_calendar WHERE cal_date = ?", (date_str,)
        ).fetchone()
        return bool(row and row["is_open"])


def write_signals(
    strategy_id: str,
    date_str: str,
    signals: list[dict[str, Any]],
) -> int:
    with sqlite_session() as conn:
        # Remove old signals for this strategy+date before inserting new ones
        conn.execute(
            "DELETE FROM signals WHERE strategy_id = ? AND date = ?",
            (strategy_id, date_str),
        )
        count = 0
        for s in signals:
            detail = s.get("detail", {})
            conn.execute(
                """INSERT INTO signals
                   (strategy_id, date, ts_code, signal_type, score, percentile, detail_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(strategy_id, date, ts_code) DO UPDATE SET
                       signal_type=excluded.signal_type,
                       score=excluded.score,
                       percentile=excluded.percentile,
                       detail_json=excluded.detail_json""",
                (
                    strategy_id,
                    date_str,
                    s["ts_code"],
                    s["signal_type"],
                    s.get("score"),
                    s.get("percentile"),
                    json.dumps(detail, ensure_ascii=False) if detail else None,
                ),
            )
            count += 1
        return count


def read_signals(
    strategy_id: str | None = None,
    date_str: str | None = None,
    signal_type: str | None = None,
    ts_code: str | None = None,
) -> pd.DataFrame:
    with sqlite_session() as conn:
        where = ["1=1"]
        params: list = []
        if strategy_id:
            where.append("strategy_id = ?"); params.append(strategy_id)
        if date_str:
            where.append("date = ?"); params.append(date_str)
        if signal_type:
            where.append("signal_type = ?"); params.append(signal_type)
        if ts_code:
            where.append("ts_code = ?"); params.append(ts_code)
        sql = f"SELECT * FROM signals WHERE {' AND '.join(where)} ORDER BY date DESC, score DESC"
        return pd.read_sql_query(sql, conn, params=params)
