"""Baostock-based data fetcher — fallback / cross-validation source.

Provides daily OHLCV with built-in adjustment factors, financial data,
and trading calendar. More stable API than akshare but less comprehensive.
"""

import time

import baostock as bs
import pandas as pd

from .base import DataFetcher


class BaostockFetcher(DataFetcher):
    source_name = "baostock"

    def __init__(self):
        self._logged_in = False

    def _ensure_login(self):
        if not self._logged_in:
            lg = bs.login()
            if lg.error_code != "0":
                raise RuntimeError(f"Baostock login failed: {lg.error_msg}")
            self._logged_in = True

    def _logout(self):
        if self._logged_in:
            bs.logout()
            self._logged_in = False

    @staticmethod
    def _normalize_code(ts_code: str) -> str:
        """Convert '000001.SZ' to 'sz.000001'."""
        if "." in ts_code:
            num, mkt = ts_code.split(".")
            return f"{mkt.lower()}.{num}"
        return ts_code

    @staticmethod
    def _to_ts_code(baostock_code: str) -> str:
        """Convert 'sz.000001' to '000001.SZ'."""
        if "." in baostock_code:
            mkt, num = baostock_code.split(".")
            return f"{num}.{mkt.upper()}"
        return baostock_code

    @staticmethod
    def _fmt_date(date_str: str) -> str:
        """Convert to YYYY-MM-DD for baostock API."""
        d = date_str.replace("-", "")
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"

    def fetch_daily(
        self, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        self._ensure_login()
        try:
            bs_code = self._normalize_code(ts_code)
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,preclose,volume,amount,turn,tradestatus,isST,adjustflag",
                start_date=self._fmt_date(start_date),
                end_date=self._fmt_date(end_date),
                frequency="d",
                adjustflag="2",
            )
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=[
                "trade_date", "open", "high", "low", "close", "pre_close",
                "vol", "amount", "turnover_rate", "trade_status", "is_st", "adj_flag"
            ])
            numeric = ["open", "high", "low", "close", "pre_close", "vol", "amount", "turnover_rate"]
            df[numeric] = df[numeric].apply(pd.to_numeric, errors="coerce")
            df["ts_code"] = self._to_ts_code(bs_code)
            # baostock '2' adjustflag means backward-adjusted prices
            df["adj_factor"] = 1.0
            df["is_st"] = df["is_st"].apply(lambda x: 1 if x == "1" else 0)

            keep = ["ts_code", "trade_date", "open", "high", "low", "close",
                    "pre_close", "vol", "amount", "turnover_rate",
                    "adj_factor", "trade_status", "is_st"]
            return df[[c for c in keep if c in df.columns]]
        except Exception as e:
            print(f"[baostock] fetch_daily error for {ts_code}: {e}")
            return pd.DataFrame()

    def fetch_all_daily(self, trade_date: str) -> pd.DataFrame:
        """Baostock doesn't have a single-call snapshot; fetch per-stock via query_all_stock."""
        self._ensure_login()
        try:
            stocks = self.fetch_stock_list()
            if stocks.empty:
                return pd.DataFrame()

            frames = []
            for ts_code in stocks["ts_code"]:
                df = self.fetch_daily(ts_code, trade_date, trade_date)
                if not df.empty:
                    frames.append(df)
                time.sleep(0.02)
            return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        except Exception as e:
            print(f"[baostock] fetch_all_daily error: {e}")
            return pd.DataFrame()

    def fetch_stock_list(self) -> pd.DataFrame:
        self._ensure_login()
        try:
            rs = bs.query_stock_basic()
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=["ts_code", "name", "ipoDate", "outDate", "type", "status"])
            df["ts_code"] = df["ts_code"].apply(self._to_ts_code)
            return df[df["type"] == "1"][["ts_code", "name"]]
        except Exception as e:
            print(f"[baostock] fetch_stock_list error: {e}")
            return pd.DataFrame()

    def fetch_financial(
        self, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Fetch profit data and balance sheet from baostock."""
        self._ensure_login()
        try:
            bs_code = self._normalize_code(ts_code)
            # Determine year range
            start_year = int(start_date[:4])
            end_year = int(end_date[:4])
            frames = []
            for year in range(start_year, end_year + 1):
                for quarter in [1, 2, 3, 4]:
                    rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
                    rows = []
                    while rs.next():
                        rows.append(rs.get_row_data())
                    if rows:
                        cols = rs.fields if hasattr(rs, 'fields') else ["code", "pubDate", "statDate", "roeAvg",
                              "npMargin", "gpMargin", "netProfit", "epsTTM", "MBRevenue", "totalShare", "liqaShare"]
                        part = pd.DataFrame(rows, columns=cols)
                        part["ts_code"] = ts_code
                        frames.append(part)
                    time.sleep(0.05)
            return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        except Exception as e:
            print(f"[baostock] fetch_financial error for {ts_code}: {e}")
            return pd.DataFrame()

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        self._ensure_login()
        try:
            rs = bs.query_trade_dates(
                start_date=self._fmt_date(start_date),
                end_date=self._fmt_date(end_date),
            )
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=["calendar_date", "is_trading_day"])
            df = df.rename(columns={
                "calendar_date": "cal_date",
                "is_trading_day": "is_open",
            })
            df["is_open"] = df["is_open"].astype(int)
            return df
        except Exception as e:
            print(f"[baostock] fetch_trade_calendar error: {e}")
            return pd.DataFrame()

    def fetch_industry_classification(self) -> pd.DataFrame:
        """Baostock doesn't provide industry classification directly."""
        return pd.DataFrame()

    def __del__(self):
        self._logout()
