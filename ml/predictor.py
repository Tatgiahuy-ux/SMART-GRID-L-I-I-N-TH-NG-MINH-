"""Temporary prediction boundary for the ML teammate's implementation."""

import pandas as pd


def predict_consumption(data: pd.DataFrame) -> float:
    """Return a small baseline prediction until the real model is integrated.

    Contract for replacement:
    - input: DataFrame with a numeric ``consumption_kwh`` column
    - output: one numeric prediction in kWh
    """
    if "consumption_kwh" not in data or data.empty:
        raise ValueError("Dữ liệu cần có cột consumption_kwh và ít nhất một bản ghi.")

    window = data["consumption_kwh"].tail(3)
    return float(window.mean())
