# Smart Grid Monitor

Bộ khung Streamlit cho đề tài Smart Grid: dự đoán tiêu thụ điện và kiểm tra tính toàn vẹn dữ liệu bằng chuỗi hash.

## Chạy local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Hợp đồng tích hợp

- ML thay `ml/predictor.py`, giữ hàm `predict_consumption(data: pandas.DataFrame) -> float` hoặc cập nhật rõ ràng trong README.
- Blockchain thay `blockchain/chain.py`, giữ kết quả có hash và trạng thái xác thực để `app.py` hiển thị.
- Mọi thay đổi thư viện phải cập nhật `requirements.txt`.

Các số liệu hiện tại là dữ liệu minh họa, không phải kết quả nghiên cứu chính thức.
