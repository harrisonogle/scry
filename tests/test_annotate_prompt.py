import json
import re

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


def test_versions():
    assert prompt_version() == "annotate-v4"
    assert prompt_version(transcribe=False) == "annotate-v4+grouponly"
    assert prompt_version(scale=0.5) == "annotate-v4+s0.5"
    assert prompt_version(transcribe=False, scale=0.67) == "annotate-v4+grouponly+s0.67"
    assert prompt_version(reference="coords") == "annotate-v4+coords"
    assert prompt_version(transcribe=False, scale=0.5, reference="coords") == "annotate-v4+coords+grouponly+s0.5"
    assert prompt_version(reference="ids") == prompt_version()


def test_coords_prompt_differs_only_where_a_box_is_named():
    """Under reference = "coords" the model sees no overlay and no box id: the images paragraph is replaced, and the
    assign, links and texts paragraphs name boxes by their rectangles; containers and the description are today's,
    character for character. Group-only replaces the texts paragraph by the same sentence as under ids."""
    ids, coords = system_prompt().split("\n\n"), system_prompt(reference="coords").split("\n\n")
    assert len(coords) == 7
    assert [i for i in range(7) if ids[i] != coords[i]] == [1, 3, 4, 5]
    ids_g, coords_g = system_prompt(transcribe=False).split("\n\n"), system_prompt(transcribe=False, reference="coords").split("\n\n")
    assert [i for i in range(7) if ids_g[i] != coords_g[i]] == [1, 3, 4]
    assert coords_g[5] == ids_g[5] == "Do not transcribe any text: the OCR reading of each box is used."
    assert [i for i in range(7) if coords[i] != coords_g[i]] == [5]
    for prompt in (system_prompt(reference="coords"), system_prompt(transcribe=False, reference="coords")):
        assert not re.search(r"\bb\d+\b", prompt)  # no "b1"-style id anywhere
        for phrase in ("Image 1", "Image 2", "numbered", "overlay", "point"):
            assert phrase not in prompt, phrase
        # the shared description paragraph keeps its "never mention box numbers, box ids" sentence; no other paragraph says "box id"
        assert "box id" not in "\n\n".join(prompt.split("\n\n")[:6])
    assert coords[1].startswith("You are shown one screenshot.")
    assert "Name a box by its rectangle exactly as the user message lists it." in coords[1]
    for phrase in ("rectangle", "targets", "x0,y0,x1,y1"):
        assert phrase in coords[1], phrase
    assert coords[3].startswith("assign: for every target, its rectangle")
    # every rule of today's links paragraph is kept: one link per box, runs are not separate lines, a pair needs two boxes
    head = coords[4].split("\n")[0]
    assert coords[4].startswith("links:") and "may appear in at most one link" in head and "column headings are the exception" in head
    runs = next(line for line in coords[4].split("\n") if line.startswith("  runs:"))
    pairs = next(line for line in coords[4].split("\n") if line.startswith("  pairs:"))
    records = next(line for line in coords[4].split("\n") if line.startswith("  records:"))
    assert "separate rows of a list or table and separate menu items are NOT a run, even when they follow one another" in runs
    assert "a pair needs at least two different boxes" in pairs and "give no link for it" in pairs
    assert "inside that pair's key or value and give no separate run" in pairs
    assert "lists of rectangles" in pairs and "list of rectangles" in records and "rectangles of the column headings" in records
    assert coords[4].endswith("breadcrumbs.")
    assert coords[5].startswith("texts: for every target, its rectangle") and "read from the screenshot" in coords[5]
    assert "Never correct, complete or normalize commands, code, paths or identifiers." in coords[5] and "missed: text no box covers" in coords[5]


def test_no_sample_video_content():
    # every paid answer is cached under this text, and the evaluation checks these very containers
    sent = [system_prompt(), system_prompt(transcribe=False), system_prompt(reference="coords"), system_prompt(transcribe=False, reference="coords"),
            json.dumps(output_model("A", True).model_json_schema()), json.dumps(output_model("A", False).model_json_schema()),
            json.dumps(output_model("A", True, reference="coords").model_json_schema()),
            json.dumps(output_model("A", False, reference="coords").model_json_schema())]
    for word in ("PowerShell", "Cloud Shell", "Azure", "kubectl", "msadmin"):
        assert not any(word in text for text in sent), word
