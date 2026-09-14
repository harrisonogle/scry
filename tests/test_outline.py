from scry.outline import parse_outline_text


def test_parse_outline_text_handles_fences_and_bad_entries():
    text = '```json\n[{"start_s": 312, "end_s": 600, "title": "Create the cluster", "gist": "…"}, {"start_s": 0, "end_s": 312, "title": "Resource group", "gist": "g"}, {"bad": 1}]\n```'
    ch = parse_outline_text(text)
    assert [c.id for c in ch] == ["c1", "c2"] and ch[0].title == "Resource group" and ch[1].start_s == 312.0
