"""Streamlit dashboard cho demo Smart Grid – Nhóm 17.

Đề tài: *Ứng dụng Trí tuệ nhân tạo (Machine Learning) và Blockchain bảo mật trong
Thành phố thông minh*. Phần được giao: ML cho Smart Grid và cơ chế đồng thuận
Blockchain chống giả mạo.

Ứng dụng gồm 5 tab, đi theo đúng luồng thuyết trình:

1. Tổng quan & ML    – dự đoán tiêu thụ điện bằng RandomForest, đối chiếu baseline.
2. Blockchain / Hash – chuỗi hash liên kết phát hiện sửa đổi dữ liệu.
3. Đồng thuận PoW    – đào khối Proof of Work, luật đồng thuận chuỗi nặng nhất,
                       mô phỏng tấn công 51%.
4. Dữ liệu           – bảng dữ liệu đầu vào và tải xuống.
5. Hướng dẫn demo    – kịch bản thuyết trình trước giảng viên.

Giao diện chỉ dùng thành phần gốc của Streamlit (không HTML/CSS trang trí); màu sắc và
kiểu chữ đặt trong ``.streamlit/config.toml``.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from blockchain.chain import IntegrityChain
from blockchain.consensus import MAX_DIFFICULTY, ProofOfWorkChain
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
    DEFAULT_DATASET_LABEL: ROOT
    / "data"
    / "power_consumption.csv",
    "sample_energy.csv – 8 giờ (dữ liệu minh họa nhỏ)": ROOT / "data" / "sample_energy.csv",
}
DEFAULT_CONSUMER_ID = "METER_001"

# Giá trị dùng cho kịch bản "dữ liệu bị sửa": đủ khác thực tế để mắt thường thấy ngay.
TAMPERED_KWH = 9999.0
BLOCK_VIEW_OPTIONS = (2, 4, 6)
DEFAULT_BLOCK_VIEW = 4


def render_header() -> None:
    """Tiêu đề + phạm vi đề tài, đủ ngắn để người xem nắm trong vài giây."""
    st.title("HỆ THỐNG GIÁM SÁT VÀ DỰ ĐOÁN PHỤ TẢI ĐIỆN")
    st.caption("Đề tài 17 – Smart Grid · Machine Learning kết hợp Blockchain")
    st.write(
        "RandomForest học từ dữ liệu tiêu thụ điện theo giờ để dự đoán phụ tải; "
        "chuỗi hash SHA-256 lưu vết dữ liệu và Proof of Work minh họa cơ chế đồng thuận."
    )


def render_section_heading(title: str, description: str, icon: str) -> None:
    st.subheader(title, icon=icon)
    st.caption(description)


# --------------------------------------------------------------------------- #
# Nạp dữ liệu mẫu (dữ liệu người dùng tải lên do security.py kiểm tra)
# --------------------------------------------------------------------------- #
@st.cache_data
def load_sample_data(path: str) -> pd.DataFrame:
    """Đọc bộ dữ liệu mẫu đã commit trong repository."""
    return pd.read_csv(path, parse_dates=["timestamp"])


@st.cache_data(show_spinner=False)
def run_forecast(data: pd.DataFrame, horizon: int, model: str) -> ForecastResult:
    """Gọi ``ml.predictor.predict_consumption`` và cache lại (đổi tham số mới tính lại)."""
    return predict_consumption(data, horizon=horizon, model=model)


def _format_metric(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _format_count(value: int | None) -> str:
    return "—" if value is None else f"{value:,}"


def _format_hash_rate(value: float) -> str:
    """Rút gọn tốc độ băm để không bị cắt chữ trong ô số liệu."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M H/s"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k H/s"
    return f"{value:,.0f} H/s"


def _short_hash(value: str, head: int = 10, tail: int = 6) -> str:
    if len(value) <= head + tail + 1:
        return value
    return f"{value[:head]}…{value[-tail:]}"


# --------------------------------------------------------------------------- #
# Tab 1 – Tổng quan & ML
# --------------------------------------------------------------------------- #
def render_overview(
    data: pd.DataFrame,
    forecast: ForecastResult,
    horizon: int,
    model_choice: str,
    show_saved_metrics: bool,
) -> None:
    latest = float(data["consumption_kwh"].iloc[-1])
    average = float(data["consumption_kwh"].mean())
    next_value = forecast.predictions[0]

    render_section_heading(
        "Dự đoán phụ tải",
        f"RandomForest được huấn luyện trên dữ liệu tiêu thụ theo giờ để dự đoán phụ tải "
        f"{horizon} giờ tiếp theo.",
        ":material/electric_bolt:",
    )
    st.caption(
        f"Đang dùng: **{forecast.model_name}** · Nguồn: {len(data):,} bản ghi theo giờ"
    )

    data_columns = st.columns(4, border=True)
    data_columns[0].metric("Bản ghi dữ liệu", f"{len(data):,}")
    data_columns[1].metric("Điện năng hiện tại", f"{latest:.2f} kWh")
    data_columns[2].metric("Trung bình toàn bộ", f"{average:.2f} kWh")
    data_columns[3].metric("Dự đoán giờ kế tiếp", f"{next_value:.2f} kWh")

    quality_columns = st.columns(4, border=True)
    if model_choice == MODE_LINEAR:
        quality_columns[0].metric("MAE (kWh)", _format_metric(forecast.mae))
        quality_columns[1].metric("RMSE (kWh)", "—")
        quality_columns[2].metric("R²", "—")
        quality_columns[3].metric("Bản ghi kiểm tra", "—")
        st.caption(forecast.metrics_source)
    elif show_saved_metrics:
        quality_columns[0].metric("MAE (kWh)", _format_metric(forecast.mae))
        quality_columns[1].metric("RMSE (kWh)", _format_metric(forecast.rmse))
        quality_columns[2].metric("R²", _format_metric(forecast.r2, digits=4))
        quality_columns[3].metric("Bản ghi kiểm tra", _format_count(_saved_test_size()))
        st.caption(f"Nguồn chỉ số: {forecast.metrics_source}")
    else:
        for column, label in zip(
            quality_columns, ("MAE (kWh)", "RMSE (kWh)", "R²", "Bản ghi kiểm tra")
        ):
            column.metric(label, "—")
        st.caption(
            "Chưa có chỉ số đánh giá RandomForest cho bộ dữ liệu đang chọn; "
            "metrics hiển thị ở đây chỉ áp dụng cho bộ dữ liệu huấn luyện mặc định."
        )
    if forecast.note:
        st.caption(forecast.note)
    if forecast.fallback_reason:
        st.warning(
            "Đang dùng baseline thay cho RandomForest. Lý do: "
            f"{forecast.fallback_reason}"
        )

    with st.container(border=True):
        st.markdown("**Phụ tải lịch sử**")
        st.line_chart(
            data.set_index("timestamp")["consumption_kwh"],
            height=340,
            alt="Biểu đồ phụ tải lịch sử theo giờ",
        )

    chart_column, table_column = st.columns([1.5, 1], gap="medium")
    with chart_column:
        with st.container(border=True):
            st.markdown(f"**Dự báo {horizon} giờ tiếp theo**")
            if forecast.future_timestamps:
                forecast_frame = pd.DataFrame(
                    {"consumption_kwh": forecast.predictions},
                    index=pd.to_datetime(pd.Series(forecast.future_timestamps)),
                )
                st.line_chart(
                    forecast_frame,
                    height=240,
                    alt="Biểu đồ dự báo phụ tải",
                )
            else:
                st.write([round(value, 2) for value in forecast.predictions])
    with table_column:
        with st.container(border=True):
            st.markdown("**Bảng dự báo**")
            if forecast.future_timestamps:
                st.dataframe(
                    pd.DataFrame(
                        {
                            "thời điểm": forecast.future_timestamps,
                            "dự đoán (kWh)": [round(value, 2) for value in forecast.predictions],
                        }
                    ),
                    width="stretch",
                    hide_index=True,
                    height=240,
                    alt="Bảng dự báo tiêu thụ điện theo giờ",
                )
            else:
                st.write("Dữ liệu không có cột timestamp nên không hiển thị được mốc thời gian.")

    render_model_comparison(forecast, show_saved_metrics)

    if forecast.fitted is not None and len(forecast.fitted) == len(data):
        with st.expander(
            "Đối chiếu giá trị thực tế và mô hình (in-sample)", icon=":material/compare_arrows:"
        ):
            st.caption(
                "Giá trị mô hình ở đây là dự đoán **trên chính dữ liệu đã dùng để huấn luyện** "
                "nên lạc quan hơn chỉ số ở bảng trên (chỉ số ở trên tính trên tập kiểm tra)."
            )
            st.line_chart(
                pd.DataFrame(
                    {
                        "Thực tế": data["consumption_kwh"].to_numpy(),
                        "Mô hình": forecast.fitted,
                    },
                    index=data["timestamp"],
                ),
                height=280,
                alt="So sánh giá trị tiêu thụ thực tế và giá trị mô hình",
            )


def _saved_test_size() -> int | None:
    saved = load_saved_metrics() or {}
    return saved.get("n_test")


def render_model_comparison(forecast: ForecastResult, show_saved_metrics: bool) -> None:
    """So sánh RandomForest với baseline trên **cùng một tập kiểm tra**.

    Số liệu lấy từ ``ml/metrics.json`` (do ``ml/train_model.py`` sinh ra), không nhập tay.
    """
    if not show_saved_metrics:
        st.caption(
            "Bảng so sánh chỉ áp dụng cho bộ dữ liệu huấn luyện mặc định "
            "(720 bản ghi); không dùng metrics mặc định cho dữ liệu đang chọn."
        )
        return

    saved = load_saved_metrics()
    if not saved or saved.get("mae") is None:
        st.caption(
            "Chưa có `ml/metrics.json` nên không có bảng so sánh. "
            "Chạy `ml/train_model.py` để sinh chỉ số."
        )
        return

    with st.container(border=True):
        st.markdown("**So sánh mô hình trên cùng tập kiểm tra**")
        comparison = pd.DataFrame(
            [
                {
                    "Mô hình": f"RandomForest ({saved.get('n_estimators', 100)} cây)",
                    "MAE (kWh)": saved.get("mae"),
                    "RMSE (kWh)": saved.get("rmse"),
                    "R²": saved.get("r2"),
                },
                {
                    "Mô hình": saved.get("baseline_linear_name") or "Ngoại suy tuyến tính 1 bước",
                    "MAE (kWh)": saved.get("baseline_linear_mae"),
                    "RMSE (kWh)": saved.get("baseline_linear_rmse"),
                    "R²": saved.get("baseline_linear_r2"),
                },
            ]
        )
        st.dataframe(comparison, width="stretch", hide_index=True, alt="Bảng so sánh mô hình")
        st.caption(
            f"Tập kiểm tra {saved.get('n_test')} bản ghi "
            f"({_short_time(saved.get('test_start'))} → {_short_time(saved.get('test_end'))}), "
            f"{saved.get('n_train')} bản ghi để huấn luyện. "
            "Các số baseline trong bảng này cũng được tính trên tập kiểm tra 20%; "
            "MAE baseline ở KPI khi chọn baseline là backtest trên toàn bộ dữ liệu đầu vào. "
            "RandomForest dùng đặc trưng thời gian nên học được quy luật giờ/thứ; "
            "ngoại suy tuyến tính chỉ kéo dài xu hướng nên sai số lớn hơn nhiều."
        )
        if forecast.model_name != saved.get("model_name"):
            st.caption(
                "Bảng này luôn so trên mô hình đã huấn luyện sẵn trong `ml/model.pkl`, "
                "không phụ thuộc mô hình đang chọn ở thanh bên."
            )


def _short_time(value: str | None) -> str:
    return (value or "—").replace("T", " ")[:16]


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


def render_block_cards(chain: IntegrityChain, displayed: int, broken_index: int | None) -> None:
    """Vẽ các block đầu tiên thành thẻ: dữ liệu, hash, previous_hash."""
    blocks = chain.blocks[:displayed]
    for row_start in range(0, len(blocks), 2):
        columns = st.columns(2)
        for column, block in zip(columns, blocks[row_start : row_start + 2]):
            with column, st.container(border=True):
                damaged = broken_index is not None and block.index == broken_index
                mark = "❌ hash không khớp" if damaged else "✅ hash khớp"
                st.markdown(f"**Block #{block.index}** · {mark}")
                st.caption(
                    f"timestamp: {block.payload.get('timestamp', '—')} · "
                    f"consumption_kwh: {block.payload.get('consumption_kwh', '—')}"
                )
                st.caption("hash")
                st.code(block.hash, language=None, wrap_lines=True)
                st.caption("previous_hash")
                st.code(block.previous_hash, language=None, wrap_lines=True)


def render_integrity(data: pd.DataFrame, tamper_demo: bool) -> None:
    render_section_heading(
        "Kiểm tra tính toàn vẹn dữ liệu",
        "Mỗi bản ghi được băm SHA-256 kèm hash của block trước; sửa dữ liệu là hash lệch ngay.",
        ":material/fingerprint:",
    )
    chain = build_chain(data)
    if tamper_demo and chain.blocks:
        chain.tamper_block(0, "consumption_kwh", TAMPERED_KWH)

    is_valid = chain.is_valid()
    broken_index = chain.invalid_index()

    status_columns = st.columns(3, border=True)
    status_columns[0].metric("Số block", f"{len(chain.blocks):,}")
    status_columns[1].metric("Block bị sửa", "—" if broken_index is None else f"#{broken_index}")
    status_columns[2].metric("Trạng thái", "Hợp lệ" if is_valid else "Bị sửa")

    if is_valid:
        st.success("✅ Dữ liệu hợp lệ: hash của mọi block khớp với dữ liệu đã ghi.")
    else:
        st.error(
            f"❌ Phát hiện dữ liệu bị thay đổi: Block #{broken_index} có hash không khớp "
            "với nội dung đang lưu. Đây là kịch bản mô phỏng để minh họa."
        )

    view_columns = st.columns([1, 2], vertical_alignment="bottom")
    with view_columns[0]:
        displayed = st.segmented_control(
            "Số block hiển thị",
            options=list(BLOCK_VIEW_OPTIONS),
            default=DEFAULT_BLOCK_VIEW,
            key="hash_block_view",
            help="Chuỗi hash có một block cho mỗi bản ghi; ở đây chỉ xem các block đầu.",
        )
    with view_columns[1]:
        if len(chain.blocks) > (displayed or DEFAULT_BLOCK_VIEW):
            st.caption(
                f"Đang xem {displayed or DEFAULT_BLOCK_VIEW}/{len(chain.blocks):,} block đầu tiên. "
                "Bảng đầy đủ nằm trong mục bên dưới."
            )
    render_block_cards(chain, int(displayed or DEFAULT_BLOCK_VIEW), broken_index)

    if chain.blocks:
        with st.container(border=True):
            st.markdown("**Hash của block cuối chuỗi**")
            st.code(chain.blocks[-1].hash, language=None)

    with st.expander(f"Bảng đầy đủ {len(chain.blocks):,} block", icon=":material/table_chart:"):
        st.dataframe(
            chain.to_frame(),
            width="stretch",
            hide_index=True,
            height=420,
            alt="Bảng toàn bộ block trong chuỗi hash",
        )

    st.caption(
        "Chuỗi hash chỉ **phát hiện** sửa đổi. Nếu kẻ tấn công sửa dữ liệu rồi đào lại toàn bộ "
        "chuỗi thì hash sẽ khớp trở lại — khi đó phải dùng luật đồng thuận ở tab "
        "**Đồng thuận PoW**."
    )


# --------------------------------------------------------------------------- #
# Tab 3 – Đồng thuận Proof of Work
# --------------------------------------------------------------------------- #
def build_mining_records(
    data: pd.DataFrame,
    forecast: ForecastResult,
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


def render_chain_card(
    chain: ProofOfWorkChain, title: str, chosen: bool, target_block: int
) -> None:
    """Thẻ tóm tắt một chuỗi trong phần so sánh đồng thuận."""
    with st.container(border=True):
        st.markdown(f"**{title}**" + (" — được chọn" if chosen else ""))
        columns = st.columns(3)
        columns[0].metric("Số block", f"{len(chain.blocks)}")
        columns[1].metric("Tổng công", f"{chain.cumulative_work:,}")
        columns[2].metric("Hợp lệ", "Có" if chain.is_valid() else "Không")
        st.caption(
            f"Tổng nonce {chain.total_nonce:,} · đào {chain.total_mine_seconds:.3f} s · "
            f"dữ liệu tại block bị sửa: "
            f"{chain.blocks[target_block].payload.get('actual_usage_kwh', '—')} kWh"
        )


def render_consensus(
    records: pd.DataFrame,
    difficulty: int,
    tamper_demo: bool,
    attacker_demo: bool,
    forged_value: float,
    extra_blocks: int,
) -> None:
    render_section_heading(
        "Đồng thuận Proof of Work",
        "Block chỉ được chấp nhận khi tìm được nonce tạo ra hash bắt đầu bằng số 0 theo độ khó.",
        ":material/account_tree:",
    )
    st.caption(
        "Mô phỏng chạy trong một tiến trình (độ khó thấp, không có mạng P2P) để minh họa cơ chế "
        "đào và luật chọn chuỗi. Mỗi block lưu một bản ghi điện năng gồm **số thực tế** và "
        "**số mô hình ML dự đoán**."
    )

    chain = mine_chain(records, difficulty)
    if tamper_demo and len(chain.blocks) > 1:
        chain = chain.clone()
        chain.tamper_block(1, "actual_usage_kwh", forged_value)

    summary = chain.summary()
    columns = st.columns(5, border=True)
    columns[0].metric("Số block", f"{summary['blocks']}")
    columns[1].metric("Độ khó", f"{summary['difficulty']} số 0")
    columns[2].metric("Tổng nonce", f"{summary['total_nonce']:,}")
    columns[3].metric("Thời gian đào", f"{summary['total_mine_seconds']:.2f} s")
    columns[4].metric("Tốc độ băm", _format_hash_rate(summary["hash_rate"]))
    st.caption(
        f"Đo thực tế: {summary['total_attempts']:,} phép băm cho {summary['blocks']} block "
        f"trong {summary['total_mine_seconds']:.3f} s "
        f"({summary['hash_rate']:,.0f} H/s). Nonce là số phải thử để hash đạt độ khó."
    )

    if summary["valid"]:
        st.success("Chuỗi hợp lệ: mọi block khớp hash, nonce đạt độ khó và liên kết đúng.")
    else:
        st.error(f"Chuỗi KHÔNG hợp lệ: {summary['error']}")

    with st.container(border=True):
        st.markdown("**Bảng block**")
        st.dataframe(
            chain.to_frame(),
            width="stretch",
            hide_index=True,
            height="auto",
            alt="Bảng block Proof of Work",
        )
        last = chain.blocks[-1]
        st.caption(
            f"Block cuối #{last.index}: nonce = {last.nonce:,} · hash = {_short_hash(last.hash)} · "
            f"previous_hash = {_short_hash(last.previous_hash)}"
        )

    st.markdown("#### Luật đồng thuận: chuỗi nặng nhất thắng")
    st.write(
        "Kịch bản: kẻ tấn công sửa số điện tiêu thụ của một block rồi **đào lại** block đó và "
        "phần đuôi của chuỗi, sau đó đào thêm khối mới. Nhánh của kẻ tấn công vẫn hợp lệ về hash "
        "— vì vậy chỉ kiểm tra hash là không đủ, phải so **tổng công** giữa các nút."
    )

    if not attacker_demo:
        st.info(
            "Bật **Mô phỏng kẻ tấn công đào lại** ở thanh bên để chạy so sánh hai chuỗi."
        )
        return

    target_block = 1 if len(records) > 1 else 0
    honest, attacker = build_attacker_chain(
        records, difficulty, target_block, forged_value, extra_blocks
    )
    winner, reason = ProofOfWorkChain.resolve_conflict([honest, attacker])

    comparison_columns = st.columns(2, gap="medium")
    with comparison_columns[0]:
        render_chain_card(honest, "Chuỗi trung thực", winner is honest, target_block)
    with comparison_columns[1]:
        render_chain_card(
            attacker, "Chuỗi tấn công (đã đào lại)", winner is attacker, target_block
        )

    honest_work = honest.cumulative_work
    attacker_work = attacker.cumulative_work
    if winner is None:
        st.error(reason)
    elif winner is honest:
        st.success(
            f"Kết luận: giữ chuỗi của nút trung thực — tổng công {honest_work:,} "
            f"so với {attacker_work:,} của chuỗi tấn công."
        )
        if attacker_work == honest_work:
            st.caption(
                f"Hai chuỗi hòa tổng công ({honest_work}) và hòa độ dài "
                f"({len(honest.blocks)} block) nên giữ chuỗi đến trước. Tăng "
                "**Số khối đào vượt thêm** lên 1–3 để thấy kẻ tấn công chiếm ưu thế."
            )
        else:
            st.caption(
                "Nhánh đào lại của kẻ tấn công không nặng hơn chuỗi trung thực nên "
                "không được các nút chấp nhận."
            )
    else:
        st.error(
            f"Kết luận: nút tấn công thắng — tổng công {attacker_work:,} lớn hơn "
            f"{honest_work:,} của chuỗi trung thực."
        )
        st.caption(
            "Theo luật chuỗi nặng nhất, dữ liệu giả của kẻ tấn công được chấp nhận. "
            "Đây là mô phỏng tấn công 51% để thấy giới hạn của Proof of Work, không phải "
            "khẳng định bảo mật tuyệt đối."
        )

    with st.expander("Bảng so sánh chi tiết hai chuỗi", icon=":material/table_chart:"):
        st.caption(f"Luật đồng thuận áp dụng: {reason}")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Chuỗi": "Nút trung thực",
                        "Hợp lệ": honest.is_valid(),
                        "Số block": len(honest.blocks),
                        "Tổng công": honest.cumulative_work,
                        "Tổng nonce": honest.total_nonce,
                        "actual_usage_kwh tại block bị sửa": honest.blocks[
                            target_block
                        ].payload.get("actual_usage_kwh"),
                    },
                    {
                        "Chuỗi": "Nút tấn công (đã đào lại)",
                        "Hợp lệ": attacker.is_valid(),
                        "Số block": len(attacker.blocks),
                        "Tổng công": attacker.cumulative_work,
                        "Tổng nonce": attacker.total_nonce,
                        "actual_usage_kwh tại block bị sửa": attacker.blocks[
                            target_block
                        ].payload.get("actual_usage_kwh"),
                    },
                ]
            ),
            width="stretch",
            hide_index=True,
            alt="So sánh chuỗi trung thực và chuỗi tấn công",
        )


# --------------------------------------------------------------------------- #
# Tab 5 – Kịch bản thuyết trình
# --------------------------------------------------------------------------- #
def render_guide() -> None:
    render_section_heading(
        "Kịch bản thuyết trình",
        "Sáu bước bấm máy liên tục, đi từ dự báo đến kiểm chứng và giới hạn bảo mật.",
        ":material/slideshow:",
    )
    steps = [
        (
            "1",
            "Tổng quan & ML",
            "Tab **Tổng quan & ML**: nêu dữ liệu 720 giờ, mô hình RandomForest và dự báo 6 giờ tới.",
        ),
        (
            "2",
            "So sánh với baseline",
            "Cùng tab, xem bảng **So sánh mô hình trên cùng tập kiểm tra** "
            "(RandomForest MAE 0,20 so với baseline 1,23).",
        ),
        (
            "3",
            "Kiểm tra hash",
            "Tab **Blockchain / Hash**: xem hash từng block, rồi bật "
            "**Mô phỏng dữ liệu bị sửa** để thấy trạng thái bị sửa, sau đó tắt lại.",
        ),
        (
            "4",
            "Proof of Work",
            "Tab **Đồng thuận PoW**: giải thích nonce, độ khó, thời gian đào, tốc độ băm.",
        ),
        (
            "5",
            "Tấn công 51%",
            "Cùng tab: bật **Mô phỏng kẻ tấn công đào lại**, để *số khối đào vượt thêm* = 0 "
            "(trung thực thắng) rồi = 2 (tấn công thắng).",
        ),
        (
            "6",
            "Kết luận",
            "Chốt: ML dự báo phụ tải; chuỗi hash phát hiện sửa đổi; PoW cộng luật chuỗi nặng "
            "nhất mới chống sửa đổi — và vẫn có giới hạn khi kẻ tấn công nắm đa số năng lực đào.",
        ),
    ]
    for number, title, detail in steps:
        with st.container(border=True):
            left, right = st.columns([0.08, 0.92], vertical_alignment="center")
            left.markdown(f"**{number}**")
            right.markdown(f"**{title}**  \n{detail}")

    st.warning(
        "Không trình bày hash/PoW là bảo mật tuyệt đối. Chuỗi hash phát hiện sửa đổi; "
        "PoW cộng luật đồng thuận chống sửa đổi khi kẻ tấn công không nắm đa số năng lực đào. "
        "Toàn bộ phần đào khối ở đây là mô phỏng trong một tiến trình, độ khó rất thấp và "
        "không có mạng P2P."
    )
    st.info(
        "Huấn luyện lại mô hình: `.\\.venv\\Scripts\\python.exe ml\\train_model.py` "
        "(sinh lại `ml/model.pkl` và `ml/metrics.json`)."
    )


# --------------------------------------------------------------------------- #
# Giao diện chính
# --------------------------------------------------------------------------- #
def render_sidebar() -> dict[str, object]:
    """Khu điều khiển chia theo nhóm Dữ liệu / Mô hình / Mô phỏng Blockchain."""
    options = model_options()
    available = [option for option in options if option["available"]]
    unavailable = [option for option in options if not option["available"]]

    with st.sidebar:
        st.header("Điều khiển demo", icon=":material/tune:")
        st.caption("Tham số áp dụng cho cả 5 tab trong cùng một phiên.")

        st.subheader("Dữ liệu", divider="gray")
        dataset_label = st.selectbox("Bộ dữ liệu mẫu", list(DATASETS.keys()), key="dataset")
        uploaded_file = st.file_uploader(
            "Hoặc tải lên CSV của bạn",
            type=["csv"],
            help=f"Cần hai cột timestamp và consumption_kwh · tối đa {MAX_UPLOAD_MB} MB.",
        )

        st.subheader("Mô hình", divider="gray")
        model_choice = st.selectbox(
            "Mô hình dự đoán",
            [option["value"] for option in available],
            format_func=lambda value: next(
                option["label"] for option in options if option["value"] == value
            ),
            key="model_choice",
        )
        horizon = st.slider("Số giờ dự đoán", min_value=1, max_value=12, value=6, key="horizon")

        st.subheader("Mô phỏng Blockchain", divider="gray")
        tamper_demo = st.toggle(
            "Mô phỏng dữ liệu bị sửa",
            value=False,
            key="tamper_demo",
            help="Sửa một giá trị điện năng đã ghi để thấy chuỗi hash báo sai.",
        )
        difficulty = st.select_slider(
            "Độ khó đào (số số 0 đầu hash)",
            options=list(range(1, MAX_DIFFICULTY + 1)),
            value=2,
            key="difficulty",
        )
        block_count = st.slider(
            "Số block đào từ dữ liệu", min_value=3, max_value=12, value=6, key="block_count"
        )
        consumer_id = st.text_input(
            "Mã đồng hồ (consumer_id)", value=DEFAULT_CONSUMER_ID, key="consumer_id"
        )
        attacker_demo = st.toggle(
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
            "Số khối đào vượt thêm",
            min_value=0,
            max_value=3,
            value=0,
            key="extra_blocks",
            help="0 = hòa tổng công (nút trung thực thắng); từ 1 trở lên = mô phỏng tấn công 51%.",
        )

        for option in unavailable:
            st.warning(f"{option['label']} chưa khả dụng: {option['detail']}")

    return {
        "dataset_label": dataset_label,
        "uploaded_file": uploaded_file,
        "model_choice": model_choice,
        "horizon": horizon,
        "tamper_demo": tamper_demo,
        "difficulty": difficulty,
        "block_count": block_count,
        "consumer_id": consumer_id,
        "attacker_demo": attacker_demo,
        "forged_value": forged_value,
        "extra_blocks": extra_blocks,
    }


def load_input_data(uploaded_file, dataset_label: str) -> pd.DataFrame:
    """Đọc dữ liệu mẫu hoặc file người dùng tải lên (đã qua kiểm tra của security.py)."""
    if uploaded_file is not None:
        # Mục 7 & 8 của checklist: chặn sai định dạng / quá dung lượng trước khi đọc nội dung.
        validate_upload(uploaded_file.name, uploaded_file.size)
        raw_data = read_uploaded_csv(uploaded_file.getvalue())
    else:
        raw_data = load_sample_data(str(DATASETS[dataset_label]))
    return prepare_data(raw_data)


def main() -> None:
    configure_logging()
    st.set_page_config(
        page_title="Giám sát và dự đoán phụ tải điện · Nhóm 17",
        page_icon=":material/electric_bolt:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    render_header()

    controls = render_sidebar()
    horizon = int(controls["horizon"])
    uploaded_file = controls["uploaded_file"]
    dataset_label = str(controls["dataset_label"])

    try:
        data = load_input_data(uploaded_file, dataset_label)
        forecast = run_forecast(data, horizon, str(controls["model_choice"]))
    except (OSError, ValueError, RuntimeError, pd.errors.ParserError) as exc:
        # Mục 6 của checklist: giao diện chỉ thấy thông báo an toàn; chi tiết nằm trong log.
        st.error(safe_error(exc, "Không thể xử lý dữ liệu đầu vào."))
        st.stop()

    source_label = "file CSV vừa tải lên" if uploaded_file is not None else dataset_label
    st.caption(f"Nguồn dữ liệu: {source_label}")
    show_saved_metrics = uploaded_file is None and dataset_label == DEFAULT_DATASET_LABEL

    mining_records = build_mining_records(
        data, forecast, int(controls["block_count"]), str(controls["consumer_id"])
    )

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
        render_overview(
            data,
            forecast,
            horizon,
            str(controls["model_choice"]),
            show_saved_metrics,
        )
    with integrity_tab:
        render_integrity(data, bool(controls["tamper_demo"]))
    with consensus_tab:
        render_consensus(
            mining_records,
            int(controls["difficulty"]),
            bool(controls["tamper_demo"]),
            bool(controls["attacker_demo"]),
            float(controls["forged_value"]),
            int(controls["extra_blocks"]),
        )
    with data_tab:
        render_section_heading(
            "Dữ liệu đầu vào",
            "Kiểm tra dữ liệu đã làm sạch trước khi đưa sang ML và Blockchain.",
            ":material/table_chart:",
        )
        with st.container(border=True):
            st.markdown("**Bảng dữ liệu đầu vào**")
            st.dataframe(
                data,
                width="stretch",
                hide_index=True,
                height=380,
                alt="Bảng dữ liệu đầu vào đã làm sạch",
            )
        with st.container(border=True):
            st.markdown("**Bản ghi sẽ ghi vào Blockchain**")
            st.caption(
                "Mỗi dòng thành một block: mã đồng hồ, thời điểm, số thực tế và số mô hình "
                "ML dự đoán cho đúng thời điểm đó."
            )
            st.dataframe(
                mining_records,
                width="stretch",
                hide_index=True,
                height=280,
                alt="Bảng bản ghi chuẩn bị ghi vào Blockchain",
            )
            st.download_button(
                "Tải dữ liệu đã làm sạch",
                data.to_csv(index=False).encode("utf-8"),
                file_name="smart_grid_cleaned.csv",
                mime="text/csv",
                icon=":material/download:",
            )
    with guide_tab:
        render_guide()


if __name__ == "__main__":
    main()
