import base64
import io
from pathlib import Path

from annotate_fixtures import fb, fixture_e, frame, mk
from PIL import Image

from scry.annotate.blocks import build_blocks, input_hashes
from scry.annotate.output import output_model
from scry.annotate.targets import CallPlan, plan_calls
from scry.jsonl import sha256_obj
from scry.prompts.annotate import prompt_version, system_prompt
from scry.providers.cache import CallCache


def _pngs(tmp_path: Path) -> tuple[Path, Path]:
    frame_png, overlay_png = tmp_path / "frame.png", tmp_path / "overlay.png"
    Image.new("RGB", (128, 64), (128, 128, 128)).save(frame_png)
    Image.new("RGB", (128, 64), (0, 0, 0)).save(overlay_png)
    return frame_png, overlay_png


def _texts(blocks: list[dict]) -> list[str]:
    return [b["text"] for b in blocks if b["type"] == "text"]


# a call with no target is still made, for the screen description; the line says so, or the model labels every box anyway
NO_TARGETS = "Targets: none. Label no box: return every list empty and give only the description."


def test_arm_a_blocks(tmp_path: Path):
    frames, boxes = fixture_e()
    frame_png, overlay_png = _pngs(tmp_path)
    blocks = build_blocks(frames[0], boxes[0], CallPlan(0, ("b1", "b2")), "A", 1.0, frame_png, overlay_png)
    assert [b["type"] for b in blocks] == ["text", "image", "text", "image", "text", "text", "text"]
    assert _texts(blocks) == ["Image 1 (clean frame 0, t=0.00s):", "Image 2 (same frame with numbered boxes):",
                              "Boxes: b1, b2.", "Targets: all boxes.", "Return the JSON object."]
    empty = build_blocks(frames[0], fb(0, []), CallPlan(0, ()), "A", 1.0, frame_png, overlay_png)
    assert _texts(empty)[2:4] == ["Boxes: none.", NO_TARGETS]
    unchanged = build_blocks(frames[1], boxes[1], CallPlan(1, ()), "A", 1.0, frame_png, overlay_png)  # pixels changed, no box is new
    assert _texts(unchanged)[2:] == ["Boxes: b1, b2.", NO_TARGETS, "Return the JSON object."]


def test_partial_targets_churn_and_unsettled(tmp_path: Path):
    frame_png, overlay_png = _pngs(tmp_path)
    boxes = fb(0, [mk("b1", 4, 4, 40, 20, "a", in_churn=True), mk("b2", 70, 4, 110, 20, "b")])
    blocks = build_blocks(frame(0, 128, 64, settled=False), boxes, CallPlan(0, ("b2",)), "A", 1.0, frame_png, overlay_png)
    # no sentence about the description: it is in the shared system prompt (ledger L59)
    assert _texts(blocks)[2:] == ["Boxes: b1, b2.", "Targets: b2.",
                                  "Boxes inside animating areas (low confidence): b1.",
                                  "This frame was captured while the screen was still changing (not settled).",
                                  "Return the JSON object."]


COORDS = "Coordinates are pixels of the 128x64 frame: top-left origin, x1 and y1 exclusive."


def test_arm_d_blocks(tmp_path: Path):
    frames, boxes = fixture_e()
    frame_png, _ = _pngs(tmp_path)
    blocks = build_blocks(frames[0], boxes[0], CallPlan(0, ("b1", "b2")), "D", 1.0, frame_png, None)
    assert [b["type"] for b in blocks] == ["text", "image", "text", "text", "text", "text"]
    assert _texts(blocks) == ["Screenshot (frame 0, t=0.00s):", COORDS,
                              "Boxes, as id: x0,y0,x1,y1 in reading order: b1: 4,4,40,20; b2: 70,4,110,20.",
                              "Targets: all boxes.", "Return the JSON object."]
    assert blocks[1]["source"]["data"] == base64.standard_b64encode(frame_png.read_bytes()).decode()  # the clean frame as it is
    empty = build_blocks(frames[0], fb(0, []), CallPlan(0, ()), "D", 1.0, frame_png, None)
    assert _texts(empty)[2:4] == ["Boxes: none.", NO_TARGETS]
    unchanged = build_blocks(frames[1], boxes[1], CallPlan(1, ()), "D", 1.0, frame_png, None)  # the same line under both arms
    assert _texts(unchanged)[2:] == ["Boxes, as id: x0,y0,x1,y1 in reading order: b1: 4,4,40,20; b2: 70,4,110,20.", NO_TARGETS,
                                     "Return the JSON object."]
    hashes = input_hashes(frames[0], None, blocks)
    assert hashes[:2] == ["sha-0", "-"]  # no overlay is sent
    moved = fb(0, [mk("b1", 4, 4, 40, 20, "a"), mk("b2", 71, 4, 110, 20, "b")])
    other = build_blocks(frames[0], moved, CallPlan(0, ("b1", "b2")), "D", 1.0, frame_png, None)
    assert input_hashes(frames[0], None, other)[2] != hashes[2]  # the rectangles are text of the user turn, so they are hashed


def test_arm_d_blocks_at_a_reduced_scale(tmp_path: Path):
    frame_png, _ = _pngs(tmp_path)
    boxes = fb(0, [mk("b1", 4, 4, 40, 20, "a", in_churn=True), mk("b2", 70, 4, 110, 20, "b")])
    blocks = build_blocks(frame(0, 128, 64, settled=False), boxes, CallPlan(0, ("b2",)), "D", 0.5, frame_png, None)
    assert _texts(blocks) == [
        "Screenshot (frame 0, t=0.00s):",
        COORDS + " The image is scaled by 0.5; every coordinate is in the unscaled 128x64 frame.",
        "Boxes, as id: x0,y0,x1,y1 in reading order: b1: 4,4,40,20; b2: 70,4,110,20.",  # unscaled at every image scale
        "Targets: b2.", "Boxes inside animating areas (low confidence): b1.",
        "This frame was captured while the screen was still changing (not settled).", "Return the JSON object."]
    images = [b for b in blocks if b["type"] == "image"]
    assert len(images) == 1 and Image.open(io.BytesIO(base64.standard_b64decode(images[0]["source"]["data"]))).size == (64, 32)


def test_every_frame_call_is_pinned(tmp_path: Path):
    # paid answers are cached under these: the every-frame call's system prompt, version, user-turn text and key must
    # not change by a byte unless the version is bumped (ledger L56). User-turn digests taken at f0e7691 and unchanged
    # since; the system prompt's digest, the version and the key retaken at annotate-v4 (ledger L59). The one exception
    # is a frame with no box at all: its `Targets:` line is the no-target line, reworded without a version bump because
    # the user turn's text is among the input hashes, so that frame's call is asked again and no other key moves.
    frames, boxes = fixture_e()
    frame_png, overlay_png = _pngs(tmp_path)
    full = build_blocks(frames[0], boxes[0], plan_calls(boxes, [], [], "every_frame")[0], "A", 1.0, frame_png, overlay_png)
    hashes = input_hashes(frames[0], None, full)
    assert hashes == ["sha-0", "-", "7e2d9f13c1945ccb72445e3779521b37d5cc6a50ead7e7da4f8086c84983fff7"]
    none = fb(0, [])  # a frame without boxes: the no-target line in every-frame mode too
    empty = build_blocks(frames[0], none, plan_calls([none], [], [], "every_frame")[0], "A", 1.0, frame_png, overlay_png)
    assert input_hashes(frames[0], None, empty)[2] == "249b08e966da5386c54f7fc6f58d02c6359808f275377166d98f4582fc0bab5c"
    assert sha256_obj([system_prompt(), system_prompt(transcribe=False)]) == "0f7e9852109c96a3fbc04021498ed2ad727b75fc2f224a1a44d6b78153d2b55d"
    assert (prompt_version(), prompt_version(transcribe=False)) == ("annotate-v4", "annotate-v4+grouponly")
    schema = sha256_obj(output_model("A", True).model_json_schema())
    assert CallCache.key("annotate", "fake-model", "high", 1000, prompt_version(), schema, hashes) == \
        "448903502de4a7561ec4ee24874fddfe8102a7886e52e0e8208473b70dad4958"


def test_scale_halves_the_clean_frame_in_memory(tmp_path: Path):
    frames, boxes = fixture_e()
    frame_png, overlay_png = _pngs(tmp_path)
    before = sorted(p.name for p in tmp_path.iterdir())
    half = build_blocks(frames[0], boxes[0], CallPlan(0, ("b1", "b2")), "A", 0.5, frame_png, overlay_png)
    assert Image.open(io.BytesIO(base64.standard_b64decode(half[1]["source"]["data"]))).size == (64, 32)
    assert sorted(p.name for p in tmp_path.iterdir()) == before  # nothing written
    full = build_blocks(frames[0], boxes[0], CallPlan(0, ("b1", "b2")), "A", 1.0, frame_png, overlay_png)
    assert full[1]["source"]["data"] == base64.standard_b64encode(frame_png.read_bytes()).decode()


def test_no_ocr_text_is_sent(tmp_path: Path):
    frames, _ = fixture_e()
    frame_png, overlay_png = _pngs(tmp_path)
    boxes = fb(0, [mk("b1", 4, 4, 40, 20, "SECRET-A"), mk("b2", 70, 4, 110, 20, "SECRET-B")])
    for arm, overlay in (("A", overlay_png), ("D", None)):  # arm D lists ids and rectangles, never what OCR read
        blocks = build_blocks(frames[0], boxes, CallPlan(0, ("b1", "b2")), arm, 1.0, frame_png, overlay)
        assert not any("SECRET" in t for t in _texts(blocks))


def test_input_hashes(tmp_path: Path):
    frames, boxes = fixture_e()
    frame_png, overlay_png = _pngs(tmp_path)

    def hashes(targets, overlay=overlay_png):
        blocks = build_blocks(frames[0], boxes[0], CallPlan(0, targets), "A", 1.0, frame_png, overlay_png)
        return input_hashes(frames[0], overlay, blocks)

    base = hashes(("b1", "b2"))
    assert len(base) == 3 and base[0] == "sha-0"
    fewer = hashes(("b2",))
    assert fewer[:2] == base[:2] and fewer[2] != base[2]
    Image.new("RGB", (128, 64), (255, 255, 255)).save(overlay_png)
    redrawn = hashes(("b1", "b2"))
    assert redrawn[0] == base[0] and redrawn[1] != base[1] and redrawn[2] == base[2]
    assert hashes(("b1", "b2"), overlay=None)[1] == "-"
