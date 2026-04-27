"""Factor registry — discovers and provides access to all registered factors.

Import all factor modules at the bottom to trigger @register decorators.
"""

from __future__ import annotations

from typing import Type

from .base import Factor, get_registry


def get(name: str) -> dict | None:
    cls = get_registry().get(name)
    return cls.meta() if cls else None


def create(name: str) -> Factor | None:
    cls = get_registry().get(name)
    return cls() if cls else None


def list_all() -> list[dict]:
    return [cls.meta() for cls in get_registry().values()]


def list_by_category(category: str) -> list[dict]:
    return [cls.meta() for cls in get_registry().values() if cls.category == category]


# Import all factor implementations to trigger registration
from .value import pe_ttm, pb, ps_ttm, dividend_yield as dy
from .momentum import mom_6m, residual_momentum
from .quality import roe_ttm, gross_margin, accruals_ratio
from .growth import revenue_yoy, netprofit_yoy
from .sentiment import turnover_change
from .technical import rsi_14
