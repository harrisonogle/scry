from pathlib import Path

from minirun import mini_interpretations, mini_run

from scry.config import Config
from scry.evaluation.commands import (claims, command_scores, reader_views, score_claims, score_commands, score_exact_by_reader,
                                      score_found, window)
from scry.groundtruth import Entry, parse_commands, scorable
from scry.index import build_index
from scry.schemas import Change, FrameTime, Interpretation, Lifetime

E1 = Entry(n=1, text="az account show", first_frame=157, first_t=628.77, submitted_frame=158, submitted_t=629.57)
E2 = Entry(n=2, text="az configure --defaults group=RG1", first_frame=161, first_t=649.17, submitted_frame=164, submitted_t=653.57)
E3 = Entry(n=3, text="y", first_frame=170, first_t=660.83, submitted_frame=171, submitted_t=664.13)
E4 = Entry(n=4, text="kubectl config current-context", first_frame=175, first_t=674.23, submitted_frame=177, submitted_t=677.13)
EXECUTED = [E1, E2, E3, E4]
NEVER = [Entry(n=None, text="az login", frames=[155]), Entry(n=None, text="kubectl config current-context", frames=[178])]

HITS = {
    '"az account show"': [{"node_id": "v:V", "level": "video", "frames": [155, 187]},
                          {"node_id": "v:L1", "level": "lifetime", "frames": [157, 186]}],
    '"az configure --defaults group=RG1"': [{"node_id": "v:S3", "level": "step", "frames": [160, 165]}],
    '"kubectl config current-context"': [{"node_id": "v:L3", "level": "lifetime", "frames": [178, 178]},
                                         {"node_id": "v:T22", "level": "transition", "frames": [176, 177]}],
    '"kubectl get nodes"': [{"node_id": "v:L9", "level": "lifetime", "frames": [180, 181], "t": [702.0333, 706.7]}],
}


def _found_rows(entries=EXECUTED, hits=HITS, asked=None):
    def hits_for(query: str) -> list[dict]:
        if asked is not None:
            asked.append(query)
        return hits.get(query, [])
    return score_found(entries, hits_for)


def test_found_by_frame_and_level():
    asked: list[str] = []
    e5 = Entry(n=5, text="kubectl get nodes", first_frame=180, first_t=702.03, submitted_frame=180, submitted_t=702.03)
    r1, r2, r3, r4, r5 = _found_rows([*EXECUTED, e5], asked=asked)
    assert (r1["found"], r1["rank"], r1["level"], r1["node_id"]) == (True, 2, "lifetime", "v:L1")  # the video's summary covers, and never counts
    assert (r2["found"], r2["rank"], r2["level"], r2["node_id"]) == (False, None, "step", None)  # only a summary quotes it
    assert (r3["found"], r3["scorable"]) == (None, False)
    assert '"y"' not in asked and len(asked) == 4
    assert (r4["found"], r4["rank"], r4["level"]) == (True, 2, "transition")  # 178 > 177: the first hit does not cover
    assert (r5["found"], r5["rank"]) == (True, 1)  # by seconds, 702.0333 > 702.03 would miss it
    [r2] = _found_rows([E2], hits={})
    assert (r2["found"], r2["level"]) == (False, None)
    assert window(E4) == (175, 177) and window(Entry(n=9, text="kubectl")) is None


def _life(n: int, text: str, frame: int) -> Lifetime:
    return Lifetime(id=f"L{n}", text=text, readings={text: [frame]}, unstable=False, sightings=1,
                    first=FrameTime(frame=frame, t=float(frame)), last=FrameTime(frame=frame, t=float(frame)), boxes=[f"{frame}:b1"])


PS = "PS C:\\Users\\msadmin>"
LIFETIMES = [_life(1, f"{PS} az account show", 157), _life(2, f"{PS}azconfigure --defaultsgroup=RG1", 161),
             _life(3, f"{PS} kubectl config current-context", 178), _life(4, f"{PS} kubect1 config current-context", 175)]
VLM = {"L2": f"{PS} az configure --defaults group=RG1", "L4": f"{PS} kubectl config current-context"}


def _exact_rows(vlm=VLM):
    return score_exact_by_reader(EXECUTED, reader_views(LIFETIMES, vlm))


def test_exact_per_reader():
    r1, r2, _, r4 = rows = _exact_rows()
    assert r1["exact"] == {"ocr": True, "vlm": False, "any": True}
    assert r1["first_frame_error"] == {"ocr": 0, "vlm": None, "any": 0}
    assert r2["exact"] == {"ocr": False, "vlm": True, "any": True} and r2["first_frame_error"]["any"] == 0
    assert (r4["exact"]["ocr"], r4["lifetime"]["ocr"], r4["first_frame_error"]["ocr"]) == (True, "L3", 3)  # 178 − 175
    assert (r4["exact"]["vlm"], r4["lifetime"]["vlm"], r4["first_frame_error"]["vlm"]) == (True, "L4", 0)
    assert r4["first_frame_error"]["any"] == 0
    scores = command_scores(EXECUTED, NEVER, None, rows, None, None)
    assert scores["rates"]["exact"] == {"ocr": (2, 3), "vlm": (2, 3), "any": (3, 3)}
    assert scores["first_frame_error_abs_mean"] == {"ocr": 1.5, "vlm": 0.0, "any": 0.0}  # OCR: 0 and 3 over two entries
    assert scores["first_frame_error_abs_n"] == {"ocr": 2, "vlm": 2, "any": 3}
    r1, _, _, r4 = rows = _exact_rows(vlm={})  # no second reader
    assert all("vlm" not in r[k] for r in rows for k in ("exact", "lifetime", "first_frame_error", "first_t_error"))
    assert all(r["exact"]["any"] == r["exact"]["ocr"] for r in rows)
    assert r4["first_frame_error"]["any"] == 3


def _change(n: int, a: int) -> Change:
    return Change(id=f"T{n}", from_frame=a, to_frame=a + 1, t=(float(a), float(a + 1)), kind="single", pixels=None)


CHANGES = [_change(1, 155), _change(3, 157), _change(9, 163), _change(16, 170), _change(22, 176), _change(23, 177), _change(30, 184)]
ENTERED = {"T1": ("az login", "yes"), "T3": ("az account show", "yes"), "T9": ("az configure --defaults group=RG1", "unclear"),
           "T16": ("y", "yes"), "T22": (" kubectl  config current-context ", "yes"),  # spaces to collapse
           "T23": ("kubectl config current-context", "yes"), "T30": ("clear", "yes")}


def _claim_rows(entered=ENTERED):
    interps = {i: Interpretation(id=i, entered_text=text, submitted=submitted) for i, (text, submitted) in entered.items()}
    cs = claims(CHANGES, interps)
    return cs, *score_claims(EXECUTED, NEVER, cs)


def test_claims_one_per_row():
    cs, submit, false = _claim_rows()
    assert [c["change"] for c in cs] == ["T1", "T3", "T16", "T22", "T23", "T30"]  # T9 is none
    assert cs[3] == {"change": "T22", "to_frame": 177, "text": "kubectl config current-context"}
    s1, s2, s3, s4 = submit
    assert (s1["submitted"], s1["claim"], s1["submit_frame_error"]) == (True, "T3", 0)
    assert (s2["submitted"], s2["claim"], s2["submit_frame_error"]) == (False, None, None)
    assert (s3["claim"], s3["submit_frame_error"]) == ("T16", 0)
    assert (s4["claim"], s4["submit_frame_error"]) == ("T22", 0)  # 0 frames away against 1
    assert [(r["false_run"], r["claim"]) for r in false] == [(True, "T1"), (True, "T23")]  # T23 is left over
    scores = command_scores(EXECUTED, NEVER, None, _exact_rows(), submit, false)
    assert scores["rates"]["submitted"] == (2, 3) and scores["rates"]["false_run"] == (2, 2)
    assert (scores["submit_frame_error_abs_mean"], scores["submit_frame_error_abs_n"]) == (0.0, 2)

    _, submit, false = _claim_rows({k: v for k, v in ENTERED.items() if k != "T22"})  # marked one transition late
    assert (submit[3]["claim"], submit[3]["submit_frame_error"]) == ("T23", 1)
    assert (false[1]["false_run"], false[1]["claim"]) == (False, None)
    scores = command_scores(EXECUTED, NEVER, None, _exact_rows(), submit, false)
    assert scores["rates"]["false_run"] == (1, 2) and scores["submit_frame_error_abs_mean"] == 0.5

    _, submit, _ = _claim_rows(ENTERED | {"T16": ("kubectl get deployment", "yes")})  # it contains a y: equality, not containment
    assert submit[2]["submitted"] is False


def test_command_scores_rates_and_units():
    _, submit, false = _claim_rows()
    scores = command_scores(EXECUTED, NEVER, _found_rows(), _exact_rows(), submit, false)
    units = scores["units"]
    assert scores["rates"]["found"] == (2, 3)
    assert units["found"] == {"1": 1.0, "2": 0.0, "4": 1.0}
    assert units["exact.ocr"] == {"1": 1.0, "2": 0.0, "4": 1.0}
    assert units["exact.vlm"] == {"1": 0.0, "2": 1.0, "4": 1.0}
    assert units["exact.any"] == {"1": 1.0, "2": 1.0, "4": 1.0}
    assert units["first_frame_error_abs.any"] == {"1": 0.0, "2": 0.0, "4": 0.0}
    assert units["submitted"] == {"1": 1.0, "2": 0.0, "4": 1.0}
    assert units["submit_frame_error_abs"] == {"1": 0.0, "4": 0.0}
    assert units["false_run"] == {"N1": 1.0, "N2": 1.0}
    assert all("3" not in by_unit for by_unit in units.values())  # `y` is reported, not rated
    e3 = scores["entries"][2]
    assert (e3["text"], e3["scorable"], e3["claim"], e3["found"]) == ("y", False, "T16", None)
    assert [r["text"] for r in scores["never_run"]] == ["az login", "kubectl config current-context"]
    bare = command_scores(EXECUTED, NEVER, None, _exact_rows(), None, None)
    assert bare["rates"]["found"] is None and bare["rates"]["submitted"] is None and bare["rates"]["false_run"] is None
    assert not {"found", "submitted", "submit_frame_error_abs", "false_run"} & bare["units"].keys()
    assert bare["entries"][0]["found"] is None and bare["entries"][0]["submitted"] is None


GROUND_TRUTH = """## Executed, in order

| # | Text as displayed | First fully visible (frame, t) | Submitted (frame, t) | Confidence note |
|---|---|---|---|---|
| 1 | `git status` | 11, 24.40 | 12, 26.40 | High |

## Appeared on screen but was never run

| Text as displayed | Frames (t) | What the presenter had actually entered | What happened next |
|---|---|---|---|
| `git stash` | 11 (24.40) | `git st` | replaced |
"""


def test_score_commands_on_the_mini_run(tmp_path: Path):
    """The tripwire for the adapters: the real loaders, labels, interpretations and index over plan 3's Fixture M."""
    gt = tmp_path / "gt.md"
    gt.write_text(GROUND_TRUTH)
    cfg = Config()
    run = mini_run(tmp_path / "full", labels=True)
    mini_interpretations(run)
    build_index(run, cfg)
    scores = score_commands(run, cfg, gt)
    [e] = scores["entries"]
    assert (e["found"], e["level"]) == (True, "lifetime")
    assert e["exact"] == {"ocr": True, "vlm": True, "any": True} and e["first_frame_error"]["any"] == 0
    assert (e["submitted"], e["claim"], e["submit_frame_error"]) == (True, "T2", 0)
    assert scores["rates"]["false_run"] == (0, 1)

    bare = mini_run(tmp_path / "bare", labels=False)  # no second reader, no index.sqlite, no interpretations.jsonl
    scores = score_commands(bare, cfg, gt)
    assert "vlm" not in scores["entries"][0]["exact"]
    assert scores["rates"]["found"] is None and scores["rates"]["submitted"] is None
    assert not bare.index_db.exists()  # scoring creates nothing


def test_repo_ground_truth_frames():
    """Reads the committed command list on purpose, to catch a silent edit."""
    executed, never = parse_commands((Path(__file__).parents[1] / "docs/ground-truth/span2-commands.md").read_text())
    assert (len(executed), len(never)) == (9, 5)
    assert [scorable(e) for e in executed] == [True, True, True, False, False, True, True, True, True]
    assert (executed[1].first_frame, executed[1].submitted_frame) == (161, 164)
    assert (executed[6].first_frame, executed[6].submitted_frame) == (180, 180)
    assert executed[8].submitted_frame == 187
    assert [n.frames for n in never] == [[155], [165], [172, 173, 174], [178], [179]]
    assert all(window(e) is not None for e in executed)
