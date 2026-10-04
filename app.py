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
from security import (
    MAX_UPLOAD_MB,
    UserInputError,
    configure_logging,
    prepare_data,
    safe_error,
    validate_upload,
)

ROOT = Path(__file__).parent
DATASETS = {
    "power_consumption.csv · 30 ngày / 720 giờ (dữ liệu huấn luyện ML)": ROOT
    / "data"
    / "power_consumption.csv",
    "sample_energy.csv · 8 giờ (dữ liệu minh họa nhỏ)": ROOT / "data" / "sample_energy.csv",
}
DEFAULT_CONSUMER_ID = "METER_001"


def inject_styles() -> None:
    """Visual layer only: keep the Streamlit dashboard readable and scannable."""
    st.markdown(
        """
        <style>
        :root {
            --sg-bg: #0f172a;
            --sg-surface: #182235;
            --sg-surface-soft: #202b40;
            --sg-border: rgba(148, 163, 184, .22);
            --sg-text: #f8fafc;
            --sg-muted: #94a3b8;
            --sg-accent: #22c55e;
            --sg-accent-soft: rgba(34, 197, 94, .14);
            --sg-danger: #f87171;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 88% 0%, rgba(34, 197, 94, .09), transparent 28rem),
                var(--sg-bg);
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] {
            background: #111c31;
            border-right: 1px solid var(--sg-border);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label { color: #cbd5e1; }
        .block-container { max-width: 1480px; padding-top: 2.4rem; padding-bottom: 3rem; }

        .sg-hero {
            position: relative;
            overflow: hidden;
            padding: 1.5rem 1.7rem;
            margin: 0 0 1.25rem;
            border: 1px solid var(--sg-border);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(30, 41, 59, .96), rgba(24, 34, 53, .82));
            box-shadow: 0 18px 45px rgba(2, 6, 23, .22);
        }
        .sg-hero::after {
            content: "";
            position: absolute;
            width: 17rem;
            height: 17rem;
            right: -6rem;
            top: -9rem;
            border-radius: 50%;
            background: rgba(34, 197, 94, .12);
            filter: blur(8px);
        }
        .sg-eyebrow, .sg-meta, .sg-sidebar-kicker {
            color: var(--sg-muted);
            font-size: .73rem;
            font-weight: 700;
            letter-spacing: .12em;
            text-transform: uppercase;
        }
        .sg-eyebrow { display: flex; align-items: center; gap: .5rem; }
        .sg-dot {
            display: inline-block;
            width: .5rem;
            height: .5rem;
            border-radius: 50%;
            background: var(--sg-accent);
            box-shadow: 0 0 0 .25rem var(--sg-accent-soft);
        }
        .sg-hero h1 {
            position: relative;
            z-index: 1;
            margin: .6rem 0 .35rem;
            color: var(--sg-text);
            font-size: clamp(2rem, 4vw, 3.35rem);
            letter-spacing: -.045em;
            line-height: 1.02;
        }
        .sg-hero h1 span { color: var(--sg-accent); }
        .sg-hero p {
            position: relative;
            z-index: 1;
            max-width: 48rem;
            margin: 0;
            color: #cbd5e1;
            font-size: .98rem;
            line-height: 1.65;
        }
        .sg-meta { position: relative; z-index: 1; display: flex; gap: .75rem; flex-wrap: wrap; margin-top: 1.1rem; }
        .sg-meta span { padding: .38rem .62rem; border: 1px solid var(--sg-border); border-radius: 999px; background: rgba(15, 23, 42, .45); letter-spacing: .04em; }

        [data-testid="stMetric"] {
            min-height: 7.2rem;
            padding: 1rem 1.05rem;
            border: 1px solid var(--sg-border);
            border-radius: 14px;
            background: rgba(24, 34, 53, .78);
        }
        [data-testid="stMetricLabel"] { color: var(--sg-muted); }
        [data-testid="stMetricValue"] { color: var(--sg-text); }
        [data-testid="stMetricDelta"] { color: var(--sg-accent); }

        [data-testid="stTabs"] button { color: var(--sg-muted); font-weight: 650; }
        [data-testid="stTabs"] button[aria-selected="true"] { color: var(--sg-accent); }
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: var(--sg-accent); }
        [data-testid="stDataFrame"] { border: 1px solid var(--sg-border); border-radius: 12px; overflow: hidden; }
        [data-testid="stExpander"] { border-color: var(--sg-border); border-radius: 12px; background: rgba(24, 34, 53, .42); }
        [data-testid="stDownloadButton"] button, [data-testid="stButton"] button { border-radius: 9px; }
        code { color: #86efac; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <section class="sg-hero" aria-label="Smart Grid Monitor">
            <div class="sg-eyebrow"><span class="sg-dot"></span> Smart city / operations lab</div>
            <h1>Smart Grid <span>Monitor</span></h1>
            <p>Giám sát phụ tải điện bằng Machine Learning và kiểm chứng dữ liệu bằng Blockchain — một dashboard demo cho Nhóm 17.</p>
            <div class="sg-meta">
                <span>ML forecasting</span><span>SHA-256 integrity</span><span>Proof of Work</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
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


# --------------------------------------------------------------------------- #
# Tab 1 – Tổng quan & ML
# --------------------------------------------------------------------------- #
def render_overview(data: pd.DataFrame, forecast, horizon: int) -> None:
    latest = float(data["consumption_kwh"].iloc[-1])
    average = float(data["consumption_kwh"].mean())
    next_value = forecast.predictions[0]

    render_section_heading(
        "Tín hiệu phụ tải điện",
        f"{len(data):,} bản ghi theo giờ · mô hình đang dùng: {forecast.model_name}",
        ":material/electric_bolt:",
    )
    metric_columns = st.columns(4, border=True)
    metric_columns[0].metric("Bản ghi gần nhất", f"{latest:.2f} kWh")
    metric_columns[1].metric("Trung bình dữ liệu", f"{average:.2f} kWh")
    metric_columns[2].metric("Dự đoán giờ kế tiếp", f"{next_value:.2f} kWh")
    metric_columns[3].metric("MAE (kWh)", _format_metric(forecast.mae))

    chart_col, forecast_col = st.columns([1.6, 1], gap="large")
    with chart_col:
        with st.container(border=True):
            st.markdown("**Lịch sử tiêu thụ**")
            st.line_chart(
                data.set_index("timestamp")["consumption_kwh"],
                height=320,
                alt="Biểu đồ lịch sử tiêu thụ điện theo giờ",
            )

    with forecast_col:
        with st.container(border=True):
            st.markdown(f"**Dự báo {horizon} giờ tiếp theo**")
            if forecast.future_timestamps:
                forecast_frame = pd.DataFrame(
                    {"consumption_kwh": forecast.predictions},
                    index=pd.to_datetime(pd.Series(forecast.future_timestamps)),
                )
                st.line_chart(
                    forecast_frame,
                    height=150,
                    alt="Biểu đồ dự báo tiêu thụ điện",
                )
                st.dataframe(
                    pd.DataFrame(
                        {
                            "thời điểm": forecast.future_timestamps,
                            "dự đoán (kWh)": [round(value, 2) for value in forecast.predictions],
                        }
                    ),
                    width="stretch",
                    hide_index=True,
                    height=230,
                    alt="Bảng dự báo tiêu thụ điện",
                )
            else:
                st.write([round(value, 2) for value in forecast.predictions])

    with st.container(border=True):
        st.markdown("**Chất lượng mô hình**")
        quality = st.columns(3)
        quality[0].metric("RMSE (kWh)", _format_metric(forecast.rmse))
        quality[1].metric("R²", _format_metric(forecast.r2, digits=4))
        quality[2].metric("Số bản ghi", f"{len(data):,}")

    st.caption(f"Nguồn chỉ số: {forecast.metrics_source}")
    if forecast.note:
        st.caption(forecast.note)
    if forecast.fallback_reason:
        st.warning(
            "Đang dùng baseline thay cho RandomForest. Lý do: "
            f"{forecast.fallback_reason}"
        )

    if forecast.fitted is not None and len(forecast.fitted) == len(data):
        with st.expander("Đối chiếu giá trị thực tế và mô hình", icon=":material/compare_arrows:"):
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

    saved = load_saved_metrics()
    if saved:
        with st.expander("Chi tiết huấn luyện", icon=":material/model_training:"):
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
    render_section_heading(
        "Tính toàn vẹn dữ liệu",
        "SHA-256 tạo dấu vết bất biến cho từng bản ghi và phát hiện thay đổi trái phép.",
        ":material/fingerprint:",
    )
    chain = build_chain(data)
    if tamper_demo and chain.blocks:
        chain.tamper_block(0, "consumption_kwh", 9999.0)

    is_valid = chain.is_valid()
    status_left, status_right = st.columns(2, border=True)
    status_left.metric("Số block", len(chain.blocks))
    status_right.metric("Trạng thái", "HỢP LỆ" if is_valid else "ĐÃ BỊ SỬA")

    if is_valid:
        st.success("Chuỗi hash hợp lệ: dữ liệu khớp với các mã băm đã lưu.")
    else:
        st.error(
            "Phát hiện dữ liệu không khớp hash. Đây là mô phỏng thay đổi dữ liệu để minh họa."
        )

    if chain.blocks:
        with st.container(border=True):
            st.markdown("**Hash của block cuối**")
            st.code(chain.blocks[-1].hash)
    with st.container(border=True):
        st.dataframe(
            chain.to_frame(),
            width="stretch",
            hide_index=True,
            height=440,
            alt="Bảng các block trong chuỗi hash",
        )
    st.caption(
        "Chuỗi hash chỉ phát hiện sửa đổi. Nếu kẻ tấn công đào lại từ block bị sửa, "
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
    render_section_heading(
        "Proof of Work và đồng thuận",
        "Đào block, kiểm tra nonce và chọn chuỗi hợp lệ có tổng công lớn nhất.",
        ":material/account_tree:",
    )
    st.caption(
        "Mỗi block lưu một bản ghi điện năng gồm **số thực tế** và **số mô hình ML dự đoán**; "
        "block chỉ được chấp nhận khi hash bắt đầu bằng chuỗi số 0 theo độ khó đã chọn."
    )

    chain = mine_chain(records, difficulty)
    if tamper_demo and len(chain.blocks) > 1:
        chain = chain.clone()
        chain.tamper_block(1, "actual_usage_kwh", forged_value)

    summary = chain.summary()
    columns = st.columns(5, border=True)
    columns[0].metric("Số block", summary["blocks"])
    columns[1].metric("Độ khó", summary["difficulty"])
    columns[2].metric("Tổng nonce", f"{summary['total_nonce']:,}")
    columns[3].metric("Thời gian đào", f"{summary['total_mine_seconds']:.2f} s")
    columns[4].metric("Tốc độ băm", f"{summary['hash_rate']:,.0f} H/s")

    if summary["valid"]:
        st.success("Chuỗi hợp lệ: mọi block khớp hash, nonce đạt độ khó và liên kết đúng.")
    else:
        st.error(f"Chuỗi KHÔNG hợp lệ: {summary['error']}")

    with st.container(border=True):
        st.dataframe(
            chain.to_frame(),
            width="stretch",
            hide_index=True,
            height=360,
            alt="Bảng block Proof of Work",
        )

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
    st.dataframe(
        comparison,
        width="stretch",
        hide_index=True,
        alt="So sánh chuỗi trung thực và chuỗi tấn công",
    )

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
    render_section_heading(
        "Kịch bản thuyết trình",
        "Một luồng demo ngắn, đi từ dự báo đến kiểm chứng và giới hạn bảo mật.",
        ":material/slideshow:",
    )
    steps = [
        ("01", "Đọc tín hiệu", "Mở Tổng quan & ML, chọn RandomForest và xem dự báo phụ tải."),
        ("02", "Đối chiếu mô hình", "So sánh MAE / RMSE / R² với baseline tuyến tính."),
        ("03", "Kiểm chứng hash", "Bật mô phỏng dữ liệu bị sửa để thấy trạng thái ĐÃ BỊ SỬA."),
        ("04", "Đào Proof of Work", "Giải thích nonce, độ khó, thời gian đào và tốc độ băm."),
        ("05", "Chạy đồng thuận", "Bật đào lại, sau đó tăng block vượt để mô phỏng tấn công 51%."),
    ]
    for number, title, detail in steps:
        with st.container(border=True):
            left, right = st.columns([0.12, 0.88], vertical_alignment="center")
            left.markdown(f"### {number}")
            right.markdown(f"**{title}**  \n{detail}")
    st.warning(
        "Không trình bày hash/PoW là bảo mật tuyệt đối. Chuỗi hash phát hiện sửa đổi; "
        "PoW + luật đồng thuận chống sửa đổi khi kẻ tấn công không nắm đa số năng lực đào."
    )
    st.info(
        "Huấn luyện lại mô hình: `.\\.venv\\Scripts\\python.exe ml\\train_model.py` "
        "(sinh lại `ml/model.pkl` và `ml/metrics.json`)."
    )


def main() -> None:
    configure_logging()
    st.set_page_config(
        page_title="Smart Grid Monitor · Nhóm 17",
        page_icon=":material/electric_bolt:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()
    render_header()

    options = model_options()
    available = [option for option in options if option["available"]]
    unavailable = [option for option in options if not option["available"]]

    with st.sidebar:
        st.markdown('<div class="sg-sidebar-kicker">Demo control room</div>', unsafe_allow_html=True)
        st.header("Điều khiển demo", icon=":material/tune:")
        st.caption("Điều chỉnh tham số ở đây; các tab bên phải cập nhật theo cùng một phiên.")
        dataset_label = st.selectbox("Nguồn dữ liệu mẫu", list(DATASETS.keys()), key="dataset")
        uploaded_file = st.file_uploader(
            "Hoặc tải dữ liệu CSV",
            type=["csv"],
            help=f"Chỉ nhận file .csv tối đa {MAX_UPLOAD_MB} MB.",
        )
        model_choice = st.selectbox(
            "Mô hình ML",
            [option["value"] for option in available],
            format_func=lambda value: next(
                option["label"] for option in options if option["value"] == value
            ),
            key="model_choice",
        )
        horizon = st.slider("Số giờ muốn dự đoán", min_value=1, max_value=12, value=6, key="horizon")

        st.caption("Chuỗi hash")
        tamper_demo = st.toggle("Mô phỏng dữ liệu bị sửa (tab Hash)", value=False, key="tamper_demo")

        st.caption("Proof of Work")
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
        st.caption(
            f"CSV cần có hai cột: timestamp và consumption_kwh · tối đa {MAX_UPLOAD_MB} MB."
        )

    for option in unavailable:
        st.sidebar.warning(f"{option['label']} chưa khả dụng: {option['detail']}")

    try:
        if uploaded_file is not None:
            # Mục 7 & 8: chặn sai định dạng / quá dung lượng trước khi đọc nội dung.
            validate_upload(uploaded_file.name, uploaded_file.size)
            raw_data = pd.read_csv(uploaded_file)
        else:
            raw_data = load_sample_data(str(DATASETS[dataset_label]))
        data = prepare_data(raw_data)
        forecast = predict_consumption(data, horizon=horizon, model=model_choice)
    except (OSError, ValueError, RuntimeError, pd.errors.ParserError) as exc:
        # Mục 6: giao diện chỉ thấy thông báo an toàn; chi tiết nằm trong log terminal.
        st.error(safe_error(exc, "Không thể xử lý dữ liệu đầu vào."))
        st.stop()

    source_label = "file CSV vừa tải" if uploaded_file is not None else dataset_label
    st.markdown(
        f'<div class="sg-meta"><span>Nguồn: {source_label}</span><span>Mô hình: {forecast.model_name}</span></div>',
        unsafe_allow_html=True,
    )

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
        render_section_heading(
            "Dữ liệu đầu vào",
            "Kiểm tra dữ liệu đã làm sạch trước khi đưa sang ML và Blockchain.",
            ":material/table_chart:",
        )
        with st.container(border=True):
            st.markdown("**Bảng dữ liệu đầu vào**")
            st.dataframe(data, width="stretch", hide_index=True, height=380, alt="Bảng dữ liệu đầu vào đã làm sạch")
        with st.container(border=True):
            st.markdown("**Bản ghi sẽ ghi vào Blockchain**")
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
