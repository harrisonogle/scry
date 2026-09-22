import base64
import io
import re
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
    blocks = build_blocks(frames[0], boxes, CallPlan(0, ("b1", "b2")), "A", 1.0, frame_png, overlay_png)
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


# ---------- reference = "coords": no overlay, no box id in either direction ----------
COORDS = "Coordinates are pixels of the 128x64 frame: top-left origin, x1 and y1 exclusive."
BOX_ID = re.compile(r"\bb\d+\b")


def test_coords_blocks(tmp_path: Path):
    frames, boxes = fixture_e()
    frame_png, _ = _pngs(tmp_path)
    blocks = build_blocks(frames[0], boxes[0], CallPlan(0, ("b1", "b2")), "A", 1.0, frame_png, None, reference="coords")
    assert [b["type"] for b in blocks] == ["text", "image", "text", "text", "text", "text"]
    assert _texts(blocks) == ["Screenshot (frame 0, t=0.00s):", COORDS,
                              "Boxes, as x0,y0,x1,y1 in reading order: 4,4,40,20; 70,4,110,20.", "Targets: all boxes.",
                              "Return the JSON object."]
    assert blocks[1]["source"]["data"] == base64.standard_b64encode(frame_png.read_bytes()).decode()  # the clean frame, as it is
    empty = build_blocks(frames[0], fb(0, []), CallPlan(0, ()), "A", 1.0, frame_png, None, reference="coords")
    assert _texts(empty)[2:4] == ["Boxes: none.", NO_TARGETS]
    churn = fb(0, [mk("b1", 4, 4, 40, 20, "a", in_churn=True), mk("b2", 70, 4, 110, 20, "b")])
    partial = build_blocks(frame(0, 128, 64, settled=False), churn, CallPlan(0, ("b2",)), "A", 1.0, frame_png, None, reference="coords")
    assert _texts(partial)[2:] == ["Boxes, as x0,y0,x1,y1 in reading order: 4,4,40,20; 70,4,110,20.", "Targets: 70,4,110,20.",
                                   "Boxes inside animating areas (low confidence): 4,4,40,20.",
                                   "This frame was captured while the screen was still changing (not settled).",
                                   "Return the JSON object."]
    for turn in (blocks, empty, partial):
        assert not any(BOX_ID.search(t) for t in _texts(turn))  # no id anywhere: the answer comes back as points


def test_coords_at_half_scale(tmp_path: Path):
    """Below scale 1 every rectangle is in the pixels of the image sent, rounded outward as the overlay rounds, and the
    coordinates sentence names that image and no unscaled frame (ledger L71)."""
    frames, boxes = fixture_e()
    frame_png, _ = _pngs(tmp_path)
    before = sorted(p.name for p in tmp_path.iterdir())
    half = build_blocks(frames[0], boxes[0], CallPlan(0, ("b2",)), "A", 0.5, frame_png, None, reference="coords")
    assert Image.open(io.BytesIO(base64.standard_b64decode(half[1]["source"]["data"]))).size == (64, 32)
    assert _texts(half) == ["Screenshot (frame 0, t=0.00s):",
                            "Coordinates are pixels of the 64x32 image you are shown: top-left origin, x1 and y1 exclusive.",
                            "Boxes, as x0,y0,x1,y1 in reading order: 2,2,20,10; 35,2,55,10.", "Targets: 35,2,55,10.",
                            "Return the JSON object."]
    assert not any("unscaled" in t or "128x64" in t for t in _texts(half))
    assert sorted(p.name for p in tmp_path.iterdir()) == before  # nothing written: no overlay, no scaled frame
    # odd pixels round outward, and the animating line is in the same pixels
    churn = fb(0, [mk("b1", 5, 5, 41, 21, "a", in_churn=True), mk("b2", 70, 4, 110, 20, "b")])
    two_thirds = build_blocks(frames[0], churn, CallPlan(0, ("b2",)), "A", 0.67, frame_png, None, reference="coords")
    assert Image.open(io.BytesIO(base64.standard_b64decode(two_thirds[1]["source"]["data"]))).size == (86, 43)
    assert _texts(two_thirds)[1:5] == ["Coordinates are pixels of the 86x43 image you are shown: top-left origin, x1 and y1 exclusive.",
                                       "Boxes, as x0,y0,x1,y1 in reading order: 3,3,28,15; 46,2,74,14.", "Targets: 46,2,74,14.",
                                       "Boxes inside animating areas (low confidence): 3,3,28,15."]
    # at scale 1 the turn is what it always was, byte for byte
    full = build_blocks(frames[0], boxes[0], CallPlan(0, ("b2",)), "A", 1.0, frame_png, None, reference="coords")
    assert _texts(full) == ["Screenshot (frame 0, t=0.00s):", COORDS,
                            "Boxes, as x0,y0,x1,y1 in reading order: 4,4,40,20; 70,4,110,20.", "Targets: 70,4,110,20.",
                            "Return the JSON object."]


def test_coords_sends_no_overlay_and_no_ocr_text(tmp_path: Path):
    frames, _ = fixture_e()
    frame_png, _ = _pngs(tmp_path)
    boxes = fb(0, [mk("b1", 4, 4, 40, 20, "SECRET-A"), mk("b2", 70, 4, 110, 20, "SECRET-B")])
    blocks = build_blocks(frames[0], boxes, CallPlan(0, ("b1", "b2")), "A", 1.0, frame_png, None, reference="coords")
    assert not any("SECRET" in t for t in _texts(blocks))
    hashes = input_hashes(frames[0], None, blocks)
    assert hashes[0] == "sha-0" and hashes[1] == "-"
    fewer = build_blocks(frames[0], boxes, CallPlan(0, ("b2",)), "A", 1.0, frame_png, None, reference="coords")
    assert input_hashes(frames[0], None, fewer)[2] != hashes[2]  # the targets line is in the hashed text
