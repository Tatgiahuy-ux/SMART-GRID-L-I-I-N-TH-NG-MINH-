"""Sinh dữ liệu tiêu thụ điện mô phỏng 30 ngày cho demo Smart Grid (Nhóm 17).

Chạy từ thư mục gốc project:

    .\\.venv\\Scripts\\python.exe ml\\generate_data.py

Bản này chỉnh từ ``generate_data.py`` của thành viên phụ trách ML (bản gốc:
``file-can-gop/SmartGrid_MachineLearning/SmartGrid_MachineLearning/generate_data.py``):

1. Đường dẫn tính theo vị trí file thay vì phụ thuộc thư mục làm việc.
2. Tách hàm ``build_dataset()`` để phần huấn luyện/kiểm thử có thể tái sử dụng.
3. Giữ nguyên công thức và ``np.random.seed(42)`` nên dữ liệu sinh ra **trùng khớp**
   với ``data/power_consumption.csv`` mà nhóm đã gửi.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "power_consumption.csv"

DAYS = 30
SEED = 42
COLUMNS = ["timestamp", "consumption_kwh"]


def build_dataset(days: int = DAYS, seed: int = SEED) -> pd.DataFrame:
    """Sinh chuỗi tiêu thụ điện theo giờ với các đỉnh sáng/trưa/tối và nhiễu nhỏ.

    Cố ý dùng API ``np.random.seed`` + ``np.random.normal`` (legacy) giống bản gốc của
    nhóm để dữ liệu sinh ra trùng khớp từng dòng với ``data/power_consumption.csv``;
    đổi sang ``default_rng`` sẽ cho chuỗi số ngẫu nhiên khác và làm lệch mô hình.
    """
    time_index = pd.date_range(start="2026-01-01 00:00:00", periods=days * 24, freq="h")
    np.random.seed(seed)

    rows = []
    for moment in time_index:
        hour = moment.hour
        consumption = 2.0

        if 6 <= hour <= 9:
            consumption += 2.5
        elif 10 <= hour <= 16:
            consumption += 2.0
        elif 17 <= hour <= 21:
            consumption += 4.0

        if moment.dayofweek >= 5:
            consumption += 0.5

        consumption += float(np.random.normal(0, 0.2))
        rows.append([moment, round(consumption, 2)])

    return pd.DataFrame(rows, columns=COLUMNS)


def main() -> None:
    frame = build_dataset()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT_PATH, index=False)
    print("Đã tạo dữ liệu thành công!")
    print(f"Số dòng dữ liệu: {len(frame)}")
    print(f"Đã ghi: {OUTPUT_PATH}")
    print(frame.head())


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):  # console Windows mặc định cp1252
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
