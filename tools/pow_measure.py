"""Đo bảng thông số Proof of Work cho báo cáo/slide Smart Grid (Nhóm 17).

Chạy:

    .\\.venv\\Scripts\\python.exe tools\\pow_measure.py
    .\\.venv\\Scripts\\python.exe tools\\pow_measure.py --blocks 6 --difficulties 1 2 3 4

Script đào thật ``--blocks`` bản ghi cuối của ``data/power_consumption.csv`` (kèm số dự đoán của
RandomForest) ở từng độ khó rồi in bảng: tổng nonce, tổng số phép băm, thời gian đào, tốc độ băm.

Lưu ý khi trích vào báo cáo:
- Số nonce **không đoán trước được**, nhưng tái lập được: cùng payload + cùng độ khó ⇒ cùng nonce.
  Đổi cấu trúc payload (thêm/bớt trường) là nonce đổi hết.
- Thời gian đào và tốc độ băm **phụ thuộc máy**, nên chỉ nên nêu khoảng.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):  # console Windows mặc định cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from blockchain.consensus import ProofOfWorkChain  # noqa: E402
from ml.predictor import predict_consumption  # noqa: E402
from security import prepare_data  # noqa: E402

DATA_PATH = ROOT / "data" / "power_consumption.csv"


def build_records(count: int) -> list[dict[str, object]]:
    """Lấy ``count`` bản ghi cuối của dữ liệu thật + số dự đoán của mô hình ML."""
    data = prepare_data(pd.read_csv(DATA_PATH, parse_dates=["timestamp"]))
    forecast = predict_consumption(data, horizon=count, model="random_forest")
    fitted = forecast.fitted or []
    predicted = (
        fitted[-count:]
        if len(fitted) >= count
        else [forecast.predictions[0]] * count
    )
    return [
        {
            "consumer_id": "METER_001",
            "recorded_time": row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "actual_usage_kwh": round(float(row.consumption_kwh), 4),
            "predicted_usage_kwh": round(float(value), 4),
        }
        for row, value in zip(data.tail(count).itertuples(index=False), predicted)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Đo bảng Proof of Work cho báo cáo.")
    parser.add_argument("--blocks", type=int, default=6, help="số bản ghi đào (mặc định 6)")
    parser.add_argument(
        "--difficulties",
        type=int,
        nargs="+",
        default=[1, 2, 3, 4],
        help="các mức độ khó cần đo (mặc định 1 2 3 4)",
    )
    args = parser.parse_args()

    records = build_records(args.blocks)
    print(f"Dữ liệu: {DATA_PATH.name} · {args.blocks} bản ghi · nguồn {records[0]['recorded_time']} "
          f"→ {records[-1]['recorded_time']}")
    print(f"Chuỗi: genesis + {args.blocks} bản ghi = {args.blocks + 1} block\n")
    print("| Độ khó | Tổng nonce | Tổng phép băm | Thời gian đào | Tốc độ băm | Hợp lệ |")
    print("|---|---|---|---|---|---|")

    failed = 0
    for difficulty in args.difficulties:
        chain = ProofOfWorkChain(difficulty=difficulty)
        chain.add_energy_records(records)
        summary = chain.summary()
        if not summary["valid"]:
            failed += 1
        print(
            f"| {difficulty} | {summary['total_nonce']:,} | {summary['total_attempts']:,} | "
            f"{summary['total_mine_seconds']:.3f} s | ~{summary['hash_rate']:,.0f} H/s | "
            f"{'✔' if summary['valid'] else '✘'} |"
        )

    print(
        "\nGhi chú: nonce tái lập được nhưng không đoán trước được; thời gian đào và tốc độ băm "
        "phụ thuộc máy đang chạy."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
