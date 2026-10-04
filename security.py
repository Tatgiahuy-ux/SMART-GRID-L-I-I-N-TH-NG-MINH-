"""Kiểm tra dữ liệu đầu vào và che chi tiết lỗi (các mục bảo mật cơ bản).

Tách riêng khỏi ``app.py`` để kiểm thử được mà không cần Streamlit. Module này xử lý:

- **Mục 7 – định dạng file upload**: chỉ nhận ``.csv``, chặn trước khi đọc nội dung.
- **Mục 8 – dung lượng file upload**: chặn file > 5 MB (khớp với ``server.maxUploadSize``
  trong ``.streamlit/config.toml``).
- **Mục 9 – validate lại ở phía server**: kiểm tra cột, kiểu dữ liệu, giá trị âm/vô lý,
  số dòng, trùng mốc thời gian — không tin bất cứ thứ gì trình duyệt gửi lên.
- **Mục 4 & 6 – log và thông báo lỗi**: chi tiết lỗi (traceback, đường dẫn file) chỉ ghi ra
  log phía server; giao diện chỉ nhận thông báo an toàn.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger("smart_grid")

# --- Giới hạn upload (mục 7 & 8) ------------------------------------------- #
ALLOWED_UPLOAD_EXTENSIONS = {".csv"}
MAX_UPLOAD_MB = 5
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# --- Giới hạn dữ liệu (mục 9) ---------------------------------------------- #
REQUIRED_COLUMNS = ("timestamp", "consumption_kwh")
MAX_ROWS = 200_000
MAX_ABS_KWH = 1_000_000.0


class UserInputError(ValueError):
    """Lỗi do dữ liệu người dùng gửi lên; thông báo an toàn để hiển thị."""


# Mã lỗi rút gọn để tra cứu log, KHÔNG chứa tên class/traceback/đường dẫn (mục 6).
ERROR_CODES = {
    "ParserError": "E-CSV-01",
    "EmptyDataError": "E-CSV-02",
    "UnicodeDecodeError": "E-CSV-03",
    "FileNotFoundError": "E-IO-01",
    "OSError": "E-IO-02",
    "PermissionError": "E-IO-03",
    "RuntimeError": "E-ML-01",
    "ValueError": "E-DATA-01",
}
DEFAULT_ERROR_CODE = "E-UNKNOWN"


def configure_logging() -> None:
    """Bật log phía server (ra terminal), không hiển thị ra giao diện."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    LOGGER.setLevel(logging.INFO)


def validate_upload(filename: str | None, size: int | None) -> None:
    """Chặn file sai định dạng hoặc quá lớn trước khi đọc nội dung (mục 7 & 8)."""
    if not filename:
        raise UserInputError("Chưa chọn file.")
    if "/" in filename or "\\" in filename or ".." in filename:
        raise UserInputError("Tên file không hợp lệ.")

    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        raise UserInputError(
            f"Chỉ chấp nhận file {allowed}. File bạn gửi có định dạng "
            f"'{suffix or 'không xác định'}'."
        )
    if size is None or size <= 0:
        raise UserInputError("File rỗng, không có dữ liệu để xử lý.")
    if size > MAX_UPLOAD_BYTES:
        raise UserInputError(
            f"File vượt quá giới hạn {MAX_UPLOAD_MB} MB "
            f"({size / (1024 * 1024):.1f} MB). Vui lòng chia nhỏ dữ liệu."
        )


def prepare_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Validate và chuẩn hoá dữ liệu ở phía server trước khi đưa vào mô hình (mục 9)."""
    if not isinstance(raw_data, pd.DataFrame) or raw_data.empty:
        raise UserInputError("File không có dữ liệu.")

    missing = [column for column in REQUIRED_COLUMNS if column not in raw_data.columns]
    if missing:
        raise UserInputError("Thiếu cột bắt buộc: " + ", ".join(missing) + ".")
    if len(raw_data) > MAX_ROWS:
        raise UserInputError(f"Dữ liệu vượt quá {MAX_ROWS:,} dòng cho phép.")

    data = raw_data[list(REQUIRED_COLUMNS)].copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data["consumption_kwh"] = pd.to_numeric(data["consumption_kwh"], errors="coerce")
    data = data.replace([float("inf"), float("-inf")], pd.NA).dropna()
    data = (
        data.drop_duplicates(subset="timestamp", keep="last")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    if data.empty:
        raise UserInputError(
            "Không có bản ghi hợp lệ sau khi làm sạch. Kiểm tra định dạng "
            "'YYYY-MM-DD HH:MM:SS' của cột timestamp và giá trị số của consumption_kwh."
        )
    if (data["consumption_kwh"] < 0).any():
        raise UserInputError("Mức tiêu thụ điện không được âm.")
    if (data["consumption_kwh"] > MAX_ABS_KWH).any():
        raise UserInputError(f"Có giá trị tiêu thụ vượt mức hợp lệ ({MAX_ABS_KWH:,.0f} kWh).")
    return data


def safe_error(exc: BaseException, fallback: str) -> str:
    """Ghi chi tiết lỗi vào log server, trả về thông báo an toàn cho giao diện.

    Không bao giờ trả về traceback, câu lệnh, tên server, tên class hay đường dẫn file
    (mục 6). Người dùng chỉ thấy câu thông báo chung + mã lỗi rút gọn; muốn xem chi tiết
    thì đọc log ở terminal đang chạy Streamlit.
    """
    LOGGER.error("%s | %s: %s", fallback, type(exc).__name__, exc, exc_info=exc)
    if isinstance(exc, UserInputError):
        return str(exc)
    code = ERROR_CODES.get(type(exc).__name__, DEFAULT_ERROR_CODE)
    return f"{fallback} Vui lòng kiểm tra lại định dạng file. (mã lỗi: {code})"
