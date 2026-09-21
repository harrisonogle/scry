import scry.prompts.ask
import scry.prompts.interpret
import scry.prompts.summarize
from scry.ask import TOOL_DEFS


def _prompts() -> tuple[list[str], list[str]]:
    """The system prompts of plan 3, and every text a model reads from it (the prompts and the tool descriptions)."""
    systems = [scry.prompts.interpret.SYSTEM, scry.prompts.summarize.BOUNDARY_SYSTEM, scry.prompts.summarize.ELABORATE_SYSTEM,
               scry.prompts.ask.SYSTEM]
    return systems, systems + [d["description"] for d in TOOL_DEFS]


def test_prompts_hold_the_rulings():
    """Only the owner's rulings: `submitted` is there; no focus; nothing of the sample video. Nothing else about the
    wording is pinned. Whitespace runs are collapsed first because the prompt text is hard-wrapped."""
    systems, texts = _prompts()
    for s in systems:
        assert "submitted" in " ".join(s.split())
    for s in texts:
        flat = " ".join(s.split())
        for banned in ("focus", "az ", "kubectl"):
            assert banned not in flat, banned
    assert scry.prompts.interpret.VERSION == "interpret-v1"
    assert scry.prompts.summarize.VERSION == "summarize-v1"
    assert scry.prompts.ask.VERSION == "ask-v1"
