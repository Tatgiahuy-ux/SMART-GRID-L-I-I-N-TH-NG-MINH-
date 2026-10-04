"""Kiểm thử end-to-end trên trình duyệt thật (Playwright + Microsoft Edge/Chrome).

Chạy:

    .\\.venv\\Scripts\\python.exe tools\\browser_test.py

Script tự khởi động Streamlit, mở app bằng trình duyệt thật (headless), rồi:

1. Kiểm tra trang hiển thị đúng tiêu đề, đủ 5 tab, có số liệu ML và bảng so sánh baseline.
2. Bấm qua từng tab và chụp ảnh màn hình vào ``anh-demo/`` (dùng cho slide báo cáo).
3. Bật công tắc "Mô phỏng dữ liệu bị sửa" → phải thấy trạng thái bị sửa; tắt lại → hợp lệ.
4. Bật "Mô phỏng kẻ tấn công đào lại" → phải thấy kết luận đồng thuận giữ nút trung thực,
   sau đó tăng số khối đào vượt → phải thấy kết luận nút tấn công thắng (mô phỏng 51%).
5. Kiểm tra bố cục ở độ phân giải laptop: không tràn ngang, ô số liệu không bị cắt chữ.
6. Xác nhận không có traceback nào lộ ra trình duyệt.

Yêu cầu: đã cài ``playwright`` và có sẵn Microsoft Edge hoặc Google Chrome
(không cần tải Chromium riêng: script dùng kênh ``msedge`` rồi tới ``chrome``).
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOT_DIR = ROOT / "anh-demo"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ensure_writable_temp() -> str:
    """Dùng thư mục tạm trong project cho Playwright (thay vì %TEMP% của Windows).

    Trên máy bị hạn chế quyền (hoặc môi trường sandbox), ``%TEMP%`` có thể cho Python ghi
    nhưng **chặn tiến trình con của Playwright** (node) tạo thư mục tạm, dẫn tới lỗi
    ``EPERM: operation not permitted, mkdtemp '...\\playwright-artifacts-XXXXXX'`` và không
    mở được trình duyệt nào. Thư mục ``.pw-tmp`` trong project (đã bị .gitignore) luôn dùng
    được, lại gọn vì artifact không rơi vào ổ hệ thống.
    """
    local_temp = ROOT / ".pw-tmp"
    local_temp.mkdir(exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = os.environ["TMPDIR"] = str(local_temp)
    tempfile.tempdir = str(local_temp)
    print(f"       Thư mục tạm cho trình duyệt: {local_temp}", flush=True)
    return str(local_temp)


ensure_writable_temp()

import requests  # noqa: E402
from playwright.sync_api import Error as PlaywrightError, sync_playwright  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
BROWSER_CHANNELS = ("msedge", "chrome")
VIEWPORT = {"width": 1440, "height": 900}  # độ phân giải laptop phổ biến khi demo


def check(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((name, passed, detail))
    print(f"[{'OK  ' if passed else 'FAIL'}] {name}{' – ' + detail if detail else ''}", flush=True)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(base_url: str, timeout: float = 120.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(f"{base_url}/_stcore/health", timeout=3).text.strip() == "ok":
                return True
        except requests.RequestException:
            time.sleep(0.5)
    return False


def launch_browser(playwright):
    """Mở Edge trước, không được thì thử Chrome (không tải Chromium)."""
    errors: list[str] = []
    for channel in BROWSER_CHANNELS:
        try:
            browser = playwright.chromium.launch(channel=channel, headless=True)
            return browser, channel
        except PlaywrightError as exc:
            errors.append(f"{channel}: {str(exc).splitlines()[0][:120]}")
    raise RuntimeError("Không mở được trình duyệt nào → " + " | ".join(errors))


def wait_text(page, text: str, timeout: int = 30000) -> bool:
    try:
        page.get_by_text(text, exact=False).first.wait_for(state="visible", timeout=timeout)
        return True
    except PlaywrightError:
        return False


def click_text(page, text: str, timeout: int = 20000) -> bool:
    try:
        page.get_by_text(text, exact=False).first.click(timeout=timeout)
        return True
    except PlaywrightError:
        return False


def click_control(page, name: str, timeout: int = 20000) -> bool:
    """Bấm một công tắc theo nhãn, chịu được cả ``st.toggle`` và ``st.checkbox``."""
    for locator in (
        page.get_by_role("checkbox", name=name),
        page.get_by_role("switch", name=name),
        page.get_by_text(name, exact=False),
    ):
        try:
            if locator.count() == 0:
                continue
            locator.first.click(timeout=5000)
            return True
        except PlaywrightError:
            continue
    return click_text(page, name, timeout)


def click_tab(page, name: str, timeout: int = 20000) -> bool:
    """Bấm đúng tab trong thanh tab (tránh nhầm với nhãn/nút trùng chữ ở sidebar và trong tab).

    DOM thật của Streamlit 1.65: các tab là ``[role="tab"]`` nằm trong ``[role="tablist"]``
    (mỗi tab là ``div[data-testid="stTab"]``), KHÔNG phải ``button`` — nếu tìm theo
    ``[data-testid="stTabs"] button`` sẽ bắt nhầm nút bên trong tab (ví dụ nút "Tải dữ liệu đã làm sạch").
    """
    for selector in ('[role="tablist"] [role="tab"]', '[data-testid="stTab"]'):
        locator = page.locator(selector).filter(has_text=name)
        try:
            if locator.count() == 0:
                continue
            locator.first.click(timeout=timeout)
            return True
        except PlaywrightError:
            continue
    return click_text(page, name, timeout)


def screenshot(page, name: str, focus_text: str | None = None) -> None:
    """Chụp ảnh màn hình; nếu có ``focus_text`` thì cuộn tới phần cần thấy trước."""
    if focus_text:
        try:
            page.get_by_text(focus_text, exact=False).first.scroll_into_view_if_needed(timeout=8000)
            page.wait_for_timeout(500)
        except PlaywrightError:
            pass
    SHOT_DIR.mkdir(exist_ok=True)
    page.screenshot(path=str(SHOT_DIR / f"{name}.png"), full_page=True)


def layout_report(page) -> tuple[bool, str]:
    """Kiểm tra bố cục: không tràn ngang và ô số liệu không bị cắt chữ."""
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    clipped = page.evaluate(
        """() => Array.from(document.querySelectorAll('[data-testid="stMetricValue"]'))
            .filter(node => node.scrollWidth > node.clientWidth + 2)
            .map(node => node.textContent.trim())"""
    )
    detail = f"tràn ngang {overflow}px"
    if clipped:
        detail += f", {len(clipped)} ô số liệu bị cắt: {clipped[:3]}"
    return overflow <= 4 and not clipped, detail


def main() -> int:
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
            check("Server sẵn sàng cho trình duyệt", False, f"cổng {port}")
            return 1
        check("Server sẵn sàng cho trình duyệt", True, f"cổng {port}")

        with sync_playwright() as playwright:
            browser, channel = launch_browser(playwright)
            check("Mở được trình duyệt thật", True, channel)
            page = browser.new_page(viewport=VIEWPORT)
            page.goto(base, wait_until="domcontentloaded", timeout=60000)

            check(
                "Trang hiển thị đúng tiêu đề đề tài",
                wait_text(page, "HỆ THỐNG GIÁM SÁT VÀ DỰ ĐOÁN PHỤ TẢI ĐIỆN"),
            )
            check("Sidebar điều khiển demo hiển thị", wait_text(page, "Điều khiển demo"))
            check(
                "Sidebar chia nhóm Dữ liệu / Mô hình / Mô phỏng Blockchain",
                wait_text(page, "Mô phỏng Blockchain", timeout=15000)
                and wait_text(page, "Dữ liệu", timeout=15000)
                and wait_text(page, "Mô hình", timeout=15000),
            )

            tabs = ["Tổng quan & ML", "Blockchain / Hash", "Đồng thuận PoW", "Dữ liệu", "Hướng dẫn demo"]
            found = sum(1 for tab in tabs if wait_text(page, tab, timeout=15000))
            check("Đủ 5 tab điều hướng", found == 5, f"thấy {found}/5 tab")

            # --- Tab 1: ML -------------------------------------------------- #
            check("Tab Tổng quan hiện chỉ số MAE của mô hình", wait_text(page, "MAE (kWh)"))
            check(
                "Tab Tổng quan có bảng so sánh RandomForest với baseline",
                wait_text(page, "So sánh mô hình trên cùng tập kiểm tra"),
            )
            page.wait_for_timeout(1500)
            ok, detail = layout_report(page)
            check("Tab Tổng quan không tràn ngang, không cắt chữ số liệu", ok, detail)
            screenshot(page, "01-tong-quan-ml")

            # --- Tab 2: chuỗi hash ------------------------------------------ #
            click_tab(page, "Blockchain / Hash")
            check("Tab Hash báo dữ liệu hợp lệ", wait_text(page, "Dữ liệu hợp lệ"))
            check("Tab Hash có thẻ block kèm hash", wait_text(page, "Block #0"))
            check("Tab Hash hiện trạng thái Hợp lệ", wait_text(page, "Hợp lệ"))
            ok, detail = layout_report(page)
            check("Tab Hash không tràn ngang, không cắt chữ số liệu", ok, detail)
            screenshot(page, "02-blockchain-hop-le")

            # --- Tab 3: đồng thuận PoW -------------------------------------- #
            click_tab(page, "Đồng thuận PoW")
            check("Tab PoW hiện bảng block và tổng nonce", wait_text(page, "Tổng nonce"))
            screenshot(page, "03-dong-thuan-pow")

            # --- Kịch bản sửa dữ liệu --------------------------------------- #
            if click_control(page, "Mô phỏng dữ liệu bị sửa"):
                # Tab đang mở là "Đồng thuận PoW": khi bật sửa dữ liệu, chuỗi PoW cũng phải báo không hợp lệ.
                pow_alert = wait_text(page, "KHÔNG hợp lệ", timeout=60000)
                click_tab(page, "Blockchain / Hash")
                hash_alert = wait_text(page, "Phát hiện dữ liệu bị thay đổi", timeout=30000)
                check(
                    "Bật mô phỏng sửa dữ liệu → tab Hash báo bị sửa và tab PoW báo không hợp lệ",
                    pow_alert and hash_alert,
                    f"PoW: {pow_alert}, Hash: {hash_alert}",
                )
                screenshot(page, "04-phat-hien-sua-du-lieu")
                click_control(page, "Mô phỏng dữ liệu bị sửa")  # tắt lại
                page.wait_for_timeout(1200)
                check(
                    "Tắt mô phỏng sửa dữ liệu → chuỗi quay lại hợp lệ",
                    wait_text(page, "Dữ liệu hợp lệ", timeout=30000),
                )
                click_tab(page, "Đồng thuận PoW")
            else:
                check("Bật mô phỏng sửa dữ liệu → tab Hash báo bị sửa", False, "không bấm được công tắc")

            # --- Kịch bản kẻ tấn công đào lại ------------------------------- #
            if click_control(page, "Mô phỏng kẻ tấn công đào lại"):
                honest = wait_text(page, "giữ chuỗi của nút trung thực", timeout=60000)
                check("Kẻ tấn công bằng độ dài → đồng thuận giữ nút trung thực", honest)
                screenshot(page, "05-dong-thuan-giu-trung-thuc", "Chuỗi trung thực")

                # Tăng "Số khối đào vượt thêm" bằng phím mũi tên phải.
                slider = page.get_by_role("slider").last
                try:
                    slider.focus()
                    for _ in range(2):
                        page.keyboard.press("ArrowRight")
                        page.wait_for_timeout(800)
                    attacker = wait_text(page, "nút tấn công thắng", timeout=60000)
                    check("Tăng số khối đào vượt → mô phỏng tấn công 51%", attacker)
                    ok, detail = layout_report(page)
                    check("Tab PoW (kịch bản 51%) không tràn ngang", ok, detail)
                    screenshot(page, "06-tan-cong-51", "nút tấn công thắng")
                except PlaywrightError as exc:
                    check("Tăng số khối đào vượt → mô phỏng tấn công 51%", False, str(exc)[:80])
            else:
                check("Kẻ tấn công bằng độ dài → đồng thuận giữ nút trung thực", False, "không bấm được công tắc")

            # --- Tab dữ liệu + hướng dẫn ------------------------------------ #
            if click_tab(page, "Dữ liệu"):
                check("Tab Dữ liệu hiện bảng dữ liệu đầu vào", wait_text(page, "Bảng dữ liệu đầu vào"))
                screenshot(page, "07-du-lieu")
            else:
                check("Tab Dữ liệu hiện bảng dữ liệu đầu vào", False, "không bấm được tab")

            if click_tab(page, "Hướng dẫn demo"):
                check("Tab Hướng dẫn hiện kịch bản thuyết trình", wait_text(page, "Kịch bản thuyết trình"))
                screenshot(page, "08-huong-dan-demo")
            else:
                check("Tab Hướng dẫn hiện kịch bản thuyết trình", False, "không bấm được tab")

            body = page.inner_text("body")
            check(
                "Không lộ traceback / đường dẫn file ra trình duyệt",
                "Traceback" not in body and "C:\\Users" not in body,
            )
            check(
                "Không còn giao diện cũ (hero tiếng Anh, pill trang trí)",
                "Smart Grid Monitor" not in body
                and "operations lab" not in body
                and "ML forecasting" not in body,
            )
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()

    failed = [name for name, passed, _ in RESULTS if not passed]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} kiểm tra trình duyệt đạt.", flush=True)
    if SHOT_DIR.exists():
        print(f"Ảnh chụp: {SHOT_DIR} ({len(list(SHOT_DIR.glob('*.png')))} file)", flush=True)
    if failed:
        print("Chưa đạt:\n - " + "\n - ".join(failed), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
