from __future__ import annotations

import json
from pathlib import Path

from vt.jsonl import sha256_obj


class CallCache:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(stage: str, model: str, effort: str, max_tokens: int, prompt_version: str, schema_hash: str, input_hashes: list[str]) -> str:
        return sha256_obj([stage, model, effort, max_tokens, prompt_version, schema_hash, list(input_hashes)])

    def path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str) -> dict | None:
        p = self.path(key)
        return json.loads(p.read_text()) if p.exists() else None

    def put(self, key: str, request: dict, response: dict) -> None:
        self.path(key).write_text(json.dumps({"request": request, "response": response}, indent=1, default=str))
