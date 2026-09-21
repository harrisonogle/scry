import json

import pytest

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
    # the description is about the screen, in every call and both variants (ledger L59)
    sentence = ("The description is about the whole screen, as a person looking at it would describe it, and must never "
                "mention box numbers, box ids, targets, or what was or was not requested.")
    assert paras[6].endswith("Plain prose. " + sentence)
    assert system_prompt(transcribe=False).split("\n\n")[6] == paras[6]


def test_group_only_differs_in_one_paragraph():
    full, group = system_prompt().split("\n\n"), system_prompt(transcribe=False).split("\n\n")
    assert len(full) == len(group) == 7
    assert [i for i in range(7) if full[i] != group[i]] == [5]
    assert group[5] == "Do not transcribe any text: the OCR reading of each box is used."
    assert full[6].startswith("description:") and group[6].startswith("description:")


def test_arm_d_differs_from_arm_a_only_where_intended():
    a, d = system_prompt("A").split("\n\n"), system_prompt("D").split("\n\n")
    assert len(a) == len(d) == 7 and [i for i in range(7) if a[i] != d[i]] == [1, 5]
    assert d[1] == ("You are shown one screenshot. The user message lists every piece of text an OCR engine detected on it as a "
                    "box id with its rectangle, b1: x0,y0,x1,y1, in reading order, in the coordinates it states. Use the "
                    "rectangles to know which id refers to which text on screen. The user message also names the targets: the "
                    "boxes you are asked to label.")
    assert d[5] == a[5].replace("read from Image 1", "read from the screenshot") != a[5]
    group_a, group_d = system_prompt("A", transcribe=False).split("\n\n"), system_prompt("D", transcribe=False).split("\n\n")
    assert [i for i in range(7) if group_a[i] != group_d[i]] == [1] and group_d[1] == d[1]
    for text in (system_prompt("D"), system_prompt("D", transcribe=False)):  # nothing that arm D does not send is mentioned
        assert not any(phrase in text for phrase in ("Image 1", "Image 2", "twice", "numbered box"))
    with pytest.raises(ValueError):
        system_prompt("B")  # arms B and C are not built


def test_versions():
    assert prompt_version() == "annotate-v4"
    assert prompt_version(transcribe=False) == "annotate-v4+grouponly"
    assert prompt_version(scale=0.5) == "annotate-v4+s0.5"
    assert prompt_version(transcribe=False, scale=0.67) == "annotate-v4+grouponly+s0.67"
    assert prompt_version("D") == "annotate-v4+D"
    assert prompt_version("D", scale=0.67) == "annotate-v4+D+s0.67"
    assert prompt_version("D", transcribe=False, scale=0.5) == "annotate-v4+D+grouponly+s0.5"


def test_no_sample_video_content():
    # every paid answer is cached under this text, and the evaluation checks these very containers
    sent = [system_prompt(), system_prompt(transcribe=False), system_prompt("D"), system_prompt("D", transcribe=False),
            json.dumps(output_model("A", True).model_json_schema()), json.dumps(output_model("A", False).model_json_schema())]
    for word in ("PowerShell", "Cloud Shell", "Azure", "kubectl", "msadmin"):
        assert not any(word in text for text in sent), word
