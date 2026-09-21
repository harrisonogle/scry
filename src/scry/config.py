from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class DetectParams(BaseModel):
    theta_pix: int = 12
    theta_min: int = 8
    theta_comp: int = 24
    theta_count: int = 100
    bar_max_width: int = 3
    bar_min_height: int = 8
    bar_max_height: int = 30
    downsample: Literal[1, 2] = 1


class SettleParams(BaseModel):
    still_s: float = 0.4
    max_hold_s: float = 3.0


class ChurnParams(BaseModel):
    window_s: float = 5.0
    rho_on: float = 0.5
    rho_off: float = 0.2
    min_area: int = 400


class BlinkParams(BaseModel):
    max_w: int = 12
    max_h: int = 32
    min_period_s: float = 0.15
    max_period_s: float = 0.7
    confirm_recurrences: int = 2
    confirm_window_s: float = 3.0
    expiry_s: float = 2.0
    iou: float = 0.5


class Stage1Config(BaseModel):
    detect: DetectParams = DetectParams()
    settle: SettleParams = SettleParams()
    churn: ChurnParams = ChurnParams()
    blink: BlinkParams = BlinkParams()


class OcrConfig(BaseModel):
    engine: Literal["vision", "rapid"] = "vision"
    languages: list[str] = ["en-US"]
    language_correction: bool = False
    minimum_text_height: float = 0.0


class OverlayConfig(BaseModel):
    font_size: int = 12
    font_path: str = "/System/Library/Fonts/Menlo.ttc"
    scale: float = Field(1.0, gt=0, le=1)  # < 1 sends both Stage 2c images downscaled by this factor; tags keep font_size


Effort = Literal["low", "medium", "high", "xhigh", "max"]


class ModelConfig(BaseModel):
    provider: Literal["anthropic"] = "anthropic"
    model: str = "claude-opus-5"
    effort_stage2c: Effort = "low"
    effort_stage5: Effort = "low"
    effort_stage6: Effort = "medium"
    effort_agent: Effort = "high"
    stage2c_mark_coords: bool = False  # list each mark's box in the Stage 2c prompt (ledger L30 experiment)
    stage2c_transcribe: bool = True  # False: Stage 2c groups marks into regions and rows but transcribes nothing (§18.3 item 3 ablation)
    max_tokens: int = 16000
    retry_max_tokens: int = 32000
    concurrency: int = 4
    mode: Literal["sync", "batch"] = "sync"


class MergeConfig(BaseModel):
    row_y_tol: float = 0.5
    row_gap_lines: float = 3.0
    align_sim: float = 0.8
    align_short_len: int = 8
    align_short_lev: int = 1
    glyph_max_len: int = 2


class DiffConfig(BaseModel):
    modify_sim: float = 0.6
    typed_tolerance: int = 3
    transient_max_s: float = 2.0
    corr_w_text: float = 0.5
    corr_w_iou: float = 0.3
    corr_w_app: float = 0.1
    corr_w_name: float = 0.1
    corr_accept: float = 0.3
    pixel_gate_max_fraction: float = 0.05  # §11.2 pixel gate: veto ops on unchanged lines when this fraction of the screen or less changed; 0 = off


class HierarchyConfig(BaseModel):
    window: int = 2000
    overlap: int = 200
    fallback_step_transitions: int = 20
    fallback_section_steps: int = 8


class IndexConfig(BaseModel):
    embedder: Literal["none", "fastembed"] = "none"
    k: int = 20
    k_filtered: int = 50
    rrf: int = 60


class OutlineConfig(BaseModel):
    enabled: bool = False
    model: str = "gemini-3.8-flash"


class Config(BaseModel):
    stage1: Stage1Config = Stage1Config()
    ocr: OcrConfig = OcrConfig()
    overlay: OverlayConfig = OverlayConfig()
    model: ModelConfig = ModelConfig()
    merge: MergeConfig = MergeConfig()
    diff: DiffConfig = DiffConfig()
    hierarchy: HierarchyConfig = HierarchyConfig()
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
