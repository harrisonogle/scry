"""The model-facing answer schema of `annotate`. Every field is required and none has a default; links are three
lists; no tagged union, no tuple (plan 2, D2: what the SDK's strict transform keeps as schema). The field descriptions
travel in the JSON schema, so they are prompt text: every example in them is invented."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, RootModel, create_model


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


# reference = "coords": the same shape, with a point [x, y] wherever the ids schema holds a box id. The point is described
# here once, in its $defs entry (a description beside a $ref is dropped by the SDK's strict transform); the prompt says it
# once more. A wrong-length list is not a point: code drops the reference (point_unplaced), so no schema constraint.
class OutPoint(RootModel[list[int]]):
    """A point [x, y]: a pixel inside the box's text, near its middle, in the unscaled frame's coordinates."""


class OutAssignAt(BaseModel):
    point: OutPoint
    container: str = Field(description="Id of the container the box belongs to.")


class OutRunAt(BaseModel):
    boxes: list[OutPoint] = Field(description="One point per box, in reading order.")
    joiner: Literal["", " "] = Field(description="'' when a word was cut in two, ' ' otherwise.")


class OutPairAt(BaseModel):
    key: list[OutPoint] = Field(description="One point per box of the label.")
    value: list[OutPoint] = Field(description="One point per box of its value.")


class OutRecordAt(BaseModel):
    members: list[list[OutPoint]] = Field(description="The row's cells, left to right, each a list of points, one per box.")
    header: list[OutPoint] = Field(description="One point per column heading when they are visible, otherwise [].")


class OutTextAt(BaseModel):
    point: OutPoint
    text: str = Field(description="Verbatim text inside the box; '' for an icon.")


_MODELS: dict[tuple[str, bool, bool, str], type[BaseModel]] = {}


def output_model(arm: str = "A", transcribe: bool = True, pane: bool = False, reference: str = "ids") -> type[BaseModel]:
    """The answer class of a variant, built once: equal arguments return the same class, and each variant has its own
    name, so its own JSON-schema title and schema hash in the call-cache key."""
    if arm != "A":
        raise ValueError(f"no output schema for arm {arm!r}")
    if pane:
        raise ValueError("no output schema with a pane label")
    if reference not in ("ids", "coords"):
        raise ValueError(f"no output schema for reference {reference!r}")
    key = (arm, transcribe, pane, reference)
    if key not in _MODELS:
        coords = reference == "coords"
        fields: dict = {
            "containers": (list[OutContainer], ...),
            "assign": (list[OutAssignAt if coords else OutAssign], ...),
            "unassigned": (list[OutPoint], Field(description="One point per target that belongs to no container.")) if coords
            else (list[str], Field(description="Target box ids that belong to no container.")),
            "runs": (list[OutRunAt if coords else OutRun], ...),
            "pairs": (list[OutPairAt if coords else OutPair], ...),
            "records": (list[OutRecordAt if coords else OutRecord], ...),
        }
        if transcribe:
            fields["texts"] = (list[OutTextAt if coords else OutText], ...)
            fields["missed"] = (list[OutMissed], ...)
        fields["description"] = (str, Field(description="What the boxes cannot express about this screen, in plain prose."))
        _MODELS[key] = create_model("AnnotateOut" + arm + ("Coords" if coords else "") + ("T" if transcribe else "G"), **fields)
    return _MODELS[key]
