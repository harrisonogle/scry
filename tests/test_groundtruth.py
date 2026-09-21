import pytest

from scry.groundtruth import exact_rate, parse_commands, scorable, score_exact
from scry.schemas import FrameTime, Lifetime

MD = """## Executed, in order

| # | Text as displayed | First fully visible (frame, t) | Submitted (frame, t) | Confidence note |
|---|---|---|---|---|
| 1 | `az configure --defaults group=RG1` | 161, 649.17 (10:49.2) as typed `az c`; fully typed from 162, 652.00 | 164, 653.57 (10:53.6), new prompt | High |
| 2 | `y` (answer to `Overwrite? (y/n):`) | question visible 170, 660.83; answer visible 171, 664.13 | 171, 664.13 (11:04.1) | High |
| 3 | `kubectl get pods` | 187, 721.00 (12:01.0) | between 186, 716.90 (11:56.9) and 187, 721.00 (12:01.0) | High |

## Appeared on screen but was never run

| Text as displayed | Frames (t) | What the presenter had actually entered | What happened next |
|---|---|---|---|
| `kubectl rollout undo deployment/kodekloudapp` | 172 (668.13), 173 (668.87) | `kubect` | replaced |
"""


def life(n: int, text: str, frame: int, t: float) -> Lifetime:
    return Lifetime(id=f"L{n}", text=text, readings={text: [frame]}, unstable=False, sightings=1,
                    first=FrameTime(frame=frame, t=t), last=FrameTime(frame=frame, t=t), boxes=[f"{frame}:b1"])


LIFETIMES = [life(3, "PS C:\\Users\\msadmin>azconfigure --defaultsgroup=RG1", 161, 649.17),
             life(4, "PS C:\\Users\\msadmin> az configure --defaults group=RG1", 162, 652.0),
             life(7, "PS C:\\Users\\msadmin> kubectl get pods", 187, 721.0),
             life(9, "PSC:\\Users\\msadmin> kubect1rollout undo deployment/kodekloudapp", 172, 668.13)]


def test_parse_commands():
    executed, never = parse_commands(MD)
    assert [e.text for e in executed] == ["az configure --defaults group=RG1", "y", "kubectl get pods"]
    e1, e2, e3 = executed
    assert (e1.n, e1.first_frame, e1.first_t, e1.submitted_frame, e1.submitted_t) == (1, 161, 649.17, 164, 653.57)
    assert (e2.first_frame, e2.first_t, e2.submitted_frame, e2.submitted_t) == (170, 660.83, 171, 664.13)
    assert not scorable(e2) and scorable(e1)
    assert (e3.first_frame, e3.first_t, e3.submitted_frame, e3.submitted_t) == (187, 721.0, 187, 721.0)
    [n1] = never
    assert n1.text == "kubectl rollout undo deployment/kodekloudapp" and n1.frames == [172, 173] and n1.n is None


def test_score_exact():
    executed, never = parse_commands(MD)
    rows = score_exact(executed, LIFETIMES)
    r1, r2, r3 = rows
    assert (r1["exact"], r1["lifetime"], r1["frame_error"], r1["t_error"], r1["matches"]) == (True, "L4", 1, 2.83, 1)
    assert (r3["exact"], r3["lifetime"], r3["frame_error"], r3["t_error"]) == (True, "L7", 0, 0.0)
    assert r2["scorable"] is False
    assert exact_rate(rows) == (2, 2)
    assert score_exact(never, LIFETIMES)[0]["matches"] == 0


def test_exact_is_case_sensitive():
    executed, _ = parse_commands("## Executed\n\n| # | Text as displayed | First | Submitted | Note |\n|---|---|---|---|---|\n"
                                 "| 1 | `az aks get-Credentials` | 166, 656.20 | 169, 659.27 | High |\n")
    [row] = score_exact(executed, [life(1, "PS C:\\Users\\msadmin> az aks get-credentials --name AKS1", 166, 656.2)])
    assert row["exact"] is False


def test_malformed_row_raises():
    lines = MD.split("\n")
    assert lines[4].startswith("| 1 |")
    lines[4] = lines[4].rsplit("|", 2)[0] + "|"  # remove the last cell of executed row 1 (line 5 of the fixture)
    with pytest.raises(ValueError, match="line 5"):
        parse_commands("\n".join(lines))
