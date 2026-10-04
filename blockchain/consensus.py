"""Chuỗi khối Proof of Work cho demo Smart Grid (Nhóm 17).

Mô-đun này tích hợp ``blockchain_module.py`` do thành viên phụ trách Blockchain gửi
(bản gốc lưu tại ``team-deliverables/blockchain_module_goc.py``). Những điểm đã xử lý:

1. **Sửa lỗi bản gốc**: ``Block.calculate_hash()`` không có ``return`` nên ``self.hash``
   luôn là ``None`` và ``mine_block`` sẽ ném ``TypeError``. Bản này tính hash thật.
2. Ghi lại ``nonce``, ``difficulty`` và thời gian đào của từng block để trình bày.
3. Bổ sung **luật đồng thuận**: so sánh tổng công (cumulative work) và chọn chuỗi nặng
   nhất – chuỗi dài nhất (``resolve_conflict``), kèm kịch bản kẻ tấn công đào lại.
4. Payload chuẩn hoá cho dữ liệu lưới điện: ``consumer_id``, ``actual_usage_kwh``,
   ``predicted_usage_kwh`` – đúng điểm nối giữa mô-đun ML và Blockchain.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import pandas as pd

GENESIS_PREVIOUS_HASH = "0" * 64
DEFAULT_DIFFICULTY = 3
MAX_DIFFICULTY = 4


def _parse_timestamp(recorded_time: str) -> float:
    """Đổi ``recorded_time`` sang epoch giây; nếu không phân tích được thì lấy giờ hiện tại.

    Ghi chú: ``pandas.Timestamp`` coi mốc thời gian **không có múi giờ** là UTC (khác với
    ``datetime.timestamp()`` vốn hiểu theo giờ địa phương), nên kết quả đào khối — nonce,
    hash — giống nhau trên mọi máy. Đừng đổi sang ``datetime`` nếu không muốn số nonce
    trong báo cáo/slide thay đổi theo múi giờ của máy demo.
    """
    try:
        stamp = pd.Timestamp(recorded_time)
    except (ValueError, TypeError):
        return time.time()
    if pd.isna(stamp):
        return time.time()
    return float(stamp.timestamp())


def _format_number(value: Any, digits: int = 2) -> str:
    """Định dạng số cho bảng hiển thị; trả về '—' nếu khối không có trường số."""
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


@dataclass(frozen=True)
class ProofBlock:
    """Một khối đã được đào (mined)."""

    index: int
    timestamp: float
    payload: dict[str, Any]
    previous_hash: str
    nonce: int
    difficulty: int
    hash: str
    mine_seconds: float


class ProofOfWorkChain:
    """Chuỗi khối PoW cục bộ dùng cho phần trình diễn cơ chế đồng thuận."""

    def __init__(self, difficulty: int = DEFAULT_DIFFICULTY, with_genesis: bool = True) -> None:
        if not 1 <= difficulty <= MAX_DIFFICULTY:
            raise ValueError(f"Difficulty phải trong khoảng 1..{MAX_DIFFICULTY}.")
        self.difficulty = difficulty
        self.blocks: list[ProofBlock] = []
        if with_genesis:
            self.blocks.append(self._make_genesis_block())

    # ------------------------------------------------------------------ #
    # Hash & đào
    # ------------------------------------------------------------------ #
    @staticmethod
    def calculate_hash(
        index: int,
        timestamp: float,
        payload: dict[str, Any],
        previous_hash: str,
        nonce: int,
    ) -> str:
        """SHA-256 trên toàn bộ nội dung khối (kể cả nonce)."""
        block_string = json.dumps(
            {
                "index": index,
                "timestamp": timestamp,
                "data": payload,
                "previous_hash": previous_hash,
                "nonce": nonce,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(block_string).hexdigest()

    def _make_genesis_block(self) -> ProofBlock:
        payload = {"info": "Genesis Block - khởi tạo hệ thống lưới điện thông minh"}
        return self._mine(index=0, payload=payload, timestamp=0.0)

    def _mine(
        self,
        payload: dict[str, Any],
        index: int | None = None,
        timestamp: float | None = None,
    ) -> ProofBlock:
        index = len(self.blocks) if index is None else index
        previous_hash = self.blocks[-1].hash if self.blocks else GENESIS_PREVIOUS_HASH
        timestamp = time.time() if timestamp is None else timestamp

        target = "0" * self.difficulty
        nonce = 0
        started = time.perf_counter()
        digest = self.calculate_hash(index, timestamp, payload, previous_hash, nonce)
        while not digest.startswith(target):
            nonce += 1
            digest = self.calculate_hash(index, timestamp, payload, previous_hash, nonce)
        elapsed = time.perf_counter() - started

        return ProofBlock(
            index=index,
            timestamp=timestamp,
            payload=payload,
            previous_hash=previous_hash,
            nonce=nonce,
            difficulty=self.difficulty,
            hash=digest,
            mine_seconds=elapsed,
        )

    # ------------------------------------------------------------------ #
    # API ghi dữ liệu
    # ------------------------------------------------------------------ #
    def add_energy_record(
        self,
        consumer_id: str,
        recorded_time: str,
        actual_usage_kwh: float,
        predicted_usage_kwh: float,
        block_timestamp: float | None = None,
    ) -> ProofBlock:
        """Ghi một bản ghi điện năng (thực tế + dự đoán của mô hình ML) vào chuỗi.

        ``block_timestamp`` mặc định lấy từ ``recorded_time`` để việc đào khối có tính
        lặp lại (deterministic) – cần thiết khi so sánh hai chuỗi trong phần đồng thuận.
        """
        payload = {
            "consumer_id": str(consumer_id),
            "recorded_time": str(recorded_time),
            "actual_usage_kwh": round(float(actual_usage_kwh), 4),
            "predicted_usage_kwh": round(float(predicted_usage_kwh), 4),
            "deviation_kwh": round(float(predicted_usage_kwh) - float(actual_usage_kwh), 4),
        }
        timestamp = block_timestamp
        if timestamp is None:
            timestamp = _parse_timestamp(recorded_time)
        block = self._mine(payload, timestamp=timestamp)
        self.blocks.append(block)
        return block

    def add_energy_records(self, records: Iterable[dict[str, Any]]) -> list[ProofBlock]:
        """Ghi nhiều bản ghi theo thứ tự; mỗi phần tử là kwargs của ``add_energy_record``."""
        return [self.add_energy_record(**record) for record in records]

    # ------------------------------------------------------------------ #
    # Kiểm tra & tấn công mô phỏng
    # ------------------------------------------------------------------ #
    def validation_error(self) -> str | None:
        """Trả về mô tả lỗi đầu tiên, hoặc ``None`` nếu chuỗi hợp lệ."""
        previous_hash = GENESIS_PREVIOUS_HASH
        for position, block in enumerate(self.blocks):
            if block.index != position:
                return f"Block #{block.index} sai vị trí (mong đợi #{position})."
            if block.difficulty != self.difficulty:
                return (
                    f"Block #{block.index} có độ khó {block.difficulty}, "
                    f"không khớp độ khó chuỗi {self.difficulty}."
                )
            if block.previous_hash != previous_hash:
                return (
                    f"Chuỗi đứt gãy: Block #{block.index} trỏ tới hash không khớp khối trước."
                )
            expected = self.calculate_hash(
                block.index, block.timestamp, block.payload, block.previous_hash, block.nonce
            )
            if block.hash != expected:
                return f"Dữ liệu Block #{block.index} đã bị thay đổi so với hash đã đào."
            if not block.hash.startswith("0" * self.difficulty):
                return f"Block #{block.index} có hash không đạt độ khó {self.difficulty}."
            previous_hash = block.hash
        return None

    def is_valid(self) -> bool:
        return self.validation_error() is None

    def tamper_block(self, index: int, field: str, value: Any) -> None:
        """Sửa payload nhưng giữ nguyên hash/nonce – kịch bản kẻ tấn công ẩu."""
        block = self.blocks[index]
        payload = dict(block.payload)
        payload[field] = value
        self.blocks[index] = ProofBlock(
            index=block.index,
            timestamp=block.timestamp,
            payload=payload,
            previous_hash=block.previous_hash,
            nonce=block.nonce,
            difficulty=block.difficulty,
            hash=block.hash,
            mine_seconds=block.mine_seconds,
        )

    def tamper_and_remine(
        self,
        index: int,
        field: str,
        value: Any,
        extra_blocks: int = 0,
    ) -> ProofOfWorkChain:
        """Kẻ tấn công sửa payload rồi **đào lại** để dựng nhánh riêng (private fork).

        Nhánh của kẻ tấn công giữ nguyên các khối trước ``index``, thay payload tại
        ``index``, rồi **đào lại đúng những khối còn lại của chuỗi trung thực** (giữ nguyên
        ``index``/``timestamp``/payload, chỉ khác hash vì ``previous_hash`` đã đổi). Sau đó
        mới đào thêm ``extra_blocks`` khối mới để giành ưu thế tổng công.

        Vì vậy ``extra_blocks=0`` cho ra nhánh **cùng độ dài, cùng tổng công** với chuỗi
        trung thực (hòa → nút trung thực thắng theo luật), còn ``extra_blocks>=1`` mô phỏng
        tấn công 51%: nhánh tấn công nặng hơn nên được chọn.

        Chuỗi trả về vẫn hợp lệ về mặt hash – cho thấy chỉ kiểm tra hash là không đủ,
        phải dùng luật đồng thuận theo tổng công.
        """
        if not 0 <= index < len(self.blocks):
            raise IndexError(f"Block #{index} không tồn tại.")
        if extra_blocks < 0:
            raise ValueError("extra_blocks không được âm.")

        attacker = ProofOfWorkChain(difficulty=self.difficulty, with_genesis=False)
        for block in self.blocks[:index]:
            attacker._append_clone(block)

        victim = self.blocks[index]
        payload = dict(victim.payload)
        payload[field] = value
        attacker.blocks.append(
            attacker._mine(payload, index=victim.index, timestamp=victim.timestamp)
        )

        # Đào lại phần đuôi của chuỗi trung thực với đúng dữ liệu gốc (không bịa bản ghi).
        for block in self.blocks[index + 1 :]:
            attacker._remine_clone(block)

        target_length = len(self.blocks) + extra_blocks
        offset = 1
        while len(attacker.blocks) < target_length:
            attacker._mine_attacker_block(offset=offset, base_timestamp=victim.timestamp)
            offset += 1

        return attacker

    def _append_clone(self, block: ProofBlock) -> None:
        """Chép nguyên trạng một khối đã đào (giữ hash) sang chuỗi mới."""
        self.blocks.append(
            ProofBlock(
                index=block.index,
                timestamp=block.timestamp,
                payload=dict(block.payload),
                previous_hash=block.previous_hash,
                nonce=block.nonce,
                difficulty=block.difficulty,
                hash=block.hash,
                mine_seconds=block.mine_seconds,
            )
        )

    def _remine_clone(self, block: ProofBlock) -> ProofBlock:
        """Đào lại một khối của chuỗi trung thực với **đúng nội dung gốc** (nhánh tấn công).

        Khác ``_append_clone`` (chép nguyên hash cũ): hàm này tính hash mới trên
        ``previous_hash`` của nhánh tấn công, nên nhánh vẫn hợp lệ về mặt hash.
        """
        remined = self._mine(dict(block.payload), index=block.index, timestamp=block.timestamp)
        self.blocks.append(remined)
        return remined

    def _mine_attacker_block(self, offset: int, base_timestamp: float) -> ProofBlock:
        payload = {
            "consumer_id": "ATTACKER",
            "recorded_time": f"khối tấn công #{offset}",
            "note": "Kẻ tấn công đào thêm để giành ưu thế tổng công (mô phỏng).",
        }
        block = self._mine(payload, timestamp=base_timestamp + offset * 3600.0)
        self.blocks.append(block)
        return block

    def clone(self) -> ProofOfWorkChain:
        duplicate = ProofOfWorkChain(difficulty=self.difficulty, with_genesis=False)
        for block in self.blocks:
            duplicate._append_clone(block)
        return duplicate

    # ------------------------------------------------------------------ #
    # Số liệu & đồng thuận
    # ------------------------------------------------------------------ #
    @property
    def cumulative_work(self) -> int:
        """Tổng công ước lượng: mỗi khối đóng góp 2^difficulty phép băm trung bình."""
        return sum(1 << block.difficulty for block in self.blocks)

    @property
    def total_nonce(self) -> int:
        return sum(block.nonce for block in self.blocks)

    @property
    def total_attempts(self) -> int:
        """Tổng số lần băm thực tế đã thực hiện.

        ``_mine`` băm thử ở ``nonce = 0`` rồi mới tăng dần, nên mỗi khối tốn đúng
        ``nonce + 1`` phép băm. Dùng giá trị này để tính tốc độ băm cho chính xác.
        """
        return sum(block.nonce + 1 for block in self.blocks)

    @property
    def total_mine_seconds(self) -> float:
        return sum(block.mine_seconds for block in self.blocks)

    @property
    def hash_rate(self) -> float:
        """Tốc độ băm thực đo: số phép băm / tổng thời gian đào (H/s)."""
        elapsed = self.total_mine_seconds
        return self.total_attempts / elapsed if elapsed > 0 else 0.0

    @staticmethod
    def resolve_conflict(chains: Sequence["ProofOfWorkChain"]) -> tuple["ProofOfWorkChain | None", str]:
        """Luật đồng thuận: chọn chuỗi hợp lệ có tổng công lớn nhất (hòa thì chọn sớm nhất)."""
        if not chains:
            return None, "Không có chuỗi nào để so sánh."

        valid = [
            (position, chain) for position, chain in enumerate(chains) if chain.is_valid()
        ]
        if not valid:
            return None, "Tất cả chuỗi đều không hợp lệ – các nút từ chối dữ liệu."

        best_position, best = max(
            valid,
            key=lambda item: (item[1].cumulative_work, len(item[1].blocks), -item[0]),
        )
        tied = [
            chain
            for _, chain in valid
            if chain.cumulative_work == best.cumulative_work
            and len(chain.blocks) == len(best.blocks)
        ]
        if len(tied) > 1:
            reason = (
                f"Hòa tổng công ({best.cumulative_work}) và độ dài ({len(best.blocks)} khối) "
                "→ giữ chuỗi xuất hiện trước (nút trung thực)."
            )
        else:
            rejected = len(chains) - len(valid)
            reason = (
                f"Chọn chuỗi #{best_position} với tổng công {best.cumulative_work} và "
                f"{len(best.blocks)} khối."
            )
            if rejected:
                reason += f" Đã loại {rejected} chuỗi không hợp lệ."
        return best, reason

    # ------------------------------------------------------------------ #
    # Trình bày
    # ------------------------------------------------------------------ #
    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "block": block.index,
                    "consumer_id": block.payload.get("consumer_id", "—"),
                    "thời điểm ghi": block.payload.get("recorded_time", "—"),
                    "thực tế (kWh)": _format_number(block.payload.get("actual_usage_kwh")),
                    "dự đoán (kWh)": _format_number(block.payload.get("predicted_usage_kwh")),
                    "nonce": block.nonce,
                    "difficulty": block.difficulty,
                    "đào (ms)": round(block.mine_seconds * 1000, 2),
                    "hash": block.hash,
                    "previous_hash": block.previous_hash,
                }
                for block in self.blocks
            ]
        )

    def summary(self) -> dict[str, Any]:
        return {
            "difficulty": self.difficulty,
            "blocks": len(self.blocks),
            "valid": self.is_valid(),
            "error": self.validation_error(),
            "cumulative_work": self.cumulative_work,
            "total_nonce": self.total_nonce,
            "total_attempts": self.total_attempts,
            "total_mine_seconds": round(self.total_mine_seconds, 3),
            "hash_rate": round(self.hash_rate, 1),
        }
