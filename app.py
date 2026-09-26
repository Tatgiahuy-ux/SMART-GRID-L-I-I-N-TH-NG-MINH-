"""Streamlit dashboard for the Smart Grid classroom demonstration."""

from pathlib import Path

import pandas as pd
import streamlit as st

from blockchain.chain import IntegrityChain
from ml.predictor import ForecastResult, predict_consumption


ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "sample_energy.csv"
REQUIRED_COLUMNS = {"timestamp", "consumption_kwh"}


@st.cache_data
def load_sample_data() -> pd.DataFrame:
    """Load the committed fallback dataset."""
    return pd.read_csv(DATA_PATH, parse_dates=["timestamp"])


def prepare_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the input contract shared with the ML module."""
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


def render_overview(data: pd.DataFrame, forecast: ForecastResult) -> None:
    st.subheader("Tổng quan tiêu thụ điện")
    st.line_chart(data.set_index("timestamp")["consumption_kwh"])

    latest = float(data["consumption_kwh"].iloc[-1])
    average = float(data["consumption_kwh"].mean())
    next_value = forecast.predictions[0]
    metric_left, metric_middle, metric_right = st.columns(3)
    metric_left.metric("Bản ghi gần nhất", f"{latest:.1f} kWh")
    metric_middle.metric("Trung bình dữ liệu", f"{average:.1f} kWh")
    metric_right.metric("Dự đoán giờ kế tiếp", f"{next_value:.1f} kWh")

    future_times = pd.date_range(
        start=data["timestamp"].iloc[-1] + pd.Timedelta(hours=1),
        periods=len(forecast.predictions),
        freq="h",
    )
    forecast_data = pd.DataFrame(
        {"timestamp": future_times, "consumption_kwh": forecast.predictions}
    ).set_index("timestamp")
    st.write("**Đường dự đoán cho các giờ tiếp theo**")
    st.line_chart(forecast_data)

    if forecast.mae is not None:
        st.info(
            f"Độ sai số MAE kiểm tra nhanh: {forecast.mae:.2f} kWh. "
            "Đây là baseline minh họa, chưa phải mô hình nghiên cứu chính thức."
        )
    else:
        st.info("Cần ít nhất 4 bản ghi để tính sai số kiểm tra nhanh.")


def render_integrity(data: pd.DataFrame, tamper_demo: bool) -> None:
    st.subheader("Kiểm tra tính toàn vẹn dữ liệu")
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


def main() -> None:
    st.set_page_config(page_title="Smart Grid Monitor", page_icon="⚡", layout="wide")
    st.title("Smart Grid Monitor")
    st.write(
        "Bản demo kết hợp dự đoán tiêu thụ điện và kiểm tra tính toàn vẹn dữ liệu bằng hash."
    )

    with st.sidebar:
        st.header("Điều khiển demo")
        uploaded_file = st.file_uploader("Tải dữ liệu CSV", type="csv")
        horizon = st.slider("Số giờ muốn dự đoán", min_value=1, max_value=6, value=3)
        tamper_demo = st.toggle("Mô phỏng dữ liệu bị sửa", value=False)
        st.caption("CSV cần có hai cột: timestamp và consumption_kwh.")

    try:
        raw_data = (
            pd.read_csv(uploaded_file)
            if uploaded_file is not None
            else load_sample_data()
        )
        data = prepare_data(raw_data)
        forecast = predict_consumption(data, horizon=horizon)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        st.error(f"Không thể xử lý dữ liệu: {exc}")
        st.stop()

    source_label = "file CSV vừa tải" if uploaded_file is not None else "dữ liệu mẫu trong repository"
    st.caption(f"Nguồn dữ liệu: {source_label} · Mô hình: {forecast.model_name}")

    overview_tab, integrity_tab, data_tab, guide_tab = st.tabs(
        ["Tổng quan", "Blockchain / Hash", "Dữ liệu", "Hướng dẫn demo"]
    )
    with overview_tab:
        render_overview(data, forecast)
    with integrity_tab:
        render_integrity(data, tamper_demo)
    with data_tab:
        st.subheader("Bảng dữ liệu đầu vào")
        st.dataframe(data, width="stretch", hide_index=True)
        st.download_button(
            "Tải dữ liệu đã làm sạch",
            data.to_csv(index=False).encode("utf-8"),
            file_name="smart_grid_cleaned.csv",
            mime="text/csv",
        )
    with guide_tab:
        st.subheader("Kịch bản thuyết trình")
        st.markdown(
            """
            1. Mở **Tổng quan** và giải thích dữ liệu tiêu thụ theo thời gian.
            2. Chọn số giờ dự đoán và trình bày đường dự đoán.
            3. Sang **Blockchain / Hash** để cho thấy mỗi bản ghi được liên kết bằng hash.
            4. Bật **Mô phỏng dữ liệu bị sửa** để chứng minh trạng thái chuyển sang không hợp lệ.
            5. Tắt mô phỏng và nhấn mạnh đây là baseline giáo dục, sẽ thay bằng model thật sau.
            """
        )
        st.warning(
            "Hash giúp phát hiện thay đổi trên chuỗi dữ liệu trong demo; không nên trình bày là bảo mật tuyệt đối."
        )


if __name__ == "__main__":
    main()
