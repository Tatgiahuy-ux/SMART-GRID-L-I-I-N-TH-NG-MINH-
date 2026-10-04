import pandas as pd
import numpy as np

# Tạo dữ liệu 30 ngày, mỗi giờ một mẫu
time = pd.date_range(
    start="2026-01-01 00:00:00",
    periods=30 * 24,
    freq="h"
)

data = []

np.random.seed(42)

for t in time:
    hour = t.hour
    dayofweek = t.dayofweek

    # Mức điện tiêu thụ cơ bản
    consumption = 2.0

    # Điện tăng vào buổi sáng
    if 6 <= hour <= 9:
        consumption += 2.5

    # Điện tăng vào buổi trưa
    elif 10 <= hour <= 16:
        consumption += 2.0

    # Điện tăng mạnh vào buổi tối
    elif 17 <= hour <= 21:
        consumption += 4.0

    # Cuối tuần có mức tiêu thụ khác một chút
    if dayofweek >= 5:
        consumption += 0.5

    # Thêm nhiễu nhỏ
    consumption += np.random.normal(0, 0.2)

    data.append([t, round(consumption, 2)])

# Tạo DataFrame
df = pd.DataFrame(
    data,
    columns=["timestamp", "consumption_kwh"]
)

# Lưu vào file CSV
df.to_csv(
    "data/power_consumption.csv",
    index=False
)

print("Đã tạo dữ liệu thành công!")
print(f"Số dòng dữ liệu: {len(df)}")
print("\n5 dòng đầu tiên:")
print(df.head())