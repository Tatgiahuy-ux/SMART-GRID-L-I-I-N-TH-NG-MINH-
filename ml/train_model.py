"""Huấn luyện mô hình RandomForest cho demo Smart Grid (Nhóm 17).

Chạy từ thư mục gốc project:

    .\\.venv\\Scripts\\python.exe ml\\train_model.py

Đầu vào : data/power_consumption.csv (timestamp, consumption_kwh)
Đầu ra  : ml/model.pkl, ml/metrics.json, ml/evaluation.png (nếu có matplotlib)

Script này là bản chỉnh sửa từ ``ml_model.py`` của thành viên phụ trách ML
(xem ``team-deliverables/ml_model_goc.py``). Các thay đổi so với bản gốc:

1. Đường dẫn tính theo vị trí file thay vì phụ thuộc thư mục làm việc.
2. Bỏ ``plt.show()`` (chặn khi chạy tự động) và lưu biểu đồ ra file.
3. Ghi thêm ``ml/metrics.json`` để ứng dụng Streamlit đọc lại chỉ số MAE/RMSE/R².
4. Tính thêm MAE của baseline xu hướng tuyến tính trên cùng tập test để so sánh.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):  # console Windows mặc định cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from ml.predictor import linear_trend_forecast  # noqa: E402  (cần ROOT ở sys.path)

DATA_PATH = ROOT / "data" / "power_consumption.csv"
MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"
METRICS_PATH = Path(__file__).resolve().parent / "metrics.json"
CHART_PATH = Path(__file__).resolve().parent / "evaluation.png"

FEATURES = ["hour", "day", "month", "dayofweek"]
TARGET = "consumption_kwh"
TEST_RATIO = 0.2
RANDOM_STATE = 42
N_ESTIMATORS = 100


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Tạo đặc trưng thời gian từ cột ``timestamp`` (giống bản gốc của nhóm)."""
    enriched = frame.copy()
    enriched["timestamp"] = pd.to_datetime(enriched["timestamp"])
    enriched["hour"] = enriched["timestamp"].dt.hour
    enriched["day"] = enriched["timestamp"].dt.day
    enriched["month"] = enriched["timestamp"].dt.month
    enriched["dayofweek"] = enriched["timestamp"].dt.dayofweek
    return enriched


def load_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = {"timestamp", TARGET}.difference(frame.columns)
    if missing:
        raise ValueError(f"Thiếu cột trong {path.name}: {', '.join(sorted(missing))}")
    frame = add_time_features(frame)
    return frame.dropna(subset=["timestamp", TARGET]).sort_values("timestamp").reset_index(drop=True)


def baseline_predictions(values: list[float], start: int) -> list[float]:
    """Dự đoán 1 bước (walk-forward) của baseline xu hướng tuyến tính trên đoạn test.

    Mỗi mốc ``index`` chỉ dùng dữ liệu **trước** nó (``values[:index]``) rồi ngoại suy
    tuyến tính 1 bước – nhờ vậy baseline được đánh giá trên **đúng cửa sổ test** và đúng
    kiểu dự đoán như RandomForest, không dùng thông tin tương lai.
    """
    return [
        linear_trend_forecast(values[:index], 1)[0]
        for index in range(max(start, 1), len(values))
    ]


def baseline_mae(values: list[float], start: int) -> float:
    """MAE một bước của baseline xu hướng tuyến tính trên đoạn test."""
    predictions = baseline_predictions(values, start)
    if not predictions:
        return float("nan")
    actual = values[max(start, 1) :]
    return float(np.mean(np.abs(np.array(predictions) - np.array(actual))))


def train(frame: pd.DataFrame) -> tuple[RandomForestRegressor, dict]:
    split_index = int(len(frame) * (1 - TEST_RATIO))
    train_frame = frame.iloc[:split_index]
    test_frame = frame.iloc[split_index:]

    model = RandomForestRegressor(n_estimators=N_ESTIMATORS, random_state=RANDOM_STATE)
    model.fit(train_frame[FEATURES], train_frame[TARGET])

    predicted = model.predict(test_frame[FEATURES])
    actual = test_frame[TARGET].to_numpy()
    values = [float(value) for value in frame[TARGET]]
    baseline_predicted = np.array(baseline_predictions(values, split_index))

    metrics = {
        "model_name": f"RandomForestRegressor ({N_ESTIMATORS} cây)",
        "n_estimators": N_ESTIMATORS,
        "features": FEATURES,
        "target": TARGET,
        "data_file": DATA_PATH.name,
        "n_rows": int(len(frame)),
        "n_train": int(len(train_frame)),
        "n_test": int(len(test_frame)),
        "test_ratio": TEST_RATIO,
        "random_state": RANDOM_STATE,
        "mae": round(float(mean_absolute_error(actual, predicted)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(actual, predicted))), 4),
        "r2": round(float(r2_score(actual, predicted)), 4),
        # Baseline được chấm trên CÙNG cửa sổ test để so sánh công bằng với RandomForest.
        "baseline_linear_mae": round(float(mean_absolute_error(actual, baseline_predicted)), 4),
        "baseline_linear_rmse": round(
            float(np.sqrt(mean_squared_error(actual, baseline_predicted))), 4
        ),
        "baseline_linear_r2": round(float(r2_score(actual, baseline_predicted)), 4),
        "baseline_linear_name": "Ngoại suy tuyến tính 1 bước (walk-forward)",
        "test_start": test_frame["timestamp"].iloc[0].isoformat(),
        "test_end": test_frame["timestamp"].iloc[-1].isoformat(),
        "trained_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "sklearn_version": sklearn.__version__,
        "pandas_version": pd.__version__,
    }

    if CHART_PATH is not None:
        save_chart(test_frame["timestamp"], actual, predicted)

    return model, metrics


def save_chart(timestamps: pd.Series, actual: np.ndarray, predicted: np.ndarray) -> None:
    """Lưu biểu đồ so sánh thực tế/dự đoán; bỏ qua nếu thiếu matplotlib."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Bỏ qua biểu đồ: chưa cài matplotlib (không bắt buộc cho demo).")
        return

    figure, axis = plt.subplots(figsize=(10, 4.5))
    axis.plot(timestamps, actual, label="Thực tế", marker="o", markersize=3)
    axis.plot(timestamps, predicted, label="Dự đoán (RandomForest)", marker="x", markersize=3)
    axis.set_title("Điện năng thực tế và dự đoán trên tập kiểm tra (20%)")
    axis.set_xlabel("Thời gian")
    axis.set_ylabel("Điện năng (kWh)")
    axis.grid(alpha=0.3)
    axis.legend()
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(CHART_PATH, dpi=120)
    plt.close(figure)
    print(f"Đã lưu biểu đồ: {CHART_PATH.name}")


def main() -> None:
    print("===== DỮ LIỆU ĐIỆN NĂNG =====")
    frame = load_dataset()
    print(frame.head())

    print("\n===== HUẤN LUYỆN RANDOM FOREST =====")
    model, metrics = train(frame)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"MAE  : {metrics['mae']:.4f}")
    print(f"RMSE : {metrics['rmse']:.4f}")
    print(f"R²   : {metrics['r2']:.4f}")
    print(
        "Baseline xu hướng tuyến tính (cùng tập test): "
        f"MAE {metrics['baseline_linear_mae']:.4f} · "
        f"RMSE {metrics['baseline_linear_rmse']:.4f} · "
        f"R² {metrics['baseline_linear_r2']:.4f}"
    )
    print(f"\nĐã lưu mô hình: {MODEL_PATH}")
    print(f"Đã lưu chỉ số: {METRICS_PATH}")


if __name__ == "__main__":
    main()
