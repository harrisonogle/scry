from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def text_block(s: str) -> dict:
    return {"type": "text", "text": s}


def image_block(png: Path) -> dict:
    data = base64.standard_b64encode(png.read_bytes()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}


@dataclass
class VlmResult:
    parsed: BaseModel | None
    error: str | None
    usage: dict = field(default_factory=dict)
    raw_text: str | None = None
    cached: bool = False
    stop_reason: str | None = None


class VlmProvider(Protocol):
    model: str

    async def complete(self, *, stage: str, system: str, blocks: list[dict], output_model: type[T], effort: str,
                       prompt_version: str, input_hashes: list[str]) -> VlmResult: ...
