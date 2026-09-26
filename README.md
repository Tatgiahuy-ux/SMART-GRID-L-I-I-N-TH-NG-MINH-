# Smart Grid Monitor

Bản demo Streamlit cho đề tài Smart Grid: dự đoán tiêu thụ điện và kiểm tra tính toàn vẹn dữ liệu bằng chuỗi hash.

## Chạy local

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Không cần activate `.venv`, nên cách này vẫn chạy khi PowerShell đang chặn file `Activate.ps1`.

## Tính năng hiện có

- Đọc dữ liệu mẫu hoặc tải CSV có hai cột `timestamp` và `consumption_kwh`.
- Dự đoán từ 1 đến 6 giờ bằng baseline xu hướng tuyến tính dễ giải thích.
- Tạo hash cho từng bản ghi và kiểm tra liên kết giữa các block.
- Mô phỏng dữ liệu bị sửa để trình bày việc phát hiện sai lệch.
- Tải xuống dữ liệu sau khi làm sạch.

## Hợp đồng tích hợp

- ML thay `ml/predictor.py`, giữ hàm `predict_consumption(data: pandas.DataFrame, horizon: int) -> ForecastResult` hoặc cập nhật rõ ràng trong README.
- Blockchain thay `blockchain/chain.py`, giữ kết quả có hash và trạng thái xác thực để `app.py` hiển thị.
- Mọi thay đổi thư viện phải cập nhật `requirements.txt`.

Các số liệu và baseline hiện tại là minh họa, không phải kết quả nghiên cứu chính thức.
