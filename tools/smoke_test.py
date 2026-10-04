"""Kiểm thử nhanh toàn bộ luồng demo Smart Grid (không cần Streamlit).

Chạy:

    .\\.venv\\Scripts\\python.exe tools\\smoke_test.py

Script kiểm tra:

1. Dữ liệu sinh lại trùng khớp ``data/power_consumption.csv``.
2. Dự đoán ML (RandomForest nếu có, baseline nếu không) và **chỉ số trong
   ``ml/metrics.json`` được tính lại từ dữ liệu gốc** (không tin số ghi sẵn).
3. Chuỗi hash toàn vẹn: hợp lệ trước khi sửa, phát hiện sửa đổi, chỉ đúng block lỗi.
4. Proof of Work: hash thật sự đạt độ khó, nonce lưu trong block tái tạo được hash,
   thời gian đào / tốc độ băm được đo thật.
5. Luật đồng thuận: hòa tổng công thì giữ nút trung thực; đào vượt thì nút tấn công thắng
   (mô phỏng tấn công 51%), và nhánh tấn công là **đào lại đúng dữ liệu gốc**.
6. Kiểm tra dữ liệu đầu vào và che chi tiết lỗi (các mục bảo mật của checklist).
"""

from __future__ import annotations

import io
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
from blockchain.consensus import (  # noqa: E402
    GENESIS_PREVIOUS_HASH,
    ProofBlock,
    ProofOfWorkChain,
)
from ml.generate_data import build_dataset  # noqa: E402
from ml.predictor import load_saved_metrics, predict_consumption  # noqa: E402
from security import (  # noqa: E402
    MAX_UPLOAD_BYTES,
    UserInputError,
    prepare_data,
    read_uploaded_csv,
    safe_error,
    validate_upload,
)

DATA_PATH = ROOT / "data" / "power_consumption.csv"
METRICS_PATH = ROOT / "ml" / "metrics.json"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((name, passed, detail))
    # flush=True để không mất log nếu tiến trình gặp sự cố lúc thoát
    print(f"[{'OK  ' if passed else 'FAIL'}] {name}{' – ' + detail if detail else ''}", flush=True)


def verify_saved_metrics(data: pd.DataFrame) -> None:
    """Tính lại MAE/RMSE/R² và baseline từ dữ liệu gốc, đối chiếu ``ml/metrics.json``.

    Mục đích: bảo đảm các con số hiển thị trên giao diện là kết quả thật của pipeline,
    không phải số nhập tay.
    """
    saved = load_saved_metrics()
    if not saved:
        check("ml/metrics.json tồn tại để đối chiếu chỉ số", False, "chưa huấn luyện")
        return

    try:
        import numpy as np
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    except ImportError:
        print("       (bỏ qua đối chiếu chỉ số: chưa cài scikit-learn)")
        return

    from ml.train_model import FEATURES, TARGET, add_time_features, baseline_predictions

    frame = add_time_features(data).dropna(subset=["timestamp", TARGET])
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    split = int(len(frame) * (1 - saved["test_ratio"]))
    train_frame, test_frame = frame.iloc[:split], frame.iloc[split:]

    model = RandomForestRegressor(
        n_estimators=saved["n_estimators"], random_state=saved["random_state"]
    )
    model.fit(train_frame[FEATURES], train_frame[TARGET])
    predicted = model.predict(test_frame[FEATURES])
    actual = test_frame[TARGET].to_numpy()

    recomputed = {
        "n_rows": len(frame),
        "n_train": len(train_frame),
        "n_test": len(test_frame),
        "mae": round(float(mean_absolute_error(actual, predicted)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(actual, predicted))), 4),
        "r2": round(float(r2_score(actual, predicted)), 4),
    }
    mismatched = [
        f"{key}: ghi {saved.get(key)} ≠ tính lại {value}"
        for key, value in recomputed.items()
        if saved.get(key) != value
    ]
    check(
        "ml/metrics.json khớp kết quả huấn luyện lại từ dữ liệu gốc",
        not mismatched,
        "; ".join(mismatched)
        or f"MAE {recomputed['mae']} · RMSE {recomputed['rmse']} · R² {recomputed['r2']}",
    )

    baseline = baseline_predictions([float(value) for value in frame[TARGET]], split)
    baseline_predicted = np.array(baseline)
    baseline_actual = actual[: len(baseline)]
    baseline_recomputed = {
        "baseline_linear_mae": round(float(mean_absolute_error(baseline_actual, baseline_predicted)), 4),
        "baseline_linear_rmse": round(
            float(np.sqrt(mean_squared_error(baseline_actual, baseline_predicted))), 4
        ),
        "baseline_linear_r2": round(float(r2_score(baseline_actual, baseline_predicted)), 4),
    }
    baseline_mismatched = [
        f"{key}: ghi {saved.get(key)} ≠ tính lại {value}"
        for key, value in baseline_recomputed.items()
        if saved.get(key) != value
    ]
    check(
        "Chỉ số baseline trong metrics.json khớp tính lại (cùng tập kiểm tra)",
        not baseline_mismatched,
        "; ".join(baseline_mismatched)
        or f"MAE {baseline_recomputed['baseline_linear_mae']} · "
        f"RMSE {baseline_recomputed['baseline_linear_rmse']} · "
        f"R² {baseline_recomputed['baseline_linear_r2']}",
    )
    check(
        "RandomForest tốt hơn baseline rõ rệt trên cùng tập kiểm tra",
        saved["mae"] < saved["baseline_linear_mae"] and saved["r2"] > saved["baseline_linear_r2"],
        f"MAE {saved['mae']} < {saved['baseline_linear_mae']} · "
        f"R² {saved['r2']} > {saved['baseline_linear_r2']}",
    )

    # Chỉ số mà giao diện hiển thị phải đúng bằng kết quả pipeline trả về.
    try:
        forecast_rf = predict_consumption(data, horizon=6, model="random_forest")
    except (RuntimeError, ValueError) as exc:  # thiếu model.pkl hoặc thiếu sklearn
        forecast_rf = None
        print(f"       (bỏ qua đối chiếu chỉ số RandomForest: {exc})")
    if forecast_rf is not None:
        check(
            "Chỉ số app.py hiển thị lấy đúng từ model + ml/metrics.json",
            forecast_rf.mae == saved["mae"]
            and forecast_rf.rmse == saved["rmse"]
            and forecast_rf.r2 == saved["r2"],
            f"predict_consumption → MAE {forecast_rf.mae} / "
            f"RMSE {forecast_rf.rmse} / R² {forecast_rf.r2}",
        )


def verify_proof_of_work() -> None:
    """Kiểm tra nonce/độ khó là thật: hash đạt độ khó và nonce tái tạo được hash."""
    for difficulty in (1, 2, 3):
        chain = ProofOfWorkChain(difficulty=difficulty)
        chain.add_energy_record("METER_001", "2026-01-01 00:00:00", 2.5, 2.4)
        block = chain.blocks[-1]
        expected = ProofOfWorkChain.calculate_hash(
            block.index, block.timestamp, block.payload, block.previous_hash, block.nonce
        )
        hashes_meet_difficulty = all(
            item.hash.startswith("0" * difficulty) for item in chain.blocks
        )
        nonce_is_real = block.hash == expected
        one_less_fails = not ProofOfWorkChain.calculate_hash(
            block.index, block.timestamp, block.payload, block.previous_hash, max(block.nonce - 1, 0)
        ).startswith("0" * difficulty) or block.nonce == 0
        check(
            f"Độ khó {difficulty}: hash đạt độ khó, nonce tái tạo đúng hash, nonce nhỏ hơn thì trượt",
            hashes_meet_difficulty and nonce_is_real and one_less_fails,
            f"nonce={block.nonce}, hash={block.hash[:12]}…",
        )

    chain = ProofOfWorkChain(difficulty=2)
    chain.add_energy_records(
        [
            {
                "consumer_id": "METER_001",
                "recorded_time": f"2026-01-01 0{hour}:00:00",
                "actual_usage_kwh": 2.0 + hour,
                "predicted_usage_kwh": 2.1 + hour,
            }
            for hour in range(4)
        ]
    )
    summary = chain.summary()
    attempts_match = summary["total_attempts"] == chain.total_nonce + len(chain.blocks)
    rate_match = abs(summary["hash_rate"] - chain.hash_rate) < 0.05
    measured = summary["total_mine_seconds"] > 0 and summary["hash_rate"] > 0
    check(
        "Tổng số lần băm / tốc độ băm / thời gian đào được đo thật",
        attempts_match and rate_match and measured,
        f"{summary['total_attempts']} phép băm, {summary['total_mine_seconds']:.4f}s, "
        f"{summary['hash_rate']:.0f} H/s",
    )
    previous_hash_ok = all(
        chain.blocks[index].previous_hash == chain.blocks[index - 1].hash
        for index in range(1, len(chain.blocks))
    )
    check("Mỗi block lưu đúng previous_hash của block trước", previous_hash_ok)

    weak_chain = ProofOfWorkChain(difficulty=2, with_genesis=False)
    nonce = 0
    while True:
        digest = weak_chain.calculate_hash(
            0, 0.0, {"test": "không đạt PoW"}, GENESIS_PREVIOUS_HASH, nonce
        )
        if not digest.startswith("00"):
            break
        nonce += 1
    weak_chain.blocks.append(
        ProofBlock(
            index=0,
            timestamp=0.0,
            payload={"test": "không đạt PoW"},
            previous_hash=GENESIS_PREVIOUS_HASH,
            nonce=nonce,
            difficulty=2,
            hash=digest,
            mine_seconds=0.0,
        )
    )
    check(
        "Validation từ chối hash tái tạo được nhưng không đạt tiền tố difficulty",
        not weak_chain.is_valid() and "không đạt độ khó" in (weak_chain.validation_error() or ""),
        f"hash={digest[:12]}…",
    )


def verify_consensus_51() -> None:
    """Hai kịch bản bắt buộc: đào vượt 0 khối → trung thực thắng; vượt 2 khối → tấn công thắng."""
    chain = ProofOfWorkChain(difficulty=2)
    chain.add_energy_records(
        [
            {
                "consumer_id": "METER_001",
                "recorded_time": f"2026-01-01 0{hour}:00:00",
                "actual_usage_kwh": 2.0 + hour,
                "predicted_usage_kwh": 2.1 + hour,
            }
            for hour in range(4)
        ]
    )
    forged = 10.0

    tied = chain.tamper_and_remine(1, "actual_usage_kwh", forged, extra_blocks=0)
    winner_tied, reason_tied = ProofOfWorkChain.resolve_conflict([chain, tied])
    same_tail = all(
        tied.blocks[index].payload == chain.blocks[index].payload
        for index in range(2, len(chain.blocks))
    )
    check(
        "Đào vượt 0 khối: nhánh tấn công hợp lệ, cùng tổng công, nút trung thực thắng",
        winner_tied is chain
        and tied.is_valid()
        and tied.cumulative_work == chain.cumulative_work
        and len(tied.blocks) == len(chain.blocks)
        and tied.blocks[1].payload["actual_usage_kwh"] == forged,
        reason_tied,
    )
    check(
        "Nhánh tấn công đào lại đúng dữ liệu gốc (không bịa bản ghi ở phần đuôi)",
        same_tail,
        "payload các block sau block bị sửa giống chuỗi trung thực",
    )

    stronger = chain.tamper_and_remine(1, "actual_usage_kwh", forged, extra_blocks=2)
    winner_51, reason_51 = ProofOfWorkChain.resolve_conflict([chain, stronger])
    check(
        "Đào vượt 2 khối: chuỗi tấn công nặng hơn và được chọn (mô phỏng 51%)",
        winner_51 is stronger
        and stronger.is_valid()
        and stronger.cumulative_work > chain.cumulative_work
        and len(stronger.blocks) == len(chain.blocks) + 2,
        f"{reason_51} (công {chain.cumulative_work} → {stronger.cumulative_work})",
    )

    # Nhánh tấn công tự nó vẫn hợp lệ về hash → chỉ kiểm tra hash là không đủ.
    check(
        "Nhánh tấn công vẫn hợp lệ về hash (lý do phải dùng luật tổng công)",
        stronger.is_valid() and chain.is_valid(),
        "cả hai chuỗi đều valid=True",
    )

    broken = chain.clone()
    broken.tamper_block(2, "actual_usage_kwh", forged)
    winner_broken, _ = ProofOfWorkChain.resolve_conflict([broken, chain])
    check(
        "Chuỗi không hợp lệ bị loại khỏi đồng thuận",
        winner_broken is chain,
        f"chuỗi sửa mà không đào lại: valid={broken.is_valid()}",
    )


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
    check(
        "Dữ liệu đúng 720 bản ghi theo giờ trong 30 ngày, không trùng mốc thời gian",
        len(data) == 720
        and data["timestamp"].diff().dropna().eq(pd.Timedelta(hours=1)).all()
        and not data["timestamp"].duplicated().any(),
        f"{data['timestamp'].min()} → {data['timestamp'].max()}",
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
    check(
        "Dự đoán 6 giờ tới dùng mốc thời gian nối tiếp bản ghi cuối",
        len(forecast.future_timestamps) == 6
        and pd.Timestamp(forecast.future_timestamps[0])
        == data["timestamp"].iloc[-1] + pd.Timedelta(hours=1),
        f"{forecast.future_timestamps[0]} … {forecast.future_timestamps[-1]}",
    )
    if forecast.fallback_reason:
        print(f"       (RandomForest không khả dụng: {forecast.fallback_reason})")

    verify_saved_metrics(data)

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
    check("Chuỗi hợp lệ thì invalid_index() = None", chain.invalid_index() is None)

    original_hash = chain.blocks[5].hash
    chain.tamper_block(5, "consumption_kwh", 9999.0)
    check(
        "Sửa payload → hash không còn khớp và chuỗi báo không hợp lệ",
        not chain.is_valid() and chain.invalid_index() == 5 and chain.blocks[5].hash == original_hash,
        f"hash giữ nguyên {original_hash[:12]}… nhưng dữ liệu đã đổi",
    )

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

    verify_proof_of_work()
    verify_consensus_51()

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

    # CSV do Excel lưu có BOM: nếu đọc sai sẽ hỏng tên cột đầu tiên.
    bom_csv = "timestamp,consumption_kwh\n2026-01-01 00:00:00,2.4\n".encode("utf-8-sig")
    bom_frame = prepare_data(read_uploaded_csv(bom_csv))
    check(
        "read_uploaded_csv đọc được CSV có BOM (Excel) và giữ đúng tên cột",
        len(bom_frame) == 1 and float(bom_frame["consumption_kwh"].iloc[0]) == 2.4,
        f"{len(bom_frame)} dòng",
    )
    try:
        read_uploaded_csv(b"")
        empty_rejected = False
    except UserInputError:
        empty_rejected = True
    check("read_uploaded_csv từ chối file rỗng", empty_rejected)

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
    check(
        "app.py không nhúng CSS/HTML trang trí (giao diện dùng theme của Streamlit)",
        "unsafe_allow_html" not in (ROOT / "app.py").read_text(encoding="utf-8"),
        "không còn st.markdown(..., unsafe_allow_html=True) hay <style>",
    )

    failed = [name for name, passed, _ in RESULTS if not passed]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} kiểm tra đạt.")
    if failed:
        print("Chưa đạt: " + "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
