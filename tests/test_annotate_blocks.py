import base64
import io
from pathlib import Path

from annotate_fixtures import fb, fixture_e, frame, mk
from PIL import Image

from scry.annotate.blocks import build_blocks, input_hashes
from scry.annotate.targets import CallPlan


def _pngs(tmp_path: Path) -> tuple[Path, Path]:
    frame_png, overlay_png = tmp_path / "frame.png", tmp_path / "overlay.png"
    Image.new("RGB", (128, 64), (128, 128, 128)).save(frame_png)
    Image.new("RGB", (128, 64), (0, 0, 0)).save(overlay_png)
    return frame_png, overlay_png


def _texts(blocks: list[dict]) -> list[str]:
    return [b["text"] for b in blocks if b["type"] == "text"]


def test_arm_a_blocks(tmp_path: Path):
    frames, boxes = fixture_e()
    frame_png, overlay_png = _pngs(tmp_path)
    blocks = build_blocks(frames[0], boxes[0], CallPlan(0, ("b1", "b2")), "A", 1.0, frame_png, overlay_png)
    assert [b["type"] for b in blocks] == ["text", "image", "text", "image", "text", "text", "text"]
    assert _texts(blocks) == ["Image 1 (clean frame 0, t=0.00s):", "Image 2 (same frame with numbered boxes):",
                              "Boxes: b1, b2.", "Targets: all boxes.", "Return the JSON object."]
    empty = build_blocks(frames[0], fb(0, []), CallPlan(0, ()), "A", 1.0, frame_png, overlay_png)
    assert _texts(empty)[2:4] == ["Boxes: none.", "Targets: none."]


def test_partial_targets_churn_and_unsettled(tmp_path: Path):
    frame_png, overlay_png = _pngs(tmp_path)
    boxes = fb(0, [mk("b1", 4, 4, 40, 20, "a", in_churn=True), mk("b2", 70, 4, 110, 20, "b")])
    blocks = build_blocks(frame(0, 128, 64, settled=False), boxes, CallPlan(0, ("b2",)), "A", 1.0, frame_png, overlay_png)
    assert _texts(blocks)[2:] == ["Boxes: b1, b2.", "Targets: b2.", "Boxes inside animating areas (low confidence): b1.",
                                  "This frame was captured while the screen was still changing (not settled).",
                                  "Return the JSON object."]


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
