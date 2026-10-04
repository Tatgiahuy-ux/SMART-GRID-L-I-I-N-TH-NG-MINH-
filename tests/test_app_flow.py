from streamlit.testing.v1 import AppTest


SAMPLE_DATASET = "sample_energy.csv – 8 giờ (dữ liệu minh họa nhỏ)"


def test_app_flow():
    at = AppTest.from_file("../app.py", default_timeout=60).run()
    assert not at.exception

    at.button(key="t2_predict").click().run()
    assert at.session_state["prediction"] is not None

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


if __name__ == "__main__":
    test_app_flow()
    print("1 passed")
