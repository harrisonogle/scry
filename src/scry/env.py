"""Load a git-ignored .env file into the process environment (no dependency on python-dotenv)."""
from __future__ import annotations

import os
from pathlib import Path

LOADED: list[str] = []  # keys that came from the .env file in this process (for `scry setup`)


def parse_dotenv(text: str) -> dict[str, str]:
    """KEY=VALUE per line; blank lines and # comments ignored; optional `export`; quotes stripped;
    an unquoted value loses a trailing ` # comment`."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not key or not key.replace("_", "").isalnum():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        out[key] = value
    return out


def load_dotenv(path: Path | None = None) -> list[str]:
    """Set variables from `path` (default: ./.env) that are not already in the environment. Returns the keys set."""
    path = Path(".env") if path is None else path
    if not path.is_file():
        return []
    loaded: list[str] = []
    for key, value in parse_dotenv(path.read_text()).items():
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    LOADED.extend(loaded)
    return loaded
