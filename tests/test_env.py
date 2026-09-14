import os
from pathlib import Path

from vt.env import load_dotenv, parse_dotenv


def test_parse_dotenv_forms():
    text = '# comment\nexport ANTHROPIC_API_KEY="sk-ant-x"\nFOO=bar # trailing comment\nEMPTY=\nnot a pair\n  SPACED = \'v v\' \n'
    assert parse_dotenv(text) == {"ANTHROPIC_API_KEY": "sk-ant-x", "FOO": "bar", "EMPTY": "", "SPACED": "v v"}


def test_load_dotenv_does_not_override_and_ignores_missing(tmp_path: Path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text("ANTHROPIC_API_KEY=from-file\nFOO=from-file\n")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("FOO", "from-env")
    assert load_dotenv(p) == ["ANTHROPIC_API_KEY"]
    assert os.environ["ANTHROPIC_API_KEY"] == "from-file" and os.environ["FOO"] == "from-env"
    assert load_dotenv(tmp_path / "missing") == []
