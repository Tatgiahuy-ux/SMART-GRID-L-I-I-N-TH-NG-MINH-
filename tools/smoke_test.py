"""Kiểm thử nhanh toàn bộ luồng demo Smart Grid (không cần Streamlit).

Chạy:

    .\\.venv\\Scripts\\python.exe tools\\smoke_test.py

Script kiểm tra: dự đoán ML (RandomForest nếu có, baseline nếu không), chuỗi hash
toàn vẹn, đào khối Proof of Work, phát hiện sửa đổi và luật đồng thuận chuỗi nặng nhất.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):  # console Windows mặc định cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from blockchain.chain import IntegrityChain  # noqa: E402
from blockchain.consensus import ProofOfWorkChain  # noqa: E402
from ml.generate_data import build_dataset  # noqa: E402
from ml.predictor import predict_consumption  # noqa: E402
from security import (  # noqa: E402
    MAX_UPLOAD_BYTES,
    UserInputError,
    prepare_data,
    safe_error,
    validate_upload,
)

DATA_PATH = ROOT / "data" / "power_consumption.csv"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((name, passed, detail))
    # flush=True để không mất log nếu tiến trình gặp sự cố lúc thoát
    print(f"[{'OK  ' if passed else 'FAIL'}] {name}{' – ' + detail if detail else ''}", flush=True)


def main() -> int:
    data = pd.read_csv(DATA_PATH, parse_dates=["timestamp"]).sort_values("timestamp")
    data = data.reset_index(drop=True)

    # 1. ML ------------------------------------------------------------------ #
    regenerated = build_dataset()
    same_length = len(regenerated) == len(data)
    same_time = same_length and bool(
        (pd.to_datetime(regenerated["timestamp"]).to_numpy()
         == pd.to_datetime(data["timestamp"]).to_numpy()).all()
    )
    close_values = same_length and bool(
        (abs(regenerated["consumption_kwh"].to_numpy() - data["consumption_kwh"].to_numpy()) < 1e-9).all()
    )
    check(
        "ml/generate_data.py tái lập đúng data/power_consumption.csv",
        same_length and same_time and close_values,
        f"{len(regenerated)} dòng",
    )

    forecast = predict_consumption(data, horizon=6)
    check(
        "Dự đoán ML trả về đủ số giờ yêu cầu",
        len(forecast.predictions) == 6 and all(value >= 0 for value in forecast.predictions),
        f"{forecast.model_name} → {[round(value, 2) for value in forecast.predictions]}",
    )
    check(
        "Chuỗi khớp của mô hình cùng độ dài dữ liệu đầu vào",
        forecast.fitted is not None and len(forecast.fitted) == len(data),
    )
    if forecast.fallback_reason:
        print(f"       (RandomForest không khả dụng: {forecast.fallback_reason})")

    # 2. Chuỗi hash toàn vẹn ------------------------------------------------- #
    chain = IntegrityChain()
    for row in data.head(50).itertuples(index=False):
        chain.add_record(
            {
                "timestamp": row.timestamp.isoformat(),
                "consumption_kwh": round(float(row.consumption_kwh), 4),
            }
        )
    check("Chuỗi hash hợp lệ trước khi sửa", chain.is_valid(), f"{len(chain.blocks)} block")
    chain.tamper_block(0, "consumption_kwh", 9999.0)
    check("Chuỗi hash phát hiện dữ liệu bị sửa", not chain.is_valid())

    # 3. Proof of Work ------------------------------------------------------- #
    records = [
        {
            "consumer_id": "METER_001",
            "recorded_time": row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "actual_usage_kwh": round(float(row.consumption_kwh), 4),
            "predicted_usage_kwh": round(float(fitted), 4),
        }
        for row, fitted in zip(data.tail(4).itertuples(index=False), forecast.fitted[-4:])
    ]

    pow_chain = ProofOfWorkChain(difficulty=2)
    pow_chain.add_energy_records(records)
    summary = pow_chain.summary()
    check(
        "Đào khối PoW: chuỗi hợp lệ và hash đạt độ khó",
        summary["valid"] and all(block.hash.startswith("00") for block in pow_chain.blocks),
        f"{summary['blocks']} block, nonce={summary['total_nonce']}, {summary['total_mine_seconds']}s",
    )

    tampered = pow_chain.clone()
    tampered.tamper_block(1, "actual_usage_kwh", 10.0)
    check("Sửa payload không đào lại → chuỗi không hợp lệ", not tampered.is_valid())

    attacker_same_length = pow_chain.tamper_and_remine(1, "actual_usage_kwh", 10.0, extra_blocks=0)
    winner, reason = ProofOfWorkChain.resolve_conflict([pow_chain, attacker_same_length])
    check(
        "Đồng thuận giữ nút trung thực khi tổng công bằng nhau",
        winner is pow_chain and attacker_same_length.is_valid(),
        reason,
    )

    attacker_stronger = pow_chain.tamper_and_remine(1, "actual_usage_kwh", 10.0, extra_blocks=2)
    winner_51, reason_51 = ProofOfWorkChain.resolve_conflict([pow_chain, attacker_stronger])
    check(
        "Mô phỏng tấn công 51%: chuỗi đào thêm thắng theo tổng công",
        winner_51 is attacker_stronger,
        reason_51,
    )

    # 4. Bảo mật đầu vào (mục 6, 7, 8, 9, 16 của checklist) ------------------ #
    validate_upload("dulieu.csv", 1024)

    rejected: list[str] = []
    for name, size in (
        ("virus.exe", 1024),
        ("baocao.pdf", 1024),
        ("dulieu.csv", MAX_UPLOAD_BYTES + 1),
        ("dulieu.csv", 0),
        ("../etc/passwd.csv", 1024),
    ):
        try:
            validate_upload(name, size)
        except UserInputError:
            rejected.append(name)
    check(
        "validate_upload chặn file sai định dạng / quá lớn / tên xấu",
        len(rejected) == 5,
        f"đã chặn {len(rejected)}/5 trường hợp",
    )

    bad_inputs = {
        "thiếu cột": pd.DataFrame({"timestamp": ["2026-01-01 00:00:00"], "kwh": [1.0]}),
        "giá trị âm": pd.DataFrame(
            {"timestamp": ["2026-01-01 00:00:00"], "consumption_kwh": [-5.0]}
        ),
        "giá trị vô lý": pd.DataFrame(
            {"timestamp": ["2026-01-01 00:00:00"], "consumption_kwh": [1e12]}
        ),
        "rỗng sau làm sạch": pd.DataFrame(
            {"timestamp": ["sai-dinh-dang"], "consumption_kwh": ["abc"]}
        ),
    }
    blocked = 0
    for label, frame in bad_inputs.items():
        try:
            prepare_data(frame)
        except UserInputError:
            blocked += 1
    check(
        "prepare_data từ chối dữ liệu sai ở phía server",
        blocked == len(bad_inputs),
        f"đã chặn {blocked}/{len(bad_inputs)} trường hợp",
    )

    logging.disable(logging.CRITICAL)  # tránh in traceback giả trong lúc kiểm thử
    try:
        raise OSError(r"Lỗi hệ thống: C:\Users\huy\server\config.toml không tìm thấy")
    except OSError as exc:
        message = safe_error(exc, "Không thể xử lý dữ liệu đầu vào.")
    finally:
        logging.disable(logging.NOTSET)
    leaked = [token for token in ("C:\\", "server", "config.toml", "Traceback", "OSError") if token in message]
    check(
        "safe_error không lộ đường dẫn / chi tiết kỹ thuật ra giao diện",
        not leaked and "mã lỗi: E-IO-02" in message,
        f"thông báo: {message}",
    )

    config_path = ROOT / ".streamlit" / "config.toml"
    config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    required_settings = (
        "maxUploadSize = 5",
        'showErrorDetails = "none"',
        "enableCORS = true",
        "enableXsrfProtection = true",
    )
    check(
        "config.toml giữ đúng cấu hình bảo mật (upload, ẩn lỗi, CORS/XSRF)",
        all(setting in config_text for setting in required_settings),
        f"{config_path.name} {'có' if config_text else 'KHÔNG TỒN TẠI'}",
    )
    check(
        "Không có file secret nào bị commit",
        not (ROOT / ".streamlit" / "secrets.toml").exists(),
    )

    failed = [name for name, passed, _ in RESULTS if not passed]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} kiểm tra đạt.")
    if failed:
        print("Chưa đạt: " + "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
