from pathlib import Path

import pytest
from PIL import Image

from scry.jsonl import write_jsonl
from scry.run import Run
from scry.schemas import Stage1Record
from scry.subset import make_subset, parse_frames


def _source(tmp_path: Path) -> Run:
    src = Run(tmp_path / "src")
    recs = []
    for n in range(4):
        Image.new("L", (8, 8), 40 * n).save(src.frames_dir / f"{n:05d}.png")
        recs.append(Stage1Record(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=n != 2,
                                 width=8, height=8, sha256=f"{n:064x}", png=f"frames/{n:05d}.png"))
    write_jsonl(src.stage1, recs)
    src.manifest_update(video="v.mp4", video_sha256="abc", video_id="v", fps=30.0, duration=4.0, width=8, height=8)
    src.stage_done("stage1", [tmp_path / "v.mp4"], "cfg", emitted=4, settled=3)
    (src.cache_dir / "k.json").write_text("{}")
    return src


def test_parse_frames():
    assert parse_frames("145-155") == (145, 155)
    assert parse_frames("7") == (7, 7)
    with pytest.raises(ValueError):
        parse_frames("9-3")


def test_subset_keeps_range_and_marks_stage1_done(tmp_path):
    src = _source(tmp_path)
    dst = make_subset(src, tmp_path / "sub", (1, 2))
    assert [r.frame for r in dst.load_stage1()] == [1, 2]
    assert (dst.root / "frames/00001.png").exists() and not (dst.root / "frames/00000.png").exists()
    m = dst.manifest_read()
    assert m["video"] == "v.mp4" and m["video_id"] == "v" and m["fps"] == 30.0
    assert m["subset"] == {"source": str(src.root), "frames": [1, 2]}
    st = m["stages"]["stage1"]
    assert st["inputs"] == src.manifest_read()["stages"]["stage1"]["inputs"] and st["config"] == "cfg"
    assert st["emitted"] == 2 and st["settled"] == 1
    assert dst.stage_up_to_date("stage1", [tmp_path / "v.mp4"], "cfg")  # `scry run` will skip decoding
    assert "ocr" not in m["stages"]


def test_subset_shares_the_source_call_cache(tmp_path):
    src = _source(tmp_path)
    dst = make_subset(src, tmp_path / "sub", (0, 3))
    assert dst.cache_dir.is_symlink() and (dst.cache_dir / "k.json").exists()
    (dst.cache_dir / "new.json").write_text("{}")
    assert (src.cache_dir / "new.json").exists()
    again = Run(dst.root)  # re-opening the run must tolerate the symlinked cache directory
    assert again.cache_dir.is_dir()


def test_subset_private_cache_and_refusals(tmp_path):
    src = _source(tmp_path)
    dst = make_subset(src, tmp_path / "sub2", (0, 0), share_cache=False)
    assert dst.cache_dir.is_dir() and not dst.cache_dir.is_symlink() and not (dst.cache_dir / "k.json").exists()
    with pytest.raises(FileExistsError):
        make_subset(src, tmp_path / "sub2", (0, 0))
    with pytest.raises(ValueError):
        make_subset(src, tmp_path / "sub3", (9, 9))
