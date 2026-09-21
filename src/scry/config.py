from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DetectParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theta_pix: int = 12
    theta_min: int = 8
    theta_comp: int = 24
    theta_count: int = 100
    bar_max_width: int = 3
    bar_min_height: int = 8
    bar_max_height: int = 30
    downsample: Literal[1, 2] = 1


class SettleParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    still_s: float = 0.4
    max_hold_s: float = 3.0


class ChurnParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window_s: float = 5.0
    rho_on: float = 0.5
    rho_off: float = 0.2
    min_area: int = 400


class BlinkParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_w: int = 12
    max_h: int = 32
    min_period_s: float = 0.15
    max_period_s: float = 0.7
    confirm_recurrences: int = 2
    confirm_window_s: float = 3.0
    expiry_s: float = 2.0
    iou: float = 0.5


class DecodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detect: DetectParams = DetectParams()
    settle: SettleParams = SettleParams()
    churn: ChurnParams = ChurnParams()
    blink: BlinkParams = BlinkParams()


class ReadConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    engine: Literal["rapid"] = "rapid"  # RapidOCR 3.9 is the only reader (ledger L36, L43)
    gap_ratio: float = 0.25  # spacing guard: a gap of at least this × the box height between two words is a space


class OverlayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    font_size: int = 12
    font_path: str = "/System/Library/Fonts/Menlo.ttc"
    scale: float = Field(1.0, gt=0, le=1)  # < 1 sends both Stage 2c images downscaled by this factor; tags keep font_size
    # Stage 2c masking experiment (group-only mode): cover every OCR box in both images. opaque = light grey fill, tag
    # outside as usual; opaque_label = grey fill with the tag inside the box; rendered = white fill with the OCR text
    # re-set in font_path at the box height. none = the frame as is.
    mask: Literal["none", "opaque", "opaque_label", "rendered"] = "none"


Effort = Literal["low", "medium", "high", "xhigh", "max"]


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["anthropic"] = "anthropic"
    model: str = "claude-opus-5"
    max_tokens: int = 16000
    retry_max_tokens: int = 32000
    concurrency: int = 4
    mode: Literal["sync", "batch"] = "sync"


class IndexConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    embedder: Literal["none", "fastembed"] = "none"
    k: int = 20
    k_filtered: int = 50
    rrf: int = 60


class OutlineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    model: str = "gemini-3.8-flash"


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decode: DecodeConfig = DecodeConfig()
    read: ReadConfig = ReadConfig()
    overlay: OverlayConfig = OverlayConfig()
    model: ModelConfig = ModelConfig()
    index: IndexConfig = IndexConfig()
    outline: OutlineConfig = OutlineConfig()


def load_config(path: Path | None = None) -> Config:
    """Load scry.toml (or the given path); missing file means defaults."""
    if path is None:
        path = Path("scry.toml")
    if not path.exists():
        return Config()
    with path.open("rb") as f:
        return Config.model_validate(tomllib.load(f))


def config_hash(cfg: Config, *sections: str) -> str:
    """SHA-256 of the named top-level sections (all sections if none given)."""
    data = cfg.model_dump()
    if sections:
        data = {s: data[s] for s in sections}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
