from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class TrackConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    margin: float = 0.5  # × the median box height of the two frames; 0 = exact touch


class AnnotateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # which frames get a call and which boxes are targets (spec §2). "every_frame": every frame, every box;
    # "incremental": the first frame and every frame whose incoming transition changed pixels, the targets being the
    # boxes whose lifetime starts there or continues there by a move; "off": the "no annotation" base. [model] mode =
    # "batch" works with each.
    # There is no `arm` key: the only referencing arm is A; `reference` below says how it names a box. Arm D was evaluated
    # and removed behind the tag `arm-d-evaluated` (ledger L63); arms B and C, which incremental annotation does not
    # serve, were never built.
    # The default is the working default of ledger L59 (incremental, transcribing), for the owner to confirm.
    mode: Literal["every_frame", "incremental", "off"] = "incremental"
    transcribe: bool = False  # true: the call also returns a second reading (texts, missed); false: group-only (the default, L73)
    scale: float = Field(1.0, gt=0, le=1)  # factor applied to every image sent; tags keep their pixel size
    # how the call refers to a box. "ids": the clean frame plus a second image with every box tagged with a number, and
    # the answer names boxes by id. "coords": the clean frame alone, every box listed as a rectangle in the unscaled
    # frame, and the answer names a box by its rectangle, which code matches back to the box (no id in either direction).
    reference: Literal["ids", "coords"] = "ids"
    box_text: bool = False  # lists each box's OCR reading in the user turn; group-only only

    @model_validator(mode="after")
    def _box_text_is_group_only(self) -> "AnnotateConfig":
        if self.box_text and self.transcribe:  # the second reading must stay independent of OCR
            raise ValueError("box_text = true needs transcribe = false: the second reading must stay independent of OCR")
        return self


class OverlayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    font_size: int = 12  # px, not scaled with the image
    font_path: str = "/System/Library/Fonts/Menlo.ttc"


Effort = Literal["low", "medium", "high", "xhigh", "max"]


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # "anthropic": the Claude API. "openai_compat": any server speaking OpenAI's /v1/chat/completions with json_schema
    # output, at base_url (a model served on this machine: mlx_vlm.server, llama.cpp); effort_* are ignored there, and
    # mode must be "sync". Its key comes from the OPENAI_COMPAT_API_KEY environment variable, "none" when unset.
    provider: Literal["anthropic", "openai_compat"] = "anthropic"
    model: str = "claude-opus-5"
    base_url: str = ""  # openai_compat only, e.g. "http://127.0.0.1:8080/v1"
    # openai_compat only, the two settings the local measurements needed (ledger L76, L78; configs/local-qwen.toml):
    # `temperature` is sent as the request's sampling temperature when set (unset: the server's own default, 1.0 for
    # the local 27B, which scrambled the pairs); `schema_in_prompt` appends the answer's JSON schema, field
    # descriptions included, to the system message as text, because a grammar runtime uses response_format only to
    # constrain the output and the model never sees the descriptions. The Claude API ignores both (its knob is
    # effort, and it shows the descriptions itself). Each changes the request, so each is in the call cache key.
    temperature: float | None = None
    schema_in_prompt: bool = False
    max_tokens: int = 16000
    retry_max_tokens: int = 32000
    concurrency: int = 4
    mode: Literal["sync", "batch"] = "sync"
    effort_annotate: Effort = "low"
    effort_interpret: Effort = "low"
    effort_summarize: Effort = "medium"
    effort_ask: Effort = "high"


class InterpretConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    images: Literal["scaled", "full"] = "scaled"  # how the two frames are sent (ledger L39)
    scale: float = Field(0.5, gt=0, le=1)  # factor; scaled: both frames downscaled by it
    context_transitions: int = 3  # transitions; the preceding ones rendered one line each


class SummarizeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window: int = 2000  # items per boundary call
    overlap: int = 200  # items shared by two consecutive windows
    fallback_step_transitions: int = 20  # transitions per step when the boundary call fails
    fallback_section_steps: int = 8  # steps per section when the boundary call fails and there is no outline


class IndexConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    embedder: Literal["none", "fastembed"] = "none"
    k: int = 20
    k_filtered: int = 50
    rrf: int = 60
    collapse: bool = True  # collapse identical consecutive frame hits in the result list


class AskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_turns: int = 12  # model turns before the loop gives up
    max_tool_result_chars: int = 60000  # characters; a JSON tool result longer than this is cut
    redecode_max_frames: int = 6  # frames one redecode call may return
    frames: bool = True  # false: no pixel reaches the agent: get_frame returns a frame's record without its image, no redecode
    model: str = ""  # the model the answering agent runs on; empty: the pipeline's, [model] model


class OutlineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    model: str = "gemini-3.8-flash"


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decode: DecodeConfig = DecodeConfig()
    read: ReadConfig = ReadConfig()
    track: TrackConfig = TrackConfig()
    annotate: AnnotateConfig = AnnotateConfig()
    interpret: InterpretConfig = InterpretConfig()
    summarize: SummarizeConfig = SummarizeConfig()
    overlay: OverlayConfig = OverlayConfig()
    model: ModelConfig = ModelConfig()
    index: IndexConfig = IndexConfig()
    ask: AskConfig = AskConfig()
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
