from scry.ocr.base import RawLine
from scry.schemas import RawWord
from scry.stage2a import assign_ids, is_confusable


def test_confusable_flags_mixed_script_tokens():
    assert is_confusable("3ебb0e8a-2743")      # Cyrillic е and б inside an ASCII token
    assert not is_confusable("git status")
    assert not is_confusable("naïve café")      # whole-word non-ASCII letters are fine
    assert not is_confusable("• Zone 1")


def test_assign_ids_reading_order_and_churn():
    raw = [RawLine("second", 1.0, (10, 40, 100, 58), None), RawLine("first", 1.0, (10, 10, 100, 28), None),
           RawLine("spinner text", 1.0, (500, 10, 600, 28), [RawWord(text="spinner", bbox=(500, 10, 560, 28))])]
    lines = assign_ids(raw, churn=[(490, 0, 700, 100)])
    assert [ln.id for ln in lines] == ["l1", "l2", "l3"]
    assert [ln.text for ln in lines] == ["first", "spinner text", "second"]
    assert [ln.in_churn for ln in lines] == [False, True, False]
    assert lines[1].words[0].text == "spinner"
