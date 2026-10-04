"""Small hash chain for the classroom integration demo."""

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
    """Minimal local chain; replace or extend only when the Blockchain module arrives."""

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
        previous_hash = "0" * 64
        for index, block in enumerate(self.blocks):
            if block.index != index or block.previous_hash != previous_hash:
                return False
            expected = self._hash_block(block)
            if block.hash != expected:
                return False
            previous_hash = block.hash
        return True

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
