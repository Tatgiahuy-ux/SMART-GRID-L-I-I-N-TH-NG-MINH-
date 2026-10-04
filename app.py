"""Streamlit dashboard cho demo Smart Grid – Nhóm 17.

Đề tài: *Ứng dụng Trí tuệ nhân tạo (Machine Learning) và Blockchain bảo mật trong
Thành phố thông minh*. Phần được giao: ML cho Smart Grid và cơ chế đồng thuận
Blockchain chống giả mạo.

Ứng dụng gồm 5 tab:
1. Tổng quan & ML    – dự đoán tiêu thụ điện bằng RandomForest, đối chiếu baseline.
2. Blockchain / Hash – chuỗi hash liên kết phát hiện sửa đổi dữ liệu.
3. Đồng thuận PoW    – đào khối Proof of Work, luật đồng thuận chuỗi nặng nhất.
4. Dữ liệu           – bảng dữ liệu đầu vào và tải xuống.
5. Hướng dẫn demo    – kịch bản thuyết trình trước giảng viên.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from blockchain.chain import IntegrityChain
from blockchain.consensus import MAX_DIFFICULTY, ProofOfWorkChain
from ml.predictor import (
    load_saved_metrics,
    model_options,
    predict_consumption,
)

ROOT = Path(__file__).parent
DATASETS = {
    "power_consumption.csv · 30 ngày / 720 giờ (dữ liệu huấn luyện ML)": ROOT
    / "data"
    / "power_consumption.csv",
    "sample_energy.csv · 8 giờ (dữ liệu minh họa nhỏ)": ROOT / "data" / "sample_energy.csv",
}
REQUIRED_COLUMNS = {"timestamp", "consumption_kwh"}
DEFAULT_CONSUMER_ID = "METER_001"


# --------------------------------------------------------------------------- #
# Nạp và làm sạch dữ liệu
# --------------------------------------------------------------------------- #
@st.cache_data
def load_sample_data(path: str) -> pd.DataFrame:
    """Đọc bộ dữ liệu mẫu đã commit trong repository."""
    return pd.read_csv(path, parse_dates=["timestamp"])


def prepare_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Kiểm tra và chuẩn hoá dữ liệu theo hợp đồng chung với mô-đun ML."""
    missing = REQUIRED_COLUMNS.difference(raw_data.columns)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"Thiếu cột bắt buộc: {names}")

    data = raw_data[["timestamp", "consumption_kwh"]].copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data["consumption_kwh"] = pd.to_numeric(data["consumption_kwh"], errors="coerce")
    data = data.dropna().sort_values("timestamp").reset_index(drop=True)
    if data.empty:
        raise ValueError("Không có bản ghi hợp lệ sau khi làm sạch dữ liệu.")
    if (data["consumption_kwh"] < 0).any():
        raise ValueError("Mức tiêu thụ điện không được âm.")
    return data


# --------------------------------------------------------------------------- #
# Tab 1 – Tổng quan & ML
# --------------------------------------------------------------------------- #
def render_overview(data: pd.DataFrame, forecast, horizon: int) -> None:
    st.subheader("Dữ liệu tiêu thụ điện")
    st.line_chart(data.set_index("timestamp")["consumption_kwh"])

    latest = float(data["consumption_kwh"].iloc[-1])
    average = float(data["consumption_kwh"].mean())
    next_value = forecast.predictions[0]
    left, middle, right = st.columns(3)
    left.metric("Bản ghi gần nhất", f"{latest:.2f} kWh")
    middle.metric("Trung bình dữ liệu", f"{average:.2f} kWh")
    right.metric("Dự đoán giờ kế tiếp", f"{next_value:.2f} kWh")

    st.subheader(f"Dự đoán {horizon} giờ tiếp theo · {forecast.model_name}")
    if forecast.future_timestamps:
        forecast_frame = pd.DataFrame(
            {"consumption_kwh": forecast.predictions},
            index=pd.to_datetime(pd.Series(forecast.future_timestamps)),
        )
        st.line_chart(forecast_frame)
        st.dataframe(
            pd.DataFrame(
                {
                    "thời điểm": forecast.future_timestamps,
                    "dự đoán (kWh)": [round(value, 2) for value in forecast.predictions],
                }
            ),
            width="stretch",
            hide_index=True,
        )
    else:
        st.write([round(value, 2) for value in forecast.predictions])

    st.subheader("Chất lượng mô hình")
    metric_columns = st.columns(4)
    metric_columns[0].metric("MAE (kWh)", _format_metric(forecast.mae))
    metric_columns[1].metric("RMSE (kWh)", _format_metric(forecast.rmse))
    metric_columns[2].metric("R²", _format_metric(forecast.r2, digits=4))
    metric_columns[3].metric("Số bản ghi", f"{len(data)}")
    st.caption(f"Nguồn chỉ số: {forecast.metrics_source}")
    if forecast.note:
        st.caption(forecast.note)
    if forecast.fallback_reason:
        st.warning(
            "Đang dùng baseline thay cho RandomForest. Lý do: "
            f"{forecast.fallback_reason}"
        )

    if forecast.fitted is not None and len(forecast.fitted) == len(data):
        st.write("**Thực tế và giá trị mô hình khớp trên dữ liệu đầu vào**")
        st.line_chart(
            pd.DataFrame(
                {
                    "Thực tế": data["consumption_kwh"].to_numpy(),
                    "Mô hình": forecast.fitted,
                },
                index=data["timestamp"],
            )
        )

    saved = load_saved_metrics()
    if saved:
        st.caption(
            "ml/metrics.json · "
            f"{saved.get('n_train')} bản ghi huấn luyện / {saved.get('n_test')} bản ghi kiểm tra · "
            f"MAE baseline tuyến tính cùng tập test: {saved.get('baseline_linear_mae')} · "
            f"huấn luyện lúc {saved.get('trained_at')}"
        )


def _format_metric(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


# --------------------------------------------------------------------------- #
# Tab 2 – Chuỗi hash phát hiện sửa đổi
# --------------------------------------------------------------------------- #
def build_chain(data: pd.DataFrame) -> IntegrityChain:
    chain = IntegrityChain()
    for row in data.itertuples(index=False):
        chain.add_record(
            {
                "timestamp": row.timestamp.isoformat(),
                "consumption_kwh": round(float(row.consumption_kwh), 4),
            }
        )
    return chain


def render_integrity(data: pd.DataFrame, tamper_demo: bool) -> None:
    st.subheader("Kiểm tra tính toàn vẹn dữ liệu bằng chuỗi hash")
    chain = build_chain(data)
    if tamper_demo and chain.blocks:
        chain.tamper_block(0, "consumption_kwh", 9999.0)

    is_valid = chain.is_valid()
    status_left, status_right = st.columns(2)
    status_left.metric("Số block", len(chain.blocks))
    status_right.metric("Trạng thái", "HỢP LỆ" if is_valid else "ĐÃ BỊ SỬA")

    if is_valid:
        st.success("Chuỗi hash hợp lệ: dữ liệu khớp với các mã băm đã lưu.")
    else:
        st.error(
            "Phát hiện dữ liệu không khớp hash. Đây là mô phỏng thay đổi dữ liệu để minh họa."
        )

    if chain.blocks:
        st.write("**Hash của block cuối**")
        st.code(chain.blocks[-1].hash)
    st.dataframe(chain.to_frame(), width="stretch", hide_index=True)
    st.caption(
        "Lưu ý: chuỗi hash chỉ phát hiện sửa đổi. Nếu kẻ tấn công đào lại từ block bị sửa, "
        "cần đến luật đồng thuận ở tab **Đồng thuận PoW**."
    )


# --------------------------------------------------------------------------- #
# Tab 3 – Đồng thuận Proof of Work
# --------------------------------------------------------------------------- #
def build_mining_records(
    data: pd.DataFrame,
    forecast,
    count: int,
    consumer_id: str,
) -> pd.DataFrame:
    """Ghép dữ liệu thực tế với dự đoán của mô hình để ghi vào blockchain."""
    tail = data.tail(count).reset_index(drop=True)
    size = len(tail)
    fitted = forecast.fitted or []
    if fitted and len(fitted) >= size:
        predicted = [round(float(value), 4) for value in fitted[-size:]]
    else:
        predicted = [round(float(forecast.predictions[0]), 4)] * size

    return pd.DataFrame(
        {
            "consumer_id": [consumer_id] * size,
            "recorded_time": tail["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"),
            "actual_usage_kwh": tail["consumption_kwh"].astype(float).round(4),
            "predicted_usage_kwh": predicted,
        }
    )


@st.cache_data(show_spinner="Đang đào khối Proof of Work…")
def mine_chain(records: pd.DataFrame, difficulty: int) -> ProofOfWorkChain:
    chain = ProofOfWorkChain(difficulty=difficulty)
    chain.add_energy_records(records.to_dict("records"))
    return chain


@st.cache_data(show_spinner="Kẻ tấn công đang đào lại chuỗi…")
def build_attacker_chain(
    records: pd.DataFrame,
    difficulty: int,
    target_block: int,
    forged_value: float,
    extra_blocks: int,
) -> tuple[ProofOfWorkChain, ProofOfWorkChain]:
    honest = ProofOfWorkChain(difficulty=difficulty)
    honest.add_energy_records(records.to_dict("records"))
    attacker = honest.tamper_and_remine(
        target_block, "actual_usage_kwh", forged_value, extra_blocks
    )
    return honest, attacker


def render_consensus(
    records: pd.DataFrame,
    difficulty: int,
    tamper_demo: bool,
    attacker_demo: bool,
    forged_value: float,
    extra_blocks: int,
) -> None:
    st.subheader("Đào khối và kiểm tra bằng luật đồng thuận")
    st.caption(
        "Mỗi block lưu một bản ghi điện năng gồm **số thực tế** và **số mô hình ML dự đoán**; "
        "block chỉ được chấp nhận khi hash bắt đầu bằng chuỗi số 0 theo độ khó đã chọn."
    )

    chain = mine_chain(records, difficulty)
    if tamper_demo and len(chain.blocks) > 1:
        chain = chain.clone()
        chain.tamper_block(1, "actual_usage_kwh", forged_value)

    summary = chain.summary()
    columns = st.columns(5)
    columns[0].metric("Số block", summary["blocks"])
    columns[1].metric("Độ khó", summary["difficulty"])
    columns[2].metric("Tổng nonce", f"{summary['total_nonce']:,}")
    columns[3].metric("Thời gian đào", f"{summary['total_mine_seconds']:.2f} s")
    columns[4].metric("Tốc độ băm", f"{summary['hash_rate']:,.0f} H/s")

    if summary["valid"]:
        st.success("Chuỗi hợp lệ: mọi block khớp hash, nonce đạt độ khó và liên kết đúng.")
    else:
        st.error(f"Chuỗi KHÔNG hợp lệ: {summary['error']}")

    st.dataframe(chain.to_frame(), width="stretch", hide_index=True)

    st.divider()
    st.markdown("#### Luật đồng thuận: chuỗi nặng nhất thắng")
    st.write(
        "Kịch bản: kẻ tấn công sửa số điện tiêu thụ của một block rồi **đào lại** block đó "
        "và đào thêm khối mới. Chuỗi của kẻ tấn công vẫn hợp lệ về hash – đây là lý do phải "
        "so sánh **tổng công** giữa các nút."
    )

    if not attacker_demo:
        st.info("Bật **Mô phỏng kẻ tấn công đào lại** ở thanh bên để chạy so sánh hai chuỗi.")
        return

    target_block = 1 if len(records) > 1 else 0
    honest, attacker = build_attacker_chain(
        records, difficulty, target_block, forged_value, extra_blocks
    )
    winner, reason = ProofOfWorkChain.resolve_conflict([honest, attacker])

    comparison = pd.DataFrame(
        [
            {
                "Chuỗi": "Nút trung thực",
                "Hợp lệ": honest.is_valid(),
                "Số block": len(honest.blocks),
                "Tổng công": honest.cumulative_work,
                "Tổng nonce": honest.total_nonce,
                "actual_usage_kwh tại block bị sửa": honest.blocks[target_block].payload.get(
                    "actual_usage_kwh"
                ),
            },
            {
                "Chuỗi": "Nút tấn công (đã đào lại)",
                "Hợp lệ": attacker.is_valid(),
                "Số block": len(attacker.blocks),
                "Tổng công": attacker.cumulative_work,
                "Tổng nonce": attacker.total_nonce,
                "actual_usage_kwh tại block bị sửa": attacker.blocks[target_block].payload.get(
                    "actual_usage_kwh"
                ),
            },
        ]
    )
    st.dataframe(comparison, width="stretch", hide_index=True)

    if winner is None:
        st.error(reason)
    elif winner is honest:
        st.success(f"Kết luận đồng thuận: giữ chuỗi của nút trung thực. {reason}")
        st.caption(
            "Kẻ tấn công chưa đào được nhiều công hơn nên không thể áp đặt dữ liệu giả."
        )
    else:
        st.error(f"Kết luận đồng thuận: nút tấn công thắng. {reason}")
        st.caption(
            "Đây là mô phỏng tấn công 51%: khi kẻ tấn công nắm nhiều năng lực đào hơn, "
            "chuỗi hợp lệ dài nhất có thể là chuỗi giả. Demo không tuyên bố bảo mật tuyệt đối."
        )


# --------------------------------------------------------------------------- #
# Giao diện chính
# --------------------------------------------------------------------------- #
def render_guide() -> None:
    st.subheader("Kịch bản thuyết trình")
    st.markdown(
        """
        1. **Tổng quan & ML**: chiếu dữ liệu 720 giờ, chọn mô hình *RandomForest* và số giờ dự đoán,
           đọc các chỉ số MAE / RMSE / R² trên tập kiểm tra 20%.
        2. So sánh với **Baseline xu hướng tuyến tính** để thấy mô hình ML tốt hơn ở đâu.
        3. **Blockchain / Hash**: mỗi bản ghi được liên kết bằng SHA-256; bật *Mô phỏng dữ liệu bị sửa*
           để trạng thái chuyển sang ĐÃ BỊ SỬA.
        4. **Đồng thuận PoW**: chọn độ khó, đào khối và giải thích `nonce`, thời gian đào, tốc độ băm.
        5. Bật *Mô phỏng kẻ tấn công đào lại*: kẻ tấn công đào lại chuỗi vẫn hợp lệ về hash,
           luật đồng thuận theo tổng công mới là thứ bảo vệ dữ liệu.
        6. Tăng số khối đào thêm của kẻ tấn công để mô phỏng **tấn công 51%** và nêu giới hạn.
        7. Kết thúc: đây là demo giáo dục, dữ liệu mô phỏng, chưa phải kết quả nghiên cứu chính thức.
        """
    )
    st.warning(
        "Không trình bày hash/PoW là bảo mật tuyệt đối. Chuỗi hash phát hiện sửa đổi; "
        "PoW + luật đồng thuận chống sửa đổi khi kẻ tấn công không nắm đa số năng lực đào."
    )
    st.info(
        "Huấn luyện lại mô hình: `.\\.venv\\Scripts\\python.exe ml\\train_model.py` "
        "(sinh lại `ml/model.pkl` và `ml/metrics.json`)."
    )


def main() -> None:
    st.set_page_config(page_title="Smart Grid Monitor · Nhóm 17", page_icon="⚡", layout="wide")
    st.title("Smart Grid Monitor")
    st.caption(
        "Nhóm 17 · Ứng dụng AI (Machine Learning) và Blockchain bảo mật trong Thành phố thông minh · "
        "Nhiệm vụ: ML cho Smart Grid và cơ chế đồng thuận Blockchain chống giả mạo."
    )

    options = model_options()
    available = [option for option in options if option["available"]]
    unavailable = [option for option in options if not option["available"]]

    with st.sidebar:
        st.header("Điều khiển demo")
        dataset_label = st.selectbox("Nguồn dữ liệu mẫu", list(DATASETS.keys()), key="dataset")
        uploaded_file = st.file_uploader("Hoặc tải dữ liệu CSV", type="csv")
        model_choice = st.selectbox(
            "Mô hình ML",
            [option["value"] for option in available],
            format_func=lambda value: next(
                option["label"] for option in options if option["value"] == value
            ),
            key="model_choice",
        )
        horizon = st.slider("Số giờ muốn dự đoán", min_value=1, max_value=12, value=6, key="horizon")

        st.divider()
        st.caption("Mô phỏng chuỗi hash")
        tamper_demo = st.toggle("Mô phỏng dữ liệu bị sửa (tab Hash)", value=False, key="tamper_demo")

        st.divider()
        st.caption("Mô phỏng Proof of Work")
        difficulty = st.select_slider(
            "Độ khó đào", options=list(range(1, MAX_DIFFICULTY + 1)), value=2, key="difficulty"
        )
        block_count = st.slider(
            "Số block đào từ dữ liệu", min_value=3, max_value=12, value=6, key="block_count"
        )
        consumer_id = st.text_input("Mã đồng hồ (consumer_id)", value=DEFAULT_CONSUMER_ID, key="consumer_id")
        attacker_demo = st.checkbox(
            "Mô phỏng kẻ tấn công đào lại", value=False, key="attacker_demo"
        )
        forged_value = st.number_input(
            "Giá trị giả mạo (kWh)",
            min_value=0.0,
            max_value=9999.0,
            value=10.0,
            step=1.0,
            key="forged_value",
        )
        extra_blocks = st.slider(
            "Số khối kẻ tấn công đào vượt thêm",
            min_value=0,
            max_value=3,
            value=0,
            key="extra_blocks",
        )
        st.caption(
            "0 = hòa tổng công (nút trung thực thắng); từ 1 trở lên = mô phỏng tấn công 51%."
        )
        st.caption("CSV cần có hai cột: timestamp và consumption_kwh.")

    for option in unavailable:
        st.sidebar.warning(f"{option['label']} chưa khả dụng: {option['detail']}")

    try:
        raw_data = (
            pd.read_csv(uploaded_file)
            if uploaded_file is not None
            else load_sample_data(str(DATASETS[dataset_label]))
        )
        data = prepare_data(raw_data)
        forecast = predict_consumption(data, horizon=horizon, model=model_choice)
    except (OSError, ValueError, RuntimeError, pd.errors.ParserError) as exc:
        st.error(f"Không thể xử lý dữ liệu: {exc}")
        st.stop()

    source_label = "file CSV vừa tải" if uploaded_file is not None else dataset_label
    st.caption(f"Nguồn dữ liệu: {source_label} · Mô hình: {forecast.model_name}")

    mining_records = build_mining_records(data, forecast, block_count, consumer_id)

    overview_tab, integrity_tab, consensus_tab, data_tab, guide_tab = st.tabs(
        [
            "Tổng quan & ML",
            "Blockchain / Hash",
            "Đồng thuận PoW",
            "Dữ liệu",
            "Hướng dẫn demo",
        ]
    )
    with overview_tab:
        render_overview(data, forecast, horizon)
    with integrity_tab:
        render_integrity(data, tamper_demo)
    with consensus_tab:
        render_consensus(
            mining_records,
            difficulty,
            tamper_demo,
            attacker_demo,
            float(forged_value),
            extra_blocks,
        )
    with data_tab:
        st.subheader("Bảng dữ liệu đầu vào")
        st.dataframe(data, width="stretch", hide_index=True)
        st.subheader("Bản ghi sẽ ghi vào blockchain")
        st.dataframe(mining_records, width="stretch", hide_index=True)
        st.download_button(
            "Tải dữ liệu đã làm sạch",
            data.to_csv(index=False).encode("utf-8"),
            file_name="smart_grid_cleaned.csv",
            mime="text/csv",
        )
    with guide_tab:
        render_guide()


if __name__ == "__main__":
    main()
