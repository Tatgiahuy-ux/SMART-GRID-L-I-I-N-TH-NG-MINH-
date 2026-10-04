"""Chuỗi hash SHA-256 phát hiện sửa đổi dữ liệu (phần "Blockchain / Hash" của demo).

Mỗi block lưu một bản ghi điện năng kèm ``previous_hash`` của block trước. Sửa payload mà
không đào lại thì hash không còn khớp → ``is_valid()`` trả ``False``.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable

import pandas as pd


@dataclass(frozen=True)
class Block:
    index: int
    payload: dict[str, Any]
    previous_hash: str
    hash: str


class IntegrityChain:
    """Chuỗi block tối giản chỉ để kiểm tra toàn vẹn (không có nonce/đồng thuận).

    Phần đào khối và luật đồng thuận nằm ở ``blockchain/consensus.py``.
    """

    def __init__(self) -> None:
        self.blocks: list[Block] = []

    def add_record(self, payload: dict[str, Any]) -> Block:
        previous_hash = self.blocks[-1].hash if self.blocks else "0" * 64
        index = len(self.blocks)
        digest_input = json.dumps(
            {
                "index": index,
                "payload": payload,
                "previous_hash": previous_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        block = Block(
            index=index,
            payload=payload,
            previous_hash=previous_hash,
            hash=hashlib.sha256(digest_input).hexdigest(),
        )
        self.blocks.append(block)
        return block

    def add_records(self, records: Iterable[dict[str, Any]]) -> None:
        """Append multiple records while preserving their order."""
        for record in records:
            self.add_record(record)

    def tamper_block(self, index: int, field: str, value: Any) -> None:
        """Change a payload without updating its hash for the demo tamper scenario."""
        block = self.blocks[index]
        payload = dict(block.payload)
        payload[field] = value
        self.blocks[index] = Block(
            index=block.index,
            payload=payload,
            previous_hash=block.previous_hash,
            hash=block.hash,
        )

    def to_frame(self) -> pd.DataFrame:
        """Return a compact table suitable for Streamlit."""
        return pd.DataFrame(
            [
                {
                    "block": block.index,
                    "timestamp": block.payload.get("timestamp", ""),
                    "consumption_kwh": block.payload.get("consumption_kwh", ""),
                    "hash": block.hash,
                    "previous_hash": block.previous_hash,
                }
                for block in self.blocks
            ]
        )

    def is_valid(self) -> bool:
        return self.invalid_index() is None

    def invalid_index(self) -> int | None:
        """Vị trí block đầu tiên không hợp lệ; ``None`` nếu cả chuỗi hợp lệ.

        Dùng cho giao diện: chỉ rõ block nào bị lệch hash hoặc đứt liên kết, thay vì chỉ
        báo "chuỗi sai".
        """
        previous_hash = "0" * 64
        for index, block in enumerate(self.blocks):
            if block.index != index or block.previous_hash != previous_hash:
                return index
            if block.hash != self._hash_block(block):
                return index
            previous_hash = block.hash
        return None

    @staticmethod
    def _hash_block(block: Block) -> str:
        digest_input = json.dumps(
            {
                "index": block.index,
                "payload": block.payload,
                "previous_hash": block.previous_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(digest_input).hexdigest()
