"""Explainable baseline forecast for the Smart Grid demo."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ForecastResult:
    """Output contract consumed by the Streamlit integration layer."""

    predictions: list[float]
    model_name: str
    mae: float | None


def _linear_forecast(values: list[float], steps: int) -> list[float]:
    if not values:
        raise ValueError("Cần ít nhất một giá trị tiêu thụ điện.")
    if len(values) == 1:
        return [values[0]] * steps

    x_mean = (len(values) - 1) / 2
    y_mean = sum(values) / len(values)
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    slope = (
        sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values))
        / denominator
    )
    intercept = y_mean - slope * x_mean
    return [max(0.0, intercept + slope * (len(values) + offset)) for offset in range(steps)]


def _backtest_mae(values: list[float]) -> float | None:
    if len(values) < 4:
        return None
    errors: list[float] = []
    for index in range(3, len(values)):
        predicted = _linear_forecast(values[:index], 1)[0]
        errors.append(abs(predicted - values[index]))
    return sum(errors) / len(errors)


def predict_consumption(data: pd.DataFrame, horizon: int = 1) -> ForecastResult:
    """Forecast future consumption with an explainable linear-trend baseline.

    Replacement contract for the ML teammate:
    - input: DataFrame with numeric ``consumption_kwh`` values
    - output: ``ForecastResult`` with predictions in kWh and optional MAE
    """
    if "consumption_kwh" not in data or data.empty:
        raise ValueError("Dữ liệu cần có cột consumption_kwh và ít nhất một bản ghi.")
    if horizon < 1:
        raise ValueError("Horizon phải lớn hơn hoặc bằng 1.")

    values = [float(value) for value in data["consumption_kwh"].dropna()]
    return ForecastResult(
        predictions=_linear_forecast(values, horizon),
        model_name="Linear trend baseline",
        mae=_backtest_mae(values),
    )
