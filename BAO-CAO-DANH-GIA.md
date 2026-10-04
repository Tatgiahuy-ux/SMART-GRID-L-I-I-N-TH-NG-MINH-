# Báo cáo đánh giá hiện trạng dự án — đối chiếu đề tài Nhóm 17

**Đề tài:** *Ứng dụng Trí tuệ nhân tạo (Machine Learning) và Blockchain bảo mật trong Thành phố thông minh.*
**Nhiệm vụ được giao:** *Nghiên cứu ứng dụng ML cho Smart Grid/Mobility và cơ chế đồng thuận Blockchain chống giả mạo.*
**Ngày lập báo cáo:** 2026-10-03 · **Phạm vi:** workspace `C:\Users\huy\Project\CongNgheVienThong`

---

## 1. Kết luận nhanh

| Câu hỏi | Trả lời |
|---|---|
| Project trước khi tích hợp có phải demo của đề tài này? | **Đúng một phần.** Đó là khung demo Smart Grid (ML + hash) — tức chỉ nửa đầu của nhiệm vụ. Không có Smart Mobility, không có cơ chế đồng thuận. |
| Trước khi tích hợp đã dùng mô hình ML thật chưa? | **Chưa.** `ml/predictor.py` chỉ là hồi quy tuyến tính tự viết; mô hình RandomForest do thành viên ML gửi nằm ở `Downloads`, chưa nối vào app. |
| Trước khi tích hợp đã có cơ chế đồng thuận chưa? | **Chưa.** `blockchain/chain.py` chỉ là chuỗi hash 1 nút, chỉ *phát hiện* sửa đổi. Module PoW của thành viên Blockchain chưa nối và còn lỗi. |
| Sau khi tích hợp (hôm nay) đã đạt gì? | ML RandomForest chạy thật có chỉ số kiểm tra (**MAE 0.1977 · RMSE 0.2467 · R² 0.9729**), chuỗi PoW có **luật đồng thuận chuỗi nặng nhất**, mô phỏng được **tấn công 51%**; 18/18 kiểm tra tự động đạt. |
| Còn thiếu gì để đúng đề tài? | Smart Mobility (0%), dữ liệu thật, mạng P2P nhiều nút thật, chữ ký số/smart contract, đánh giá học thuật. |

---

## 2. Đề tài được giao được phân rã thành 4 yêu cầu con

| Mã | Yêu cầu con | Trạng thái hiện tại |
|---|---|---|
| **R1** | Ứng dụng ML cho **Smart Grid** (dự đoán phụ tải điện) | Đã có mô hình thật + chỉ số |
| **R2** | Ứng dụng ML cho **Smart Mobility** | Chưa có |
| **R3** | **Blockchain bảo mật** dữ liệu (chống sửa đổi) | Đã có hash chain + PoW |
| **R4** | **Cơ chế đồng thuận** chống giả mạo | Có luật đồng thuận mô phỏng trong 1 tiến trình |

---

## 3. Hiện trạng **trước** khi tích hợp (bằng chứng)

### 3.1 Những gì đã có

- `app.py` — Streamlit 4 tab: Tổng quan, Blockchain/Hash, Dữ liệu, Hướng dẫn demo. Có mô phỏng sửa dữ liệu và trạng thái HỢP LỆ/ĐÃ BỊ SỬA.
- `ml/predictor.py` — `_linear_forecast()` ngoại suy tuyến tính + backtest MAE. **Không huấn luyện, không có mô hình học máy.**
- `blockchain/chain.py` — `IntegrityChain` (SHA-256, `previous_hash`), `tamper_block()`, `is_valid()`. **Không có nonce, độ khó, đào, hay đồng thuận.**
- `data/sample_energy.csv` — **8 dòng** dữ liệu minh họa.
- `README.md` dòng 29 và `PRODUCT.md` dòng 41–42 tự ghi rõ: *"các số liệu và baseline hiện tại là minh họa, không phải kết quả nghiên cứu chính thức"*, *"dataset, trained model, hash schema… chưa được chọn"*.
- Thư mục `SMART-GRID-L-I-I-N-TH-NG-MINH-/` là **bản clone repo GitHub của nhóm** (`Tatgiahuy-ux/SMART-GRID-L-I-I-N-TH-NG-MINH-`) — bản khung **cũ hơn**: `ml/predictor.py` chỉ trả trung bình 3 giá trị cuối, `app.py` chỉ ghi 1 block.

### 3.2 Sản phẩm của các thành viên đã gửi nhưng **chưa được dùng**

| Vị trí | Nội dung | Vấn đề khi tích hợp |
|---|---|---|
| `Downloads\SmartGrid_MachineLearning\...\ml_model.py` | RandomForest 100 cây, feature `hour/day/month/dayofweek`, chia 80/20, in MAE/RMSE/R², lưu `model.pkl` | `plt.show()` chặn khi chạy tự động; đường dẫn phụ thuộc thư mục làm việc; không lưu chỉ số ra file cho app đọc |
| `...\generate_data.py` + `data\power_consumption.csv` | 720 giờ dữ liệu mô phỏng (30 ngày) | Chưa nằm trong repo |
| `Downloads\blockchain_module.py` | Có `mine_block(difficulty)` = **PoW**, `add_power_data_block()`, `is_chain_valid()` | **Lỗi**: `Block.calculate_hash()` (dòng 14–21) tính `block_string` nhưng **không có `return`** ⇒ `self.hash = None` ⇒ `mine_block` ném `TypeError`. Ngoài ra chỉ là 1 nút, không có luật đồng thuận |

> Kết luận mục 3: project cũ **chưa phải** demo của đề tài; nó là khung của **một nửa** đề tài, và nửa đó cũng chỉ ở mức minh họa.

---

## 4. Những gì đã thực hiện trong phiên này

| File | Thay đổi |
|---|---|
| `data/power_consumption.csv` | Đưa bộ dữ liệu 720 giờ của thành viên ML vào repo (thay vì chỉ 8 dòng mẫu) |
| `ml/train_model.py` | Viết lại script huấn luyện: bỏ `plt.show()`, đường dẫn theo vị trí file, **ghi `ml/model.pkl` + `ml/metrics.json`**, tính thêm MAE baseline trên cùng tập test, biểu đồ là tùy chọn |
| `ml/predictor.py` | Viết lại: `ForecastResult` mở rộng (RMSE, R², `fitted`, `metrics_source`, `fallback_reason`); hỗ trợ `model="random_forest" / "linear" / "auto"`; **tự lùi về baseline kèm lý do** nếu thiếu scikit-learn hoặc `model.pkl` |
| `blockchain/consensus.py` | **Mới**: `ProofOfWorkChain` — đào PoW có `nonce`/`difficulty`/thời gian đào, `validation_error()` mô tả lỗi cụ thể, `tamper_block()` (sửa ẩu) và `tamper_and_remine()` (kẻ tấn công đào lại), **`resolve_conflict()` = luật đồng thuận chuỗi nặng nhất**, payload `consumer_id / actual_usage_kwh / predicted_usage_kwh` |
| `app.py` | 5 tab: Tổng quan & ML (chỉ số MAE/RMSE/R², biểu đồ thực tế vs mô hình, chọn mô hình), Blockchain/Hash, **Đồng thuận PoW** (đào khối, nonce, tốc độ băm, so sánh 2 chuỗi, kết luận đồng thuận), Dữ liệu, Hướng dẫn |
| `tools/smoke_test.py` | **Mới**: 9 kiểm tra luồng tích hợp (không cần Streamlit) |
| `tools/ui_test.py` | **Mới**: 9 kiểm tra giao diện bằng `streamlit.testing.v1.AppTest` (chạy thật `app.py`) |
| `ml/generate_data.py` | Đưa script sinh dữ liệu của thành viên ML vào repo; chạy lại cho ra `data/power_consumption.csv` **trùng khớp từng byte** |
| `run_demo.ps1` | Một lệnh chạy demo: kiểm tra `.venv` → cài thư viện → huấn luyện → chạy kiểm thử → mở Streamlit (đã kiểm chứng dưới Windows PowerShell 5.1: HTTP 200) |
| `TICH-HOP-NOTE-PPT.md` | Note logic + số liệu + bố cục 12 slide cho thành viên làm PPT/Word |
| `KICH-BAN-DEMO.md` | Kịch bản bấm máy 7 chặng, 6 phương án dự phòng, Q&A 8 câu |
| `team-deliverables/` | Lưu bản gốc `ml_model_goc.py`, `generate_data.py`, `blockchain_module_goc.py` để đối chiếu, không sửa bản gốc |
| `README.md`, `PRODUCT.md`, `requirements.txt` | Cập nhật theo hiện trạng mới; thêm `scikit-learn`, `joblib` |

### 4.1 Đối chiếu trực tiếp với 2 file nhóm gửi trong `file-can-gop/`

| Kiểm chứng | Cách làm | Kết quả |
|---|---|---|
| Dữ liệu tái lập được | Chạy `ml/generate_data.py` (giữ nguyên `np.random.seed(42)`), so SHA-256 với `file-can-gop/.../power_consumption.csv` | **Trùng khớp từng byte** |
| Mô hình tái lập được | Nạp `model.pkl` gốc của thành viên ML bằng joblib, dự đoán tập test, so với `ml/model.pkl` | **Chênh lệch 0.0000 kWh** (giống tuyệt đối), cùng MAE 0.1977 / R² 0.9729 |
| Module blockchain gốc | Chạy thử `blockchain_module.py` | **Lỗi**: `calculate_hash()` thiếu `return` ⇒ `hash = None` ⇒ `mine_block` ném `TypeError`; đã sửa trong `blockchain/consensus.py` |

Điểm nối ML ↔ Blockchain: mỗi block PoW lưu **một bản ghi điện năng gồm số thực tế và số mô hình ML dự đoán** — đúng ý tưởng `add_power_data_block(consumer_id, actual_usage, predicted_usage)` của thành viên Blockchain, nhưng nay có luật đồng thuận đi kèm.

---

## 5. Kết quả đo được (chạy thật, không phải số ước lượng)

### 5.1 Mô hình ML (RandomForestRegressor 100 cây, `random_state=42`)

| Chỉ số | RandomForest | Baseline xu hướng tuyến tính (cùng tập test) |
|---|---|---|
| MAE (kWh) | **0.1977** | 1.2324 |
| RMSE (kWh) | **0.2467** | — |
| R² | **0.9729** | — |

- Dữ liệu: 720 giờ, `2026-01-01 00:00` → `2026-01-30 23:00`; min/max 1.46 / 6.93 kWh, trung bình 3.965 kWh.
- Chia 576 huấn luyện / 144 kiểm tra; tập test `2026-01-25 00:00` → `2026-01-30 23:00`.
- Môi trường kiểm chứng: Python 3.12.14 · pandas 3.0.1 · scikit-learn 1.9.1 · streamlit 1.65.0.
- **RandomForest giảm MAE khoảng 6,2 lần** so với baseline trên cùng tập test.

### 5.2 Proof of Work (7 block = genesis + 6 bản ghi, Python thuần)

| Độ khó | Tổng nonce | Thời gian đào | Tốc độ băm | Hợp lệ |
|---|---|---|---|---|
| 1 | 136 | 0.001 s | ~170.600 H/s | ✔ |
| 2 | 1.724 | 0.010 s | ~171.500 H/s | ✔ |
| 3 | 14.061 | 0.073 s | ~192.100 H/s | ✔ |
| 4 | 246.685 | 1.305 s | ~189.000 H/s | ✔ |

### 5.3 Kiểm thử tự động

- `tools/smoke_test.py`: **9/9 đạt** — dự đoán RF trả đủ số giờ; chuỗi hash hợp lệ; phát hiện sửa payload; hash PoW đạt độ khó; sửa payload không đào lại ⇒ chuỗi không hợp lệ; hòa tổng công ⇒ giữ nút trung thực; đào vượt 2 khối ⇒ kẻ tấn công thắng (mô phỏng 51%).
- `tools/ui_test.py`: **9/9 đạt** — app khởi động không ngoại lệ, 5 tab, thông báo hợp lệ/không hợp lệ, hai kết luận đồng thuận, đổi mô hình sang baseline không lỗi, và bộ dữ liệu nhỏ 8 giờ vẫn đào khối được.

---

## 6. Mức độ đáp ứng đề tài (đánh giá định tính)

| Yêu cầu con | Mức đáp ứng | Căn cứ | Còn thiếu |
|---|---|---|---|
| R1 · ML cho Smart Grid | **~70%** | Có mô hình thật, có chỉ số kiểm tra, có so sánh baseline, có quy trình huấn luyện lặp lại được | Dữ liệu mô phỏng; feature chỉ là thời gian (không dùng độ trễ/lịch sử phụ tải); chưa dự báo nhiều ngày; chưa có phân tích sai số theo giờ |
| R2 · ML cho Smart Mobility | **0%** | Không có dữ liệu/module giao thông | Toàn bộ |
| R3 · Blockchain bảo mật | **~55%** | Hash chain + PoW có nonce/độ khó; sửa dữ liệu bị phát hiện | Chưa có chữ ký số/ví, chưa có smart contract, chưa có nhiều nút thật |
| R4 · Cơ chế đồng thuận | **~45%** | Có luật chuỗi nặng nhất, có so sánh tổng công, có mô phỏng 51% | Chỉ mô phỏng 2 nhánh trong 1 tiến trình; chưa có mạng P2P, lan truyền khối, chọn nút, hay PBFT/PoS để so sánh |

**Tổng thể:** dự án hiện là **demo tích hợp ML + Blockchain cho Smart Grid**, đã trả lời được câu hỏi trọng tâm của nhiệm vụ ("ML dự đoán + chuỗi khối chống giả mạo"), nhưng **chưa bao phủ Smart Mobility** và **đồng thuận mới ở mức mô phỏng**.

---

## 7. Khoảng trống & rủi ro cần nói trước hội đồng

1. **Dữ liệu là mô phỏng** (`generate_data.py`, seed 42) — không phải số đo công tơ thật. Mọi chỉ số chỉ có ý nghĩa minh họa phương pháp.
2. **Rò rỉ dữ liệu ở biểu đồ "giá trị mô hình khớp"**: đường in-sample của RandomForest lạc quan hơn tập test. App đã ghi chú rõ; khi báo cáo chỉ nên trích chỉ số tập test (MAE 0.1977).
3. **RandomForest không dùng dữ liệu quá khứ**: dự đoán chỉ từ giờ/ngày/tháng/thứ nên không học được phụ thuộc chuỗi thời gian (mùa, xu hướng, sự kiện). Đây là hạn chế phương pháp, nên nêu thẳng.
4. **Đồng thuận chưa phải mạng thật**: `resolve_conflict()` so sánh hai chuỗi trong cùng một tiến trình. Chưa có P2P, chưa có độ trễ lan truyền, chưa có nút độc lập.
5. **Không có chữ ký số**: bất kỳ ai sửa payload rồi đào lại đều tạo được chuỗi hợp lệ. Cần chữ ký (ECDSA) trên từng bản ghi để ràng buộc danh tính người gửi.
6. **Tấn công 51% là giới hạn thật**, đã mô phỏng minh bạch. Không được trình bày hash/PoW là bảo mật tuyệt đối (chính `PRODUCT.md` đã ràng buộc điều này).
7. **Trùng lặp cấu trúc**: `SMART-GRID-L-I-I-N-TH-NG-MINH-/` là repo con nằm trong project, dễ gây nhầm phiên bản khi nộp bài. Nên tách ra ngoài hoặc xoá sau khi đã đối chiếu.

---

## 8. Đề xuất bước tiếp theo

| Ưu tiên | Việc cần làm | Gợi ý phụ trách |
|---|---|---|
| **P0** | Bổ sung phần **Smart Mobility**: dữ liệu lưu lượng theo giờ, mô hình dự đoán (cùng khung `predict_consumption`), tab riêng trong app | Thành viên ML thứ hai |
| **P0** | Thêm **chữ ký số ECDSA** cho mỗi bản ghi trước khi đưa vào block; từ chối block có chữ ký sai | Thành viên Blockchain |
| **P1** | Mô phỏng **nhiều nút P2P trong tiến trình** (3–5 nút, lan truyền block, độ trễ, nút độc hại) để phần đồng thuận thuyết phục hơn | Thành viên Blockchain |
| **P1** | Nâng ML: thêm feature độ trễ (lag 1/24/168), so sánh RandomForest với mô hình chuỗi thời gian; dùng **dữ liệu thật** nếu xin được | Thành viên ML |
| **P2** | Thêm smart contract mô phỏng (ví dụ hợp đồng mua bán điện P2P) | Cả nhóm |
| **P2** | Viết báo cáo học thuật: đặt vấn đề, kiến trúc, thực nghiệm, so sánh tài liệu tham khảo | Nhóm trưởng + thư ký |
| **P2** | Dọn `SMART-GRID-L-I-I-N-TH-NG-MINH-/` ra khỏi workspace, gắn repo gốc bằng git để tránh lệch phiên bản | Nhóm trưởng |

---

## 9. Cách tái lập toàn bộ kết quả trong báo cáo

```powershell
cd C:\Users\huy\Project\CongNgheVienThong
python -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe ml\train_model.py     # sinh ml\model.pkl + ml\metrics.json (số ở mục 5.1)
.\.venv\Scripts\python.exe tools\smoke_test.py   # 9 kiểm tra luồng tích hợp
.\.venv\Scripts\python.exe tools\ui_test.py      # 9 kiểm tra giao diện
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## 10. Phụ lục — danh mục bằng chứng

| Bằng chứng | Đường dẫn |
|---|---|
| Chỉ số mô hình (nguồn số ở mục 5.1) | `ml/metrics.json` |
| Mô hình đã huấn luyện | `ml/model.pkl` |
| Dữ liệu 720 giờ | `data/power_consumption.csv` |
| Luật đồng thuận | `blockchain/consensus.py` → `resolve_conflict()`, `tamper_and_remine()` |
| Lỗi module gốc của nhóm | `team-deliverables/blockchain_module_goc.py` dòng 14–21 (thiếu `return`) |
| Bản ML gốc của nhóm | `team-deliverables/ml_model_goc.py` |
| Kịch bản thuyết trình | `app.py` → tab "Hướng dẫn demo" |
| Kiểm thử | `tools/smoke_test.py`, `tools/ui_test.py` |
