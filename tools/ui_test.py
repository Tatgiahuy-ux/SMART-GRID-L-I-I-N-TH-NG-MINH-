"""Kiểm thử giao diện Streamlit bằng ``streamlit.testing.v1.AppTest`` (headless).

Chạy:

    .\\.venv\\Scripts\\python.exe tools\\ui_test.py

Script chạy thật ``app.py`` trong bộ kiểm thử của Streamlit, kiểm tra không có ngoại lệ
và các kịch bản chính hiển thị đúng thông báo: hợp lệ, bị sửa, đồng thuận giữ nút trung
thực và mô phỏng tấn công 51%.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from streamlit.testing.v1 import AppTest  # noqa: E402

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import DATASETS  # noqa: E402  (import an toàn: main() được bảo vệ bởi __main__)

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((name, passed, detail))
    # flush=True để không mất log nếu tiến trình gặp sự cố lúc thoát
    print(f"[{'OK  ' if passed else 'FAIL'}] {name}{' – ' + detail if detail else ''}", flush=True)


def messages(app: AppTest) -> str:
    """Gom toàn bộ văn bản đang hiển thị để so khớp nội dung."""
    parts: list[str] = []
    for attribute in ("success", "error", "warning", "info", "caption", "markdown"):
        for element in getattr(app, attribute, []) or []:
            value = getattr(element, "value", None)
            if isinstance(value, str):
                parts.append(value)
    return " || ".join(parts)


def run_app() -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=300)
    app.run()
    return app


def main() -> int:
    app = run_app()
    check("Ứng dụng khởi động không có ngoại lệ", not app.exception, str(app.exception))
    check("Có 5 tab điều hướng", len(app.tabs) == 5, f"{len(app.tabs)} tab")
    text = messages(app)
    check("Tab Hash báo chuỗi hợp lệ", "Chuỗi hash hợp lệ" in text)
    check("Tab PoW báo chuỗi hợp lệ", "Chuỗi hợp lệ" in text)

    # Kịch bản 1: bật mô phỏng sửa dữ liệu ở tab hash.
    app = run_app()
    app.toggle(key="tamper_demo").set_value(True).run()
    check("Bật sửa dữ liệu → báo không hợp lệ", not app.exception and "KHÔNG hợp lệ" in messages(app))

    # Kịch bản 2: kẻ tấn công đào lại nhưng chưa vượt tổng công.
    app = run_app()
    app.checkbox(key="attacker_demo").set_value(True).run()
    check(
        "Tấn công bằng độ dài → đồng thuận giữ nút trung thực",
        not app.exception and "giữ chuỗi của nút trung thực" in messages(app),
    )

    # Kịch bản 3: kẻ tấn công đào vượt thêm 2 khối (tấn công 51%).
    app.checkbox(key="attacker_demo").set_value(True).run()
    app.slider(key="extra_blocks").set_value(2).run()
    check(
        "Đào vượt thêm 2 khối → mô phỏng tấn công 51%",
        not app.exception and "nút tấn công thắng" in messages(app),
    )

    # Kịch bản 4: đổi sang baseline tuyến tính.
    app = run_app()
    app.selectbox(key="model_choice").set_value("linear").run()
    check(
        "Chuyển sang baseline tuyến tính không lỗi",
        not app.exception and "Baseline" in messages(app),
    )

    # Kịch bản 5: bộ dữ liệu nhỏ 8 giờ (dữ liệu ít hơn số block muốn đào).
    app = run_app()
    small_dataset = [key for key in DATASETS if "sample_energy" in key]
    app.selectbox(key="dataset").set_value(small_dataset[0]).run()
    check(
        "Bộ dữ liệu 8 giờ vẫn chạy và đào khối được",
        not app.exception and "Chuỗi hợp lệ" in messages(app),
        str(app.exception),
    )

    failed = [name for name, passed, _ in RESULTS if not passed]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} kiểm tra giao diện đạt.")
    if failed:
        print("Chưa đạt: " + "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
