"""Output formatting utilities for ModelPulse."""

import math
from typing import Any


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Format a float as a percentage string, e.g. 0.056 -> '5.6%'."""
    return f"{value * 100:.{decimals}f}%"


def fmt_number(value: float, decimals: int = 4) -> float:
    """Round a float to the given decimal places for JSON output."""
    return round(value, decimals)


def safe_float(value: Any) -> float | None:
    """Safely convert a value to float, returning None on failure.

    Returns None for NaN and Inf values as well.
    """
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except (TypeError, ValueError):
        return None
