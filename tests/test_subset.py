import json
from pathlib import Path

import pytest
from PIL import Image

from scry.jsonl import write_jsonl
from scry.run import Run
from scry.schemas import Frame
from scry.subset import make_subset, parse_frames


def _source(tmp_path: Path) -> Run:
    src = Run(tmp_path / "src")
    recs = []
    for n in range(4):
        Image.new("L", (8, 8), 40 * n).save(src.frames_dir / f"{n:05d}.png")
        recs.append(Frame(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=n != 2,
                          width=8, height=8, sha256=f"{n:064x}", png=f"frames/{n:05d}.png"))
    write_jsonl(src.frames, recs)
    src.manifest_update(video="v.mp4", video_sha256="abc", video_id="v", fps=30.0, duration=4.0, width=8, height=8)
    src.stage_done("decode", [tmp_path / "v.mp4"], "cfg", emitted=4, settled=3)
    (src.cache_dir / "k.json").write_text("{}")
    return src


# One boxes.jsonl line per frame, written by hand: a key `read` would not write back (`seconds`), so a copy that went
# through the schema would not be byte-identical, and a bbox as a list, which the schema also normalises.
BOX_LINES = [b'{"frame": %d, "png": "frames/%05d.png", "engine": {"engine": "rapidocr"}, "seconds": 0.%d, '
             b'"boxes": [{"id": "b1", "bbox": [1, 2, 3, %d], "text": "t%d", "conf": 0.9}]}\n' % (n, n, n + 1, n + 4, n)
             for n in range(4)]
READ_STATS = {"frames": 4, "boxes": 4, "dropped_empty": 1, "seconds": 8.0, "seconds_per_frame": 2.0, "engine": {"engine": "rapidocr"}}


def _with_ocr(src: Run, config: str = "rc") -> Run:
    """The source after a finished `read`: its boxes.jsonl and the manifest entry read's own up-to-date check reads."""
    src.boxes.write_bytes(b"".join(BOX_LINES))
    src.stage_done("read", [src.frames], config, **READ_STATS)
    return src


def _listing(root: Path):
    return sorted((str(p.relative_to(root)), p.read_bytes() if p.is_file() else None) for p in root.rglob("*"))


def test_parse_frames():
    assert parse_frames("145-155") == (145, 155)
    assert parse_frames("7") == (7, 7)
    with pytest.raises(ValueError):
        parse_frames("9-3")


def test_subset_keeps_range_and_marks_decode_done(tmp_path):
    src = _source(tmp_path)
    dst = make_subset(src.root, tmp_path / "sub", (1, 2))
    assert [r.frame for r in dst.load_frames()] == [1, 2]
    assert (dst.root / "frames/00001.png").exists() and not (dst.root / "frames/00000.png").exists()
    m = dst.manifest_read()
    assert m["video"] == "v.mp4" and m["video_id"] == "v" and m["fps"] == 30.0
    assert m["subset"] == {"source": str(src.root), "frames": [1, 2]}
    st = m["stages"]["decode"]
    assert st["inputs"] == src.manifest_read()["stages"]["decode"]["inputs"] and st["config"] == "cfg"
    assert st["emitted"] == 2 and st["settled"] == 1
    assert dst.stage_up_to_date("decode", [tmp_path / "v.mp4"], "cfg")  # `scry run` will skip decoding
    assert "read" not in m["stages"]


def test_subset_shares_the_source_call_cache(tmp_path):
    src = _source(tmp_path)
    dst = make_subset(src.root, tmp_path / "sub", (0, 3))
    assert dst.cache_dir.is_symlink() and (dst.cache_dir / "k.json").exists()
    (dst.cache_dir / "new.json").write_text("{}")
    assert (src.cache_dir / "new.json").exists()
    again = Run(dst.root)  # re-opening the run must tolerate the symlinked cache directory
    assert again.cache_dir.is_dir()


def test_subset_private_cache_and_refusals(tmp_path):
    src = _source(tmp_path)
    dst = make_subset(src.root, tmp_path / "sub2", (0, 0), share_cache=False)
    assert dst.cache_dir.is_dir() and not dst.cache_dir.is_symlink() and not (dst.cache_dir / "k.json").exists()
    with pytest.raises(FileExistsError):
        make_subset(src.root, tmp_path / "sub2", (0, 0))
    with pytest.raises(ValueError):
        make_subset(src.root, tmp_path / "sub3", (9, 9))


def test_subset_imports_the_source_ocr_when_read_would_hash_the_same(tmp_path):
    src = _with_ocr(_source(tmp_path))
    before = _listing(src.root)
    dst = make_subset(src.root, tmp_path / "sub", (1, 2), share_cache=False, read_config_hash="rc")
    assert dst.boxes.read_bytes() == BOX_LINES[1] + BOX_LINES[2]  # the span's frames, in order, every byte the source's
    assert [r.frame for r in dst.load_boxes()] == [1, 2]
    assert dst.stage_up_to_date("read", [dst.frames], "rc")  # `read` skips itself: the hash is of this run's frames.jsonl
    assert not dst.stage_up_to_date("read", [dst.frames], "other")
    st = dst.manifest_read()["stages"]["read"]
    assert st["inputs"] == dst.inputs_hash([dst.frames]) != src.manifest_read()["stages"]["read"]["inputs"]
    assert (st["frames"], st["boxes"], st["imported_from"]) == (2, 2, str(src.root))  # counted over what was copied
    assert {k: st[k] for k in ("dropped_empty", "seconds", "seconds_per_frame", "engine")} == {
        "dropped_empty": 1, "seconds": 8.0, "seconds_per_frame": 2.0, "engine": {"engine": "rapidocr"}}  # the source's
    assert st["finished"]
    assert dst.manifest_read()["stages"]["decode"]["emitted"] == 2  # the decode entry is what it always was
    assert _listing(src.root) == before  # nothing is written under the source


def test_subset_runs_read_itself_when_the_ocr_cannot_be_imported(tmp_path):
    def subset(name: str, src: Run, **kw) -> dict:
        dst = make_subset(src.root, tmp_path / name, (1, 2), share_cache=False, **kw)
        assert not dst.boxes.exists()
        assert [r.frame for r in dst.load_frames()] == [1, 2]
        return dst.manifest_read()["stages"]

    assert "read" not in subset("no-boxes", _source(tmp_path), read_config_hash="rc")  # the source was never read
    src = _with_ocr(_source(tmp_path / "b"))
    assert "read" not in subset("other-config", src, read_config_hash="other")  # [read] differs: read runs as today
    assert "read" not in subset("no-hash", src)  # no config to compare against (`scry subset`): as today
    src.boxes.unlink()
    assert "read" not in subset("entry-only", src, read_config_hash="rc")  # a manifest entry without the file
    src = _with_ocr(_source(tmp_path / "c"))
    src.frames.write_bytes(src.frames.read_bytes() + b"\n")  # decoded again since read ran: read's inputs are stale
    assert "read" not in subset("stale", src, read_config_hash="rc")
    src = _with_ocr(_source(tmp_path / "d"))
    src.boxes.write_bytes(BOX_LINES[0] + BOX_LINES[1] + BOX_LINES[3])  # a frame of the span has no boxes record
    src.stage_done("read", [src.frames], "rc", **READ_STATS)
    assert "read" not in subset("missing-frame", src, read_config_hash="rc")


def test_subset_imports_a_legacy_directory(tmp_path):
    old = tmp_path / "old"
    (old / "frames").mkdir(parents=True)
    recs = []
    for n in range(4):
        Image.new("L", (8, 8), 40 * n).save(old / "frames" / f"{n:05d}.png")
        recs.append(Frame(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=n != 2,
                          width=8, height=8, sha256=f"{n:064x}", png=f"frames/{n:05d}.png"))
    write_jsonl(old / "stage1.jsonl", recs)
    (old / "frames.jsonl").write_text('{"not": "a frame"}\n')  # the pre-re-base merged file: never read
    (old / "boxes.jsonl").write_bytes(b"".join(BOX_LINES))  # a legacy read: never imported, whatever its hash
    (old / "manifest.json").write_text(json.dumps({"video": "v.mp4", "video_id": "v", "stages": {
        "stage1": {"inputs": "v.mp4:abc", "config": "cfg", "emitted": 4, "settled": 3},
        "read": {"inputs": "stage1.jsonl:xyz", "config": "rc", "frames": 4}}}))

    def listing():
        return sorted((str(p.relative_to(old)), p.stat().st_size if p.is_file() else -1) for p in old.rglob("*"))

    before = listing()
    dst = make_subset(old, tmp_path / "new", (1, 2), share_cache=False, read_config_hash="rc")
    assert [r.frame for r in dst.load_frames()] == [1, 2]
    stages = dst.manifest_read()["stages"]
    assert stages["decode"]["emitted"] == 2 and "stage1" not in stages
    assert "read" not in stages and not dst.boxes.exists()
    assert listing() == before
