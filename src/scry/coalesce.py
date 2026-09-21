from __future__ import annotations

import logging

from scry.config import Config, DiffConfig, config_hash
from scry.diff import diff_pair
from scry.jsonl import write_jsonl
from scry.merge import caret_region, combine_focus
from scry.run import Run
from scry.schemas import DiffOp, Event, FocusRecord, FrameRecord, Transition, TransientInfo
from scry.textdiff import lcp_len, norm

log = logging.getLogger(__name__)


# ---------- helpers ----------
def _other_ops_ok(t: Transition, region: str) -> bool:
    for rid, rd in t.computed_diff.items():
        if rid == region:
            continue
        if any(not (o.in_churn or o.clock) for o in rd.ops):
            return False
    return True


def _typed_op(t: Transition, region: str, cfg: DiffConfig) -> DiffOp | None:
    rd = t.computed_diff.get(region)
    if rd is None or len(rd.ops) != 1 or rd.ops[0].op != "modify":
        return None
    o = rd.ops[0]
    a, b = norm(o.old or ""), norm(o.new or "")
    if lcp_len(a, b) >= len(a) - cfg.typed_tolerance and len(b) >= len(a) - cfg.typed_tolerance and _other_ops_ok(t, region):
        return o
    return None


def _output_ops(t: Transition, region: str, prev_count: int, cur_count: int) -> list[DiffOp] | None:
    rd = t.computed_diff.get(region)
    if rd is None or not rd.ops:
        return None
    dels = [o for o in rd.ops if o.op == "delete"]
    ins = [o for o in rd.ops if o.op == "insert"]
    if len(dels) + len(ins) != len(rd.ops) or not ins:
        return None
    if any(o.old_index != k for k, o in enumerate(dels)):
        return None
    if any(o.new_index < cur_count - len(ins) for o in ins):
        return None
    if not _other_ops_ok(t, region):
        return None
    return ins


def _follow(t_next: Transition, region_in_prev_to: str) -> str | None:
    for a, b, _ in t_next.regions.matched:
        if a == region_in_prev_to:
            return b
    return None


def _kind(members: list[Transition]) -> str:
    if any(m.kind == "unsettled" for m in members):
        return "unsettled"
    return "coalesced"


def _build(frames_by_id: dict[int, FrameRecord], members: list[Transition], events: list[Event], cfg: DiffConfig) -> Transition:
    first, last = members[0], members[-1]
    t = diff_pair(frames_by_id[first.from_frame], frames_by_id[last.to_frame], cfg)
    t.intermediate_frames = [m.from_frame for m in members[1:]] if len(members) > 1 else []
    t.intermediate_frames = sorted(set(t.intermediate_frames) | {f for m in members for f in m.intermediate_frames})
    t.kind = _kind(members)
    if len(members) == 1 and members[0].kind == "transient_merged":
        t.kind = "transient_merged"
    t.transient = next((m.transient for m in members if m.transient is not None), None)  # a transient inside a run survives (§11.4)
    t.events = events
    return t


# ---------- §11.4 transients ----------
def merge_transients(frames: list[FrameRecord], singles: list[Transition], cfg: DiffConfig) -> list[Transition]:
    by_id = {f.frame: f for f in frames}
    out: list[Transition] = []
    i = 0
    while i < len(singles):
        t1 = singles[i]
        t2 = singles[i + 1] if i + 1 < len(singles) else None
        merged = None
        if t2 is not None and t1.to_frame == t2.from_frame:
            mid = by_id[t1.to_frame]
            nxt = by_id[t2.to_frame]
            nxt_texts = {norm(l.fused) for r in nxt.regions for l in r.lines}
            for rid in t1.regions.appeared:  # unit ids (§11.1)
                if rid in t2.regions.disappeared:
                    region = mid.region(rid)
                    texts = {norm(l.fused) for l in mid.unit_lines(rid) if l.fused}
                    if texts and texts & nxt_texts:
                        continue
                    hold = nxt.t_change - mid.t_change
                    if hold < cfg.transient_max_s:
                        merged = diff_pair(by_id[t1.from_frame], nxt, cfg)
                        merged.kind = "transient_merged"
                        merged.intermediate_frames = [mid.frame]
                        merged.transient = TransientInfo(frame=mid.frame, region=rid, name=region.name, hold_s=round(hold, 3))
                        break
        if merged is not None:
            out.append(merged)
            i += 2
        else:
            out.append(t1)
            i += 1
    return out


# ---------- §11.3 coalescing ----------
def coalesce(frames: list[FrameRecord], transitions: list[Transition], cfg: DiffConfig) -> list[Transition]:
    by_id = {f.frame: f for f in frames}
    out: list[Transition] = []
    i = 0
    while i < len(transitions):
        t = transitions[i]
        typed_run: list[Transition] = []
        region: str | None = None
        first_old: str | None = None
        last_new: str | None = None
        for rid in t.computed_diff:
            o = _typed_op(t, rid, cfg)
            if o is not None:
                region, first_old, last_new = rid, o.old or "", o.new or ""
                typed_run = [t]
                break
        j = i + 1
        cur_region = region
        while typed_run and j < len(transitions):
            nxt = transitions[j]
            if nxt.from_frame != typed_run[-1].to_frame:
                break
            nr = _follow(nxt, cur_region)
            o = _typed_op(nxt, nr, cfg) if nr else None
            if o is None or norm(o.old or "") != norm(last_new or ""):
                break
            typed_run.append(nxt)
            cur_region, last_new = nr, o.new or ""
            j += 1
        output_run: list[Transition] = []
        out_region = cur_region
        k = j if typed_run else i
        while k < len(transitions):
            nxt = transitions[k]
            if output_run and nxt.from_frame != output_run[-1].to_frame:
                break
            if not output_run and not typed_run:
                cand_regions = list(nxt.computed_diff)
            else:
                nr = _follow(nxt, out_region) if (output_run or typed_run) else None
                cand_regions = [nr] if nr else []
            found = None
            for rid in cand_regions:
                if rid == "r0":
                    continue
                prev_f, cur_f = by_id[nxt.from_frame], by_id[nxt.to_frame]
                from_rid = nxt.computed_diff[rid].from_region
                ins = _output_ops(nxt, rid, len(prev_f.unit_lines(from_rid)) if from_rid else 0, len(cur_f.unit_lines(rid)))
                if ins is not None:
                    found = (rid, ins)
                    break
            if found is None:
                break
            out_region = found[0]
            output_run.append(nxt)
            k += 1
        if typed_run or output_run:
            members = typed_run + output_run
            events: list[Event] = []
            if typed_run:
                text = last_new[lcp_len(first_old or "", last_new):] if last_new else ""
                events.append(Event(type="typed", region=cur_region, text=text, line=last_new,
                                    frames=(typed_run[0].from_frame, typed_run[-1].to_frame)))
            if output_run:
                lines: list[str] = []
                for m in output_run:
                    rid = next((r for r in m.computed_diff if m.computed_diff[r].ops and all(o.op in ("insert", "delete") for o in m.computed_diff[r].ops) and r != "r0"), None)
                    if rid:
                        lines += [o.new for o in m.computed_diff[rid].ops if o.op == "insert" and o.new is not None]
                events.append(Event(type="output_appended", region=out_region, lines=len(lines), text="\n".join(lines),
                                    frames=(output_run[0].from_frame, output_run[-1].to_frame)))
            if len(members) == 1 and not (typed_run and output_run):
                t1 = members[0]
                t1.events = events
                out.append(t1)
            else:
                out.append(_build(by_id, members, events, cfg))
            i = k
            continue
        out.append(t)
        i += 1
    return out


# ---------- trivial (§11.2) ----------
def tag_trivial(t: Transition) -> Transition:
    ops = [o for rd in t.computed_diff.values() for o in rd.ops]
    if ops and all(o.clock for o in ops) and not t.regions.appeared and not t.regions.disappeared and t.kind == "single":
        t.kind = "trivial"
    return t


# ---------- retrospective focus (§9.4) ----------
def _vlm_focus(f: FrameRecord) -> str | None:
    """Recover the VLM's own answer from Stage 3's focused_signals (it may have been recorded as 'vlm:rX@0.3')."""
    for sig in f.focused_signals:
        if sig.startswith("vlm:"):
            return sig[4:].split("@")[0]
    return f.focused_region if "vlm" in f.focused_signals else None


def retrospective_focus(frames: list[FrameRecord], transitions: list[Transition]) -> list[FocusRecord]:
    by_id = {f.frame: f for f in frames}
    out: list[FocusRecord] = []
    for t in transitions:
        typed = next((e for e in t.events if e.type == "typed"), None)
        if typed is None or t.regions.appeared:
            continue
        rd = t.computed_diff.get(typed.region)
        from_region = rd.from_region if rd else None
        if from_region is None:
            continue
        f, b = by_id[t.from_frame], by_id[t.to_frame]
        if f.focused_region and b.focused_region:  # §9.4: attribute only when focus did not change across the transition
            bu = b.unit_of(b.focused_region)  # matched names units (§11.1); a focus id may be a pane
            mapped = next((a for a, bb, _ in t.regions.matched if bb == bu), None)
            if mapped is not None and mapped != f.unit_of(f.focused_region):
                continue
        root = from_region
        by_rid = {r.id: r for r in f.regions}
        seen = {root}
        while by_rid.get(root) and by_rid[root].parent in by_rid and by_rid[root].parent not in seen:
            root = by_rid[root].parent
            seen.add(root)
        region, conf, signals = combine_focus(caret_region(f.caret, f.regions), root, _vlm_focus(f), f.focused_conf or 0.0)
        out.append(FocusRecord(frame=f.frame, focused_region=region, focused_conf=conf, focused_signals=signals))
    return out


def assign_ids(transitions: list[Transition]) -> None:
    for i, t in enumerate(transitions, start=1):
        t.id = f"T{i}"


def run_diff(run: Run, cfg: Config) -> None:
    inputs = [run.frames]
    ch = config_hash(cfg, "diff")
    if run.stage_up_to_date("diff", inputs, ch):
        log.info("diff up to date")
        return
    frames = run.load_frames()
    singles = [diff_pair(a, b, cfg.diff) for a, b in zip(frames, frames[1:])]
    ts = merge_transients(frames, singles, cfg.diff)
    ts = coalesce(frames, ts, cfg.diff)
    ts = [tag_trivial(t) for t in ts]
    assign_ids(ts)
    write_jsonl(run.transitions, ts)
    write_jsonl(run.focus, retrospective_focus(frames, ts))
    run.stage_done("diff", inputs, ch, transitions=len(ts), trivial=sum(t.kind == "trivial" for t in ts),
                   coalesced=sum(t.kind == "coalesced" for t in ts), transient=sum(t.kind == "transient_merged" for t in ts))
