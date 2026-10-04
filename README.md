# Smart Grid Monitor — demo Nhóm 17

Demo Streamlit cho đề tài **"Ứng dụng Trí tuệ nhân tạo (Machine Learning) và Blockchain bảo mật
trong Thành phố thông minh"** — phần được giao: *ML cho Smart Grid/Mobility và cơ chế đồng thuận
Blockchain chống giả mạo*.

Ứng dụng gồm hai mạch chính:

1. **ML**: mô hình `RandomForestRegressor` (100 cây) dự đoán tiêu thụ điện theo đặc trưng thời gian
   (giờ, ngày, tháng, thứ), kèm baseline xu hướng tuyến tính để đối chiếu.
2. **Blockchain**: chuỗi hash SHA-256 phát hiện sửa đổi dữ liệu + chuỗi **Proof of Work** có luật
   đồng thuận *chuỗi nặng nhất thắng*, mô phỏng cả kịch bản kẻ tấn công đào lại (tấn công 51%).

## Chạy nhanh bằng một lệnh (khuyên dùng khi demo)

```powershell
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1            # cổng 8501
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1 -Port 8502 # khi 8501 đang bận
```

Script tự kiểm tra `.venv`, cài thư viện còn thiếu, huấn luyện nếu chưa có `ml\model.pkl`,
chạy 14 kiểm thử nhanh rồi mở Streamlit. Tình huống bấm máy từng bước xem [KICH-BAN-DEMO.md](KICH-BAN-DEMO.md).

## Chạy local thủ công

```powershell
python -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe ml\generate_data.py        # (tuỳ chọn) sinh lại data/power_consumption.csv
.\.venv\Scripts\python.exe ml\train_model.py          # sinh ml/model.pkl + ml/metrics.json
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Không cần activate `.venv`, nên cách này vẫn chạy khi PowerShell đang chặn file `Activate.ps1`.
Nếu Streamlit hỏi email ở lần chạy đầu, cứ nhấn Enter (hoặc dùng `run_demo.ps1`, script tự tạo
`~\.streamlit\credentials.toml`).

## Kiểm thử nhanh (không cần mở giao diện)

```powershell
.\.venv\Scripts\python.exe tools\smoke_test.py   # 14 kiểm tra luồng tích hợp
.\.venv\Scripts\python.exe tools\ui_test.py      # 9 kiểm tra giao diện Streamlit (headless)
```

`smoke_test.py` kiểm tra: dự đoán ML, chuỗi hash hợp lệ/bị sửa, đào khối PoW, phát hiện sửa payload,
hai kết luận đồng thuận (hòa tổng công → giữ nút trung thực; đào vượt → mô phỏng tấn công 51%),
và 5 kiểm tra bảo mật (chặn file sai định dạng/quá lớn/dữ liệu sai, không lộ chi tiết lỗi, cấu hình an toàn).
`ui_test.py` chạy thật `app.py` bằng `streamlit.testing.v1.AppTest` và kiểm tra các thông báo trên giao diện.

## Bảo mật đầu vào (đã cấu hình sẵn)

| Hạng mục | Cấu hình trong repo |
|---|---|
| Định dạng upload | Chỉ nhận `.csv` (`st.file_uploader(type=["csv"])` + `validate_upload()` trong `security.py`) |
| Dung lượng upload | 5 MB, chặn 2 lớp: `.streamlit/config.toml` (`server.maxUploadSize`) và `security.py` |
| Validate phía server | `security.prepare_data()` kiểm tra cột, kiểu dữ liệu, giá trị âm/vô lý, số dòng, mốc thời gian trùng |
| Chi tiết lỗi | `security.safe_error()` ghi traceback ra terminal, giao diện chỉ thấy thông báo chung + mã lỗi; `[client] showErrorDetails = "none"` |
| Secret | Không hard-code secret; `.gitignore` chặn `.streamlit/secrets.toml` |
| CORS / XSRF | Giữ bật cả hai trong `.streamlit/config.toml` (không dùng CORS dấu `*`) |

Bảng đối chiếu đầy đủ 20 mục bảo mật (mục nào đã có, mục nào chỉ cần khi deploy, mục nào không áp
dụng) nằm ở [SECURITY-CHECKLIST.md](SECURITY-CHECKLIST.md).

## Cấu trúc

| Đường dẫn | Vai trò |
|---|---|
| `app.py` | Giao diện Streamlit 5 tab: Tổng quan & ML, Blockchain/Hash, Đồng thuận PoW, Dữ liệu, Hướng dẫn |
| `ml/predictor.py` | Hợp đồng dự đoán `predict_consumption(data, horizon) -> ForecastResult` |
| `ml/generate_data.py` | Sinh dữ liệu mô phỏng 30 ngày (tái lập đúng file CSV nhóm đã gửi) |
| `ml/train_model.py` | Huấn luyện RandomForest, ghi `ml/model.pkl` và `ml/metrics.json` |
| `ml/model.pkl`, `ml/metrics.json` | Mô hình đã huấn luyện + chỉ số MAE/RMSE/R² trên tập kiểm tra 20% |
| `security.py` | Giới hạn upload, validate dữ liệu phía server, che chi tiết lỗi (mục 6–9 của checklist) |
| `.streamlit/config.toml` | Cấu hình Streamlit an toàn: `maxUploadSize = 5`, CORS/XSRF bật, `showErrorDetails = "none"` |
| `blockchain/chain.py` | `IntegrityChain` – chuỗi hash phát hiện sửa đổi |
| `blockchain/consensus.py` | `ProofOfWorkChain` – đào khối, kiểm tra nonce/độ khó, luật đồng thuận |
| `data/power_consumption.csv` | 720 giờ (30 ngày) dữ liệu tiêu thụ điện của thành viên ML |
| `data/sample_energy.csv` | 8 giờ dữ liệu minh họa nhỏ |
| `tools/smoke_test.py` | Kiểm thử luồng tích hợp (14 điểm, có 5 kiểm tra bảo mật) |
| `tools/ui_test.py` | Kiểm thử giao diện Streamlit headless (9 điểm) |
| `run_demo.ps1` | Một lệnh chạy demo: kiểm tra môi trường → huấn luyện → kiểm thử → mở Streamlit |
| `file-can-gop/` | **Thư mục nhận file của nhóm** (2 file cần gộp: gói `SmartGrid_MachineLearning` + `blockchain_module.py`) |
| `team-deliverables/` | Bản gốc `ml_model.py`, `generate_data.py`, `blockchain_module.py` để đối chiếu |
| `TICH-HOP-NOTE-PPT.md` | Note logic + số liệu + bố cục slide cho người làm PPT/báo cáo |
| `KICH-BAN-DEMO.md` | Kịch bản bấm máy khi demo, phương án dự phòng, Q&A |
| `BAO-CAO-DANH-GIA.md` | Báo cáo đánh giá hiện trạng dự án so với đề tài Nhóm 17 |
| `SECURITY-CHECKLIST.md` | Đối chiếu 20 mục bảo mật: đã có / cần khi deploy / không áp dụng, kèm cấu hình Nginx + Cloudflare |

## Hợp đồng tích hợp

- ML thay `ml/predictor.py`, giữ hàm `predict_consumption(data: pandas.DataFrame, horizon: int) -> ForecastResult`.
  Nếu máy chưa cài `scikit-learn` hoặc chưa có `ml/model.pkl`, ứng dụng tự lùi về baseline tuyến tính
  và hiển thị rõ lý do (`fallback_reason`) — demo không bao giờ vỡ.
- Blockchain thay `blockchain/chain.py` (hash) hoặc `blockchain/consensus.py` (PoW + đồng thuận),
  giữ kết quả có hash và trạng thái xác thực để `app.py` hiển thị.
- Mọi thay đổi thư viện phải cập nhật `requirements.txt`.

## Đối chiếu với file nhóm gửi trong `file-can-gop/`

| File nhóm gửi | Bản tích hợp | Kiểm chứng |
|---|---|---|
| `SmartGrid_MachineLearning\...\generate_data.py` | `ml/generate_data.py` | Chạy lại cho ra `data/power_consumption.csv` **trùng khớp từng byte** (SHA-256 bằng nhau) |
| `SmartGrid_MachineLearning\...\ml_model.py` + `model.pkl` | `ml/train_model.py` + `ml/model.pkl` | `ml/model.pkl` mới cho **dự đoán trùng khớp tuyệt đối** (chênh lệch 0.0000 kWh) với `model.pkl` gốc |
| `blockchain_module.py` | `blockchain/consensus.py` + `blockchain/chain.py` | Bản gốc **lỗi** (`Block.calculate_hash` thiếu `return` → `hash = None`); bản tích hợp đã sửa và bổ sung luật đồng thuận |

Cả ba file gốc được lưu nguyên trạng trong `team-deliverables/` để đối chiếu khi bảo vệ.

## Số liệu hiện có (không phải kết quả nghiên cứu chính thức)

- Dữ liệu là **dữ liệu mô phỏng sinh bằng script** (`ml/generate_data.py`, seed 42), 720 giờ,
  chưa phải dữ liệu đo từ lưới điện thật.
- Chỉ số MAE/RMSE/R² nằm trong `ml/metrics.json`, tính trên 20% dữ liệu cuối (tập kiểm tra):
  RandomForest **MAE 0.1977 · RMSE 0.2467 · R² 0.9729** so với baseline tuyến tính **MAE 1.2324**.
- Đây là demo giáo dục: hash phát hiện sửa đổi, PoW + đồng thuận chỉ chống sửa đổi khi kẻ tấn công
  **không** nắm đa số năng lực đào. Không trình bày là bảo mật tuyệt đối.
