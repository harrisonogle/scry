import json

from scry.annotate.output import output_model
from scry.prompts.annotate import prompt_version, system_prompt


def test_arm_a_paragraphs():
    paras = system_prompt().split("\n\n")
    starts = ["You label ", "You are shown the same screenshot twice.", "containers:", "assign:", "links:", "texts:", "description:"]
    assert len(paras) == 7 and all(p.startswith(s) for p, s in zip(paras, starts))
    assert all(part in paras[4] for part in ("  runs:", "  pairs:", "  records:")) and paras[4].endswith("breadcrumbs.")
    # a box id is in one link only, and a wrapped side of a pair goes inside the pair (ledger L53)
    head, pairs = paras[4].split("\n")[0], next(line for line in paras[4].split("\n") if line.startswith("  pairs:"))
    assert "A box id may appear in at most one link" in head
    assert "inside that pair's key or value and give no separate run" in pairs and "key [b4, b5] and value [b6]" in pairs
    # separate lines are not a run, and a pair needs two different boxes (ledger L57)
    runs = next(line for line in paras[4].split("\n") if line.startswith("  runs:"))
    assert "separate rows of a list or table and separate menu items are NOT a run, even when they follow one another" in runs
    assert "a pair needs at least two different boxes" in pairs and "give no link for it" in pairs


def test_group_only_differs_in_one_paragraph():
    full, group = system_prompt().split("\n\n"), system_prompt(transcribe=False).split("\n\n")
    assert len(full) == len(group) == 7
    assert [i for i in range(7) if full[i] != group[i]] == [5]
    assert group[5] == "Do not transcribe any text: the OCR reading of each box is used."
    assert full[6].startswith("description:") and group[6].startswith("description:")


def test_versions():
    assert prompt_version() == "annotate-v3"
    assert prompt_version(transcribe=False) == "annotate-v3+grouponly"
    assert prompt_version(scale=0.5) == "annotate-v3+s0.5"
    assert prompt_version(transcribe=False, scale=0.67) == "annotate-v3+grouponly+s0.67"


def test_no_sample_video_content():
    # every paid answer is cached under this text, and the evaluation checks these very containers
    sent = [system_prompt(), system_prompt(transcribe=False),
            json.dumps(output_model("A", True).model_json_schema()), json.dumps(output_model("A", False).model_json_schema())]
    for word in ("PowerShell", "Cloud Shell", "Azure", "kubectl", "msadmin"):
        assert not any(word in text for text in sent), word
