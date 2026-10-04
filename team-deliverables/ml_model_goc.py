import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
import joblib
# 1. Đọc dữ liệu điện năng
df = pd.read_csv("data/power_consumption.csv")

print("===== DỮ LIỆU ĐIỆN NĂNG =====")
print(df.head())

# 2. Chuyển cột thời gian
df["timestamp"] = pd.to_datetime(df["timestamp"])

# 3. Tạo các đặc trưng từ thời gian
df["hour"] = df["timestamp"].dt.hour
df["day"] = df["timestamp"].dt.day
df["month"] = df["timestamp"].dt.month
df["dayofweek"] = df["timestamp"].dt.dayofweek

# 4. Xác định dữ liệu đầu vào và đầu ra
X = df[["hour", "day", "month", "dayofweek"]]
y = df["consumption_kwh"]

# 5. Chia dữ liệu: 80% để huấn luyện, 20% để kiểm tra
split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

# 6. Tạo mô hình Random Forest
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

# 7. Huấn luyện mô hình
model.fit(X_train, y_train)

# 8. Dự đoán
y_pred = model.predict(X_test)

# 9. Đánh giá mô hình
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n===== KẾT QUẢ MACHINE LEARNING =====")
print(f"MAE  : {mae:.4f}")
print(f"RMSE : {rmse:.4f}")
print(f"R²   : {r2:.4f}")

# 10. Hiển thị kết quả dự đoán
result = pd.DataFrame({
    "Thực tế (kWh)": y_test.values,
    "Dự đoán (kWh)": y_pred
})

print("\n===== SO SÁNH THỰC TẾ VÀ DỰ ĐOÁN =====")
print(result)

# 11. Vẽ biểu đồ
plt.figure(figsize=(10, 5))

plt.plot(
    y_test.values,
    marker="o",
    label="Thực tế"
)

plt.plot(
    y_pred,
    marker="x",
    label="Dự đoán"
)

plt.title("So sánh điện năng thực tế và dự đoán")
plt.xlabel("Mẫu dữ liệu")
plt.ylabel("Điện năng (kWh)")
plt.legend()
plt.grid()

plt.show()
# 12. Dự đoán điện năng cho một thời điểm mới
new_time = pd.Timestamp("2026-01-31 19:00:00")

new_data = pd.DataFrame({
    "hour": [new_time.hour],
    "day": [new_time.day],
    "month": [new_time.month],
    "dayofweek": [new_time.dayofweek]
})

new_prediction = model.predict(new_data)

print("\n===== DỰ ĐOÁN ĐIỆN NĂNG MỚI =====")
print("Thời gian:", new_time)
print(f"Điện năng dự đoán: {new_prediction[0]:.2f} kWh")
# 13. Lưu mô hình Machine Learning
joblib.dump(model, "model.pkl")

print("\nĐã lưu mô hình thành công: model.pkl")