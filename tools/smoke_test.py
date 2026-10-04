"""Kiểm thử nhanh toàn bộ luồng demo Smart Grid (không cần Streamlit).

Chạy:

    .\\.venv\\Scripts\\python.exe tools\\smoke_test.py

Script kiểm tra: dự đoán ML (RandomForest nếu có, baseline nếu không), chuỗi hash
toàn vẹn, đào khối Proof of Work, phát hiện sửa đổi và luật đồng thuận chuỗi nặng nhất.
"""

from __future__ import annotations

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

DATA_PATH = ROOT / "data" / "power_consumption.csv"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((name, passed, detail))
    print(f"[{'OK  ' if passed else 'FAIL'}] {name}{' – ' + detail if detail else ''}")


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

    failed = [name for name, passed, _ in RESULTS if not passed]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} kiểm tra đạt.")
    if failed:
        print("Chưa đạt: " + "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
