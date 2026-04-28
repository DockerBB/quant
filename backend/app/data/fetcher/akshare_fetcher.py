"""Akshare-based data fetcher — primary source for A-share market data.

Uses akshare free API for: stock list, daily OHLCV, financial indicators,
trade calendar, industry classification, fund flows.
"""

import time
from datetime import datetime, timedelta

import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None  # type: ignore

from .base import DataFetcher


class AkshareFetcher(DataFetcher):
    source_name = "akshare"

    @staticmethod
    def _normalize_code(ts_code: str) -> str:
        """Convert '000001.SZ' or '600000.SH' to akshare symbol '000001' / '600000'."""
        return ts_code.split(".")[0] if "." in ts_code else ts_code

    @staticmethod
    def _to_ts_code(symbol: str) -> str:
        """Convert akshare symbol to standard ts_code format (e.g. '000001.SZ')."""
        s = str(symbol).lower()
        # Handle prefixed codes: sh600000 / sz000001 / bj920000
        for prefix, exchange in [("sh", "SH"), ("sz", "SZ"), ("bj", "BJ")]:
            if s.startswith(prefix) and len(s) > len(prefix):
                return f"{s[len(prefix):]}.{exchange}"
        # Handle 6-digit numeric codes
        if s.isdigit() and len(s) == 6:
            if s.startswith(("0", "3")):
                return f"{s}.SZ"
            if s.startswith(("6", "9")):
                return f"{s}.SH"
            if s.startswith("92"):                    # BSE new codes (920xxx)
                return f"{s}.BJ"
            if s.startswith(("4", "8")):
                return f"{s}.BJ"
            if s.startswith("5"):
                return f"{s}.SH"
            if s.startswith("1"):
                return f"{s}.SZ"
        return symbol

    @staticmethod
    def _is_etf_code(ts_code: str) -> bool:
        """Detect ETF/LOD by ts_code prefix (5=SH-ETF, 1=SZ-ETF/LOF)."""
        code_num = ts_code.split(".")[0] if "." in ts_code else ts_code
        return code_num.startswith(("5", "1")) and code_num.isdigit() and len(code_num) == 6

    @staticmethod
    def _normalize_spot_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize spot data column names for both stocks and ETFs."""
        rename = {
            "代码": "symbol", "名称": "name", "最新价": "close",
            "涨跌幅": "pct_chg", "涨跌额": "change", "成交量": "vol",
            "成交额": "amount", "昨收": "pre_close", "换手率": "turnover_rate",
            "今开": "open", "最高": "high", "最低": "low", "振幅": "amplitude",
            "市盈率-动态": "pe", "市净率": "pb", "总市值": "total_mv", "流通市值": "circ_mv",
            "开盘价": "open", "最高价": "high", "最低价": "low",
        }
        return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    def fetch_daily(
        self, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        symbol = self._normalize_code(ts_code)

        # Route ETF codes to ETF-specific daily API
        if self._is_etf_code(ts_code):
            return self._fetch_etf_daily(symbol, start_date, end_date)

        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="",
            )
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.rename(columns={
                "日期": "trade_date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "vol",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "pct_chg",
                "涨跌额": "change",
                "换手率": "turnover_rate",
            })
            df["ts_code"] = self._to_ts_code(symbol)
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
            keep = ["ts_code", "trade_date", "open", "high", "low", "close",
                    "vol", "amount", "pct_chg", "change", "turnover_rate"]
            return df[[c for c in keep if c in df.columns]]
        except Exception as e:
            print(f"[akshare] fetch_daily error for {ts_code}: {e}")
            return pd.DataFrame()

    def _fetch_etf_daily(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch single ETF daily OHLCV using fund_etf_hist_em."""
        try:
            df = ak.fund_etf_hist_em(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="",
            )
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.rename(columns={
                "日期": "trade_date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "vol",
                "成交额": "amount", "振幅": "amplitude", "涨跌幅": "pct_chg",
                "涨跌额": "change", "换手率": "turnover_rate",
            })
            df["ts_code"] = self._to_ts_code(symbol)
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
            keep = ["ts_code", "trade_date", "open", "high", "low", "close",
                    "vol", "amount", "pct_chg", "change", "turnover_rate"]
            return df[[c for c in keep if c in df.columns]]
        except Exception as e:
            print(f"[akshare] fetch_etf_daily error for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_all_daily(self, trade_date: str) -> pd.DataFrame:
        """Fetch snapshot for all stocks + ETFs on a given date."""
        frames = []

        # 1. Stock snapshots
        try:
            stock_df = ak.stock_zh_a_spot()
            if stock_df is not None and not stock_df.empty:
                stock_df = self._normalize_spot_columns(stock_df)
                stock_df["ts_code"] = stock_df["symbol"].apply(self._to_ts_code)
                stock_df["trade_date"] = trade_date
                frames.append(stock_df)
        except Exception as e:
            print(f"[akshare] fetch_all_daily stock error: {e}")

        # 2. BSE stock snapshots
        try:
            bse_df = ak.stock_bj_a_spot_em()
            if bse_df is not None and not bse_df.empty:
                bse_df = self._normalize_spot_columns(bse_df)
                bse_df["ts_code"] = bse_df["symbol"].apply(self._to_ts_code)
                bse_df["trade_date"] = trade_date
                frames.append(bse_df)
        except Exception as e:
            print(f"[akshare] fetch_all_daily bse error: {e}")

        # 3. ETF snapshots
        try:
            etf_df = ak.fund_etf_spot_em()
            if etf_df is not None and not etf_df.empty:
                etf_df = self._normalize_spot_columns(etf_df)
                etf_df["ts_code"] = etf_df["symbol"].apply(self._to_ts_code)
                etf_df["trade_date"] = trade_date
                frames.append(etf_df)
        except Exception as e:
            print(f"[akshare] fetch_all_daily etf error: {e}")

        if not frames:
            return pd.DataFrame()

        result = pd.concat(frames, ignore_index=True)

        # ETF spot data lacks OHLC/vol — fill from available close data
        etf_flag = result["ts_code"].apply(self._is_etf_code)
        if etf_flag.any() and "close" in result.columns:
            for col in ["open", "high", "low"]:
                if col in result.columns:
                    result.loc[etf_flag & result[col].isna(), col] = result.loc[etf_flag, "close"]
            if "vol" in result.columns:
                result.loc[etf_flag & result["vol"].isna(), "vol"] = 1

        keep = ["ts_code", "trade_date", "open", "high", "low", "close",
                "pre_close", "pct_chg", "change", "vol", "amount", "turnover_rate"]
        return result[[c for c in keep if c in result.columns]]

    def fetch_etf_list(self) -> pd.DataFrame:
        """Fetch ETF list using akshare fund_etf_spot_em."""
        try:
            df = ak.fund_etf_spot_em()
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.rename(columns={"代码": "symbol", "名称": "name"})
            df["ts_code"] = df["symbol"].apply(self._to_ts_code)
            return df[["ts_code", "name"]]
        except Exception as e:
            print(f"[akshare] fetch_etf_list error: {e}")
            return pd.DataFrame()

    def fetch_stock_list(self) -> pd.DataFrame:
        try:
            df = ak.stock_info_a_code_name()
            if df is None or df.empty:
                df = pd.DataFrame()
            else:
                df = df.rename(columns={"code": "ts_code", "name": "name"})
                df["ts_code"] = df["ts_code"].apply(self._to_ts_code)
                df = df[["ts_code", "name"]]
        except Exception as e:
            print(f"[akshare] fetch_stock_list error: {e}")
            df = pd.DataFrame()

        df["asset_type"] = "stock"

        # Append ETFs
        etf_df = self.fetch_etf_list()
        if not etf_df.empty:
            etf_df["asset_type"] = "etf"
            df = pd.concat([df, etf_df], ignore_index=True)

        return df[["ts_code", "name", "asset_type"]]

    def fetch_financial(
        self, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Fetch financial indicators via akshare."""
        symbol = self._normalize_code(ts_code)
        try:
            df = ak.stock_financial_abstract(symbol=symbol)
            if df is None or df.empty:
                return pd.DataFrame()
            df["ts_code"] = ts_code
            rename_map = {
                "截止日期": "end_date",
                "总资产": "total_assets",
                "总负债": "total_liab",
                "归属于母公司股东权益合计": "total_hldr_eqy_exc_min_int",
                "营业总收入": "revenue",
                "营业收入": "revenue",
                "营业成本": "oper_cost",
                "销售费用": "sell_exp",
                "管理费用": "admin_exp",
                "财务费用": "fin_exp",
                "净利润": "n_income",
                "归属于母公司股东的净利润": "n_income_attr_p",
                "经营活动产生的现金流量净额": "cash_flow_oper_act",
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
            keep = ["ts_code", "end_date"] + [v for v in rename_map.values() if v in df.columns]
            return df[[c for c in keep if c in df.columns]]
        except Exception as e:
            print(f"[akshare] fetch_financial error for {ts_code}: {e}")
            return pd.DataFrame()

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            df = ak.tool_trade_date_hist_sina()
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.rename(columns={"trade_date": "cal_date"})
            df["cal_date"] = pd.to_datetime(df["cal_date"]).dt.strftime("%Y%m%d")
            df["is_open"] = 1
            mask = (df["cal_date"] >= start_date) & (df["cal_date"] <= end_date)
            return df[mask].reset_index(drop=True)
        except Exception as e:
            print(f"[akshare] fetch_trade_calendar error: {e}")
            return pd.DataFrame()

    def fetch_industry_classification(self) -> pd.DataFrame:
        """Fetch 申万 industry classification."""
        try:
            df = ak.stock_info_a_code_name()
            if df is None or df.empty:
                return pd.DataFrame()
            keep_cols = ["code"]
            rename = {"code": "ts_code"}
            if "industry" in df.columns:
                keep_cols.append("industry")
            result = df[keep_cols].rename(columns=rename)
            result["source"] = "ShenWan"
            return result
        except Exception as e:
            print(f"[akshare] fetch_industry error: {e}")
            return pd.DataFrame()

    def fetch_fund_flow(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch northbound / main fund flow."""
        try:
            symbol = self._normalize_code(ts_code)
            df = ak.stock_individual_fund_flow(stock=symbol, market="sh" if ts_code.endswith("SH") else "sz")
            if df is None or df.empty:
                return pd.DataFrame()
            df["ts_code"] = ts_code
            return df
        except Exception:
            return pd.DataFrame()
