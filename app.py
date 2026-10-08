"""Giao diện demo Smart Grid – Nhóm 17."""

from dataclasses import asdict
import json
from pathlib import Path
import re

import altair as alt
import pandas as pd
import streamlit as st

from blockchain.consensus import (
    GENESIS_PREVIOUS_HASH,
    MAX_DIFFICULTY,
    ProofOfWorkChain,
)
from ml.predictor import (
    ForecastResult,
    MODE_LINEAR,
    load_saved_metrics,
    model_options,
    predict_consumption,
)
from security import (
    MAX_UPLOAD_MB,
    configure_logging,
    prepare_data,
    read_uploaded_csv,
    safe_error,
    validate_upload,
)

ROOT = Path(__file__).parent
DEFAULT_DATASET_LABEL = "power_consumption.csv – 720 giờ (30 ngày, dữ liệu huấn luyện ML)"
DATASETS = {
    DEFAULT_DATASET_LABEL: ROOT / "data" / "power_consumption.csv",
    "sample_energy.csv – 8 giờ (dữ liệu minh họa nhỏ)": ROOT / "data" / "sample_energy.csv",
}
DEFAULT_CONSUMER_ID = "METER_001"
FORECAST_HOURS = 24
LIVE_DIFFICULTY = 3
CONSUMER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")

# CSS tối thiểu — chỉ những gì .streamlit/config.toml không đặt được.
# Chọn theo thuộc tính ổn định (data-testid), không theo tên lớp tự sinh css-xxxx.
BASE_CSS = """
<style>
  [data-testid="stMainBlockContainer"] { padding-top: 32px; padding-bottom: 64px; }
  [data-testid="stVerticalBlock"] { gap: 16px; }
  [data-testid="stAppViewContainer"] { font-variant-numeric: tabular-nums; }
  [data-testid="stHeading"]:has(h3) { margin: 32px 0 8px; }
  [data-testid="stMetricLabel"] { color: #756A61; }
  [data-testid="stMetricLabel"] p, [data-testid="stWidgetLabel"] p { color: #756A61; font-size: 14px; }
  @media (max-width: 640px) {
    [data-testid="stTabs"] [role="tablist"] { flex-wrap: wrap; row-gap: 4px; overflow: visible; }
  }
</style>
"""


def render_header():
    st.title("Hệ thống giám sát và dự đoán phụ tải điện")
    return st.empty()


@st.cache_data
def load_sample_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["timestamp"])


@st.cache_data(show_spinner=False)
def run_forecast(data: pd.DataFrame, horizon: int, model: str) -> ForecastResult:
    return predict_consumption(data, horizon=horizon, model=model)


def _short_hash(value: str, head: int = 10, tail: int = 6) -> str:
    if len(value) <= head + tail + 1:
        return value
    return f"{value[:head]}…{value[-tail:]}"


def _block_label(index: int) -> str:
    return "Genesis" if index == 0 else f"#{index}"


def _display_recorded_time(value) -> str:
    try:
        return pd.Timestamp(value).strftime("%d/%m %H:%M")
    except (ValueError, TypeError):
        return str(value)


def _kwh(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _display_reason(reason: str) -> str:
    return reason.replace("tổng công", "tổng sức đào").replace(" → ", ": ")


def build_mining_records(
    data: pd.DataFrame,
    forecast: ForecastResult,
    count: int,
    consumer_id: str,
) -> pd.DataFrame:
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


def load_input_data(uploaded_file, dataset_label: str) -> pd.DataFrame:
    """Đọc dữ liệu mẫu hoặc file đã qua toàn bộ kiểm tra bảo mật."""
    if uploaded_file is not None:
        validate_upload(uploaded_file.name, uploaded_file.size)
        raw_data = read_uploaded_csv(uploaded_file.getvalue())
    else:
        raw_data = load_sample_data(str(DATASETS[dataset_label]))
    return prepare_data(raw_data)


def render_overview(
    data: pd.DataFrame,
    forecast: ForecastResult,
    model_choice: str,
    show_saved_metrics: bool,
    saved: dict | None,
    default_dataset: bool,
) -> None:
    forest_metrics = show_saved_metrics and model_choice != MODE_LINEAR
    if model_choice == MODE_LINEAR:
        mae, rmse, r2 = forecast.mae, None, None
    elif forest_metrics:
        mae, rmse, r2 = saved.get("mae"), saved.get("rmse"), saved.get("r2")
    else:
        mae = rmse = r2 = None

    values = (
        f"{len(data):,}",
        "—" if mae is None else f"{mae:.2f} kWh",
        "—" if rmse is None else f"{rmse:.2f} kWh",
        "—" if r2 is None else f"{r2:.3f}",
    )
    labels = (
        "Số mẫu dữ liệu",
        "Sai số trung bình",
        "Sai số có phạt lỗi lớn",
        "Độ khớp (R²)",
    )
    for start in range(0, 4, 2):
        for column, label, value in zip(
            st.columns(2),
            labels[start : start + 2],
            values[start : start + 2],
        ):
            column.metric(label, value)

    st.markdown(
        "**Cách đọc:** Sai số trung bình càng nhỏ càng tốt; độ khớp R² càng gần 1 càng tốt."
    )

    if model_choice != MODE_LINEAR and not forest_metrics:
        st.info("Chưa có chỉ số đánh giá cho bộ dữ liệu này.")

    if forecast.fitted is not None and len(forecast.fitted) == len(data):
        rows = int(saved.get("n_test", 144)) if forest_metrics else min(168, len(data))
        rows = min(rows, len(data))
        span = f"{rows} giờ cuối" if rows < 24 else f"{rows // 24} ngày cuối"
        st.subheader(f"Điện năng thực tế và dự đoán, {span}")
        chart_data = pd.DataFrame(
            {
                "Thời gian": data["timestamp"].tail(rows).to_numpy(),
                "Thực tế": data["consumption_kwh"].tail(rows).to_numpy(),
                "Dự đoán": forecast.fitted[-rows:],
            }
        ).melt("Thời gian", var_name="Chuỗi", value_name="Điện năng (kWh)")
        series = ["Thực tế", "Dự đoán"]
        chart = (
            alt.Chart(chart_data)
            .mark_line()
            .encode(
                x=alt.X(
                    "Thời gian:T",
                    title=None,
                    axis=alt.Axis(tickCount="day"),
                ),
                y=alt.Y(
                    "Điện năng (kWh):Q",
                    title="Điện năng (kWh)",
                    scale=alt.Scale(zero=True),
                ),
                color=alt.Color(
                    "Chuỗi:N",
                    scale=alt.Scale(
                        domain=series,
                        range=["#C08A5B", "#9A5B2E"],
                    ),
                    legend=alt.Legend(title=None, orient="bottom"),
                ),
                strokeWidth=alt.StrokeWidth(
                    "Chuỗi:N",
                    sort=series,
                    scale=alt.Scale(domain=series, range=[1.4, 2.4]),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("Thời gian:T", title="Thời gian"),
                    alt.Tooltip("Chuỗi:N", title="Chuỗi"),
                    alt.Tooltip("Điện năng (kWh):Q", format=".2f"),
                ],
            )
            .interactive()
        )
        st.altair_chart(
            chart,
            height=340,
            alt="So sánh mức dùng điện thực tế và dự đoán theo giờ",
        )
        if forest_metrics:
            st.markdown("Phần này mô hình chưa từng học.")
        elif model_choice == MODE_LINEAR:
            st.markdown(
                "Phương pháp đường thẳng chỉ nhìn các giờ trước đó để đoán giờ kế tiếp."
            )
        elif default_dataset:
            st.markdown("Mô hình đã học chính dữ liệu này nên số trông đẹp hơn thực tế.")
        if not default_dataset and model_choice != MODE_LINEAR:
            st.markdown(
                "Mô hình chỉ nhìn giờ, ngày, tháng nên với file tải lên, "
                "đường dự đoán có thể lệch xa số thực; đây là hạn chế của bản demo."
            )

    st.subheader("Dự báo 24 giờ tới")
    future_hours = [pd.Timestamp(value) for value in forecast.future_timestamps]
    predictions = [float(value) for value in forecast.predictions]
    st.markdown(
        f"Từ {future_hours[0].strftime('%d/%m %H:00')} "
        f"đến {future_hours[-1].strftime('%d/%m %H:00')}."
    )
    st.bar_chart(
        pd.DataFrame(
            {"Điện năng (kWh)": predictions},
            index=pd.to_datetime(forecast.future_timestamps),
        ),
        color="#9A5B2E",
        y_label="Điện năng (kWh)",
        height=260,
    )
    peak_index = predictions.index(max(predictions))
    low_index = predictions.index(min(predictions))
    peak_column, low_column = st.columns(2)
    peak_column.metric(
        f"Giờ dùng nhiều nhất: {future_hours[peak_index].strftime('%H')}:00",
        f"{predictions[peak_index]:.2f} kWh",
    )
    low_column.metric(
        f"Giờ dùng ít nhất: {future_hours[low_index].strftime('%H')}:00",
        f"{predictions[low_index]:.2f} kWh",
    )
    st.markdown(
        "Mô hình chỉ học từ dữ liệu có sẵn nên chỉ đáng tin cho các giờ ngay sau đó."
    )
    if model_choice != MODE_LINEAR and not default_dataset:
        st.markdown(
            "RandomForest đã học sẵn từ bộ dữ liệu mặc định. "
            "File bạn tải lên chỉ quyết định mốc thời gian dự báo, "
            "không đổi hình dạng đường dự báo."
        )

    if show_saved_metrics and saved:
        with st.expander(
            "So sánh với phương pháp đường thẳng đơn giản",
            expanded=False,
            key="t1_compare",
        ):
            comparison = pd.DataFrame(
                [
                    {
                        "Mô hình": "Mô hình RandomForest",
                        "Sai số trung bình (kWh)": saved.get("mae"),
                        "Sai số có phạt lỗi lớn (kWh)": saved.get("rmse"),
                        "Độ khớp (R²)": saved.get("r2"),
                    },
                    {
                        "Mô hình": "Đường thẳng đơn giản",
                        "Sai số trung bình (kWh)": saved.get("baseline_linear_mae"),
                        "Sai số có phạt lỗi lớn (kWh)": saved.get("baseline_linear_rmse"),
                        "Độ khớp (R²)": saved.get("baseline_linear_r2"),
                    },
                ]
            )
            st.dataframe(
                comparison,
                hide_index=True,
                column_config={
                    "Sai số trung bình (kWh)": st.column_config.NumberColumn(
                        format="%.2f"
                    ),
                    "Sai số có phạt lỗi lớn (kWh)": st.column_config.NumberColumn(
                        format="%.2f"
                    ),
                    "Độ khớp (R²)": st.column_config.NumberColumn(format="%.3f"),
                },
                alt="So sánh hai cách dự đoán trên cùng dữ liệu kiểm tra",
            )
            st.markdown("Số nhỏ hơn nghĩa là dự đoán gần số điện thật hơn.")
            if comparison["Độ khớp (R²)"].lt(0).any():
                st.markdown(
                    "R² âm nghĩa là phương pháp đó dự đoán tệ hơn việc lấy số trung bình."
                )

    with st.expander(
        "Xem dữ liệu huấn luyện", expanded=False, key="t1_training_data"
    ):
        st.dataframe(data, hide_index=True, alt="Dữ liệu điện đã làm sạch")
        st.download_button(
            "Tải dữ liệu đã làm sạch",
            data.to_csv(index=False).encode("utf-8"),
            file_name="smart_grid_cleaned.csv",
            mime="text/csv",
            key="t1_download_cleaned",
        )


def _display_hour(hour_iso: str) -> str:
    return pd.Timestamp(hour_iso).strftime("%d/%m/%Y %H:00")


def render_prediction(forecast: ForecastResult) -> None:
    left, right = st.columns(2)
    with left:
        consumer_id = st.text_input(
            "Mã đồng hồ / người dùng", value=DEFAULT_CONSUMER_ID, key="t2_consumer_id"
        )
        hour_iso = st.selectbox(
            "Giờ cần dự đoán",
            forecast.future_timestamps,
            format_func=_display_hour,
            key="t2_hour",
        )
    with right:
        actual = st.number_input(
            "Mức tiêu thụ thực tế (kWh)",
            min_value=0.0,
            max_value=1000.0,
            value=0.0,
            step=0.1,
            key="t2_actual",
            help="Số đọc từ đồng hồ điện. Nhập giả lập cho buổi demo.",
        )

    st.markdown(
        "**Bước 1:** bấm Dự đoán. **Bước 2:** nhập số thực tế rồi bấm Ghi vào Blockchain."
    )
    if st.button("Dự đoán", type="primary", key="t2_predict"):
        idx = forecast.future_timestamps.index(hour_iso)
        st.session_state["prediction"] = {
            "consumer_id": consumer_id,
            "hour_iso": hour_iso,
            "predicted": float(forecast.predictions[idx]),
            "model_name": forecast.model_name,
            "written": False,
        }

    prediction = st.session_state["prediction"]
    if prediction is not None:
        st.metric(
            f"Dự đoán cho {_display_hour(prediction['hour_iso'])}",
            f"{prediction['predicted']:.2f} kWh",
        )
        st.markdown(f"Mô hình: **{prediction['model_name']}**")
        if forecast.fallback_reason:
            st.warning(f"Đang dùng phương pháp dự phòng: {forecast.fallback_reason}")

    write_note = st.empty()
    disabled = prediction is None or prediction["written"]
    if st.button("Ghi vào Blockchain", key="t2_write", disabled=disabled):
        if not CONSUMER_ID_PATTERN.fullmatch(consumer_id):
            st.error(
                "Mã đồng hồ chỉ gồm chữ, số, gạch dưới, gạch ngang (tối đa 32 ký tự)."
            )
        elif consumer_id != prediction["consumer_id"] or hour_iso != prediction["hour_iso"]:
            st.warning(
                "Bạn đã đổi mã đồng hồ hoặc giờ sau khi dự đoán. Hãy bấm Dự đoán lại."
            )
        elif actual <= 0:
            st.warning("Nhập mức tiêu thụ thực tế lớn hơn 0 kWh trước khi ghi.")
        else:
            try:
                with st.spinner("Đang đào khối…"):
                    block = st.session_state["chain"].add_energy_record(
                        consumer_id=consumer_id,
                        recorded_time=pd.Timestamp(hour_iso).strftime("%Y-%m-%d %H:%M:%S"),
                        actual_usage_kwh=float(actual),
                        predicted_usage_kwh=float(prediction["predicted"]),
                    )
            except (ValueError, RuntimeError, OSError) as exc:
                st.error(safe_error(exc, "Không thể ghi dữ liệu vào Blockchain."))
            else:
                prediction["written"] = True
                prediction["written_block"] = block.index
                prediction["written_actual"] = float(actual)
                prediction["written_predicted"] = float(prediction["predicted"])
                prediction["written_nonce"] = int(block.nonce)

    if prediction is not None and prediction.get("written_block") is not None:
        write_note.markdown(
            f"Đã ghi vào Block #{prediction['written_block']}: "
            f"thực tế {prediction['written_actual']:.2f} kWh, "
            f"dự đoán {prediction['written_predicted']:.2f} kWh, "
            f"số lần thử {prediction['written_nonce']:,}. "
            "Muốn ghi tiếp, chọn giờ khác rồi bấm Dự đoán."
        )


def _block_frame(chain: ProofOfWorkChain) -> pd.DataFrame:
    frame = chain.to_frame().rename(
        columns={
            "block": "Block",
            "thời điểm ghi": "Thời điểm ghi",
            "consumer_id": "Mã đồng hồ",
            "thực tế (kWh)": "Thực tế (kWh)",
            "dự đoán (kWh)": "Dự đoán (kWh)",
            "nonce": "Số lần thử (nonce)",
            "đào (ms)": "Đào (ms)",
            "hash": "Mã băm (hash)",
            "previous_hash": "Mã băm khối trước",
        }
    )
    frame["Block"] = frame["Block"].map(_block_label)
    frame["Thời điểm ghi"] = frame["Thời điểm ghi"].map(_display_recorded_time)
    frame["Mã băm (hash)"] = frame["Mã băm (hash)"].map(_short_hash)
    return frame[
        [
            "Block",
            "Thời điểm ghi",
            "Thực tế (kWh)",
            "Dự đoán (kWh)",
            "Số lần thử (nonce)",
            "Mã băm (hash)",
        ]
    ]


def _block_status(chain: ProofOfWorkChain, position: int) -> str:
    block = chain.blocks[position]
    expected_hash = ProofOfWorkChain.calculate_hash(
        block.index, block.timestamp, block.payload, block.previous_hash, block.nonce
    )
    expected_previous = (
        GENESIS_PREVIOUS_HASH if position == 0 else chain.blocks[position - 1].hash
    )
    content_ok = block.hash == expected_hash
    link_ok = block.previous_hash == expected_previous
    work_ok = block.hash.startswith("0" * block.difficulty)
    if not link_ok:
        return "Liên kết đứt"
    if not content_ok or not work_ok:
        return "Nội dung bị sửa"
    return "Hợp lệ"


def _integrity_frame(chain: ProofOfWorkChain) -> pd.DataFrame:
    rows = [
        {"Block": _block_label(block.index), "Kết quả": _block_status(chain, position)}
        for position, block in enumerate(chain.blocks)
    ]
    return pd.DataFrame(rows)


def _render_chain_cards(chain: ProofOfWorkChain) -> None:
    total = len(chain.blocks)
    last_blocks = chain.blocks[-6:]
    start = total - len(last_blocks)
    st.subheader("Chuỗi khối", divider="orange")
    if total > 6:
        st.markdown(
            f"Đang hiện 6 block cuối trong {total} block. "
            "Xem đủ trong bảng chi tiết bên dưới."
        )
    for row_start in range(0, len(last_blocks), 2):
        columns = st.columns(2)
        for offset, column in enumerate(columns):
            position = start + row_start + offset
            if position >= total:
                continue
            block = chain.blocks[position]
            title = "Genesis" if block.index == 0 else f"Block #{block.index}"
            with column, st.container(border=True):
                st.markdown(f"**{title}**")
                if block.index != 0:
                    st.markdown(
                        f"Thực tế {_kwh(block.payload.get('actual_usage_kwh'))} kWh · "
                        f"Dự đoán {_kwh(block.payload.get('predicted_usage_kwh'))} kWh"
                    )
                st.markdown(f"Mã băm: `{_short_hash(block.hash)}`")
                st.markdown(f"Khối trước: `{_short_hash(block.previous_hash)}`")
                status = _block_status(chain, position)
                if status == "Hợp lệ":
                    st.markdown(":green[Hợp lệ]")
                else:
                    st.error(status)


def render_blockchain() -> None:
    chain = st.session_state["chain"]
    shown = chain.clone()
    tamper = st.session_state["tamper"]
    if tamper is not None:
        shown.tamper_block(tamper["index"], "actual_usage_kwh", tamper["value"])

    st.markdown(
        f"Độ khó {shown.difficulty}: mã băm phải bắt đầu bằng {'0' * shown.difficulty}."
    )
    if shown.is_valid():
        st.success(
            f"Chuỗi hợp lệ: {len(shown.blocks)} block, mã băm khớp nội dung và nối đúng nhau."
        )
    else:
        st.error(f"Phát hiện dữ liệu bị sửa: {shown.validation_error()}")
    if tamper is not None:
        st.warning(
            f"Đang giả lập sửa trộm Block #{tamper['index']}: "
            f"{_kwh(tamper['original'])} kWh thành {_kwh(tamper['value'])} kWh."
        )

    _render_chain_cards(shown)

    with st.expander("Bảng chi tiết các block", expanded=False):
        st.dataframe(
            _block_frame(shown),
            hide_index=True,
            column_config={
                "Thực tế (kWh)": st.column_config.NumberColumn(format="%.2f"),
                "Dự đoán (kWh)": st.column_config.NumberColumn(format="%.2f"),
                "Số lần thử (nonce)": st.column_config.NumberColumn(
                    help="Máy thử nhiều con số cho đến khi mã băm đạt yêu cầu."
                ),
                "Mã băm (hash)": st.column_config.TextColumn(
                    help="Dấu niêm phong đổi hoàn toàn khi nội dung block thay đổi."
                ),
            },
            alt="Chuỗi khối điện năng đang hiển thị",
        )

    confirm_clear = st.checkbox(
        "Tôi xác nhận xóa toàn bộ dữ liệu demo", key="t3_confirm_clear"
    )
    check_column, download_column, clear_column, _ = st.columns([3, 3, 3, 2])
    with check_column:
        check = st.button("Kiểm tra toàn vẹn", key="t3_check")
    with download_column:
        st.download_button(
            "Tải Blockchain JSON",
            json.dumps(
                [asdict(block) for block in chain.blocks], ensure_ascii=False, indent=2
            ),
            file_name="blockchain.json",
            mime="application/json",
            key="t3_download",
        )
    with clear_column:
        if st.button("Xóa dữ liệu demo", key="t3_clear", disabled=not confirm_clear):
            st.session_state["chain"] = ProofOfWorkChain(difficulty=LIVE_DIFFICULTY)
            st.session_state["prediction"] = None
            st.session_state["tamper"] = None
            st.rerun()
    if check:
        st.dataframe(
            _integrity_frame(shown),
            hide_index=True,
            alt="Kết quả kiểm tra từng block",
        )

    st.subheader("Thử sửa trộm", divider="orange")
    st.write("Đổi một số điện đã ghi để xem chuỗi phát hiện thay đổi.")
    candidates = [block.index for block in chain.blocks if "actual_usage_kwh" in block.payload]
    if not candidates:
        st.info("Chưa có block dữ liệu. Sang tab Dự đoán, ghi ít nhất 1 bản ghi.")
    else:
        target = st.selectbox(
            "Chọn block muốn sửa",
            candidates,
            format_func=lambda index: f"Block #{index}",
            key="t3_tamper_block",
        )
        value = st.number_input(
            "Giá trị giả (kWh)",
            min_value=0.0,
            max_value=100000.0,
            value=9999.0,
            key="t3_tamper_value",
        )
        tamper_column, undo_column, _ = st.columns([3, 3, 5])
        with tamper_column:
            if st.button("Sửa trộm block này", key="t3_tamper"):
                st.session_state["tamper"] = {
                    "index": target,
                    "value": float(value),
                    "original": chain.blocks[target].payload["actual_usage_kwh"],
                }
                st.rerun()
        with undo_column:
            if st.button(
                "Hoàn tác sửa trộm",
                key="t3_undo",
                disabled=tamper is None,
            ):
                st.session_state["tamper"] = None
                st.rerun()

    with st.expander("Chi tiết từng block", key="t3_details"):
        for block in shown.blocks:
            st.markdown(
                "**Block khởi tạo (Genesis)**" if block.index == 0 else f"**Block #{block.index}**"
            )
            if consumer_id := block.payload.get("consumer_id"):
                st.markdown(f"**Mã đồng hồ:** `{consumer_id}`")
            payload_view = {
                key: _kwh(value) if key.endswith("_kwh") else value
                for key, value in block.payload.items()
            }
            st.json(payload_view)
            st.markdown(f"**Mã băm (hash):** `{block.hash}`")
            st.markdown(f"**Mã băm khối trước:** `{block.previous_hash}`")
            st.markdown(
                f"**Số lần thử (nonce):** {block.nonce:,} · "
                f"**Đào (ms):** {block.mine_seconds * 1000:.2f}"
            )

    with st.expander("Mã băm và số lần thử là gì?", expanded=False, key="t3_terms"):
        st.markdown(
            "Mã băm là dấu niêm phong của block; đổi nội dung thì mã băm đổi hoàn toàn. "
            "Số lần thử là số con số máy đã kiểm tra để tìm được mã băm đạt độ khó."
        )


def render_chain_card(
    chain: ProofOfWorkChain, title: str, chosen: bool, target_block: int
) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**" + (" — được chọn" if chosen else ""))
        first, second = st.columns(2)
        first.metric("Số block", len(chain.blocks))
        second.metric("Tổng sức đào", f"{chain.cumulative_work:,}")
        first.metric("Hợp lệ", "Có" if chain.is_valid() else "Không")
        st.metric(
            "Giá trị tại block bị sửa (kWh)",
            _kwh(chain.blocks[target_block].payload.get("actual_usage_kwh")),
        )


def render_consensus(data: pd.DataFrame, forecast: ForecastResult) -> None:
    st.write(
        "Kẻ tấn công sửa số điện của một block rồi đào lại cả chuỗi để mã băm khớp trở lại. "
        "Chỉ kiểm tra mã băm là chưa đủ. Các nút phải so sánh sức đào của hai chuỗi và "
        "chọn chuỗi nặng hơn."
    )
    difficulty = st.select_slider(
        "Độ khó (số số 0 đầu mã băm)",
        options=list(range(1, MAX_DIFFICULTY + 1)),
        value=2,
        key="t4_difficulty",
        help="Mã băm phải bắt đầu bằng N số 0.",
    )
    strengths = {
        "Đào kịp bằng nút trung thực": 0,
        "Đào nhanh hơn 1 khối": 1,
        "Đào nhanh hơn 3 khối": 3,
    }
    strength = st.selectbox(
        "Sức đào của kẻ tấn công", list(strengths), key="t4_strength"
    )
    forged = st.number_input(
        "Giá trị giả mạo (kWh)",
        min_value=0.0,
        max_value=9999.0,
        value=10.0,
        key="t4_forged",
    )
    if st.button("Chạy mô phỏng", key="t4_run"):
        st.session_state["sim"] = {
            "difficulty": int(difficulty),
            "extra_blocks": strengths[strength],
            "forged": float(forged),
        }

    sim = st.session_state["sim"]
    if sim is None:
        return

    records = build_mining_records(data, forecast, 6, DEFAULT_CONSUMER_ID)
    target_block = 1
    honest, attacker = build_attacker_chain(
        records,
        sim["difficulty"],
        target_block,
        sim["forged"],
        sim["extra_blocks"],
    )
    winner, reason = ProofOfWorkChain.resolve_conflict([honest, attacker])
    actual = honest.blocks[target_block].payload["actual_usage_kwh"]
    if winner is None:
        st.error(reason)
    elif winner is honest:
        st.success(f"Giữ chuỗi trung thực. Số thật {_kwh(actual)} kWh không bị thay.")
    else:
        st.error(
            f"Kẻ tấn công THẮNG. Số giả {_kwh(sim['forged'])} kWh được các nút chấp nhận."
        )
        st.markdown(
            "Đây là minh họa kẻ tấn công nắm đa số sức đào (tấn công 51%), "
            "không phải mô phỏng đầy đủ."
        )

    st.subheader("So sánh tổng sức đào")
    comparison_series = ["Chuỗi trung thực", "Chuỗi kẻ tấn công"]
    comparison_data = pd.DataFrame(
        {
            "Chuỗi": comparison_series,
            "Sức đào": [honest.cumulative_work, attacker.cumulative_work],
        }
    )
    comparison_max = max(honest.cumulative_work, attacker.cumulative_work)
    comparison_headroom = max(2, round(comparison_max * 0.15))
    comparison_bars = (
        alt.Chart(comparison_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "Chuỗi:N",
                sort=comparison_series,
                title=None,
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "Sức đào:Q",
                title="Sức đào",
                scale=alt.Scale(
                    zero=True,
                    domainMax=comparison_max + comparison_headroom,
                ),
                axis=alt.Axis(grid=True, tickMinStep=1),
            ),
            color=alt.Color(
                "Chuỗi:N",
                scale=alt.Scale(
                    domain=comparison_series,
                    range=["#4A4038", "#9A5B2E"],
                ),
                legend=None,
            ),
        )
    )
    comparison_labels = (
        alt.Chart(comparison_data)
        .mark_text(dy=-8, baseline="bottom", fontSize=14)
        .encode(
            x=alt.X("Chuỗi:N", sort=comparison_series),
            y=alt.Y("Sức đào:Q"),
            text=alt.Text("Sức đào:Q"),
        )
    )
    st.altair_chart(
        (comparison_bars + comparison_labels).interactive(),
        theme="streamlit",
        width="stretch",
        height=290,
    )
    if honest.cumulative_work == attacker.cumulative_work:
        st.markdown(_display_reason(reason))

    honest_column, attacker_column = st.columns(2)
    with honest_column:
        render_chain_card(honest, "Chuỗi trung thực", winner is honest, target_block)
    with attacker_column:
        render_chain_card(
            attacker, "Chuỗi kẻ tấn công", winner is attacker, target_block
        )

    with st.expander("Chi tiết so sánh", key="t4_details"):
        st.markdown(
            "**Số lần thử (nonce):** Máy thử nhiều con số cho đến khi mã băm đạt yêu cầu, "
            "như quay số đến khi trúng."
        )
        st.markdown(f"Luật chọn chuỗi: {reason}")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Chuỗi": "Chuỗi trung thực",
                        "Hợp lệ": honest.is_valid(),
                        "Số block": len(honest.blocks),
                        "Tổng sức đào": honest.cumulative_work,
                        "Số lần thử (nonce)": honest.total_nonce,
                        "Giá trị tại block bị sửa (kWh)": actual,
                    },
                    {
                        "Chuỗi": "Chuỗi kẻ tấn công",
                        "Hợp lệ": attacker.is_valid(),
                        "Số block": len(attacker.blocks),
                        "Tổng sức đào": attacker.cumulative_work,
                        "Số lần thử (nonce)": attacker.total_nonce,
                        "Giá trị tại block bị sửa (kWh)": attacker.blocks[
                            target_block
                        ].payload.get("actual_usage_kwh"),
                    },
                ]
            ),
            hide_index=True,
            column_config={
                "Giá trị tại block bị sửa (kWh)": st.column_config.NumberColumn(
                    format="%.2f"
                ),
            },
            alt="So sánh sức đào của hai chuỗi",
        )

    strength_label = next(
        label for label, blocks in strengths.items() if blocks == sim["extra_blocks"]
    )
    st.markdown(
        f"Kết quả ứng với: độ khó {sim['difficulty']}; "
        f"kẻ tấn công {strength_label}; "
        f"giá giả {sim['forged']:.2f} kWh."
    )


def render_guide(saved: dict | None) -> None:
    metric_note = ""
    if saved and saved.get("mae") is not None:
        metric_note = f" Sai số trung bình mẫu là {saved['mae']:.2f} kWh."
    st.markdown(
        f"""1. **Tổng quan.** Đọc bốn con số và biểu đồ thực tế so với dự đoán.{metric_note}
2. **Dự đoán.** Chọn giờ rồi bấm Dự đoán để xem mức điện dự kiến.
3. **Ghi dữ liệu.** Nhập số thực tế, bấm Ghi vào Blockchain. Lặp lại với 2 đến 3 giờ khác.
4. **Thử sửa trộm.** Mở tab Blockchain, sửa một block, kiểm tra rồi hoàn tác.
5. **So sức đào.** Chạy mức Đào kịp, sau đó chọn Đào nhanh hơn 1 khối.
6. **Kết luận.** Dự đoán hỗ trợ theo dõi phụ tải; chuỗi khối cho biết số liệu đã bị sửa."""
    )
    st.subheader("Giới hạn của bản demo")
    st.markdown(
        "- Không coi mã băm hoặc Proof of Work là bảo mật tuyệt đối.\n"
        "- Phần đào chạy trong một tiến trình, độ khó thấp và không có mạng ngang hàng."
    )


def main() -> None:
    configure_logging()
    st.set_page_config(
        page_title="Giám sát và dự đoán phụ tải điện · Nhóm 17",
        page_icon=":material/electric_bolt:",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.html(BASE_CSS)
    if "chain" not in st.session_state:
        st.session_state.setdefault("chain", ProofOfWorkChain(difficulty=LIVE_DIFFICULTY))
    st.session_state.setdefault("prediction", None)
    st.session_state.setdefault("tamper", None)
    st.session_state.setdefault("sim", None)

    source_line = render_header()
    options = model_options()
    available = [option for option in options if option["available"]]
    unavailable = [option for option in options if not option["available"]]
    with st.expander(
        "Chọn bộ dữ liệu / tải CSV (không bắt buộc)",
        expanded=False,
        key="data_settings",
    ):
        dataset_label = st.selectbox("Bộ dữ liệu mẫu", list(DATASETS), key="dataset")
        uploaded_file = st.file_uploader(
            "Hoặc tải lên CSV của bạn",
            type=["csv"],
            key="uploaded_csv",
            help=f"Cần hai cột timestamp và consumption_kwh · tối đa {MAX_UPLOAD_MB} MB.",
        )
        model_choice = st.selectbox(
            "Mô hình dự đoán",
            [option["value"] for option in available],
            format_func=lambda value: next(
                option["label"] for option in options if option["value"] == value
            ),
            key="model_choice",
        )
        for option in unavailable:
            st.warning(f"{option['label']} chưa khả dụng: {option['detail']}")

    try:
        data = load_input_data(uploaded_file, dataset_label)
        forecast = run_forecast(data, FORECAST_HOURS, model_choice)
    except (OSError, ValueError, RuntimeError, pd.errors.ParserError) as exc:
        st.error(safe_error(exc, "Không thể xử lý dữ liệu đầu vào."))
        st.stop()

    source_label = (
        uploaded_file.name
        if uploaded_file is not None
        else f"Bộ dữ liệu mẫu {len(data):,} giờ"
    )
    source_line.markdown(f"Đề tài 17 · Smart Grid · {source_label}")
    saved = load_saved_metrics()
    default_dataset = uploaded_file is None and dataset_label == DEFAULT_DATASET_LABEL
    show_saved_metrics = default_dataset and saved is not None

    overview_tab, prediction_tab, blockchain_tab, consensus_tab, guide_tab = st.tabs(
        [
            "Tổng quan",
            "Dự đoán & ghi dữ liệu",
            "Blockchain",
            "Tấn công & đồng thuận",
            "Hướng dẫn demo",
        ],
        key="main_tabs",
    )
    with overview_tab:
        render_overview(
            data, forecast, model_choice, show_saved_metrics, saved, default_dataset
        )
    with prediction_tab:
        render_prediction(forecast)
    with blockchain_tab:
        render_blockchain()
    with consensus_tab:
        render_consensus(data, forecast)
    with guide_tab:
        render_guide(saved)


if __name__ == "__main__":
    main()
