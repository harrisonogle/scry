from __future__ import annotations

import json
import time
from pathlib import Path

from scry.jsonl import read_jsonl, sha256_file
from scry.schemas import Frame, OutlineChapter


class Run:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.frames_dir = self.root / "frames"
        self.overlays_dir = self.root / "overlays"
        self.cache_dir = self.root / "cache"
        self.frames = self.root / "frames.jsonl"
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

    def inputs_hash(self, inputs: list[Path]) -> str:
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
