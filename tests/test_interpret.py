import base64
import io
from pathlib import Path

from PIL import Image

from scry.config import Config, Stage5Config
from scry.interpret import build_blocks, crop_boxes, image_mode, prompt_version, render_diff, render_transition_line, run_interpret, validate_refs
from scry.jsonl import write_jsonl
from scry.providers.base import VlmResult
from scry.run import Run
from scry.schemas import DiffOp, Event, FrameRecord, Line, PixelChange, Region, RegionDiff, Transition, TransientInfo, VlmInterpretation, VlmRefs


def ln(i, text, y, agree=True, vlm=None):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(10, y, 300, y + 18), ocr=text, ocr_conf=1, vlm=vlm or text, agree=agree, in_churn=False)


def frame(n, lines, png="", size=(1, 1)):
    reg = Region(id="r1", kind="window", name="Terminal", app="Windows Terminal", parent=None, bbox=(10, 40, 300, 400), conf=0.9, layout_conf=0.4, lines=lines)
    return FrameRecord(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=True, png=png, overlay=None, sha256=f"sha{n}",
                       width=size[0], height=size[1], regions=[reg])


def test_render_diff_shows_both_readings_and_uncertain_grouping():
    a = frame(1, [ln(1, "PS> gi", 40)])
    b = frame(2, [ln(1, "PS> git status", 40), ln(2, "On branch maln", 60, agree=False, vlm="On branch main")])
    t = Transition(id="T1", from_frame=1, to_frame=2, t=(2.0, 2.1), kind="single",
                   computed_diff={"r1": RegionDiff(from_region="r1", ops=[DiffOp(op="modify", old="PS> gi", new="PS> git status", old_index=0, new_index=0, y=40),
                                                                       DiffOp(op="insert", new="On branch maln", new_index=1, y=60, uncertain=True)])},
                   events=[Event(type="typed", region="r1", text="t status", line="PS> git status", frames=(1, 2))])
    text = render_diff(t, {1: a, 2: b})
    assert "Terminal" in text and "modify" in text and "PS> git status" in text
    assert "OCR: On branch maln" in text and "VLM: On branch main" in text
    assert "grouping uncertain" in text
    assert 'typed "t status"' in render_transition_line(t, {1: a, 2: b})


def test_render_diff_names_the_pane_an_op_came_from():
    nav = Region(id="r2", kind="pane", name="left navigation", app="Azure Portal", parent="r1", bbox=(10, 60, 100, 400), conf=0.9, layout_conf=0.9,
                 lines=[ln(2, "Overview", 60), ln(3, "Node pools", 80)])
    a, b = frame(1, [ln(1, "title", 40)]), frame(2, [ln(1, "title", 40)])
    b.regions.append(nav)
    t = Transition(id="T1", from_frame=1, to_frame=2, t=(2.0, 2.1), kind="single",
                   computed_diff={"r1": RegionDiff(from_region="r1", ops=[DiffOp(op="insert", new="Node pools", new_index=2, y=80, pane="r2"),
                                                                       DiffOp(op="delete", old="gone", old_index=1, y=60, pane="r7")])})
    text = render_diff(t, {1: a, 2: b})
    assert '  insert: "Node pools" [pane: left navigation]' in text
    assert '  delete: "gone" [pane: r7]' in text  # an id the from-frame does not know is shown as is
    assert "readings disagree" not in text


def test_render_diff_ends_the_ops_with_the_changed_pixel_line():
    a, b = frame(1, [ln(1, "x", 40)]), frame(2, [ln(1, "x", 40)])
    t = Transition(id="T1", from_frame=1, to_frame=2, t=(2.0, 2.1), kind="single",
                   pixels=PixelChange(changed_fraction=0.000227, components=[(1, 2, 3, 4), (5, 6, 7, 8)], vetoed=3))
    text = render_diff(t, {1: a, 2: b})
    assert text == "No text changes were computed; look for non-textual change.\nPixels changed: 0.02% of the screen in 2 areas"
    assert "Pixels changed" not in render_diff(Transition(id="T1", from_frame=1, to_frame=2, t=(2.0, 2.1), kind="single"), {1: a, 2: b})


def test_validate_refs_drops_unknown_frames_and_lines():
    a = frame(1, [ln(1, "x", 40)])
    b = frame(2, [ln(1, "x", 40), ln(2, "y", 60)])
    valid, bad = validate_refs(["2:l2", "1:l1", "3:l1", "2:l9", "junk"], [a, b])
    assert valid == ["2:l2", "1:l1"] and bad == 3


# ---------- Stage 5 image modes ----------
W, H = 400, 200
COMPONENTS = [(100, 50, 120, 70), (300, 150, 320, 170)]  # padded by 40: (60,10,160,110) and (260,110,360,200) after clamping


def _run_with_frames(tmp_path: Path, n: int = 3) -> tuple[Run, dict[int, FrameRecord]]:
    """A run directory with n synthetic 400x200 frames (a different square on each) and matching FrameRecords."""
    run = Run(tmp_path)
    frames = {}
    for k in range(1, n + 1):
        img = Image.new("RGB", (W, H), "white")
        img.paste((0, 0, 0), (100 + 5 * k, 50, 120 + 5 * k, 70))
        img.save(run.frames_dir / f"{k:05d}.png")
        frames[k] = frame(k, [ln(1, "x", 40)], png=f"frames/{k:05d}.png", size=(W, H))
    return run, frames


def _transition(pixels=PixelChange(changed_fraction=0.01, components=COMPONENTS), transient=False, **kw) -> Transition:
    if transient:
        return Transition(id="T1", from_frame=1, to_frame=3, t=(3.0, 3.1), kind="transient_merged", pixels=pixels,
                          transient=TransientInfo(frame=2, region="r1", name="Terminal", hold_s=0.5), **kw)
    return Transition(id="T1", from_frame=1, to_frame=2, t=(2.0, 2.1), kind="single", pixels=pixels, **kw)


def _images(blocks) -> list[Image.Image]:
    return [Image.open(io.BytesIO(base64.b64decode(b["source"]["data"]))) for b in blocks if b["type"] == "image"]


def _texts(blocks) -> str:
    return "\n".join(b["text"] for b in blocks if b["type"] == "text")


def test_full_mode_sends_both_frames_at_native_size_and_is_the_default(tmp_path: Path):
    run, frames = _run_with_frames(tmp_path)
    blocks = build_blocks(_transition(), frames, run, None, [], Stage5Config(images="full"))
    assert [im.size for im in _images(blocks)] == [(W, H), (W, H)]
    assert blocks == build_blocks(_transition(), frames, run, None, [])  # no config = full
    with_mid = build_blocks(_transition(transient=True), frames, run, None, [], Stage5Config())
    assert [im.size for im in _images(with_mid)] == [(W, H)] * 3 and "Transient frame 2" in _texts(with_mid)
    assert _texts(blocks).endswith("Return the JSON object.") and "Computed changes:" in _texts(blocks)


def test_scaled_mode_downscales_every_frame(tmp_path: Path):
    run, frames = _run_with_frames(tmp_path)
    blocks = build_blocks(_transition(transient=True), frames, run, None, [], Stage5Config(images="scaled", scale=0.5))
    assert [im.size for im in _images(blocks)] == [(W // 2, H // 2)] * 3
    assert "downscaled by 0.5" in _texts(blocks)


def test_crops_mode_sends_a_context_frame_and_paired_full_resolution_crops(tmp_path: Path):
    run, frames = _run_with_frames(tmp_path)
    blocks = build_blocks(_transition(), frames, run, None, [], Stage5Config(images="crops", scale=0.5, crop_pad=40, crop_max=4))
    sizes = [im.size for im in _images(blocks)]
    assert sizes == [(W // 2, H // 2), (100, 100), (100, 100), (100, 90), (100, 90)]  # context, then before/after per area
    text = _texts(blocks)
    assert "Area 1 (60,10,160,110) in frame 1 (before):" in text and "Area 1 in frame 2 (after):" in text
    assert "Area 2 (260,110,360,200) in frame 1 (before):" in text
    # the before-crop and the after-crop of area 1 differ (the square moved), so the model can compare them
    ims = _images(blocks)
    assert ims[1].tobytes() != ims[2].tobytes()


def test_crops_mode_adds_a_full_resolution_crop_of_the_transient_region(tmp_path: Path):
    run, frames = _run_with_frames(tmp_path)
    blocks = build_blocks(_transition(transient=True), frames, run, None, [], Stage5Config(images="crops"))
    sizes = [im.size for im in _images(blocks)]
    # context (frame 3), transient frame scaled, transient region crop (bbox 10,40,300,400 padded and clamped to 0,0,340,200), then 2 areas x 2
    assert sizes == [(W // 2, H // 2), (W // 2, H // 2), (340, 200), (100, 100), (100, 100), (100, 90), (100, 90)]
    assert "Region 'Terminal' of frame 2 at full resolution (0,0,340,200" in _texts(blocks)


def test_crops_mode_falls_back_to_scaled_without_usable_pixel_data(tmp_path: Path):
    run, frames = _run_with_frames(tmp_path)
    s5 = Stage5Config(images="crops", crop_max_fraction=0.25)
    for t in (_transition(pixels=None), _transition(pixels=PixelChange(changed_fraction=0.3, components=COMPONENTS)),
              _transition(pixels=PixelChange(changed_fraction=0.01, components=[]))):
        assert image_mode(t, s5) == "scaled"
        assert [im.size for im in _images(build_blocks(t, frames, run, None, [], s5))] == [(W // 2, H // 2)] * 2
    assert image_mode(_transition(pixels=PixelChange(changed_fraction=0.25, components=COMPONENTS)), s5) == "crops"  # at the threshold
    assert image_mode(_transition(pixels=None), Stage5Config(images="full")) == "full"


def test_text_mode_sends_no_images(tmp_path: Path):
    run, frames = _run_with_frames(tmp_path)
    blocks = build_blocks(_transition(transient=True), frames, run, None, [], Stage5Config(images="text"))
    assert _images(blocks) == []
    text = _texts(blocks)
    assert "no screenshots are attached" in text and "Transient frame 2" in text and "Pixels changed: 1.00%" in text


def test_crop_boxes_pad_clamp_merge_and_cap():
    assert crop_boxes(COMPONENTS, W, H, 40, 4) == [(60, 10, 160, 110), (260, 110, 360, 200)]
    # overlapping after padding → one rectangle; clamped at the frame origin
    assert crop_boxes([(10, 10, 20, 20), (30, 30, 40, 40), (500, 500, 510, 510)], 600, 600, 40, 4) == [(0, 0, 80, 80), (460, 460, 550, 550)]
    # more than the cap: the nearest pair merges (never dropped), so every component stays covered
    comps = [(0, 0, 10, 10), (100, 0, 110, 10), (300, 0, 310, 10), (0, 300, 10, 310), (300, 300, 310, 310), (150, 150, 160, 160)]
    out = crop_boxes(comps, 1000, 1000, 5, 4)
    assert len(out) == 4
    assert all(any(b[0] <= x0 and b[1] <= y0 and b[2] >= x1 and b[3] >= y1 for b in out) for x0, y0, x1, y1 in comps)
    assert out == sorted(out, key=lambda b: (b[1], b[0]))
    assert crop_boxes([], W, H, 40, 4) == []


def test_prompt_version_names_the_mode_and_its_parameters():
    assert prompt_version() == prompt_version(Stage5Config()) == "s5-v1"
    assert prompt_version(Stage5Config(images="text")) == "s5-v1+text"
    assert prompt_version(Stage5Config(images="scaled", scale=0.5)) == "s5-v1+scaled0.5"
    assert prompt_version(Stage5Config(images="crops")) == "s5-v1+crops0.5p40m4f0.25"
    assert prompt_version(Stage5Config(images="crops", scale=0.4)) != prompt_version(Stage5Config(images="crops"))


class FakeProvider:
    model = "fake-model"

    def __init__(self):
        self.calls = []
        self.usage_by_stage = {"stage5": {"input_tokens": 12, "output_tokens": 3}}
        self.stats = {"hits": 0, "misses": 0}

    async def complete(self, *, stage, system, blocks, output_model, effort, prompt_version, input_hashes):
        self.calls.append({"stage": stage, "blocks": blocks, "prompt_version": prompt_version, "effort": effort})
        self.stats["misses"] += 1
        return VlmResult(VlmInterpretation(action="clicked", result="r", description="d", confidence=0.7, refs=VlmRefs(lines=["2:l1", "2:l9"])), None)


def test_run_interpret_records_the_image_mode_and_fallbacks_in_the_manifest(tmp_path: Path):
    run, frames = _run_with_frames(tmp_path)
    write_jsonl(run.frames, frames.values())
    ts = [_transition(), Transition(id="T2", from_frame=2, to_frame=3, t=(3.0, 3.1), kind="single", pixels=None),
          Transition(id="T3", from_frame=2, to_frame=3, t=(3.0, 3.1), kind="trivial")]
    write_jsonl(run.transitions, ts)
    cfg = Config(stage5=Stage5Config(images="crops"))
    provider = FakeProvider()
    run_interpret(run, cfg, provider)
    st = run.manifest_read()["stages"]["interpret"]
    assert st["images"] == "crops" and st["image_fallbacks"] == 1 and st["transitions"] == 3 and st["invalid_refs"] == 2  # "2:l9" in both
    assert st["usage"] == {"input_tokens": 12, "output_tokens": 3} and st["model"] == "fake-model"
    assert [c["prompt_version"] for c in provider.calls] == ["s5-v1+crops0.5p40m4f0.25"] * 2
    assert [len(_images(c["blocks"])) for c in provider.calls] == [5, 2]  # crops for T1; T2 fell back to scaled
    out = run.load_interpretations()
    assert out["T1"].action == "clicked" and out["T1"].refs.lines == ["2:l1"] and out["T1"].prompt_version == "s5-v1+crops0.5p40m4f0.25"
    assert out["T3"].error == "trivial"
    run_interpret(run, cfg, provider)  # up to date: no further calls
    assert len(provider.calls) == 2
    run_interpret(run, Config(stage5=Stage5Config(images="text")), provider)  # a different mode is a different config hash
    assert len(provider.calls) == 4 and provider.calls[-1]["prompt_version"] == "s5-v1+text"
    assert run.manifest_read()["stages"]["interpret"]["images"] == "text"
