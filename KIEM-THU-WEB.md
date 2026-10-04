# Báo cáo kiểm thử web Smart Grid — Nhóm 17

**Người thực hiện:** thành viên phụ trách tích hợp & giao diện (bạn) · **Ngày:** 2026-10-04
**Môi trường đo:** Python 3.12.14 · pandas 3.0.1 · scikit-learn 1.9.1 · Streamlit 1.65.0 · Playwright (Microsoft Edge) · Windows

---

## 1. Kết quả tổng hợp: **97/97 kiểm tra đạt**

| Bộ kiểm thử | Số kiểm tra | Kết quả | Kiểm cái gì |
|---|---|---|---|
| `tools/smoke_test.py` | 33 | **33/33 ✅** | Tái lập dữ liệu, dự đoán ML, **đối chiếu chỉ số trong `metrics.json` bằng cách huấn luyện lại**, chuỗi hash, nonce/độ khó PoW, luật đồng thuận + kịch bản 51%, bảo mật đầu vào |
| `tools/ui_test.py` | 21 | **21/21 ✅** | Chạy thật `app.py` bằng `streamlit.testing` (headless): KPI khớp `metrics.json`, bảng so sánh baseline, thẻ block, bật/tắt sửa dữ liệu, 2 kịch bản đồng thuận, đổi mô hình/số giờ/dataset |
| `tools/web_test.py` | 20 | **20/20 ✅** | Tầng HTTP + WebSocket thật, độ bền dữ liệu (10 loại CSV), hiệu năng khi demo |
| `tools/browser_test.py` | 23 | **23/23 ✅** | Trình duyệt thật (Edge headless, 1440×900): 5 tab, 2 kịch bản giả mạo, kiểm tra tràn ngang/cắt chữ, chụp 8 ảnh màn hình |

### Lệnh chạy lại toàn bộ

```powershell
cd C:\Users\huy\Project\CongNgheVienThong
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe tools\smoke_test.py     # 33 kiểm tra logic + chỉ số
.\.venv\Scripts\python.exe tools\ui_test.py        # 21 kiểm tra giao diện (headless)
.\.venv\Scripts\python.exe tools\web_test.py       # 20 kiểm tra HTTP/WebSocket/dữ liệu/hiệu năng
.\.venv\Scripts\python.exe tools\browser_test.py   # 23 kiểm tra trên trình duyệt thật + chụp ảnh
```

`browser_test.py` cần dependency trong `requirements-test.txt`; script dùng Edge/Chrome có sẵn
trên máy nên **không phải tải Chromium**.

---

## 2. Kiểm thử logic, chỉ số ML và đồng thuận (`smoke_test.py`)

Điểm quan trọng nhất của bộ này: **các con số trên giao diện được tính lại từ dữ liệu gốc**, không
tin số ghi sẵn trong file.

| Nhóm kiểm tra | Kết quả đo |
|---|---|
| `ml/generate_data.py` tái lập đúng `data/power_consumption.csv` (seed 42) | ✅ 720 dòng trùng khớp |
| Dữ liệu đúng 720 bản ghi cách nhau 1 giờ trong 30 ngày, không trùng mốc | ✅ 2026-01-01 00:00 → 2026-01-30 23:00 |
| Dự đoán 6 giờ tiếp theo nối tiếp bản ghi cuối | ✅ 2026-01-31 00:00 → 05:00 |
| **Huấn luyện lại RandomForest từ dữ liệu gốc → so với `ml/metrics.json`** | ✅ MAE 0.1977 · RMSE 0.2467 · R² 0.9729 (khớp từng chữ số) |
| **Tính lại baseline trên cùng tập kiểm tra** | ✅ MAE 1.2324 · RMSE 1.5044 · R² -0.0086 (khớp) |
| RandomForest tốt hơn baseline | ✅ MAE 0.1977 < 1.2324 · R² 0.9729 > -0.0086 |
| Chỉ số mà app hiển thị = chỉ số pipeline trả về | ✅ `predict_consumption` → MAE 0.1977 / RMSE 0.2467 / R² 0.9729 |
| Chuỗi hash: hợp lệ trước khi sửa, phát hiện sửa, chỉ đúng block lỗi | ✅ `invalid_index()` = 5 sau khi sửa block #5 |
| PoW: hash thật sự đạt độ khó, nonce tái tạo đúng hash, nonce nhỏ hơn thì trượt | ✅ độ khó 1 / 2 / 3 (nonce 8 / 137 / 9194) |
| Tổng số lần băm, thời gian đào, tốc độ băm là số đo thật | ✅ `total_attempts = total_nonce + số block` |
| `previous_hash` của mỗi block khớp hash block trước | ✅ |
| Đồng thuận khi hòa tổng công → giữ nút trung thực | ✅ hai chuỗi cùng công 20, cùng 5 block |
| Nhánh tấn công **đào lại đúng dữ liệu gốc** (không bịa bản ghi) | ✅ payload phần đuôi giống chuỗi trung thực |
| Đào vượt 2 khối → chuỗi tấn công nặng hơn và được chọn (51%) | ✅ công 20 → 28 |
| Chuỗi không hợp lệ bị loại khỏi đồng thuận | ✅ |
| Chặn file sai định dạng / quá 5 MB / tên xấu; chặn dữ liệu âm, vô lý, rỗng | ✅ 5/5 và 4/4 trường hợp |
| Đọc CSV có BOM của Excel; từ chối file rỗng | ✅ |
| `safe_error` không lộ đường dẫn/traceback ra giao diện | ✅ chỉ còn "mã lỗi: E-IO-02" |
| `config.toml` giữ cấu hình bảo mật; không có secret bị commit | ✅ |
| `app.py` không nhúng CSS/HTML trang trí | ✅ giao diện dùng theme của Streamlit |

---

## 3. Kiểm thử tầng HTTP + WebSocket (`web_test.py`)

| Kiểm tra | Kết quả đo |
|---|---|
| Server khởi động, `/_stcore/health` = ok | ✅ cổng ngẫu nhiên, ví dụ 58756 |
| Trang chủ trả 200 và có khung ứng dụng | ✅ HTTP 200, 6.463 byte |
| Đường dẫn lạ chỉ trả khung SPA | ✅ `/khong-ton-tai-12345` giống hệt trang chủ (hành vi bình thường của Streamlit) |
| Không phục vụ file nguồn/dữ liệu qua HTTP | ✅ đã thử `/app.py`, `/security.py`, `/ml/model.pkl`, `/.streamlit/config.toml`, `/data/power_consumption.csv` → không rò rỉ |
| Tài nguyên tĩnh tải được | ✅ `static/js/index.*.js` → HTTP 200 |
| WebSocket `/_stcore/stream` (kênh chạy app) | ✅ **HTTP/1.1 101 Switching Protocols** |

**Ghi nhận (không phải lỗi, nhưng cần biết):** tầng app **không** gửi security header nào
(`X-Content-Type-Options`, `X-Frame-Options`, CSP, HSTS). Đây là việc của tầng proxy khi deploy —
đã có cấu hình Nginx sẵn ở [SECURITY-CHECKLIST.md](SECURITY-CHECKLIST.md) mục 3.1.

---

## 4. Độ bền dữ liệu đầu vào (10 loại CSV)

| Tình huống | Kỳ vọng | Thực tế |
|---|---|---|
| CSV hợp lệ | chấp nhận | ✅ 2 dòng |
| Thiếu cột `consumption_kwh` | chặn | ✅ "Thiếu cột bắt buộc: consumption_kwh." |
| Có giá trị âm | chặn | ✅ "Mức tiêu thụ điện không được âm." |
| Có `NaN` | chặn | ✅ "Không có bản ghi hợp lệ sau khi làm sạch…" |
| Có `Infinity` | chặn | ✅ như trên |
| Trùng mốc thời gian | chấp nhận, gộp | ✅ giữ bản ghi cuối |
| Thời gian dạng ISO có `T` | chấp nhận | ✅ 1 dòng |
| Timestamp sai hoàn toàn ("hom-qua") | chặn | ✅ như trên |
| File rỗng (chỉ header) | chặn | ✅ "File không có dữ liệu." |
| Giá trị phi lý (1e12 kWh) | chặn | ✅ "Có giá trị tiêu thụ vượt mức hợp lệ (1.000.000 kWh)." |
| Ngưỡng dung lượng 5 MB | đúng ngưỡng cho qua, vượt 1 byte chặn | ✅ |
| File lớn 100.000 dòng (2,4 MB) | xử lý nhanh | ✅ 0,06 s (sau khi gộp trùng còn 168 dòng do mốc thời gian lặp) |
| CSV do Excel lưu (có BOM) | đọc được, không hỏng tên cột | ✅ `security.read_uploaded_csv()` dùng `utf-8-sig` |

→ Không có trường hợp nào làm app vỡ; mọi lỗi đều trả về thông báo tiếng Việt an toàn (không traceback).

---

## 5. Hiệu năng khi đứng demo (số đo thật trên laptop)

| Thao tác trên giao diện | Thời gian | Ghi chú cho người điều khiển máy |
|---|---|---|
| Dự đoán 12 giờ bằng RandomForest — lần đầu | **~1,1 s** | Bao gồm nạp `ml/model.pkl` (5 MB); sau đó Streamlit cache lại |
| Dự đoán cùng tham số (đã cache) | **~0,02 s** | Bấm lại gần như tức thời |
| Dự đoán bằng baseline tuyến tính | ~0,06 s | Backtest 1 bước trên toàn bộ dữ liệu |
| Dựng chuỗi hash 720 block (tab Blockchain/Hash) | **~0,01 s** | Gần như tức thời |
| Đào 7 block — độ khó 1 | 0,00 s | |
| Đào 7 block — độ khó 2 (mặc định) | **0,01 s** | Nên để mức này khi demo |
| Đào 7 block — độ khó 3 | 0,10 s | |
| Đào 7 block — độ khó 4 | **~2,4 s** | Chỉ dùng khi muốn cho thấy "độ khó làm chậm việc đào" |
| Bật "Mô phỏng kẻ tấn công đào lại" (đào lại toàn bộ nhánh + so sánh 2 chuỗi) | ~0,1 – 5 s tuỳ độ khó | Có cache theo tham số; đổi độ khó là phải đào lại |

---

## 6. Kiểm thử trên trình duyệt thật (`browser_test.py`)

Trình duyệt: **Microsoft Edge (headless)** qua Playwright, viewport **1440×900** (độ phân giải laptop khi demo).

| # | Kiểm tra | Kết quả |
|---|---|---|
| 1 | Server sẵn sàng cho trình duyệt | ✅ |
| 2 | Mở được trình duyệt thật (msedge) | ✅ |
| 3 | Trang hiển thị đúng tiêu đề đề tài | ✅ |
| 4 | Sidebar "Điều khiển demo" hiển thị | ✅ |
| 5 | Sidebar chia nhóm Dữ liệu / Mô hình / Mô phỏng Blockchain | ✅ |
| 6 | Đủ 5 tab điều hướng | ✅ 5/5 |
| 7 | Tab Tổng quan hiện chỉ số MAE của mô hình | ✅ |
| 8 | Tab Tổng quan có bảng so sánh RandomForest với baseline | ✅ |
| 9 | Tab Tổng quan **không tràn ngang, không cắt chữ số liệu** | ✅ tràn ngang 0 px |
| 10 | Tab Hash báo dữ liệu hợp lệ | ✅ |
| 11 | Tab Hash có thẻ block kèm hash | ✅ |
| 12 | Tab Hash hiện trạng thái Hợp lệ | ✅ |
| 13 | Tab Hash **không tràn ngang, không cắt chữ số liệu** | ✅ tràn ngang 0 px |
| 14 | Tab PoW hiện bảng block + tổng nonce | ✅ |
| 15 | Bật "Mô phỏng dữ liệu bị sửa" → tab Hash báo bị sửa, tab PoW báo **KHÔNG hợp lệ** | ✅ cả hai |
| 16 | Tắt mô phỏng sửa dữ liệu → chuỗi quay lại **Hợp lệ** | ✅ |
| 17 | "Mô phỏng kẻ tấn công đào lại" (đào vượt = 0) → đồng thuận **giữ nút trung thực** | ✅ |
| 18 | Tăng "Số khối đào vượt thêm" → **nút tấn công thắng** (mô phỏng 51%) | ✅ |
| 19 | Tab PoW (kịch bản 51%) không tràn ngang | ✅ tràn ngang 0 px |
| 20 | Tab Dữ liệu hiện bảng dữ liệu đầu vào | ✅ |
| 21 | Tab Hướng dẫn hiện kịch bản thuyết trình | ✅ |
| 22 | Không lộ traceback / đường dẫn file ra trình duyệt | ✅ |
| 23 | Không còn giao diện cũ (hero tiếng Anh, pill trang trí) | ✅ |

### Ảnh chụp màn hình (dùng được luôn cho slide) — thư mục `anh-demo/`

| File | Nội dung |
|---|---|
| `01-tong-quan-ml.png` | Tab Tổng quan: 2 hàng ô số liệu (MAE/RMSE/R²) + biểu đồ 720 giờ + bảng dự báo |
| `02-blockchain-hop-le.png` | Tab Hash: trạng thái Hợp lệ + 4 thẻ block kèm hash/previous_hash |
| `03-dong-thuan-pow.png` | Tab PoW: số block, độ khó, tổng nonce, thời gian đào, tốc độ băm, bảng block |
| `04-phat-hien-sua-du-lieu.png` | Kịch bản sửa dữ liệu: "Block bị sửa #0", băng đỏ, thẻ Block #0 ghi 9999.0 kWh |
| `05-dong-thuan-giu-trung-thuc.png` | Hai thẻ chuỗi + kết luận giữ nút trung thực (hòa tổng công 28) |
| `06-tan-cong-51.png` | Hai thẻ chuỗi + kết luận nút tấn công thắng (36 > 28, mô phỏng 51%) |
| `07-du-lieu.png` | Tab Dữ liệu: bảng dữ liệu + bản ghi sẽ ghi vào blockchain |
| `08-huong-dan-demo.png` | Tab Hướng dẫn: kịch bản thuyết trình 6 bước |

---

## 7. Lỗi đã gặp trong lúc kiểm thử (và cách xử lý)

| Hiện tượng | Nguyên nhân | Xử lý |
|---|---|---|
| Script trình duyệt không bấm được tab "Dữ liệu" | Selector cũ `[data-testid="stTabs"] button` bắt nhầm nút **"Tải dữ liệu đã làm sạch"** nằm trong tab. DOM thật của Streamlit 1.65: tab là `[role="tab"]` trong `[role="tablist"]` | `click_tab()` dùng `[role="tablist"] [role="tab"]` |
| Không bấm được công tắc mô phỏng sau khi đổi `st.checkbox` → `st.toggle` | Vị trí bấm thay đổi | Thêm `click_control()` thử lần lượt `role=checkbox`, `role=switch`, rồi bấm theo nhãn |
| Playwright không mở được trình duyệt (`EPERM ... mkdtemp '...playwright-artifacts-XXXXXX'`) | `%TEMP%` của Windows cho Python ghi nhưng **chặn tiến trình node của Playwright** tạo thư mục tạm (gặp trong môi trường sandbox; cũng xảy ra trên máy bị hạn chế quyền) | `browser_test.py` và `ui_test.py` **luôn** đặt `TEMP/TMP` về `.pw-tmp` trong project (đã gitignore) trước khi chạy |
| Tiến trình kiểm thử trả mã lỗi 1 dù mọi kiểm tra đạt | Thư mục tạm hệ thống không xoá được lúc thoát (atexit) | Cùng cách xử lý như trên |
| Mất log khi tiến trình thoát bất thường | stdout bị buffer | Thêm `flush=True` vào các hàm in kết quả của bộ kiểm thử |

*Không có lỗi nào thuộc về ứng dụng* — các lỗi trên đều nằm ở phía script kiểm thử/môi trường.

---

## 8. Những gì **chưa** kiểm thử (nói thẳng để không nói quá)

1. **Nhiều người dùng cùng lúc** — chưa test tải (2–5 phiên đồng thời); Streamlit tạo session riêng nhưng chưa đo.
2. **Màn hình nhỏ hơn laptop** — mới test 1440×900; chưa test tablet/điện thoại (Streamlit tự xếp cột dọc dưới 640 px nhưng chưa xác minh bằng mắt).
3. **HTTPS/CORS/security headers thật** — thuộc tầng deploy (Nginx/Cloudflare), chưa dựng.
4. **Upload qua WebSocket bằng tay trong trình duyệt** — phần chặn sai định dạng/dung lượng đã test ở tầng hàm
   (`validate_upload`, `read_uploaded_csv`) và qua `AppTest`; chưa kéo–thả file thật trong trình duyệt.
5. **Trình duyệt khác** — mới chạy Edge; Chrome/Firefox chưa chạy (script hỗ trợ sẵn `chrome`).
6. **`ml/evaluation.png`** — script huấn luyện có thể xuất biểu đồ này nhưng máy hiện chưa cài `matplotlib`
   (không bắt buộc); file này không tồn tại trong repo.

---

## 9. Checklist kiểm thử trước ngày demo

- [ ] `.\.venv\Scripts\python.exe tools\smoke_test.py` → 33/33
- [ ] `.\.venv\Scripts\python.exe tools\ui_test.py` → 21/21
- [ ] `.\.venv\Scripts\python.exe tools\web_test.py` → 20/20
- [ ] `.\.venv\Scripts\python.exe tools\browser_test.py` → 23/23 (và ảnh trong `anh-demo/` được cập nhật)
- [ ] `powershell -ExecutionPolicy Bypass -File .\run_demo.ps1` → mở được `http://localhost:8501`
- [ ] Thử upload 1 file `.txt` và 1 file > 5 MB → bị chặn kèm thông báo tiếng Việt
- [ ] Bật/tắt 2 công tắc mô phỏng đúng như kịch bản ở [KICH-BAN-DEMO.md](KICH-BAN-DEMO.md)
