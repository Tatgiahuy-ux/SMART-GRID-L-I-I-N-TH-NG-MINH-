# Checklist 20 mục bảo mật — web Smart Grid (Nhóm 17)

> **Web của nhóm là gì:** một ứng dụng **Streamlit chạy nội bộ** (`app.py`), phục vụ demo môn học.
> Web **không có đăng nhập, không có tài khoản người dùng, không có trang admin, không có database**;
> dữ liệu duy nhất người dùng gửi lên là **file CSV** để mô hình dự đoán.
>
> Vì vậy trong 20 mục: **7 mục phải có ngay** (đã làm xong trong repo), **7 mục chỉ cần khi đưa web
> lên internet**, **6 mục không áp dụng** vì web chưa có thành phần tương ứng. Chi tiết ở dưới.

---

## 1. Bảng tổng hợp 20 mục

| # | Mục | Phân loại | Trạng thái trong repo này |
|---|---|---|---|
| 1 | Hash password bằng Argon2/bcrypt | ⛔ Không áp dụng | Web không có mật khẩu. Nếu thêm đăng nhập → dùng `st.login` (OIDC) thay vì tự làm; nếu vẫn tự làm thì Argon2id |
| 2 | Rate limit cho đăng nhập | 🚀 Khi deploy | Chưa có đăng nhập. Khi deploy: rate limit ở Nginx/Cloudflare cho endpoint upload và `/_stcore/stream` |
| 3 | Session có giới hạn thời gian | 🚀 Khi deploy | Streamlit **không có** cấu hình timeout phiên; xử lý ở proxy hoặc bằng IdP khi dùng `st.login` |
| 4 | Xóa debug log thừa, không in token/API key/dữ liệu người dùng | ✅ Đã có | Log chỉ ghi lỗi kỹ thuật ra terminal; không có token/secret nào trong repo |
| 5 | Không lộ secret ở frontend | ✅ Đã có | Không có secret nào trong code; `.streamlit/secrets.toml` bị `.gitignore` chặn |
| 6 | Không hiển thị chi tiết lỗi ra ngoài | ✅ Đã có | `safe_error()` + `[client] showErrorDetails = "none"` |
| 7 | Giới hạn định dạng file upload | ✅ Đã có | `type=["csv"]` + `validate_upload()` chặn đuôi lạ và tên file xấu |
| 8 | Giới hạn dung lượng file upload | ✅ Đã có | 5 MB, chặn ở 2 lớp: `server.maxUploadSize` + `validate_upload()` |
| 9 | Dữ liệu người dùng phải validate lại ở server | ✅ Đã có | `prepare_data()` kiểm tra cột, kiểu, giá trị âm/vô lý, số dòng, trùng mốc thời gian |
| 10 | Thử đổi tham số người dùng (`/user/123` → `/user/124`) | ⛔ Không áp dụng | Web không có URL dạng `/user/{id}` và không có hồ sơ người dùng nào để lộ chéo |
| 11 | Đăng nhập tài khoản thường rồi vào trang admin | ⛔ Không áp dụng | Không có đăng nhập, không có trang admin |
| 12 | Parameterized query chống SQL Injection | ⛔ Không áp dụng | Web không dùng database. Nếu thêm Supabase/Postgres → xem mục 4.4 |
| 13 | Bắt buộc HTTPS toàn bộ | 🚀 Khi deploy | Hiện chạy `http://localhost` (nội bộ, không qua mạng) |
| 14 | Security headers chuẩn production | 🚀 Khi deploy | Thêm ở tầng Nginx (mục 4.1) |
| 15 | Cookie `HttpOnly`, `Secure`, `SameSite` | 🚀 Khi deploy | Streamlit tự đặt `HttpOnly`/`SameSite=lax`; cờ `Secure` chỉ bật khi Streamlit chạy HTTPS — xem mục 4.2 |
| 16 | CORS chỉ cho domain cần thiết, không dùng `*` | ✅ Đã có | `.streamlit/config.toml`: `enableCORS = true`, `enableXsrfProtection = true` |
| 17 | Không mở public database | ⛔ Không áp dụng | Không có database nào |
| 18 | Tài khoản database đủ quyền tối thiểu | ⛔ Không áp dụng | Không có database nào |
| 19 | Đưa web qua Cloudflare (proxy + WAF) | 🚀 Khi deploy | Chưa deploy; các bước ở mục 4.4 |
| 20 | Bật backup và theo dõi lỗi sau deploy | 🚀 Khi deploy | Đã có log lỗi phía server; backup + giám sát ở mục 4.5 |

**Tóm lại: web của bạn cần 7 mục ngay (đã xong), 7 mục khi lên internet, 6 mục không cần vì không có
đăng nhập / database.**

---

## 2. Nhóm A — 7 mục phải có (đã làm trong repo)

| Mục | Đã làm gì | File |
|---|---|---|
| 4 | Không có `print()` lộ dữ liệu trong luồng web; lỗi ghi qua `logging` ra **stderr của server**, không ra trình duyệt | `security.py`, `ml/predictor.py` |
| 5 | Không hard-code secret; `.gitignore` chỉ chặn `.streamlit/secrets.toml` (để `config.toml` được commit vì chỉ chứa cấu hình bảo mật) | `.gitignore` |
| 6 | `safe_error(exc, fallback)` ghi traceback vào log, trả về câu thông báo chung + **mã lỗi rút gọn** (`E-CSV-01`, `E-IO-02`…); thêm `showErrorDetails = "none"` để Streamlit không đổ traceback ra UI | `security.py`, `.streamlit/config.toml` |
| 7 | `st.file_uploader(type=["csv"])` + `validate_upload()` từ chối đuôi khác `.csv`, file rỗng, tên chứa `..`/`/`/`\` | `app.py`, `security.py` |
| 8 | `server.maxUploadSize = 5` (MB) và `validate_upload()` chặn file > 5 MB trước khi đọc nội dung | `.streamlit/config.toml`, `security.py` |
| 9 | `prepare_data()` validate lại toàn bộ ở server: cột bắt buộc, `to_datetime`/`to_numeric` lỗi → loại, chặn giá trị âm, chặn giá trị > 1.000.000 kWh, chặn vô cực, chặn > 200.000 dòng, bỏ mốc thời gian trùng | `security.py` |
| 16 | Giữ nguyên bảo vệ CORS + XSRF của Streamlit, **không** đặt `enableCORS = false` (đặt false sẽ khiến server trả `Access-Control-Allow-Origin: *`) | `.streamlit/config.toml` |

**Kiểm chứng tự động** (chạy `tools\smoke_test.py`): 5 kiểm tra bảo mật đã đạt —
chặn 5/5 file xấu (`.exe`, `.pdf`, quá 5 MB, rỗng, tên chứa `..`), chặn 4/4 dữ liệu sai
(thiếu cột, âm, vô lý, rỗng sau làm sạch), thông báo lỗi không lộ đường dẫn, `config.toml`
giữ đúng cấu hình, không có file secret nào bị commit.

### 2.1 Cách tự kiểm tra bằng tay (làm thử trước khi bảo vệ)

1. **File sai định dạng**: đổi tên `data\power_consumption.csv` thành `.txt` rồi upload → phải báo
   "Chỉ chấp nhận file .csv" (thậm chí không hiện được trong hộp chọn file vì đã lọc `type=["csv"]`;
   muốn thử thật thì dùng nút "Browse" và chọn *All files*).
2. **File quá lớn**: tạo file CSV ~6 MB → phải báo "File vượt quá giới hạn 5 MB".
3. **File thiếu cột**: CSV chỉ có 1 cột → báo "Thiếu cột bắt buộc: consumption_kwh".
4. **File có số âm**: sửa một dòng thành `-5` → báo "Mức tiêu thụ điện không được âm".
5. **Không lộ chi tiết lỗi**: khi lỗi xảy ra, màn hình chỉ hiện câu thông báo + mã lỗi; còn
   traceback đầy đủ nằm ở **terminal đang chạy Streamlit** (chỗ này chỉ người điều khiển máy thấy).
6. **Muốn xem lại lỗi chi tiết khi gỡ lỗi**: chạy
   `streamlit run app.py --client.showErrorDetails=full` (chỉ dùng khi phát triển, đừng dùng khi demo).

---

## 3. Nhóm B — 7 mục chỉ cần khi đưa web lên internet

> Hiện tại web chạy `http://localhost:8501` trên máy demo, không ai truy cập từ ngoài, nên 7 mục này
> **chưa cần**. Làm theo thứ tự dưới đây khi nhóm muốn public (ví dụ để giảng viên xem từ xa).

### 3.1 Mục 13 + 14 — HTTPS và security headers (Nginx làm reverse proxy)

```nginx
# /etc/nginx/conf.d/smartgrid.conf
limit_req_zone $binary_remote_addr zone=app:10m rate=30r/s;   # mục 2: rate limit

server {                                   # mục 13: ép toàn bộ sang HTTPS
    listen 80;
    server_name demo-nhom17.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    http2 on;
    server_name demo-nhom17.example.com;

    ssl_certificate     /etc/letsencrypt/live/demo-nhom17.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/demo-nhom17.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # mục 14: security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options    "nosniff" always;
    add_header X-Frame-Options           "SAMEORIGIN" always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy        "geolocation=(), microphone=(), camera=()" always;
    # CSP của Streamlit cần nới inline/eval; bắt đầu từ mức này rồi siết dần, kiểm tra Console của trình duyệt
    add_header Content-Security-Policy   "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self' wss:; frame-ancestors 'self'" always;

    client_max_body_size 6m;               # mục 8: khớp giới hạn upload 5 MB

    location / {
        limit_req zone=app burst=60 nodelay;
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade           $http_upgrade;   # Streamlit cần WebSocket
        proxy_set_header Connection        "upgrade";
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;                            # mục 3: proxy đóng phiên khi hết hạn
    }
}
```

Kiểm tra sau khi dựng: `curl -I https://demo-nhom17.example.com` phải thấy các header trên;
`Invoke-WebRequest http://...` phải bị 301 sang HTTPS.

### 3.2 Mục 15 — cookie `HttpOnly` / `Secure` / `SameSite`

- Streamlit tự đặt cookie xác thực với `HttpOnly` và `SameSite=lax` (không cần code thêm).
- Cookie XSRF lấy `SameSite` từ `server.xsrfCookieSameSite` (repo đang để `"lax"`).
- **Lưu ý thật:** cờ `Secure` của cookie XSRF chỉ được bật khi Streamlit **tự chạy HTTPS**
  (`server.sslCertFile`) hoặc khi đặt `SameSite=None`. Nếu Nginx lo HTTPS rồi chuyển tiếp HTTP vào
  Streamlit thì cookie sẽ thiếu cờ `Secure`. Hai cách xử lý:
  1. Cho Streamlit chạy HTTPS trực tiếp:
     `streamlit run app.py --server.sslCertFile cert.pem --server.sslKeyFile key.pem` (Nginx chuyển tiếp HTTPS).
  2. Giữ Nginx lo HTTPS và bù bằng HSTS (đã có ở mục 3.1) — chấp nhận cookie thiếu `Secure` trong mạng nội bộ.

### 3.3 Mục 3 — giới hạn thời gian phiên

Streamlit **không** có tuỳ chọn timeout phiên sẵn (đã kiểm tra danh sách cấu hình của bản 1.65).
Ba cách, chọn 1:

| Cách | Thực hiện | Phù hợp khi |
|---|---|---|
| Proxy đóng kết nối | `proxy_read_timeout 1800s;` (30 phút) ở Nginx | Nhanh nhất, đủ cho demo public |
| IdP quản lý phiên | Dùng `st.login()` (OIDC: Google/Microsoft) — thời hạn token do nhà cung cấp quản lý | Khi cần đăng nhập thật |
| Kiểm tra trong app | Lưu `st.session_state["last_seen"]`, nếu quá 30 phút thì hiện "Phiên đã hết hạn" và `st.stop()` | Khi muốn chủ động nhắc người dùng |

### 3.4 Mục 19 — Cloudflare (proxy + WAF)

1. Trỏ DNS domain về server, bật **Proxy (đám mây cam)**.
2. **SSL/TLS → Full (strict)**, bật *Always Use HTTPS*.
3. **Security → WAF → Managed Rules**: bật bộ luật Cloudflare Managed + OWASP Core.
4. **Security → Bots**: bật *Bot Fight Mode*.
5. **Security → WAF → Rate limiting rules**: giới hạn theo IP cho `/` và `/_stcore/stream`.
6. **Caching → Cache Rules**: *Bypass cache* cho `/_stcore/*` (WebSocket, không được cache).
7. Nếu chỉ cho nội bộ xem: **Zero Trust → Access** tạo policy email OTP — vừa chặn bot vừa không cần code đăng nhập.
8. Health check dùng `https://<domain>/_stcore/health` (endpoint này trả `ok`, đã kiểm chứng).

### 3.5 Mục 20 — backup và theo dõi lỗi

```powershell
# Sao lưu phần không thể sinh lại: mô hình + chỉ số + dữ liệu + tài liệu
$stamp = Get-Date -Format 'yyyyMMdd-HHmm'
$dest  = "D:\backup-nhom17\$stamp"
New-Item -ItemType Directory -Path $dest -Force | Out-Null
Copy-Item 'C:\Users\huy\Project\CongNgheVienThong\ml\model.pkl',
          'C:\Users\huy\Project\CongNgheVienThong\ml\metrics.json',
          'C:\Users\huy\Project\CongNgheVienThong\data\*.csv' -Destination $dest
Compress-Archive -Path $dest -DestinationPath "$dest.zip" -Force
```

- Đặt lịch bằng **Task Scheduler** (weekly) và **thử phục hồi** một lần để chắc chắn bản backup dùng được.
- Code + tài liệu đã có git làm bản sao; nhớ push lên GitHub sau mỗi buổi làm.
- **Theo dõi lỗi**: ghi log ra file khi chạy demo —
  `streamlit run app.py *>> logs\app.log`; các dòng `ERROR smart_grid:` là lỗi cần xem, kèm mã lỗi
  hiển thị cho người dùng (`E-CSV-01` = CSV hỏng, `E-IO-02` = lỗi đọc file…).
- **Bất thường**: nhiều dòng `E-CSV-*` liên tiếp từ cùng một IP = có người đang thử phá upload → chặn IP ở Cloudflare.
- Nếu deploy: bật health check `/_stcore/health` ở Cloudflare/UptimeRobot để biết web sập.

---

## 4. Nhóm C — 6 mục không áp dụng (và cách làm nếu sau này mở rộng)

### 4.1 Mục 1 — hash password

Web hiện **không có đăng nhập** nên không có mật khẩu nào để hash. Khi nào cần:
- **Cách khuyến nghị của Streamlit**: dùng `st.login()` với OIDC (Google/Microsoft) — không tự lưu
  mật khẩu, không tự hash, không tự quản phiên. Cấu hình ở `.streamlit/secrets.toml` (đã bị gitignore).
- **Nếu buộc phải tự làm form đăng nhập**: hash bằng **Argon2id** (`argon2-cffi`) hoặc **bcrypt**,
  **không** dùng MD5/SHA-1/SHA-256 đơn thuần; kèm khoá tạm sau nhiều lần sai.
- Mục 2 (rate limit) đã có sẵn công thức ở mục 3.1 (`limit_req_zone`); nếu thêm form đăng nhập thì tạo
  thêm zone riêng, ví dụ `rate=5r/m` cho route đăng nhập.

### 4.2 Mục 10 — thay đổi tham số người dùng (IDOR)

Không có URL `/user/{id}`, không có hồ sơ người dùng, mỗi phiên Streamlit chỉ thấy dữ liệu mình tải
lên. Khi nào cần: lúc thêm tài khoản và lịch sử dự đoán theo người dùng — khi đó phải kiểm tra quyền
sở hữu ở **server** cho mọi truy vấn (`WHERE owner_id = :current_user`), và tự test bằng 2 tài khoản
A/B: đăng nhập A rồi sửa id trên URL thành của B, hệ thống phải trả 403/404.

### 4.3 Mục 11 — truy cập trái phép trang admin

Không có trang admin. Khi nào cần: nếu thêm trang quản trị → kiểm tra vai trò ở server
(`if not st.user.is_logged_in or role != "admin": st.stop()`), không ẩn menu bằng CSS.

### 4.4 Mục 12, 17, 18 — database

Web **không dùng database** (dữ liệu nằm trong file CSV + mô hình `.pkl`). Lưu ý: file
`opencode.jsonc` có khai báo MCP server Supabase — nếu nhóm định lưu dữ liệu lên Supabase thì 3 mục
này thành bắt buộc:

| Mục | Việc phải làm |
|---|---|
| 12 | Luôn dùng truy vấn có tham số, ví dụ `conn.query("select * from meters where id = :id", params={"id": meter_id})` — không nối chuỗi SQL |
| 17 | Bật Row Level Security, không public schema/table; chỉ mở qua API có xác thực; không mở cổng Postgres ra internet |
| 18 | Tạo role riêng cho web chỉ có `SELECT/INSERT` trên đúng bảng cần dùng, không dùng role `postgres`/service key toàn quyền trong app |

---

## 5. Bảng kiểm nhanh trước khi nộp/bảo vệ

- [ ] `.\\.venv\\Scripts\\python.exe tools\\smoke_test.py` → **14/14 đạt** (có 5 kiểm tra bảo mật).
- [ ] `.\\.venv\\Scripts\\python.exe tools\\ui_test.py` → **9/9 đạt**.
- [ ] Thử upload 1 file `.txt` và 1 file ~6 MB → bị chặn kèm thông báo tiếng Việt dễ hiểu.
- [ ] Làm lỗi cố ý (ví dụ CSV sai định dạng) → màn hình **không** hiện traceback/đường dẫn file.
- [ ] `git status` không thấy `.streamlit/secrets.toml` (và file này không tồn tại).
- [ ] Trong repo không có `API key`, `token`, mật khẩu nào (tìm bằng `grep -i "api_key\|token\|password"`).
- [ ] Nếu demo qua mạng LAN: dùng `http://<ip-máy>:8501` chỉ trong phòng học, tắt sau khi demo xong.

> Ghi chú minh bạch: repo này là **demo giáo dục**. Việc bật HTTPS/WAF/Cloudflare/backup (nhóm B) chỉ
> thực hiện khi nhóm thật sự deploy; nếu chưa deploy thì trong báo cáo nên ghi rõ "đã chuẩn bị cấu
> hình, chưa triển khai" — không nên trình bày như đã có.
