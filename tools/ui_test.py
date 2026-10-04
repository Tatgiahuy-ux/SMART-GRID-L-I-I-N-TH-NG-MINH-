"""Kiểm thử giao diện Streamlit bằng ``streamlit.testing.v1.AppTest`` (headless).

Chạy:

    .\\.venv\\Scripts\\python.exe tools\\ui_test.py

Script chạy thật ``app.py`` trong bộ kiểm thử của Streamlit và kiểm tra đúng những gì
người thuyết trình sẽ bấm:

1. Ứng dụng khởi động không lỗi, đủ 5 tab.
2. KPI trên tab Tổng quan khớp ``ml/metrics.json``; có bảng so sánh với baseline.
3. Tab Hash: chuỗi hợp lệ, thẻ block hiện dữ liệu/hash/previous_hash.
4. Bật "Mô phỏng dữ liệu bị sửa" → báo bị sửa; tắt đi → quay lại hợp lệ.
5. Tab PoW: hiện số block, tổng nonce, thời gian đào, tốc độ băm.
6. Đồng thuận: đào vượt 0 khối → nút trung thực thắng; vượt 2 khối → nút tấn công thắng.
7. Đổi mô hình sang baseline và đổi số giờ dự đoán → giao diện cập nhật, không lỗi.
8. Bộ dữ liệu 8 giờ vẫn chạy và đào được block.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ensure_writable_temp() -> None:
    """Dùng thư mục tạm trong project cho AppTest (thay vì %TEMP% của Windows).

    Trên máy bị hạn chế quyền (hoặc môi trường sandbox), ``%TEMP%`` có thể cho Python tạo
    file nhưng chặn xoá thư mục tạm, khiến tiến trình trả mã lỗi lúc thoát dù kiểm thử đã
    đạt. Đặt TEMP/TMP trước khi import Streamlit để mọi file tạm nằm trong ``.pw-tmp``
    (đã bị .gitignore).
    """
    local_temp = ROOT / ".pw-tmp"
    local_temp.mkdir(exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = os.environ["TMPDIR"] = str(local_temp)
    tempfile.tempdir = str(local_temp)
    print(f"       Thư mục tạm hệ thống không dùng được → dùng {local_temp}", flush=True)


ensure_writable_temp()

from streamlit.testing.v1 import AppTest  # noqa: E402

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import DATASETS  # noqa: E402  (import an toàn: main() được bảo vệ bởi __main__)
from ml.predictor import load_saved_metrics  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((name, passed, detail))
    # flush=True để không mất log nếu tiến trình gặp sự cố lúc thoát
    print(f"[{'OK  ' if passed else 'FAIL'}] {name}{' – ' + detail if detail else ''}", flush=True)


def messages(app: AppTest) -> str:
    """Gom toàn bộ văn bản đang hiển thị để so khớp nội dung."""
    parts: list[str] = []
    for attribute in (
        "title",
        "header",
        "subheader",
        "success",
        "error",
        "warning",
        "info",
        "caption",
        "markdown",
        "code",
        "text",
    ):
        for element in getattr(app, attribute, []) or []:
            value = getattr(element, "value", None)
            if isinstance(value, str):
                parts.append(value)
    return " || ".join(parts)


def metrics(app: AppTest) -> dict[str, str]:
    return {element.label: element.value for element in app.metric}


def metric_pairs(app: AppTest) -> list[tuple[str, str]]:
    """Danh sách (nhãn, giá trị) — giữ cả nhãn trùng nhau giữa các tab."""
    return [(element.label, element.value) for element in app.metric]


def first_metric(app: AppTest, label: str) -> str | None:
    return next((value for name, value in metric_pairs(app) if name == label), None)


def all_metric_values(app: AppTest, label: str) -> list[str]:
    return [value for name, value in metric_pairs(app) if name == label]


def run_app() -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=300)
    app.run()
    return app


def forecast_table(app: AppTest):
    """Bảng dự báo trên tab Tổng quan (nhận diện qua tên cột)."""
    for element in app.dataframe:
        frame = element.value
        if frame is not None and "dự đoán (kWh)" in getattr(frame, "columns", []):
            return frame
    return None


def comparison_table(app: AppTest):
    """Bảng so sánh RandomForest với baseline."""
    for element in app.dataframe:
        frame = element.value
        if frame is not None and "Mô hình" in getattr(frame, "columns", []):
            return frame
    return None


def main() -> int:
    saved = load_saved_metrics() or {}

    app = run_app()
    check("Ứng dụng khởi động không có ngoại lệ", not app.exception, str(app.exception))
    check("Có 5 tab điều hướng", len(app.tabs) == 5, f"{len(app.tabs)} tab")
    text = messages(app)
    check("Tiêu đề trang đúng đề tài", "GIÁM SÁT VÀ DỰ ĐOÁN PHỤ TẢI ĐIỆN" in text)
    check(
        "KPI chất lượng mô hình hiện đúng số của ml/metrics.json",
        metrics(app).get("MAE (kWh)") == f"{saved.get('mae'):.2f}"
        and metrics(app).get("RMSE (kWh)") == f"{saved.get('rmse'):.2f}"
        and metrics(app).get("R²") == f"{saved.get('r2'):.4f}"
        and metrics(app).get("Bản ghi kiểm tra") == f"{saved.get('n_test'):,}",
        f"MAE {metrics(app).get('MAE (kWh)')} · RMSE {metrics(app).get('RMSE (kWh)')} · "
        f"R² {metrics(app).get('R²')}",
    )
    check(
        "Có bảng so sánh RandomForest với baseline trên cùng tập kiểm tra",
        (comparison := comparison_table(app)) is not None
        and len(comparison) == 2
        and saved.get("baseline_linear_mae") in set(comparison["MAE (kWh)"]),
        "bảng 2 dòng" if comparison is not None else "không tìm thấy bảng",
    )
    check("Tab Hash báo dữ liệu hợp lệ", "Dữ liệu hợp lệ" in text)
    check("Tab PoW báo chuỗi hợp lệ", "Chuỗi hợp lệ" in text)
    hash_codes = [element.value for element in app.code]
    check(
        "Tab Hash có thẻ block kèm hash và previous_hash",
        "**Block #0**" in text
        and len(hash_codes) >= 4
        and all(isinstance(value, str) and len(value) == 64 for value in hash_codes[:4]),
        f"{len(hash_codes)} khối mã hash, mỗi hash 64 ký tự hex",
    )
    check(
        "Tab PoW hiện đủ 5 thông số đào",
        all(
            label in metrics(app)
            for label in ("Số block", "Độ khó", "Tổng nonce", "Thời gian đào", "Tốc độ băm")
        )
        and "phép băm cho" in text,
        f"nonce {metrics(app).get('Tổng nonce')}, tốc độ {metrics(app).get('Tốc độ băm')}",
    )

    # --- Số block hiển thị ở tab Hash (segmented control) -------------------- #
    app = run_app()
    app.segmented_control(key="hash_block_view").set_value(2).run()
    check(
        "Đổi 'Số block hiển thị' → số thẻ block đổi theo",
        not app.exception and messages(app).count("**Block #") == 2,
        f"{messages(app).count('**Block #')} thẻ",
    )

    # --- Kịch bản 1: bật/tắt mô phỏng sửa dữ liệu ---------------------------- #
    app = run_app()
    app.toggle(key="tamper_demo").set_value(True).run()
    tampered_text = messages(app)
    check(
        "Bật mô phỏng sửa dữ liệu → báo bị sửa và chỉ đúng Block #0",
        not app.exception
        and "Phát hiện dữ liệu bị thay đổi" in tampered_text
        and metrics(app).get("Trạng thái") == "Bị sửa"
        and "Block #0 có hash không khớp" in tampered_text,
    )
    check(
        "Bật mô phỏng sửa dữ liệu → tab PoW cũng báo KHÔNG hợp lệ",
        "KHÔNG hợp lệ" in tampered_text,
    )
    app.toggle(key="tamper_demo").set_value(False).run()
    check(
        "Tắt mô phỏng sửa dữ liệu → chuỗi quay lại hợp lệ",
        not app.exception
        and "Dữ liệu hợp lệ" in messages(app)
        and metrics(app).get("Trạng thái") == "Hợp lệ",
    )

    # --- Kịch bản 2: kẻ tấn công đào lại, chưa vượt tổng công ---------------- #
    app = run_app()
    app.toggle(key="attacker_demo").set_value(True).run()
    check(
        "Tấn công bằng độ dài (0 khối vượt) → đồng thuận giữ nút trung thực",
        not app.exception and "giữ chuỗi của nút trung thực" in messages(app),
    )
    check(
        "Thẻ so sánh hiện số block và tổng công của cả hai chuỗi",
        len(all_metric_values(app, "Tổng công")) == 2
        and "Chuỗi tấn công (đã đào lại)" in messages(app),
        f"tổng công hai chuỗi: {all_metric_values(app, 'Tổng công')}",
    )

    # --- Kịch bản 3: kẻ tấn công đào vượt thêm 2 khối (tấn công 51%) --------- #
    app.slider(key="extra_blocks").set_value(2).run()
    attacker_text = messages(app)
    check(
        "Đào vượt thêm 2 khối → nút tấn công thắng (mô phỏng 51%)",
        not app.exception and "nút tấn công thắng" in attacker_text,
        str(app.exception),
    )
    check(
        "Kết luận nêu rõ tổng công của hai chuỗi để giải thích lý do chọn",
        "lớn hơn" in attacker_text and "của chuỗi trung thực" in attacker_text,
        next(
            (
                line
                for line in attacker_text.split(" || ")
                if "nút tấn công thắng" in line
            ),
            "",
        )[:120],
    )

    # --- Kịch bản 4: đổi mô hình sang baseline ------------------------------ #
    app = run_app()
    app.selectbox(key="model_choice").set_value("linear").run()
    baseline_text = messages(app)
    check(
        "Chuyển sang baseline tuyến tính không lỗi và có chỉ số riêng",
        not app.exception
        and "Baseline" in baseline_text
        and "toàn bộ" in baseline_text
        and "không phải tập kiểm tra 20%" in baseline_text
        and metrics(app).get("RMSE (kWh)") == "—"
        and metrics(app).get("MAE (kWh)") not in (None, "—"),
        f"MAE baseline {metrics(app).get('MAE (kWh)')}",
    )

    # --- Kịch bản 5: đổi số giờ dự đoán ------------------------------------- #
    app = run_app()
    app.slider(key="horizon").set_value(3).run()
    table = forecast_table(app)
    check(
        "Đổi số giờ dự đoán → bảng và biểu đồ dự báo cập nhật đúng số dòng",
        not app.exception and table is not None and len(table) == 3,
        f"{0 if table is None else len(table)} dòng",
    )

    # --- Kịch bản 6: bộ dữ liệu nhỏ 8 giờ ----------------------------------- #
    app = run_app()
    small_dataset = [key for key in DATASETS if "sample_energy" in key]
    app.selectbox(key="dataset").set_value(small_dataset[0]).run()
    block_counts = all_metric_values(app, "Số block")
    check(
        "Bộ dữ liệu 8 giờ vẫn chạy, đào khối và báo hợp lệ",
        not app.exception
        and "Dữ liệu hợp lệ" in messages(app)
        and "8" in block_counts  # chuỗi hash: 8 bản ghi = 8 block
        and "7" in block_counts,  # chuỗi PoW: genesis + 6 bản ghi cuối
        f"số block hiển thị: {block_counts}",
    )
    check(
        "Bộ dữ liệu 8 giờ không hiển thị metrics mặc định của 720 giờ",
        not app.exception
        and metrics(app).get("MAE (kWh)") == "—"
        and metrics(app).get("RMSE (kWh)") == "—"
        and metrics(app).get("R²") == "—"
        and comparison_table(app) is None
        and "không dùng metrics mặc định" in messages(app),
    )

    failed = [name for name, passed, _ in RESULTS if not passed]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} kiểm tra giao diện đạt.", flush=True)
    if failed:
        print("Chưa đạt:\n - " + "\n - ".join(failed), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
