"""Load and validate strategy configuration from YAML."""

import yaml


def load_strategy_from_yaml(yaml_str: str) -> dict:
    """Parse a YAML strategy config string into a dict.

    Returns a dict with keys:
        id, name, description, active
        universe: {exclude_ST, exclude_new_stock_days, ...}
        factor_weights: {factor_name: weight, ...}  (negative weight = negative direction)
        preprocessing: {winsorize_pct, neutralization, standardize_method}
        signals: {buy_top_pct, sell_bottom_pct, max_holdings, min_holding_days, ...}
    """
    config = yaml.safe_load(yaml_str)
    if not isinstance(config, dict):
        raise ValueError("Strategy YAML must be a mapping")

    required = ["id", "name", "factor_weights"]
    for key in required:
        if key not in config:
            raise ValueError(f"Missing required field: {key}")

    # Set defaults
    config.setdefault("universe", {})
    config.setdefault("preprocessing", {})
    config.setdefault("signals", {})

    univ = config["universe"]
    univ.setdefault("exclude_ST", True)
    univ.setdefault("exclude_new_stock_days", 60)
    univ.setdefault("exclude_limit_trade", False)
    univ.setdefault("exclude_suspended", True)
    univ.setdefault("min_listing_days", 120)

    prep = config["preprocessing"]
    prep.setdefault("winsorize_pct", [1, 99])
    prep.setdefault("neutralization", [])
    prep.setdefault("standardize_method", "zscore")

    sig = config["signals"]
    sig.setdefault("buy_top_pct", 0.2)
    sig.setdefault("sell_bottom_pct", 0.2)
    sig.setdefault("max_holdings", 20)
    sig.setdefault("min_holding_days", 1)
    sig.setdefault("rebalance", "daily")

    # Normalize factor weights: negative weight means negative direction
    weights = {}
    for name, w in config["factor_weights"].items():
        weights[name] = float(w)
    config["factor_weights"] = weights

    return config
