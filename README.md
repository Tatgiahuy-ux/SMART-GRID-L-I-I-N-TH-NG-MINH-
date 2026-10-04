# Hệ thống giám sát và dự đoán phụ tải điện — demo Nhóm 17

Demo Streamlit cho đề tài **"Ứng dụng Trí tuệ nhân tạo (Machine Learning) và Blockchain bảo mật
trong Thành phố thông minh"** — phần được giao: *ML cho Smart Grid/Mobility và cơ chế đồng thuận
Blockchain chống giả mạo*.

Ứng dụng gồm hai mạch chính:

1. **ML**: mô hình `RandomForestRegressor` (100 cây) dự đoán tiêu thụ điện theo đặc trưng thời gian
   (giờ, ngày, tháng, thứ), kèm baseline xu hướng tuyến tính để đối chiếu trên **cùng tập kiểm tra**.
2. **Blockchain**: chuỗi hash SHA-256 phát hiện sửa đổi dữ liệu + chuỗi **Proof of Work** có luật
   đồng thuận *chuỗi nặng nhất thắng*, mô phỏng cả kịch bản kẻ tấn công đào lại (tấn công 51%).

Giao diện theo hướng *bảng điều khiển kỹ thuật*: nền sáng, chữ rõ, bo góc nhỏ, không gradient/glow.
Toàn bộ màu sắc và kiểu chữ nằm trong `.streamlit/config.toml` (không nhúng CSS trong `app.py`).

## Chạy nhanh bằng một lệnh (khuyên dùng khi demo)

```powershell
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1            # cổng 8501
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1 -Port 8502 # khi 8501 đang bận
```

Script tự kiểm tra `.venv`, cài thư viện còn thiếu, huấn luyện nếu chưa có `ml\model.pkl`,
chạy 33 kiểm thử nhanh rồi mở Streamlit. Tình huống bấm máy từng bước xem [KICH-BAN-DEMO.md](KICH-BAN-DEMO.md).

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

## Kiểm thử (4 bộ, tổng 97 kiểm tra)

Để chạy đủ cả kiểm thử web và trình duyệt, cài thêm dependency kiểm thử:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
```

```powershell
.\.venv\Scripts\python.exe tools\smoke_test.py     # 33 kiểm tra logic: ML, chỉ số, hash, PoW, đồng thuận, bảo mật
.\.venv\Scripts\python.exe tools\ui_test.py        # 20 kiểm tra giao diện Streamlit (headless, AppTest)
.\.venv\Scripts\python.exe tools\web_test.py       # 20 kiểm tra HTTP/WebSocket thật, độ bền dữ liệu, hiệu năng
.\.venv\Scripts\python.exe tools\browser_test.py   # 23 kiểm tra trên trình duyệt thật (Edge) + chụp ảnh vào anh-demo/
```

`smoke_test.py` kiểm tra: dữ liệu 720 giờ, dự đoán ML, **chỉ số trong `ml/metrics.json` được tính
lại từ dữ liệu gốc** (không tin số ghi sẵn) và so sánh RandomForest với baseline trên cùng tập kiểm
tra, chuỗi hash hợp lệ/bị sửa, nonce và độ khó của PoW (hash đạt độ khó, nonce tái tạo được hash,
tốc độ băm đo thật), hai kết luận đồng thuận (hòa tổng công → giữ nút trung thực; đào vượt → mô
phỏng tấn công 51%), nhánh tấn công đào lại **đúng dữ liệu gốc**, và các kiểm tra bảo mật đầu vào.
`ui_test.py` chạy thật `app.py` bằng `streamlit.testing.v1.AppTest`: KPI khớp `ml/metrics.json`, bảng
so sánh baseline, thẻ block, bật/tắt mô phỏng sửa dữ liệu, hai kịch bản đồng thuận, đổi mô hình,
đổi số giờ dự đoán và bộ dữ liệu 8 giờ.
`web_test.py` tự khởi động server rồi kiểm tra health, trang chủ, tài nguyên tĩnh, bắt tay WebSocket,
10 loại CSV xấu/tốt, ngưỡng 5 MB và đo thời gian các thao tác nặng khi demo.
`browser_test.py` mở app bằng Microsoft Edge thật (Playwright) ở 1440×900 để bấm qua 5 tab, chạy 2
kịch bản giả mạo, kiểm tra không tràn ngang/không cắt chữ số liệu và lưu 8 ảnh màn hình dùng cho
slide. Kết quả chi tiết: [KIEM-THU-WEB.md](KIEM-THU-WEB.md).

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
| `ml/model.pkl`, `ml/metrics.json` | Mô hình đã huấn luyện + chỉ số MAE/RMSE/R² của mô hình và baseline trên tập kiểm tra 20% |
| `security.py` | Giới hạn upload, `read_uploaded_csv()` (đọc được BOM của Excel), validate dữ liệu phía server, che chi tiết lỗi (mục 6–9 của checklist) |
| `.streamlit/config.toml` | Cấu hình Streamlit: giao diện sáng kiểu bảng điều khiển kỹ thuật + `maxUploadSize = 5`, CORS/XSRF bật, `showErrorDetails = "none"`, `toolbarMode = "minimal"` |
| `blockchain/chain.py` | `IntegrityChain` – chuỗi hash phát hiện sửa đổi (có `invalid_index()` chỉ đúng block lỗi) |
| `blockchain/consensus.py` | `ProofOfWorkChain` – đào khối, kiểm tra nonce/độ khó, luật đồng thuận, kịch bản đào lại |
| `data/power_consumption.csv` | 720 giờ (30 ngày) dữ liệu tiêu thụ điện của thành viên ML |
| `data/sample_energy.csv` | 8 giờ dữ liệu minh họa nhỏ |
| `tools/smoke_test.py` | Kiểm thử luồng tích hợp + đối chiếu chỉ số (33 điểm) |
| `tools/pow_measure.py` | Đo bảng Proof of Work (nonce/thời gian/tốc độ băm) để lấy số liệu cho báo cáo, slide |
| `tools/ui_test.py` | Kiểm thử giao diện Streamlit headless (21 điểm) |
| `tools/web_test.py` | Kiểm thử HTTP/WebSocket thật + độ bền dữ liệu + hiệu năng (20 điểm) |
| `tools/browser_test.py` | Kiểm thử end-to-end trên trình duyệt thật (23 điểm) + chụp ảnh slide |
| `anh-demo/` | 8 ảnh chụp màn hình 5 tab và 2 kịch bản giả mạo (dùng cho slide) |
| `KIEM-THU-WEB.md` | Báo cáo kiểm thử web: 97/97 kiểm tra, số đo hiệu năng, việc chưa test |
| `run_demo.ps1` | Một lệnh chạy demo: kiểm tra môi trường → huấn luyện → kiểm thử → mở Streamlit |
| `tools/ponytail/` | Plugin ponytail v4.10.3 (MIT) đã vendor sẵn cho OpenCode — hướng dẫn ở `tools/ponytail/CAI-DAT.md` |
| `tools/check_ponytail.cjs` | Kiểm tra bản ponytail đã vendor còn nguyên vẹn (11 điểm) |
| `.opencode/skills/` | Skill **UI/UX Pro Max v2.15.0** (7 skill, 175 file) cho OpenCode — hướng dẫn ở `UIUX-SKILL-CAI-DAT.md` |
| `tools/install_uiux_skill.cjs` | Cài/cập nhật skill UI/UX Pro Max đúng như CLI chính thức (không cần npm) |
| `tools/check_uiux_skill.cjs` | Kiểm tra skill UI/UX Pro Max, có chạy thật `search.py` (11 điểm) |
| `file-can-gop/` | **Thư mục nhận file của nhóm** (2 file cần gộp: gói `SmartGrid_MachineLearning` + `blockchain_module.py`) |
| `team-deliverables/` | Bản gốc `ml_model.py`, `generate_data.py`, `blockchain_module.py` để đối chiếu |
| `TICH-HOP-NOTE-PPT.md` | Note logic + số liệu + bố cục slide cho người làm PPT/báo cáo |
| `KICH-BAN-DEMO.md` | Kịch bản bấm máy khi demo, phương án dự phòng, Q&A |
| `BAO-CAO-DANH-GIA.md` | Báo cáo đánh giá hiện trạng dự án so với đề tài Nhóm 17 |
| `SECURITY-CHECKLIST.md` | Đối chiếu 20 mục bảo mật: đã có / cần khi deploy / không áp dụng, kèm cấu hình Nginx + Cloudflare |
| `UIUX-SKILL-CAI-DAT.md` | Nguồn gốc, cách dùng, cách cập nhật/gỡ skill UI/UX Pro Max đã cài trong `.opencode/skills/` |

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
- Chỉ số MAE/RMSE/R² nằm trong `ml/metrics.json`, tính trên 20% dữ liệu cuối (tập kiểm tra 144 giờ):
  RandomForest **MAE 0.1977 · RMSE 0.2467 · R² 0.9729**, baseline ngoại suy tuyến tính 1 bước trên
  **cùng tập kiểm tra**: **MAE 1.2324 · RMSE 1.5044 · R² -0.0086**.
- Vì sao RandomForest tốt hơn hẳn: đặc trưng thời gian (giờ/ngày/thứ) cho phép mô hình học đúng
  chu kỳ ngày (đỉnh sáng–trưa–tối), còn ngoại suy tuyến tính chỉ kéo dài một xu hướng nên không
  mô tả được chu kỳ. `tools/smoke_test.py` huấn luyện lại từ dữ liệu gốc và đối chiếu để bảo đảm
  các con số này là kết quả thật, không phải số nhập tay.
- Đây là demo giáo dục: hash phát hiện sửa đổi, PoW + đồng thuận chỉ chống sửa đổi khi kẻ tấn công
  **không** nắm đa số năng lực đào. Không trình bày là bảo mật tuyệt đối.
