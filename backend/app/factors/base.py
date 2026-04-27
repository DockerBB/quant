"""Abstract base class for all factors and the register decorator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type

import pandas as pd

_registry: dict[str, Type["Factor"]] = {}


def register(factor_cls: Type["Factor"]) -> Type["Factor"]:
    """Decorator to register a factor class in the global registry."""
    if hasattr(factor_cls, 'name') and factor_cls.name:
        _registry[factor_cls.name] = factor_cls
    return factor_cls


def get_registry() -> dict:
    return _registry


class Factor(ABC):
    """A factor computes a numeric value for each stock at a given point in time.

    Subclasses define:
    - name: unique identifier
    - category: one of value/momentum/quality/growth/sentiment/technical/risk
    - direction: 'positive' (higher is better) or 'negative' (lower is better)
    - description: human-readable explanation
    - params: dict of tunable parameters
    """

    name: str = ""
    category: str = ""
    direction: str = "positive"
    description: str = ""
    params: dict = {}

    @abstractmethod
    def compute(
        self,
        universe: list[str],
        daily: pd.DataFrame,
        **kwargs,
    ) -> pd.Series:
        ...

    @classmethod
    def meta(cls) -> dict:
        return {
            "name": cls.name,
            "category": cls.category,
            "direction": cls.direction,
            "description": cls.description,
            "params": cls.params,
        }
