from pathlib import Path
import re

from streamlit.testing.v1 import AppTest


SAMPLE_DATASET = "sample_energy.csv – 8 giờ (dữ liệu minh họa nhỏ)"
ROOT = Path(__file__).resolve().parents[1]


def test_app_flow():
    at = AppTest.from_file("../app.py", default_timeout=60).run()
    assert not at.exception

    at.button(key="t2_predict").click().run()
    assert at.session_state["prediction"] is not None

    at.button(key="t2_write").click().run()
    assert len(at.session_state["chain"].blocks) == 1
    assert any("lớn hơn 0 kWh" in warning.value for warning in at.warning)

    at.number_input(key="t2_actual").set_value(5.5).run()
    at.button(key="t2_write").click().run()
    assert len(at.session_state["chain"].blocks) == 2

    hours = at.selectbox(key="t2_hour").options
    at.selectbox(key="t2_hour").select(hours[1]).run()
    at.button(key="t2_predict").click().run()
    at.selectbox(key="t2_hour").select(hours[2]).run()
    at.button(key="t2_write").click().run()
    assert len(at.session_state["chain"].blocks) == 2
    assert any("Dự đoán lại" in warning.value for warning in at.warning)

    at.selectbox(key="t2_hour").select(hours[1]).run()
    at.button(key="t2_write").click().run()
    assert len(at.session_state["chain"].blocks) == 3
    assert at.session_state["chain"].is_valid()

    at.button(key="t3_tamper").click().run()
    assert at.error
    assert at.session_state["chain"].is_valid()
    at.button(key="t3_undo").click().run()
    assert not at.error

    assert at.button(key="t3_clear").disabled
    at.checkbox(key="t3_confirm_clear").check().run()
    assert not at.button(key="t3_clear").disabled
    at.button(key="t3_clear").click().run()
    assert len(at.session_state["chain"].blocks) == 1
    assert at.session_state["tamper"] is None

    at.button(key="t4_run").click().run()
    assert any("trung thực" in success.value for success in at.success)
    at.selectbox(key="t4_strength").select("Đào nhanh hơn 1 khối").run()
    at.button(key="t4_run").click().run()
    assert any("THẮNG" in error.value for error in at.error)

    at.session_state["sim"] = None
    at.selectbox(key="dataset").select(SAMPLE_DATASET).run()
    assert not at.exception


def test_forecast_and_block_cards():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    assert not at.exception

    # Việc 2: dự báo 24 giờ tới trên tab Tổng quan.
    assert any("Dự báo 24 giờ tới" in element.value for element in at.subheader)
    metric_labels = [element.label for element in at.metric]
    assert any(label.startswith("Giờ dùng nhiều nhất:") for label in metric_labels)
    assert any(label.startswith("Giờ dùng ít nhất:") for label in metric_labels)
    assert len(at.get("vega_lite_chart")) >= 2

    # Việc 1: ghi 2 block rồi kiểm thẻ chuỗi khối.
    at.button(key="t2_predict").click().run()
    at.number_input(key="t2_actual").set_value(5.5).run()
    at.button(key="t2_write").click().run()
    hours = at.selectbox(key="t2_hour").options
    at.selectbox(key="t2_hour").select(hours[1]).run()
    at.button(key="t2_predict").click().run()
    at.number_input(key="t2_actual").set_value(6.5).run()
    at.button(key="t2_write").click().run()
    assert len(at.session_state["chain"].blocks) == 3
    markdowns = [element.value for element in at.markdown]
    assert any("Block #1" in value for value in markdowns)
    assert any("Block #2" in value for value in markdowns)
    assert any("Thực tế" in value and "Dự đoán" in value for value in markdowns)

    # Sửa trộm Block #1: đúng 1 thẻ báo "Nội dung bị sửa".
    at.button(key="t3_tamper").click().run()
    content_errors = [
        element.value for element in at.error if "Nội dung bị sửa" in element.value
    ]
    assert len(content_errors) == 1, content_errors
    at.button(key="t3_undo").click().run()
    assert [
        element.value for element in at.error if "Nội dung bị sửa" in element.value
    ] == []


def test_long_chain_and_consensus_chart():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    assert not at.exception

    # Chuỗi 8 block: chỉ vẽ 6 thẻ cuối kèm dòng thông báo.
    chain = type(at.session_state["chain"])(difficulty=1)
    chain.add_energy_records(
        [
            {
                "consumer_id": "METER_001",
                "recorded_time": f"2026-02-01 {hour:02d}:00:00",
                "actual_usage_kwh": float(hour + 1),
                "predicted_usage_kwh": float(hour + 1),
            }
            for hour in range(7)
        ]
    )
    at.session_state["chain"] = chain
    at.run()
    assert not at.exception
    assert any(
        "Đang hiện 6 block cuối trong 8 block" in element.value
        for element in at.markdown
    )

    # Việc 3: chạy mô phỏng làm xuất hiện biểu đồ cột sức đào.
    before = len(at.get("vega_lite_chart"))
    at.button(key="t4_run").click().run()
    assert not at.exception
    assert len(at.get("vega_lite_chart")) == before + 1
    metric_labels = [element.label for element in at.metric]
    assert "Giá trị tại block bị sửa (kWh)" in metric_labels
    assert all("…" not in element.value for element in at.metric)
    assert any("Hòa tổng sức đào" in element.value for element in at.markdown)


def test_random_forest_hint_on_non_default_dataset():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    assert not at.exception
    hint = "RandomForest đã học sẵn từ bộ dữ liệu mặc định."
    assert all(hint not in element.value for element in at.markdown)
    at.selectbox(key="dataset").select(SAMPLE_DATASET).run()
    assert not at.exception
    assert any(hint in element.value for element in at.markdown)


def test_no_emoji_in_source():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    emoji = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u25B6\u21A9\uFE0F\u200D]")
    assert not emoji.search(source)


def test_upload_limit_stays_configured():
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "maxUploadSize = 5" in config


if __name__ == "__main__":
    test_app_flow()
    test_forecast_and_block_cards()
    test_long_chain_and_consensus_chart()
    test_random_forest_hint_on_non_default_dataset()
    test_no_emoji_in_source()
    test_upload_limit_stays_configured()
    print("6 passed")
