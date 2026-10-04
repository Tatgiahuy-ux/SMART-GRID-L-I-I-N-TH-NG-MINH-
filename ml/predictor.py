"""Lớp dự đoán tiêu thụ điện cho demo Smart Grid (Nhóm 17).

Hai chế độ dự đoán, cùng một hợp đồng đầu ra ``ForecastResult``:

1. ``random_forest`` – dùng mô hình RandomForest đã huấn luyện sẵn ở ``ml/model.pkl``
   (sinh ra bởi ``ml/train_model.py``). Đặc trưng đầu vào: giờ, ngày, tháng, thứ.
2. ``linear`` – baseline xu hướng tuyến tính dễ giải thích, luôn chạy được kể cả khi
   chưa cài scikit-learn hoặc chưa có ``model.pkl``.

Hợp đồng tích hợp với ``app.py`` (giữ nguyên từ bản khung):

    predict_consumption(data: pandas.DataFrame, horizon: int) -> ForecastResult

``data`` cần có cột ``consumption_kwh`` (kiểu số) và nên có cột ``timestamp`` để
dự đoán theo mốc thời gian thật.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

LOGGER = logging.getLogger("smart_grid")

MODULE_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODULE_DIR / "model.pkl"
METRICS_PATH = MODULE_DIR / "metrics.json"

FEATURE_COLUMNS = ["hour", "day", "month", "dayofweek"]
TARGET_COLUMN = "consumption_kwh"

MODE_AUTO = "auto"
MODE_RANDOM_FOREST = "random_forest"
MODE_LINEAR = "linear"

BASELINE_NAME = "Baseline xu hướng tuyến tính"
BASELINE_NOTE = (
    "Baseline minh họa: ngoại suy tuyến tính từ chuỗi quá khứ, không phải mô hình nghiên cứu."
)


@dataclass(frozen=True)
class ForecastResult:
    """Đầu ra thống nhất mà tầng giao diện Streamlit tiêu thụ."""

    predictions: list[float]
    model_name: str
    mae: float | None
    rmse: float | None = None
    r2: float | None = None
    fitted: list[float] | None = None
    future_timestamps: list[str] = field(default_factory=list)
    metrics_source: str = ""
    note: str = ""
    fallback_reason: str | None = None


# --------------------------------------------------------------------------- #
# Baseline xu hướng tuyến tính
# --------------------------------------------------------------------------- #
def linear_trend_forecast(values: list[float], steps: int) -> list[float]:
    """Ngoại suy tuyến tính ``steps`` bước tiếp theo từ chuỗi ``values``."""
    if not values:
        raise ValueError("Cần ít nhất một giá trị tiêu thụ điện.")
    if steps < 1:
        raise ValueError("Horizon phải lớn hơn hoặc bằng 1.")
    if len(values) == 1:
        return [float(values[0])] * steps

    x_mean = (len(values) - 1) / 2
    y_mean = sum(values) / len(values)
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    if denominator == 0:
        return [float(y_mean)] * steps
    slope = (
        sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values))
        / denominator
    )
    intercept = y_mean - slope * x_mean
    return [
        max(0.0, intercept + slope * (len(values) + offset)) for offset in range(steps)
    ]


def _backtest_linear(values: list[float]) -> tuple[list[float], float | None]:
    """Dự đoán 1 bước cho từng bản ghi (walk-forward) và MAE tương ứng."""
    fitted: list[float] = []
    errors: list[float] = []
    for index in range(len(values)):
        predicted = (
            float(values[0])
            if index == 0
            else linear_trend_forecast(values[:index], 1)[0]
        )
        fitted.append(predicted)
        if index >= 3:
            errors.append(abs(predicted - values[index]))
    mae = sum(errors) / len(errors) if errors else None
    return fitted, mae


# --------------------------------------------------------------------------- #
# Mô hình RandomForest đã huấn luyện
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _load_forest() -> tuple[Any | None, str | None]:
    """Nạp ``ml/model.pkl``; trả về (model, lý do an toàn nếu không nạp được).

    Chi tiết kỹ thuật (traceback, đường dẫn) chỉ ghi vào log phía server, không trả ra
    giao diện — theo yêu cầu "không hiển thị chi tiết lỗi ra ngoài".
    """
    if not MODEL_PATH.exists():
        return None, "Chưa có mô hình đã huấn luyện. Chạy `ml/train_model.py` để tạo."
    try:
        import joblib
        import sklearn  # noqa: F401  (kiểm tra phụ thuộc trước khi nạp pickle)
    except ImportError:
        LOGGER.warning("Thiếu scikit-learn/joblib, dùng baseline.", exc_info=True)
        return None, "Môi trường hiện tại chưa cài scikit-learn/joblib nên dùng baseline."
    try:
        return joblib.load(MODEL_PATH), None
    except Exception:  # noqa: BLE001 - pickle lỗi vì nhiều nguyên nhân khác nhau
        LOGGER.error("Không nạp được mô hình đã huấn luyện.", exc_info=True)
        return None, "Không nạp được mô hình đã huấn luyện nên tạm dùng baseline."


@lru_cache(maxsize=1)
def load_saved_metrics() -> dict[str, Any] | None:
    """Đọc chỉ số đánh giá do ``ml/train_model.py`` ghi ra (nếu có)."""
    if not METRICS_PATH.exists():
        return None
    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def model_options() -> list[dict[str, Any]]:
    """Danh sách mô hình cho giao diện, kèm lý do nếu không khả dụng."""
    model, reason = _load_forest()
    metrics = load_saved_metrics()
    forest_label = "RandomForest (ml/model.pkl)"
    if metrics:
        forest_label = f"RandomForest ({metrics.get('n_estimators', 100)} cây, ml/model.pkl)"
    return [
        {
            "value": MODE_RANDOM_FOREST,
            "label": forest_label,
            "available": model is not None,
            "detail": reason or "Mô hình đã huấn luyện, sẵn sàng dự đoán.",
        },
        {
            "value": MODE_LINEAR,
            "label": BASELINE_NAME,
            "available": True,
            "detail": "Luôn chạy được, dùng để đối chiếu với mô hình ML.",
        },
    ]


def _time_features(timestamps: pd.Series) -> pd.DataFrame:
    stamps = pd.to_datetime(pd.Series(timestamps), errors="coerce")
    return pd.DataFrame(
        {
            "hour": stamps.dt.hour,
            "day": stamps.dt.day,
            "month": stamps.dt.month,
            "dayofweek": stamps.dt.dayofweek,
        }
    )


def _future_timestamps(last_timestamp: pd.Timestamp, horizon: int) -> pd.DatetimeIndex:
    return pd.date_range(start=last_timestamp + pd.Timedelta(hours=1), periods=horizon, freq="h")


def _validate(data: pd.DataFrame, horizon: int) -> list[float]:
    if TARGET_COLUMN not in data or data.empty:
        raise ValueError("Dữ liệu cần có cột consumption_kwh và ít nhất một bản ghi.")
    if horizon < 1:
        raise ValueError("Horizon phải lớn hơn hoặc bằng 1.")
    return [float(value) for value in data[TARGET_COLUMN].dropna()]


def _predict_with_forest(data: pd.DataFrame, values: list[float], horizon: int) -> ForecastResult:
    model, reason = _load_forest()
    if model is None:
        raise RuntimeError(reason or "Không nạp được mô hình RandomForest.")

    if "timestamp" not in data:
        raise ValueError("Mô hình RandomForest cần cột timestamp để tạo đặc trưng thời gian.")

    stamps = pd.to_datetime(data["timestamp"], errors="coerce")
    if stamps.isna().any():
        raise ValueError("Cột timestamp có giá trị không hợp lệ.")

    fitted = [float(value) for value in model.predict(_time_features(stamps))]
    future = _future_timestamps(stamps.iloc[-1], horizon)
    predictions = [float(value) for value in model.predict(_time_features(pd.Series(future)))]

    metrics = load_saved_metrics() or {}
    return ForecastResult(
        predictions=predictions,
        model_name=metrics.get("model_name") or "RandomForestRegressor (ml/model.pkl)",
        mae=metrics.get("mae"),
        rmse=metrics.get("rmse"),
        r2=metrics.get("r2"),
        fitted=fitted,
        future_timestamps=[stamp.isoformat() for stamp in future],
        metrics_source=(
            f"ml/metrics.json – tập kiểm tra {metrics.get('n_test')} bản ghi "
            f"({metrics.get('test_start')} → {metrics.get('test_end')})"
            if metrics
            else "Chưa có ml/metrics.json: chỉ hiển thị dự đoán, không có chỉ số kiểm tra."
        ),
        note=(
            "Đặc trưng thời gian (giờ/ngày/tháng/thứ) của chính mốc cần dự đoán; "
            "cột 'khớp dữ liệu' là dự đoán in-sample nên lạc quan hơn tập kiểm tra."
        ),
    )


def _predict_with_baseline(data: pd.DataFrame, values: list[float], horizon: int) -> ForecastResult:
    fitted, mae = _backtest_linear(values)
    future_timestamps: list[str] = []
    if "timestamp" in data:
        stamps = pd.to_datetime(data["timestamp"], errors="coerce")
        if not stamps.isna().all():
            future_timestamps = [
                stamp.isoformat() for stamp in _future_timestamps(stamps.dropna().iloc[-1], horizon)
            ]
    return ForecastResult(
        predictions=linear_trend_forecast(values, horizon),
        model_name=BASELINE_NAME,
        mae=mae,
        fitted=fitted,
        future_timestamps=future_timestamps,
        metrics_source=(
            f"Baseline: backtest 1 bước (walk-forward) trên toàn bộ {len(values):,} "
            "bản ghi đầu vào; không phải tập kiểm tra 20%."
        ),
        note=BASELINE_NOTE,
    )


def predict_consumption(
    data: pd.DataFrame,
    horizon: int = 1,
    model: str = MODE_AUTO,
) -> ForecastResult:
    """Dự đoán tiêu thụ điện ``horizon`` giờ tiếp theo.

    ``model`` nhận ``"auto"`` (ưu tiên RandomForest, tự lùi về baseline nếu thiếu),
    ``"random_forest"`` hoặc ``"linear"``.
    """
    values = _validate(data, horizon)

    if model == MODE_LINEAR:
        return _predict_with_baseline(data, values, horizon)

    try:
        return _predict_with_forest(data, values, horizon)
    except (RuntimeError, ValueError) as exc:
        if model == MODE_RANDOM_FOREST:
            raise
        fallback = _predict_with_baseline(data, values, horizon)
        return ForecastResult(
            predictions=fallback.predictions,
            model_name=fallback.model_name,
            mae=fallback.mae,
            fitted=fallback.fitted,
            future_timestamps=fallback.future_timestamps,
            metrics_source=fallback.metrics_source,
            note=fallback.note,
            fallback_reason=str(exc),
        )
