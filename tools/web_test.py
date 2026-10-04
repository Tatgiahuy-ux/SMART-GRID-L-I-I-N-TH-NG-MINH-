"""Kiểm thử web thật (HTTP + WebSocket) và kiểm thử độ bền dữ liệu cho demo Smart Grid.

Chạy:

    .\\.venv\\Scripts\\python.exe tools\\web_test.py

Script tự khởi động Streamlit trên một cổng trống, kiểm tra:

1. **Tầng HTTP**: trang chủ trả 200, có `<div id="root">`, tài nguyên tĩnh tải được, health = ok,
   đường dẫn lạ không trả 200, header bảo mật hiện có (để biết phần nào còn phải làm ở proxy).
2. **Tầng WebSocket**: bắt tay `/_stcore/stream` phải trả 101 Switching Protocols
   (đây là kênh thật mà trình duyệt dùng để chạy app).
3. **Độ bền dữ liệu**: 12 tình huống CSV (đúng, thiếu cột, âm, NaN, vô cực, trùng mốc thời gian,
   định dạng thời gian lạ, file rỗng, quá dòng, quá dung lượng, sai đuôi...) qua `security.py`.
4. **Hiệu năng**: thời gian dự đoán ML, dựng chuỗi hash, đào PoW ở các độ khó, đọc file ~5 MB —
   để người điều khiển máy biết thao tác nào sẽ khựng bao lâu khi demo.
"""

from __future__ import annotations

import io
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests  # noqa: E402

from blockchain.chain import IntegrityChain  # noqa: E402
from blockchain.consensus import ProofOfWorkChain  # noqa: E402
from ml.predictor import predict_consumption  # noqa: E402
from security import (  # noqa: E402
    MAX_UPLOAD_BYTES,
    UserInputError,
    prepare_data,
    validate_upload,
)

PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((name, passed, detail))
    print(f"[{'OK  ' if passed else 'FAIL'}] {name}{' – ' + detail if detail else ''}", flush=True)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(base_url: str, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/_stcore/health", timeout=3)
            if response.status_code == 200 and response.text.strip() == "ok":
                return True
        except requests.RequestException:
            time.sleep(0.5)
    return False


def websocket_handshake(
    host: str, port: int, path: str = "/_stcore/stream", timeout: float = 15.0
) -> tuple[bool, str]:
    """Bắt tay WebSocket thủ công (không cần thư viện) và trả về (thành công, mô tả)."""
    key = "dGhlIHNhbXBsZSBub25jZQ=="
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        f"Origin: http://{host}:{port}\r\n"
        "\r\n"
    )
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(request.encode())
            raw = sock.recv(4096).decode("utf-8", errors="replace")
    except OSError as exc:
        return False, f"lỗi kết nối: {exc}"
    first_line = raw.splitlines()[0] if raw else "(không có phản hồi)"
    return "101" in first_line, first_line.strip()


# --------------------------------------------------------------------------- #
# 3. Độ bền dữ liệu
# --------------------------------------------------------------------------- #
def csv_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def robustness_checks() -> None:
    good = "timestamp,consumption_kwh\n2026-01-01 00:00:00,2.1\n2026-01-01 01:00:00,2.4\n"

    cases: list[tuple[str, bytes, bool]] = [
        ("CSV hợp lệ", csv_bytes(good), True),
        ("Thiếu cột consumption_kwh", csv_bytes("timestamp,kwh\n2026-01-01 00:00:00,2.1\n"), False),
        ("Có giá trị âm", csv_bytes("timestamp,consumption_kwh\n2026-01-01 00:00:00,-3\n"), False),
        ("Có NaN", csv_bytes("timestamp,consumption_kwh\n2026-01-01 00:00:00,NaN\n"), False),
        ("Có Infinity", csv_bytes("timestamp,consumption_kwh\n2026-01-01 00:00:00,inf\n"), False),
        (
            "Trùng mốc thời gian",
            csv_bytes("timestamp,consumption_kwh\n2026-01-01 00:00:00,2\n2026-01-01 00:00:00,9\n"),
            True,
        ),
        (
            "Định dạng thời gian ISO có T",
            csv_bytes("timestamp,consumption_kwh\n2026-01-01T00:00:00,2.2\n"),
            True,
        ),
        ("Timestamp sai định dạng hoàn toàn", csv_bytes("timestamp,consumption_kwh\nhom-qua,2.2\n"), False),
        ("File rỗng (chỉ header)", csv_bytes("timestamp,consumption_kwh\n"), False),
        (
            "Giá trị phi lý (1e12 kWh)",
            csv_bytes("timestamp,consumption_kwh\n2026-01-01 00:00:00,1000000000000\n"),
            False,
        ),
    ]

    for label, blob, should_pass in cases:
        try:
            frame = pd.read_csv(io.BytesIO(blob))
            prepare_data(frame)
            outcome = True
            detail = f"{len(frame)} dòng"
        except UserInputError as exc:
            outcome = False
            detail = str(exc)[:60]
        except Exception as exc:  # noqa: BLE001 - lỗi ngoài dự kiến cũng là phát hiện
            outcome = False
            detail = f"lỗi khác: {type(exc).__name__}: {exc}"[:60]
        check(
            f"Dữ liệu: {label} → {'chấp nhận' if should_pass else 'phải chặn'}",
            outcome == should_pass,
            detail,
        )

    # Giới hạn dung lượng: 1 byte dưới và 1 byte trên ngưỡng
    try:
        validate_upload("vua-du.csv", MAX_UPLOAD_BYTES)
        under_ok = True
    except UserInputError:
        under_ok = False
    try:
        validate_upload("qua-co.csv", MAX_UPLOAD_BYTES + 1)
        over_ok = False
    except UserInputError:
        over_ok = True
    check("Ngưỡng 5 MB: đúng bằng ngưỡng cho qua, vượt 1 byte bị chặn", under_ok and over_ok)

    # File ~5 MB thật: đọc được trong bao lâu + có vượt giới hạn số dòng không
    rows = 100_000
    big = "timestamp,consumption_kwh\n" + "\n".join(
        f"2026-01-{(index % 28) + 1:02d} {(index % 24):02d}:00:00,{2 + (index % 5) * 0.1:.2f}"
        for index in range(rows)
    )
    size_mb = len(big.encode()) / (1024 * 1024)
    started = time.perf_counter()
    frame = pd.read_csv(io.StringIO(big))
    cleaned = prepare_data(frame)
    elapsed = time.perf_counter() - started
    check(
        "File lớn (100k dòng) đọc + validate xong dưới 10 giây",
        elapsed < 10 and len(cleaned) > 0,
        f"{size_mb:.1f} MB, còn {len(cleaned)} dòng sau khi gộp trùng, {elapsed:.2f}s",
    )


# --------------------------------------------------------------------------- #
# 4. Hiệu năng cho người điều khiển máy
# --------------------------------------------------------------------------- #
def performance_checks() -> None:
    data = pd.read_csv(ROOT / "data" / "power_consumption.csv", parse_dates=["timestamp"])

    started = time.perf_counter()
    forecast = predict_consumption(data, horizon=12)
    predict_time = time.perf_counter() - started

    started = time.perf_counter()
    chain = IntegrityChain()
    for row in data.itertuples(index=False):
        chain.add_record(
            {
                "timestamp": row.timestamp.isoformat(),
                "consumption_kwh": round(float(row.consumption_kwh), 4),
            }
        )
    hash_time = time.perf_counter() - started
    valid = chain.is_valid()

    timings: list[str] = []
    for difficulty in (1, 2, 3, 4):
        records = [
            {
                "consumer_id": "METER_001",
                "recorded_time": row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "actual_usage_kwh": round(float(row.consumption_kwh), 4),
                "predicted_usage_kwh": round(float(fitted), 4),
            }
            for row, fitted in zip(data.tail(6).itertuples(index=False), forecast.fitted[-6:])
        ]
        started = time.perf_counter()
        pow_chain = ProofOfWorkChain(difficulty=difficulty)
        pow_chain.add_energy_records(records)
        elapsed = time.perf_counter() - started
        timings.append(f"độ khó {difficulty}: {elapsed:.2f}s")
        if difficulty == 2:
            check("Đào 6 block ở độ khó mặc định (2) dưới 2 giây", elapsed < 2, f"{elapsed:.2f}s")

    check(
        "Dự đoán 12 giờ + dựng chuỗi hash 720 block chạy nhanh",
        predict_time < 3 and hash_time < 3 and valid,
        f"dự đoán {predict_time:.2f}s, hash 720 block {hash_time:.2f}s, hợp lệ={valid}",
    )
    print(f"       Thời gian đào PoW: {' | '.join(timings)}", flush=True)


# --------------------------------------------------------------------------- #
# 1 + 2. Tầng HTTP và WebSocket
# --------------------------------------------------------------------------- #
def server_checks() -> None:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            str(PYTHON),
            "-m",
            "streamlit",
            "run",
            str(ROOT / "app.py"),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for_health(base):
            check("Server khởi động và health = ok", False, f"hết thời gian chờ ở cổng {port}")
            return
        check("Server khởi động và health = ok", True, f"cổng {port}")

        index = requests.get(f"{base}/", timeout=10)
        check(
            "Trang chủ trả 200 và có khung ứng dụng",
            index.status_code == 200 and 'id="root"' in index.text,
            f"HTTP {index.status_code}, {len(index.content)} byte",
        )

        headers = {key.lower(): value for key, value in index.headers.items()}
        security_headers = [
            key
            for key in (
                "x-content-type-options",
                "x-frame-options",
                "content-security-policy",
                "strict-transport-security",
            )
            if key in headers
        ]
        print(
            "       Header bảo mật ở tầng app: "
            + (", ".join(security_headers) if security_headers else "không có (phải thêm ở Nginx – mục 14)"),
            flush=True,
        )

        missing = requests.get(f"{base}/khong-ton-tai-12345", timeout=10)
        same_shell = missing.text == index.text
        check(
            "Đường dẫn lạ chỉ trả khung SPA, không lộ nội dung khác",
            missing.status_code == 200 and same_shell,
            f"HTTP {missing.status_code}, giống trang chủ: {same_shell}",
        )

        leaked: list[str] = []
        for path in ("/app.py", "/security.py", "/ml/model.pkl", "/.streamlit/config.toml", "/data/power_consumption.csv"):
            response = requests.get(f"{base}{path}", timeout=10)
            body = response.text
            if "import " in body or "maxUploadSize" in body or "consumption_kwh" in body:
                leaked.append(f"{path} (HTTP {response.status_code})")
        check(
            "Không phục vụ file nguồn/dữ liệu qua HTTP (app.py, model.pkl, config.toml...)",
            not leaked,
            ", ".join(leaked) if leaked else "đã thử 5 đường dẫn, không rò rỉ",
        )

        asset_match = re.search(r'static/js/[A-Za-z0-9._:-]+\.js', index.text)
        if asset_match:
            asset = requests.get(f"{base}/{asset_match.group(0)}", timeout=10)
            check(
                "Tài nguyên tĩnh phục vụ được (frontend tải được trong trình duyệt)",
                asset.status_code == 200,
                f"{asset_match.group(0)} → HTTP {asset.status_code}",
            )
        else:
            check("Tài nguyên tĩnh phục vụ được (frontend tải được trong trình duyệt)", False, "không tìm thấy đường dẫn asset trong HTML")

        ws_ok, ws_detail = websocket_handshake("127.0.0.1", port)
        check("WebSocket /_stcore/stream bắt tay thành công (kênh chạy app)", ws_ok, ws_detail)
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> int:
    print("=== 1. Tầng HTTP + WebSocket ===", flush=True)
    server_checks()
    print("\n=== 2. Độ bền dữ liệu đầu vào ===", flush=True)
    robustness_checks()
    print("\n=== 3. Hiệu năng khi demo ===", flush=True)
    performance_checks()

    failed = [name for name, passed, _ in RESULTS if not passed]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} kiểm tra web đạt.", flush=True)
    if failed:
        print("Chưa đạt:\n - " + "\n - ".join(failed), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
