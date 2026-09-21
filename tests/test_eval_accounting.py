import copy
import json

from scry.evaluation.accounting import cost_summary, projection_frames

MANIFEST = {"stages": {
    "read": {"boxes": 120},
    "annotate": {"usage": {"input_tokens": 100_000, "output_tokens": 20_000, "cache_creation_input_tokens": 8_000,
                           "cache_read_input_tokens": 40_000},
                 "model": "claude-opus-5", "calls": 10, "cache": {"hits": 0, "misses": 10}},
    "interpret": {"usage": {"input_tokens": 30_000, "output_tokens": 4_000}, "model": "claude-opus-5",
                  "cache": {"hits": 0, "misses": 9}},
}}
SECONDS = {"read": 50.0, "annotate": 120.0, "interpret": 30.0}


def test_cost_per_stage_frame_and_video():
    c = cost_summary(MANIFEST, SECONDS, frames=10, projection=200, default_model="claude-opus-5")
    a = c["by_stage"]["annotate"]
    assert a["dollars"] == 1.07  # 0.50 + 0.50 + 0.05 + 0.02
    assert a["per_frame"] == 0.107
    assert a["per_video"] == 21.4
    assert a["calls"] == 10
    i = c["by_stage"]["interpret"]
    assert i["dollars"] == 0.25  # 0.15 + 0.10
    assert i["calls"] == 9
    assert c["by_stage"]["read"]["dollars"] == 0.0
    assert c["dollars"] == 1.32
    assert c["per_frame"] == 0.132
    assert c["per_video"] == 26.4
    assert c["seconds"] == 200.0
    assert c["seconds_per_frame"] == 20.0
    assert c["cache_hits"] == 0
    assert c["warnings"] == []
    assert c["frames"] == 10 and c["projection_frames"] == 200


def test_a_stage_costs_what_its_manifest_says_was_paid():
    # ledger L52: one cost_usd per stage, at the price paid. A stage run in batch mode paid half the list price, and
    # for cache writes where a synchronous run reads: its usage priced again at the synchronous rates is not its cost.
    m = copy.deepcopy(MANIFEST)
    m["stages"]["annotate"]["cost_usd"] = 0.4321
    c = cost_summary(m, SECONDS, frames=10, projection=200, default_model="claude-opus-5")
    a = c["by_stage"]["annotate"]
    assert (a["dollars"], a["per_frame"], a["per_video"]) == (0.4321, 0.0432, 8.64)
    assert c["by_stage"]["interpret"]["dollars"] == 0.25  # a manifest without cost_usd: priced from its usage
    assert (c["dollars"], c["per_frame"], c["per_video"]) == (0.6821, 0.0682, 13.64)
    # no projected batch price: only a run made in batch mode has one, and it is its `dollars`
    assert not any("batch" in key for row in (c, *c["by_stage"].values()) for key in row)


def test_question_seconds_stay_out_of_seconds_per_frame():
    # seconds per frame cover the stages dollars per frame cover; answering is timed per question (ledger L57)
    c = cost_summary(MANIFEST, SECONDS | {"ask": 300.0}, frames=10, projection=200, default_model="claude-opus-5")
    assert (c["seconds"], c["seconds_per_frame"], c["question_seconds"]) == (200.0, 20.0, 300.0)
    assert "ask" not in c["by_stage"]


def test_cache_hits_and_unknown_model_are_flagged():
    m = copy.deepcopy(MANIFEST)
    m["stages"]["interpret"]["cache"] = {"hits": 3, "misses": 6}
    m["stages"]["annotate"]["model"] = "claude-nope"
    c = cost_summary(m, SECONDS, frames=10, projection=200, default_model="claude-opus-5")
    assert c["cache_hits"] == 3
    assert any("3 cache hits in interpret" in w for w in c["warnings"])
    assert any("claude-nope" in w and "priced as claude-opus-5" in w for w in c["warnings"])
    assert c["by_stage"]["annotate"]["dollars"] == 1.07


def test_projection_frames_and_zero_frames(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "manifest.json").write_text(json.dumps({"stages": {"decode": {"emitted": 4}}}))
    derived = {"subset": {"source": str(src), "frames": [1, 2]}, "stages": {"decode": {"emitted": 2}}}
    assert projection_frames(derived) == 4
    old = tmp_path / "old"
    old.mkdir()
    (old / "manifest.json").write_text(json.dumps({"stages": {"stage1": {"emitted": 7}}}))
    assert projection_frames({"subset": {"source": str(old), "frames": [1, 2]}}) == 7
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "manifest.json").write_text(json.dumps({"stages": {}}))
    assert projection_frames({"subset": {"source": str(bare), "frames": [1, 2]}}) is None
    assert projection_frames({"stages": {"decode": {"emitted": 5}}}) == 5  # no subset: the manifest's own decode
    assert projection_frames({}) is None
    c = cost_summary(MANIFEST, SECONDS, frames=0, projection=200, default_model="claude-opus-5")
    assert c["per_frame"] is None and c["per_video"] is None
