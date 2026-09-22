from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

from scry.jsonl import read_jsonl, sha256_file
from scry.schemas import Annotation, Change, Frame, FrameBoxes, HierNode, Interpretation, Lifetime, OutlineChapter

if TYPE_CHECKING:
    from scry.annotate.join import Labels


class Run:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.frames_dir = self.root / "frames"
        self.overlays_dir = self.root / "overlays"
        self.cache_dir = self.root / "cache"
        self.frames = self.root / "frames.jsonl"
        self.boxes = self.root / "boxes.jsonl"
        self.changes = self.root / "changes.jsonl"
        self.lifetimes = self.root / "lifetimes.jsonl"
        self.annotations = self.root / "annotations.jsonl"
        self.interpretations = self.root / "interpretations.jsonl"
        self.steps = self.root / "steps.jsonl"
        self.sections = self.root / "sections.jsonl"
        self.video = self.root / "video.json"
        self.index_db = self.root / "index.sqlite"
        self.outline = self.root / "outline.json"
        self.manifest = self.root / "manifest.json"
        self.batches = self.root / "batches.json"
        for d in (self.root, self.frames_dir, self.overlays_dir, self.cache_dir):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def video_id(self) -> str:
        return self.manifest_read().get("video_id", self.root.name)

    # ---- manifest ----
    def manifest_read(self) -> dict:
        return json.loads(self.manifest.read_text()) if self.manifest.exists() else {}

    def manifest_update(self, **kv) -> None:
        m = self.manifest_read()
        m.update(kv)
        self.manifest.write_text(json.dumps(m, indent=2, sort_keys=True, default=str))

    @staticmethod
    def inputs_hash(inputs: list[Path]) -> str:
        """What a stage's `inputs` entry holds for these files; of the paths alone, so a directory that must not be
        opened as a Run (a subset's source) can be checked against its manifest."""
        parts = [f"{p.name}:{sha256_file(p) if p.exists() else 'missing'}" for p in inputs]
        return "|".join(parts)

    def stage_up_to_date(self, name: str, inputs: list[Path], cfg_hash: str) -> bool:
        st = self.manifest_read().get("stages", {}).get(name)
        return bool(st) and st.get("inputs") == self.inputs_hash(inputs) and st.get("config") == cfg_hash

    def stage_done(self, name: str, inputs: list[Path], cfg_hash: str, **stats) -> None:
        m = self.manifest_read()
        m.setdefault("stages", {})[name] = {"inputs": self.inputs_hash(inputs), "config": cfg_hash,
                                            "finished": time.strftime("%Y-%m-%dT%H:%M:%S"), **stats}
        self.manifest.write_text(json.dumps(m, indent=2, sort_keys=True, default=str))

    # ---- loaders (§10.7) ----
    def load_frames(self) -> list[Frame]:
        return read_jsonl(self.frames, Frame)

    def load_boxes(self) -> list[FrameBoxes]:
        return read_jsonl(self.boxes, FrameBoxes)

    def load_changes(self) -> list[Change]:
        return read_jsonl(self.changes, Change)

    def load_lifetimes(self) -> list[Lifetime]:
        return read_jsonl(self.lifetimes, Lifetime)

    def load_annotations(self) -> list[Annotation]:
        return read_jsonl(self.annotations, Annotation)

    def load_labels(self) -> Labels | None:
        """The joined view of annotations.jsonl (scry.annotate.join.Labels): labels per box, frame and lifetime, joined
        onto the measured records on read. None when annotations.jsonl is absent or holds no record."""
        annotations = self.load_annotations()
        if not annotations:
            return None
        from scry.annotate.join import build_labels
        return build_labels(annotations, self.load_boxes(), self.load_lifetimes())

    def load_interpretations(self) -> dict[str, Interpretation]:
        return {r.id: r for r in read_jsonl(self.interpretations, Interpretation)}

    def load_steps(self) -> list[HierNode]:
        return read_jsonl(self.steps, HierNode)

    def load_sections(self) -> list[HierNode]:
        return read_jsonl(self.sections, HierNode)

    def load_video(self) -> HierNode | None:
        return HierNode.model_validate_json(self.video.read_text()) if self.video.exists() else None

    def load_outline(self) -> list[OutlineChapter]:
        if not self.outline.exists():
            return []
        mtime = self.outline.stat().st_mtime
        cached = getattr(self, "_outline_cache", None)
        if cached is None or cached[0] != mtime:  # chapter_of() is called once per frame and per transition
            chapters = [OutlineChapter.model_validate(c) for c in json.loads(self.outline.read_text())]
            self._outline_cache = (mtime, chapters)
        return self._outline_cache[1]

    def chapter_of(self, t: float) -> OutlineChapter | None:
        for c in self.load_outline():
            if c.start_s <= t < c.end_s:
                return c
        return None
