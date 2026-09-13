from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from vt.schemas import BBox, RawWord


@dataclass
class RawLine:
    text: str
    conf: float
    bbox: BBox
    words: list[RawWord] | None


class OcrEngine(Protocol):
    name: str

    def settings(self) -> dict: ...

    def recognize(self, png: Path) -> list[RawLine]: ...
