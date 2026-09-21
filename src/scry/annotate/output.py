"""The model-facing answer schema of `annotate`. Every field is required and none has a default; links are three
lists; no tagged union, no tuple (plan 2, D2: what the SDK's strict transform keeps as schema). The field descriptions
travel in the JSON schema, so they are prompt text: every example in them is invented."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, create_model


class OutContainer(BaseModel):
    id: str = Field(description="Container id: c1, c2, … unique in this answer.")
    kind: Literal["window", "popup"] = Field(
        description="window = top-level application window; popup = menu, dialog, tooltip, toast: anything drawn over a window.")
    app: str = Field(description="Application the container belongs to, e.g. 'Spreadsheet', 'Mail', 'Code editor'.")
    name: str = Field(description="The container's title as shown, or a short human name, e.g. 'Export dialog', 'tooltip: Zoom in'.")
    owner: str | None = Field(description="For a popup, the id of the window it belongs to, or null. Always null for a window.")
    covers: list[str] = Field(description="Ids of the containers this one is drawn over, in whole or in part.")


class OutAssign(BaseModel):
    box: str = Field(description="A target box id, e.g. 'b7'.")
    container: str = Field(description="Id of the container the box belongs to.")


class OutRun(BaseModel):
    boxes: list[str] = Field(description="Box ids in reading order.")
    joiner: Literal["", " "] = Field(description="'' when a word was cut in two, ' ' otherwise.")


class OutPair(BaseModel):
    key: list[str] = Field(description="Box ids of the label.")
    value: list[str] = Field(description="Box ids of its value.")


class OutRecord(BaseModel):
    members: list[list[str]] = Field(description="The row's cells, left to right, each a list of box ids.")
    header: list[str] = Field(description="Box ids of the column headings when they are visible, otherwise [].")


class OutText(BaseModel):
    box: str
    text: str = Field(description="Verbatim text inside the box; '' for an icon.")


class OutMissed(BaseModel):
    text: str = Field(description="Verbatim text that no box covers.")
    container: str | None = Field(description="Id of its container, or null.")


_MODELS: dict[tuple[str, bool, bool], type[BaseModel]] = {}


def output_model(arm: str = "A", transcribe: bool = True, pane: bool = False) -> type[BaseModel]:
    """The answer class of a variant, built once: equal arguments return the same class, and each variant has its own
    name, so its own JSON-schema title and schema hash in the call-cache key. Arm D asks for exactly what arm A asks
    for, so it has arm A's classes; its calls are kept apart in the call cache by the prompt version and the user turn."""
    if arm == "D":
        arm = "A"
    if arm != "A":
        raise ValueError(f"no output schema for arm {arm!r}")
    if pane:
        raise ValueError("no output schema with a pane label")
    key = (arm, transcribe, pane)
    if key not in _MODELS:
        fields: dict = {
            "containers": (list[OutContainer], ...),
            "assign": (list[OutAssign], ...),
            "unassigned": (list[str], Field(description="Target box ids that belong to no container.")),
            "runs": (list[OutRun], ...),
            "pairs": (list[OutPair], ...),
            "records": (list[OutRecord], ...),
        }
        if transcribe:
            fields["texts"] = (list[OutText], ...)
            fields["missed"] = (list[OutMissed], ...)
        fields["description"] = (str, Field(description="What the boxes cannot express about this screen, in plain prose."))
        _MODELS[key] = create_model("AnnotateOut" + arm + ("T" if transcribe else "G"), **fields)
    return _MODELS[key]
