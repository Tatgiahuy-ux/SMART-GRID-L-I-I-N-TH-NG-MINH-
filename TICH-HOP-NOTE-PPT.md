# Note tích hợp cho người làm slide & báo cáo — Nhóm 17

> Tài liệu này do **người phụ trách tích hợp** viết, để bạn phụ trách PPT/Word lấy số liệu và mô tả
> logic cho **chính xác**. Mọi con số dưới đây đều đo được từ code trong repo, không phải ước lượng.
> Kịch bản bấm máy khi demo nằm ở [KICH-BAN-DEMO.md](KICH-BAN-DEMO.md).

---

## 1. Phân công 5 người (theo chốt của nhóm)

| # | Vai trò | Sản phẩm bàn giao | File trong repo |
|---|---|---|---|
| 1 | **Machine Learning**: tìm dữ liệu + code Python dự đoán mức tiêu thụ điện | `generate_data.py`, `ml_model.py`, `model.pkl`, `data/power_consumption.csv` | gốc ở `file-can-gop/`, bản tích hợp ở `ml/`, `data/` |
| 2 | **Blockchain**: chuỗi khối + mã băm chống giả mạo số liệu | `blockchain_module.py` (PoW) | gốc ở `file-can-gop/`, bản tích hợp ở `blockchain/consensus.py` |
| 3 | **Tích hợp + giao diện + điều khiển máy demo** (bạn) | `app.py`, `ml/predictor.py`, `tools/*`, `run_demo.ps1` | xem mục 3 |
| 4 | **Thuyết trình chính** | Kịch bản nói, Q&A | `KICH-BAN-DEMO.md` |
| 5 | **Slide PPT + file Word báo cáo** | Slide, báo cáo | tài liệu này + `BAO-CAO-DANH-GIA.md` |

---

## 2. Luồng tích hợp (vẽ sơ đồ này lên slide 4)

```
 data/power_consumption.csv  (720 giờ, 30 ngày, dữ liệu mô phỏng seed 42)
              │
              ▼
   ml/predictor.py  ──►  RandomForestRegressor (100 cây)  ──►  dự đoán kWh theo giờ
              │            (ml/model.pkl, huấn luyện bởi ml/train_model.py)
              │
              │  ghép số THỰC TẾ + số DỰ ĐOÁN của cùng một giờ
              ▼
   app.py  ──►  build_mining_records()  ──►  blockchain/consensus.py
              │                                  ProofOfWorkChain: nonce + difficulty + SHA-256
              │                                  luật đồng thuận: chuỗi nặng nhất thắng
              ▼
   Giao diện Streamlit 5 tab: Tổng quan & ML │ Blockchain/Hash │ Đồng thuận PoW │ Dữ liệu │ Hướng dẫn
```

**Ý chính để nói trên slide:** blockchain không chỉ lưu "số điện" mà lưu **cả số mô hình ML dự đoán
trong cùng block**, kèm `deviation_kwh` (độ lệch). Nhờ vậy về sau có thể kiểm tra lại mô hình đã dự
đoán gì tại thời điểm đó mà không ai sửa được.

---

## 3. Từng module: logic, đầu vào/đầu ra, lệnh chạy

### 3.1 Module ML (thành viên 1 → bản tích hợp `ml/predictor.py`)

| Nội dung | Chi tiết |
|---|---|
| **Chức năng** | Dự đoán mức tiêu thụ điện (kWh) cho các giờ tiếp theo |
| **Thuật toán** | `RandomForestRegressor(n_estimators=100, random_state=42)` của scikit-learn |
| **Đặc trưng đầu vào** | `hour`, `day`, `month`, `dayofweek` lấy từ cột `timestamp` |
| **Nhãn (target)** | `consumption_kwh` |
| **Chia dữ liệu** | 80% huấn luyện (**576** giờ) / 20% kiểm tra (**144** giờ, từ `2026-01-25 00:00` đến `2026-01-30 23:00`) |
| **Đầu vào khi chạy app** | `pandas.DataFrame` có `timestamp` + `consumption_kwh` |
| **Đầu ra** | `ForecastResult` gồm `predictions` (danh sách kWh), `model_name`, `mae`, `rmse`, `r2`, `fitted` (giá trị mô hình khớp cho từng bản ghi) |
| **Lệnh huấn luyện lại** | `.\\.venv\\Scripts\\python.exe ml\\train_model.py` |
| **Cơ chế an toàn** | Nếu máy chưa cài scikit-learn hoặc thiếu `ml/model.pkl`, app **tự lùi về baseline xu hướng tuyến tính** và hiện rõ lý do — demo không bao giờ trắng trang |

**Số liệu chính xác để lên slide (đo trên tập kiểm tra 144 giờ):**

| Mô hình | MAE (kWh) | RMSE (kWh) | R² |
|---|---|---|---|
| **RandomForest 100 cây** | **0.1977** | **0.2467** | **0.9729** |
| Baseline ngoại suy tuyến tính 1 bước (đối chiếu) | 1.2324 | 1.5044 | -0.0086 |

→ RandomForest giảm sai số MAE khoảng **6,2 lần** so với baseline. Dữ liệu: 720 giờ, min/max 1.46 / 6.93 kWh, trung bình 3.965 kWh.
→ Cả hai mô hình được chấm trên **cùng tập kiểm tra 144 giờ** (`ml/train_model.py` sinh ra `ml/metrics.json`),
và `tools/smoke_test.py` huấn luyện lại từ dữ liệu gốc để đối chiếu — số trên slide là kết quả thật.

**Tái lập được 100% (điểm cộng khi bị hỏi):** chạy lại `ml/generate_data.py` cho ra file CSV **trùng khớp từng byte** với file nhóm gửi; `ml/train_model.py` cho ra mô hình có dự đoán **trùng khớp tuyệt đối** (chênh lệch 0.0000 kWh) với `model.pkl` gốc của thành viên ML.

### 3.2 Module Blockchain (thành viên 2 → bản tích hợp `blockchain/consensus.py`)

| Nội dung | Chi tiết |
|---|---|
| **Chức năng** | Ghi số liệu điện năng vào chuỗi khối, đào bằng Proof of Work, phát hiện giả mạo |
| **Cấu trúc block** | `index`, `timestamp`, `data` (consumer_id, recorded_time, actual_usage_kwh, predicted_usage_kwh, deviation_kwh), `previous_hash`, `nonce`, `difficulty`, `hash` |
| **Mã băm** | `SHA-256` trên JSON đã sắp xếp khóa (`sort_keys=True`) gồm cả `nonce` |
| **Đào khối** | Tăng `nonce` cho tới khi hash bắt đầu bằng `difficulty` chữ số 0 |
| **Kiểm tra toàn vẹn** | Sai hash, sai `previous_hash`, hoặc sai vị trí `index` → chuỗi KHÔNG hợp lệ, kèm mô tả lỗi cụ thể |
| **Luật đồng thuận** | So sánh **tổng công** (`Σ 2^difficulty`) của các chuỗi hợp lệ, chọn chuỗi nặng nhất; hòa thì giữ chuỗi của nút trung thực (đến trước) |
| **Đầu vào / đầu ra** | Vào: danh sách bản ghi `consumer_id, recorded_time, actual_usage_kwh, predicted_usage_kwh` → Ra: chuỗi block + `summary()` (số block, tổng nonce, thời gian đào, tốc độ băm, hợp lệ hay không) |

**Kết quả đo được (7 block = genesis + 6 bản ghi, Python thuần trên laptop):**

| Độ khó | Tổng nonce | Tổng phép băm | Thời gian đào | Tốc độ băm |
|---|---|---|---|
| 1 | 86 | 93 | 0.001 s | ~160.000 H/s |
| 2 | 2.108 | 2.115 | 0.012 s | ~170.000 H/s |
| 3 | 16.315 | 16.322 | 0.104 s | ~157.000 H/s |
| 4 | 393.097 | 393.104 | 2.399 s | ~164.000 H/s |

→ Đo lại bất cứ lúc nào: `.\\.venv\\Scripts\\python.exe tools\\pow_measure.py`.
Số nonce **không đoán trước được** nhưng tái lập được (cùng payload + cùng độ khó ⇒ cùng nonce);
thời gian đào và tốc độ băm **phụ thuộc máy** (khoảng 0,12–0,19 triệu H/s) nên chỉ nêu khoảng. Nonce
thay đổi nếu đổi cấu trúc payload của block.

**Hai kịch bản giả mạo để lên slide (đây là phần "chống giả mạo" của đề tài):**

1. **Sửa ẩu:** đổi `actual_usage_kwh` nhưng giữ nguyên hash → chuỗi **KHÔNG hợp lệ** ngay (hash không khớp).
2. **Sửa rồi đào lại (kẻ tấn công có năng lực đào):** kẻ tấn công đào lại và **đào vượt thêm 1 khối trở lên** → chuỗi của kẻ tấn công **hợp lệ về hash** và nặng hơn → thắng theo luật đồng thuận. Đây là **mô phỏng tấn công 51%**, phải nói rõ là **giới hạn thật của blockchain**, không được giấu.

### 3.3 Module tích hợp & giao diện (thành viên 3 — bạn)

| Nội dung | Chi tiết |
|---|---|
| **Chức năng** | Nối ML + Blockchain thành một luồng, đưa lên web Streamlit, chạy trong VS Code |
| **File chính** | `app.py` (5 tab), `ml/predictor.py` (hợp đồng dự đoán), `blockchain/chain.py` (chuỗi hash), `blockchain/consensus.py` (PoW + đồng thuận) |
| **Hợp đồng tích hợp** | `predict_consumption(data, horizon) -> ForecastResult`; `IntegrityChain.add_record/is_valid`; `ProofOfWorkChain.add_energy_records/is_valid/resolve_conflict` |
| **Chạy 1 lệnh** | `powershell -ExecutionPolicy Bypass -File .\run_demo.ps1` |
| **Kiểm thử tự động** | `tools\smoke_test.py` (**33/33 đạt**, có đối chiếu lại `ml/metrics.json`), `tools\ui_test.py` (**21/21 đạt**, chạy thật app bằng `streamlit.testing`), `tools\web_test.py` (**20/20**), `tools\browser_test.py` (**23/23** trên Edge thật + chụp ảnh slide) |

---

## 4. Gợi ý bố cục slide (12 slide)

| Slide | Tiêu đề | Nội dung lấy từ đâu | Ảnh nên chụp |
|---|---|---|---|
| 1 | Trang bìa | Nhóm 17, đề tài, môn học, giảng viên, thành viên + vai trò (bảng mục 1) | — |
| 2 | Đặt vấn đề | Điện năng tiêu thụ khó dự báo; số liệu công tơ có thể bị sửa để trục lợi | — |
| 3 | Mục tiêu & phạm vi | Dự đoán tiêu thụ điện bằng ML + chống giả mạo số liệu bằng blockchain | — |
| 4 | Kiến trúc hệ thống | Sơ đồ ở mục 2 | chụp sơ đồ tự vẽ |
| 5 | Dữ liệu | 720 giờ, 30 ngày, các đỉnh sáng/trưa/tối, nhiễu chuẩn 0.2, seed 42 | biểu đồ đường ở tab **Tổng quan & ML** |
| 6 | Mô hình ML | RandomForest 100 cây, 4 đặc trưng thời gian, chia 80/20 | ảnh bảng chỉ số MAE/RMSE/R² trong app |
| 7 | Kết quả ML | Bảng so sánh ở mục 3.1 (RF vs baseline, cùng tập kiểm tra) | ảnh bảng **"So sánh mô hình trên cùng tập kiểm tra"** ở tab Tổng quan & ML |
| 8 | Blockchain & PoW | Cấu trúc block, SHA-256, nonce, độ khó | bảng block ở tab **Đồng thuận PoW** (có cột nonce, difficulty, hash) |
| 9 | Chống giả mạo | Kịch bản 1 và 2 ở mục 3.2 | ảnh `anh-demo/04-phat-hien-sua-du-lieu.png` (thẻ Block #0 lệch hash) và `anh-demo/06-tan-cong-51.png` (hai chuỗi + kết luận) |
| 10 | Demo trực tiếp | Kịch bản ở `KICH-BAN-DEMO.md` | — |
| 11 | Hạn chế | Xem mục 5 bên dưới (nói thẳng, đây là điểm cộng) | — |
| 12 | Kết luận & hướng phát triển | Chữ ký số ECDSA, mạng nhiều nút P2P, dữ liệu công tơ thật | — |

---

## 5. Những điều **tuyệt đối không được nói** khi bảo vệ

1. ❌ "Hash/PoW bảo mật tuyệt đối, không thể sửa được." → ✅ "Phát hiện được sửa đổi; chống được kẻ
   tấn công **không** nắm đa số năng lực đào."
2. ❌ "Dữ liệu lấy từ lưới điện thật." → ✅ "Dữ liệu **mô phỏng** sinh bằng script, seed 42, để
   chứng minh phương pháp."
3. ❌ "Đây là blockchain đầy đủ." → ✅ "Mô phỏng trong một tiến trình: có PoW và luật đồng thuận,
   **chưa** có mạng P2P và chữ ký số."
4. ❌ Trích số liệu **in-sample** (đường "Mô hình" khớp dữ liệu) làm kết quả. → ✅ Chỉ trích chỉ số
   **tập kiểm tra**: MAE 0.1977 · RMSE 0.2467 · R² 0.9729.

---

## 6. Ba câu hỏi giảng viên hay hỏi (trả lời ngắn)

| Câu hỏi | Trả lời gợi ý |
|---|---|
| Vì sao dùng RandomForest? | Dữ liệu bảng nhỏ (720 dòng), quan hệ phi tuyến theo giờ/thứ; RF học nhanh, không cần chuẩn hoá, giải thích được qua tầm quan trọng đặc trưng; baseline tuyến tính cho MAE 1.2324 so với 0.1977 nên thấy rõ hiệu quả. |
| Nếu kẻ tấn công đào lại thì sao? | Demo mô phỏng đúng việc đó: chuỗi đào lại **vẫn hợp lệ về hash**, nên hệ thống phải so **tổng công**; nếu kẻ tấn công đào vượt thì hắn thắng — đó là tấn công 51%, cần thêm chữ ký số và mạng nhiều nút để giảm rủi ro. |
| Phần nào của nhóm là "đồng thuận"? | Luật chọn chuỗi nặng nhất (`resolve_conflict`) — mọi nút kiểm tra chuỗi hợp lệ rồi chọn chuỗi có tổng công lớn nhất; đây là bản mô phỏng luật longest/heaviest chain của Bitcoin. |

> Phần Q&A đầy đủ hơn (8 câu) nằm ở [KICH-BAN-DEMO.md](KICH-BAN-DEMO.md#6-qa-dự-kiến-8-câu).
