"""Database connection management: SQLite (metadata) + optional DuckDB (analytics)."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

try:
    import duckdb
    _has_duckdb = True
except ImportError:
    _has_duckdb = False

from .config import settings


def get_sqlite_path() -> Path:
    return settings.SQLITE_PATH


def get_sqlite_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_sqlite_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def sqlite_session():
    conn = get_sqlite_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_duckdb_conn():
    if not _has_duckdb:
        raise ImportError("duckdb is not installed. Install with: pip install duckdb")
    return duckdb.connect()


def init_metadata_tables() -> None:
    with sqlite_session() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS stock_info (
            ts_code       TEXT PRIMARY KEY,
            symbol        TEXT NOT NULL,
            name          TEXT NOT NULL,
            area          TEXT,
            industry      TEXT,
            market        TEXT,
            list_date     TEXT,
            delist_date   TEXT,
            status        TEXT DEFAULT 'normal',
            asset_type    TEXT DEFAULT 'stock',
            updated_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS trade_calendar (
            cal_date   TEXT PRIMARY KEY,
            is_open    INTEGER NOT NULL DEFAULT 1,
            pretrade_date TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_update_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            date       TEXT NOT NULL,
            data_type  TEXT NOT NULL,
            status     TEXT NOT NULL,
            record_count INTEGER DEFAULT 0,
            message    TEXT,
            started_at TEXT,
            finished_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS factor_metadata (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT UNIQUE NOT NULL,
            category    TEXT NOT NULL,
            description TEXT,
            direction   TEXT NOT NULL DEFAULT 'positive',
            params_json TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS strategies (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT,
            config_yaml TEXT NOT NULL,
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id TEXT NOT NULL,
            date        TEXT NOT NULL,
            ts_code     TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            score       REAL,
            percentile  REAL,
            detail_json TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(strategy_id, date, ts_code)
        );

        CREATE TABLE IF NOT EXISTS scheduler_tasks (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            task_type   TEXT NOT NULL,
            cron_expr   TEXT,
            is_active   INTEGER DEFAULT 1,
            last_run    TEXT,
            next_run    TEXT,
            config_json TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_signals_strategy_date ON signals(strategy_id, date);
        CREATE INDEX IF NOT EXISTS idx_signals_ts_code ON signals(ts_code);
        CREATE INDEX IF NOT EXISTS idx_daily_update_date ON daily_update_log(date);
        """)

        # Migration: add asset_type column for existing databases
        try:
            conn.execute("ALTER TABLE stock_info ADD COLUMN asset_type TEXT DEFAULT 'stock'")
        except Exception:
            pass  # Column already exists
