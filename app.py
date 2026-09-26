"""Streamlit integration shell for the Smart Grid classroom demo."""

from pathlib import Path

import pandas as pd
import streamlit as st

from blockchain.chain import IntegrityChain
from ml.predictor import predict_consumption


ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "sample_energy.csv"


@st.cache_data
def load_energy_data() -> pd.DataFrame:
    """Load the local sample dataset used until the ML owner supplies real data."""
    return pd.read_csv(DATA_PATH, parse_dates=["timestamp"])


def main() -> None:
    st.set_page_config(
        page_title="Smart Grid Monitor",
        page_icon="⚡",
        layout="wide",
    )

    st.title("Smart Grid Monitor")
    st.write(
        "Bản demo tích hợp dự đoán tiêu thụ điện và kiểm tra tính toàn vẹn dữ liệu."
    )

    try:
        data = load_energy_data()
    except (FileNotFoundError, pd.errors.ParserError) as exc:
        st.error(f"Không thể đọc dữ liệu mẫu: {exc}")
        st.stop()

    st.subheader("Dữ liệu tiêu thụ điện")
    st.line_chart(data.set_index("timestamp")["consumption_kwh"])
    st.dataframe(data, use_container_width=True, hide_index=True)

    st.subheader("Dự đoán và xác thực")
    latest_value = float(data["consumption_kwh"].iloc[-1])
    prediction = predict_consumption(data)

    left, right = st.columns(2)
    with left:
        st.metric("Mức tiêu thụ gần nhất", f"{latest_value:.1f} kWh")
        st.metric("Dự đoán giờ kế tiếp", f"{prediction:.1f} kWh")

    with right:
        chain = IntegrityChain()
        block = chain.add_record(
            {
                "timestamp": data["timestamp"].iloc[-1].isoformat(),
                "consumption_kwh": latest_value,
            }
        )
        st.write("**Hash bản ghi hiện tại**")
        st.code(block.hash)
        st.success("Xác thực chuỗi thành công." if chain.is_valid() else "Dữ liệu không hợp lệ.")

    st.caption(
        "Giá trị dự đoán hiện tại là baseline minh họa. Thay predictor.py bằng model ML thật khi có module chính thức."
    )


if __name__ == "__main__":
    main()
