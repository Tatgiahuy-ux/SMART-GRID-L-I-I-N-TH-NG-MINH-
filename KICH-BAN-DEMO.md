# Kịch bản điều khiển máy khi demo — Nhóm 17

> Dành cho **người phụ trách tích hợp & điều khiển máy** (bạn). Mục tiêu: demo 7–8 phút, không lỗi,
> không bị động khi giảng viên hỏi. Bảng số liệu để làm slide nằm ở [TICH-HOP-NOTE-PPT.md](TICH-HOP-NOTE-PPT.md).

---

## 0. Chuẩn bị trước giờ demo 15 phút

- [ ] Cắm sạc laptop, tắt chế độ ngủ (`Power & battery` → Screen timeout 30 phút).
- [ ] Tắt thông báo: `Focus assist` / `Do not disturb` bật **On**.
- [ ] Đóng các app nặng (Chrome nhiều tab, Docker, game) để Streamlit chạy mượt.
- [ ] Chạy trước một lần: `powershell -ExecutionPolicy Bypass -File .\run_demo.ps1` → xác nhận hiện
      `http://localhost:8501` và trang mở được; sau đó **Ctrl + C** để tắt, lúc demo chạy lại.
- [ ] Mở sẵn 1 cửa sổ trình duyệt trắng để dành; zoom trình duyệt **110–125%** cho giảng viên đọc được.
- [ ] Mở sẵn VS Code ở project (để chứng minh "chạy trên Visual Studio Code" khi được hỏi).
- [ ] Chụp sẵn 4 ảnh dự phòng: tab Tổng quan & ML, tab Blockchain/Hash, tab Đồng thuận PoW (hợp lệ),
      và ảnh "KHÔNG hợp lệ" khi bật mô phỏng sửa dữ liệu.

## 1. Khởi động bằng một lệnh

```powershell
cd C:\Users\huy\Project\CongNgheVienThong
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
```

Script tự: kiểm tra `.venv` → cài thư viện nếu thiếu → huấn luyện nếu chưa có `ml\model.pkl` →
chạy 9 kiểm thử nhanh → mở Streamlit. Khi thấy dòng `Địa chỉ demo: http://localhost:8501` là sẵn sàng.

- Đổi cổng nếu 8501 bận: `.\run_demo.ps1 -Port 8502`
- Bỏ qua kiểm thử khi đã kiểm tra trước: `.\run_demo.ps1 -SkipTests`
- Chạy trong VS Code: mở Terminal → dán đúng lệnh trên.

## 2. Thứ tự bấm máy (7 chặng)

| Chặng | Thao tác trên giao diện | Giá trị cài đặt | Điều sẽ thấy | Câu nói mẫu (1 câu) |
|---|---|---|---|---|
| 1 | Tab **Tổng quan & ML** | Nguồn dữ liệu: `power_consumption.csv` · Mô hình: `RandomForest` · Số giờ: `6` | Biểu đồ 720 giờ + 3 ô số liệu + bảng dự đoán 6 giờ tới | "Đây là 30 ngày dữ liệu tiêu thụ theo giờ, mô hình đang dự đoán 6 giờ tiếp theo." |
| 2 | Vẫn tab đó, cuộn xuống **Chất lượng mô hình** | — | MAE `0.20`, RMSE `0.25`, R² `0.97` | "Trên 144 giờ kiểm tra, sai số trung bình chỉ 0,2 kWh, R² 0,97." |
| 3 | Đổi **Mô hình ML** sang `Baseline xu hướng tuyến tính` | — | Chỉ số đổi thành MAE ~`1.23` (backtest) | "Nếu chỉ ngoại suy tuyến tính thì sai số gấp hơn 6 lần — đây là lý do dùng học máy." Đổi lại RandomForest. |
| 4 | Tab **Blockchain / Hash** | Tắt "Mô phỏng dữ liệu bị sửa" | Trạng thái **HỢP LỆ**, bảng hash từng block | "Mỗi bản ghi được băm SHA-256 và móc vào hash của block trước." |
| 5 | Vẫn tab đó, bật **Mô phỏng dữ liệu bị sửa** | Bật | Trạng thái **ĐÃ BỊ SỬA** (đỏ) | "Chỉ cần sửa một số điện, toàn bộ chuỗi báo sai ngay." Tắt lại. |
| 6 | Tab **Đồng thuận PoW** | Độ khó: `2` · Số block: `6` · Mã đồng hồ: `METER_001` | 7 block, tổng nonce, thời gian đào, tốc độ băm ~170.000 H/s | "Mỗi block phải được đào: tìm nonce sao cho hash bắt đầu bằng hai số 0." |
| 7 | Vẫn tab đó, bật **Mô phỏng kẻ tấn công đào lại** → kéo **Số khối đào vượt thêm** = `0`, rồi `2` | 0 → 2 | 0: "giữ chuỗi của nút trung thực"; 2: "nút tấn công thắng" | "Kẻ tấn công đào lại thì chuỗi vẫn hợp lệ về hash; hệ thống phải so tổng công. Khi hắn đào vượt, hắn thắng — đó là tấn công 51%, đây là giới hạn thật của blockchain." |
| 8 | Tab **Hướng dẫn demo** (tuỳ thời gian) | — | Kịch bản 7 bước + cảnh báo giới hạn | "Tụi em ghi rõ giới hạn để không nói quá về bảo mật." |

**Thời lượng gợi ý:** chặng 1–3 ≈ 3 phút · chặng 4–5 ≈ 1,5 phút · chặng 6–7 ≈ 2,5 phút · còn lại dự phòng.

**Lưu ý khi bấm:** đổi độ khó lên `4` sẽ mất khoảng 1,3 giây đào — chỉ dùng nếu còn thời gian và muốn
cho thấy độ khó làm chậm việc đào; đừng để ở mức 4 suốt buổi vì mỗi lần bấm lại phải đào lại.

## 3. Phương án dự phòng

| Tình huống | Dấu hiệu | Xử lý ngay |
|---|---|---|
| Cổng 8501 bận | Script báo "Cổng 8501 đang bận" | Chạy lại `.\run_demo.ps1 -Port 8502` |
| Thiếu scikit-learn / mất `ml\model.pkl` | App hiện cảnh báo vàng "Đang dùng baseline thay cho RandomForest" | Vẫn demo bình thường; nói: "app tự lùi về baseline, đây là cơ chế an toàn của phần tích hợp." Muốn có lại RF: `.\run_demo.ps1` (script tự huấn luyện) |
| Trang bị treo / trắng | Không thấy nội dung | Nhấn `R` (rerun) hoặc `Ctrl + R` trên trình duyệt; nếu vẫn lỗi, Ctrl + C ở terminal rồi chạy lại `run_demo.ps1` |
| Mất mạng | — | Demo **không cần mạng** (dữ liệu và mô hình nằm trong repo); chỉ cần mạng nếu phải cài lại thư viện |
| Mất điện / máy chết | — | Dùng 4 ảnh chụp dự phòng ở mục 0 và nhờ người thuyết trình nói theo bảng số liệu trong `TICH-HOP-NOTE-PPT.md` |
| Giảng viên yêu cầu xem code | — | Mở VS Code: `app.py` (tích hợp) → `ml/predictor.py` → `blockchain/consensus.py`; nhấn mạnh `resolve_conflict()` là luật đồng thuận |

## 4. Bảng kiểm 60 giây trước khi bắt đầu

- [ ] Terminal hiện `Địa chỉ demo: http://localhost:8501`, không có dòng lỗi đỏ.
- [ ] Trình duyệt đã mở đúng địa chỉ, đang ở tab **Tổng quan & ML**.
- [ ] Sidebar đúng: RandomForest · 6 giờ · độ khó 2 · 6 block · METER_001 · hai công tắc đều **tắt**.
- [ ] Ảnh dự phòng đã mở sẵn trong một cửa sổ khác.
- [ ] Người thuyết trình đứng cạnh, đã biết chặng nào mình nói.

## 5. Sau demo

- [ ] Ghi lại câu hỏi giảng viên đặt ra (để bổ sung vào báo cáo).
- [ ] Lưu ảnh chụp màn hình các tab vào thư mục `anh-demo/` để dán vào file Word.
- [ ] Nếu có lỗi phát sinh, ghi rõ lỗi + cách xử lý vào cuối `BAO-CAO-DANH-GIA.md`.

## 6. Q&A dự kiến (8 câu)

| Câu hỏi | Trả lời ngắn |
|---|---|
| Vì sao chọn Smart Grid mà không phải Smart Mobility? | Dữ liệu điện năng theo giờ dễ kiếm và mô hình chạy ổn định, ít lỗi vặt; nhóm tập trung làm chắc phần dự đoán + chống giả mạo trước. |
| Dữ liệu ở đâu ra? | Sinh bằng `ml/generate_data.py` (30 ngày × 24 giờ, seed 42, có đỉnh sáng/trưa/tối và nhiễu 0.2); chạy lại ra file trùng khớp từng byte với file nhóm đã gửi. |
| Sao không dùng mô hình chuỗi thời gian (LSTM/ARIMA)? | Dữ liệu nhỏ (720 dòng) và cần mô hình giải thích được trong thời gian ngắn; RandomForest cho R² 0.97 và nhanh. Hướng phát triển là thêm đặc trưng độ trễ và so sánh với ARIMA/LSTM. |
| PoW ở đây khác gì Bitcoin? | Cùng nguyên lý: tìm nonce để hash đạt độ khó, chuỗi liên kết bằng hash khối trước, luật chọn chuỗi nặng nhất. Khác: chỉ mô phỏng trong một tiến trình, độ khó rất thấp, không có mạng P2P và chữ ký số. |
| Nếu sửa dữ liệu rồi đào lại hết thì sao? | Chuỗi sẽ hợp lệ trở lại về hash — đó là lý do phải có luật đồng thuận theo tổng công; nếu kẻ tấn công nắm đa số năng lực đào thì hắn thắng (tấn công 51%), nhóm mô phỏng đúng kịch bản này. |
| Vì sao mỗi block lưu cả số dự đoán của ML? | Để lưu vết "mô hình đã dự đoán gì tại thời điểm đó" phục vụ đối soát/kiểm toán, và tính `deviation_kwh` giữa thực tế và dự đoán mà không ai sửa được. |
| Hệ thống chịu được bao nhiêu block? | Demo đào 6–12 block tuỳ chọn; tốc độ ~170.000 hash/giây trên laptop, độ khó 4 mất khoảng 1,3 giây cho 7 block. |
| Phần nào là của bạn? | Em phụ trách tích hợp: viết `app.py`, `ml/predictor.py`, `blockchain/chain.py` + `consensus.py`, bộ kiểm thử `tools/`, script chạy demo `run_demo.ps1`, và điều khiển máy khi demo. |
