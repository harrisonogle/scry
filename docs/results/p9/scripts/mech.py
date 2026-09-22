"""Mechanical check of the exact-string and time rubric lines against the judge's verdicts (method of P6's analyst)."""
import re, sys
from p9lib import *
sys.path.insert(0, str(REPO / "src"))
from scry.evaluation.questions import parse_questions
qs = {q.id: q for q in parse_questions((REPO / "docs/ground-truth/full-questions.md").read_text())}
EXACT = re.compile(r"contains the exact string `([^`]+)`")
TIME = re.compile(r"gives a time between (\d+):(\d+) and (\d+):(\d+)")
def frames_allowed(text):
    m = re.search(r"or a frame from (\d+) to (\d+)", text)
    if m: return set(range(int(m[1]), int(m[2]) + 1))
    m = re.search(r"or frame (\d+) or (\d+)", text)
    if m: return {int(m[1]), int(m[2])}
    m = re.search(r"or frame (\d+)", text)
    return {int(m[1])} if m else set()
def times_in(ans):
    out = []
    for m in re.finditer(r"(?<![\d:.])(\d{1,2}):(\d{2})(?:\.(\d+))?(?![\d:])", ans):
        out.append(int(m[1]) * 60 + int(m[2]) + (float("0." + m[3]) if m[3] else 0))
    for m in re.finditer(r"(\d{2,4}(?:\.\d+)?)\s*(?:s\b|sec|–|-\d)", ans):
        out.append(float(m[1]))
    for m in re.finditer(r"t\s*[=≈~]?\s*(\d{1,4}(?:\.\d+)?)", ans):
        out.append(float(m[1]))
    return out
def frames_in(ans):
    out = set()
    for m in re.finditer(r"[Ff]rames?\s+(\d+)(?:\s*[–-]\s*(\d+))?", ans):
        a = int(m[1]); b = int(m[2]) if m[2] else a
        out |= set(range(a, b + 1)) if b - a < 60 else {a, b}
    return out
def check(s):
    n = dis = 0; rows = []
    for r in RUNS:
        A, J = answers(s, r), judgments(s, r)
        for qid, q in qs.items():
            if qid not in A or qid not in J: continue
            ans = A[qid]["answer"]
            for it in q.rubric:
                mech = None
                m = EXACT.search(it.text)
                if m: mech = m[1] in ans
                else:
                    t = TIME.search(it.text)
                    if t and it.id.startswith("M") and qid in ("Q1", "Q3", "Q4", "Q13", "Q15", "Q16"):
                        lo, hi = int(t[1]) * 60 + int(t[2]), int(t[3]) * 60 + int(t[4])
                        mech = any(lo <= x <= hi for x in times_in(ans)) or bool(frames_allowed(it.text) & frames_in(ans))
                if mech is None: continue
                n += 1
                judge = (J[qid].get("items") or {}).get(it.id)
                if judge != mech:
                    dis += 1; rows.append((r, qid, it.id, "judge", judge, "mechanical", mech, it.text[:100]))
    print(s, "lines checked:", n, "disagreements:", dis)
    for row in rows: print("  ", *row)
if __name__ == "__main__":
    for s in sys.argv[1:] or ["P9"]: check(s)
