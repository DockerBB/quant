"""Abstract base class for data fetchers."""

from abc import ABC, abstractmethod

import pandas as pd


class DataFetcher(ABC):
    """Interface for market data providers."""

    source_name: str = "base"

    @abstractmethod
    def fetch_daily(
        self, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Fetch daily OHLCV for a single stock."""

    @abstractmethod
    def fetch_all_daily(self, trade_date: str) -> pd.DataFrame:
        """Fetch daily OHLCV snapshot for all stocks on a given date."""

    @abstractmethod
    def fetch_stock_list(self) -> pd.DataFrame:
        """Fetch full stock list with basic info."""

    @abstractmethod
    def fetch_financial(
        self, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Fetch financial statements / indicators."""

    @abstractmethod
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch trading calendar."""

    @abstractmethod
    def fetch_industry_classification(self) -> pd.DataFrame:
        """Fetch industry classification (申万)."""

    def fetch_fund_flow(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Optional: fetch fund flow data."""
        return pd.DataFrame()

    def fetch_margin(self, trade_date: str) -> pd.DataFrame:
        """Optional: fetch margin trading data."""
        return pd.DataFrame()
