"""A-share price limit rules by exchange board.

Main board (60xxxx.SH, 00xxxx.SZ): 10%
ChiNext (30xxxx.SZ): 20%
STAR (688xxx.SH): 20%
Beijing Stock Exchange (8xxxxx): 30%
Third board (4xxxxx): 30%
"""

from typing import Dict

LIMIT_BY_PREFIX: Dict[str, float] = {
    "688": 0.20,
    "30": 0.20,
    "60": 0.10,
    "00": 0.10,
    "8": 0.30,
    "4": 0.30,
}

_LIMIT_TOLERANCE = 0.002


def get_limit_threshold(ts_code: str, tolerance: bool = True) -> float:
    """Get the price limit threshold as a percentage for a given stock code."""
    code_num = ts_code.split(".")[0]
    for prefix in sorted(LIMIT_BY_PREFIX.keys(), key=len, reverse=True):
        if code_num.startswith(prefix):
            limit = LIMIT_BY_PREFIX[prefix]
            if tolerance:
                limit -= _LIMIT_TOLERANCE
            return round(limit * 100, 2)
    return 9.8 if tolerance else 10.0


def get_limit_thresholds_batch(
    ts_codes: list[str], tolerance: bool = True
) -> Dict[str, float]:
    """Get limit thresholds for multiple stock codes."""
    return {code: get_limit_threshold(code, tolerance) for code in ts_codes}
