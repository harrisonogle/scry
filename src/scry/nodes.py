"""Node extraction for the index: what each entry says, from the measured records and, when they exist, the labels.
The whole-screen entry of a frame is a superset of everything known about that frame, and no label removes a line from
it; a lifetime entry holds every reading of every reader. Storage and search are in scry.index."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from scry.changetext import PAIR_KINDS, text_of
from scry.index import Node
from scry.run import Run
from scry.schemas import Change, Frame, FrameBoxes, HierNode, Interpretation, Lifetime, box_ref, link_members

if TYPE_CHECKING:
    from scry.annotate.join import Labels, LifetimeLink
    from scry.schemas import PairLink, RecordLink, RunLink

    AnyLink = RunLink | PairLink | RecordLink | LifetimeLink


def link_anchor(link: AnyLink) -> str:
    """The id whose entry carries the link's text: a run's first box, a pair's first value box (the pairing lasts as
    long as the value does), a record's first cell. Only the fields of the link's own kind are read."""
    if link.kind == "run":
        return link.boxes[0]
    if link.kind == "pair":
        return link.value[0]
    return link.members[0][0]


def link_lines(link: AnyLink, text: Callable[[str], str]) -> list[str]:
    """The link as index text; `text` maps one of its ids to a string. A run is joined both with "" and with " ", so a
    wrong joiner cannot hide a command; a pair is `key value`; a record is its cells in order, and its header adds no
    line."""
    if link.kind == "run":
        texts = [text(i) for i in link.boxes]
        return list(dict.fromkeys(["".join(texts), " ".join(texts)]))
    if link.kind == "pair":
        return [" ".join(text(i) for i in link.key) + " " + " ".join(text(i) for i in link.value)]
    return [" ".join(" ".join(text(i) for i in cell) for cell in link.members)]


def _chapter_id(run: Run, t: float) -> str | None:
    chapter = run.chapter_of(t)
    return chapter.id if chapter is not None else None


def frame_nodes(run: Run, frames: list[Frame], boxes: dict[int, FrameBoxes], lifetimes: list[Lifetime],
                labels: Labels | None) -> list[Node]:
    """One whole-screen entry per emitted frame."""
    vid = run.video_id
    lifetime_of = {ref: l.id for l in lifetimes for ref in l.boxes}
    nodes = []
    for ordinal, f in enumerate(frames):
        fb = boxes.get(f.frame)
        frame_boxes = fb.boxes if fb is not None else []
        refs = [box_ref(f.frame, b.id) for b in frame_boxes]
        screen = labels.frame(f.frame) if labels is not None else None
        box_labels = [labels.box(ref) for ref in refs] if labels is not None else []
        lines: list[str] = []
        if screen is not None:
            lines += [f"{c.app} {c.name}".strip() for c in screen.containers]
            lines += dict.fromkeys(l.pane for l in box_labels if l is not None and l.pane)  # a name the screen may never spell out
        lines += [b.text for b in frame_boxes]  # every box, in reading order: no label removes a line
        lines += [l.vlm for l in box_labels if l is not None and l.agree is False and l.vlm]  # both readings are recorded
        if screen is not None:
            lines += [m.text for m in screen.missed]
            for link in screen.links:
                lines += link_lines(link, lambda ref: text_of(ref, boxes))
            lines.append(screen.description or "")
        text = "\n".join(line for line in lines if line)
        if not text:
            continue
        containers = screen.containers if screen is not None else []
        nodes.append(Node(
            node_id=f"{vid}:f{f.frame}", video_id=vid, level="frame", item_id=str(f.frame), frames=(f.frame, f.frame),
            t=(f.t_settled, f.t_end), apps=sorted({c.app for c in containers if c.app}), containers=[c.name for c in containers if c.name],
            chapter_id=_chapter_id(run, f.t_settled), text=text,
            payload={"frame": f.frame, "ordinal": ordinal, "png": f.png,
                     "boxes": [{"id": b.id, "text": b.text, "lifetime": lifetime_of.get(ref)} for b, ref in zip(frame_boxes, refs)],
                     "description": screen.description if screen is not None else None,
                     "containers": [{"id": c.id, "kind": c.kind, "app": c.app, "name": c.name} for c in containers],
                     "missed": [{"id": m.id, "text": m.text} for m in (screen.missed if screen is not None else [])]}))
    return nodes


def _by_count(readings: dict[str, int], first: str | None) -> list[str]:
    """`first`, then the other readings by count descending, then by string."""
    return [first] + sorted((r for r in readings if r != first), key=lambda r: (-readings[r], r))


def lifetime_nodes(run: Run, lifetimes: list[Lifetime], labels: Labels | None) -> list[Node]:
    """One entry for every lifetime: every reading of each reader, and the links whose anchor the lifetime is."""
    vid = run.video_id
    ocr = {l.id: l.text for l in lifetimes}
    label_of = {l.id: labels.lifetime(l.id) if labels is not None else None for l in lifetimes}
    vlm = {i: label.vlm for i, label in label_of.items() if label is not None and label.vlm}
    nodes = []
    for L in lifetimes:
        label = label_of[L.id]
        ocr_readings = {reading: len(frames) for reading, frames in L.readings.items()}
        lines = _by_count(ocr_readings, L.text)
        if label is not None:
            lines += _by_count(label.vlm_readings, label.vlm)
        links = []
        for link in (label.links if label is not None else []):
            if link_anchor(link) != L.id:
                continue  # its text lives on one entry only, so one pair is one hit
            own = link_lines(link, ocr.__getitem__)
            if all(i in vlm for i in link_members(link)):
                own += link_lines(link, vlm.__getitem__)
            own = list(dict.fromkeys(own))
            lines += own
            pair = link.kind == "pair"
            links.append({"kind": link.kind, "lines": own, "key": " ".join(ocr[i] for i in link.key) if pair else None,
                          "value": " ".join(ocr[i] for i in link.value) if pair else None, "seen": link.records})
        container = label.container if label is not None else None
        nodes.append(Node(
            node_id=f"{vid}:{L.id}", video_id=vid, level="lifetime", item_id=L.id, frames=(L.first.frame, L.last.frame),
            t=(L.first.t, L.last.t), apps=[container.app] if container is not None and container.app else [],
            containers=[container.name] if container is not None and container.name else [], chapter_id=_chapter_id(run, L.first.t),
            text="\n".join(dict.fromkeys(line for line in lines if line)),
            payload={"lifetime": L.model_dump(),
                     "readers": {"ocr": {"text": L.text, "readings": ocr_readings},
                                 "vlm": {"text": label.vlm, "readings": label.vlm_readings} if label is not None and label.vlm_readings else None},
                     "agree": label.agree if label is not None else None, "non_text": label.non_text if label is not None else False,
                     "seen_once": L.sightings == 1,
                     "container": {"app": container.app, "name": container.name, "kind": container.kind} if container is not None else None,
                     "links": links}))
    return nodes


def _parent_of(parents: list[HierNode], child_ids: list[str]) -> dict[str, str]:
    """child id → the id of the parent whose `children` range holds it."""
    out: dict[str, str] = {}
    for n in parents:
        first, last = n.children
        inside = False
        for cid in child_ids:
            inside = inside or cid == first
            if inside:
                out[cid] = n.id
            if cid == last:
                inside = False
    return out


def transition_nodes(run: Run, changes: list[Change], interps: dict[str, Interpretation], labels: Labels | None,
                     steps: list[HierNode], sections: list[HierNode]) -> list[Node]:
    """One entry for every change. `submitted` is not index text (yes and no match everything); it is in the payload."""
    vid = run.video_id
    step_of = _parent_of(steps, [c.id for c in changes])
    section_of = _parent_of(sections, [s.id for s in steps])
    nodes = []
    for c in changes:
        ip = interps.get(c.id)
        lines = [ip.entered_text, ip.action, ip.result] if ip is not None else []
        for r in c.records:
            if r.kind in PAIR_KINDS:
                lines += [r.before.text, r.after.text]
        if not any(lines):  # not widened: with appeared texts always listed, a page load would be a second whole-screen entry
            lines = [r.after.text for r in c.records if r.kind == "appeared"] + [r.before.text for r in c.records if r.kind == "removed"]
        text = "\n".join(line for line in lines if line)
        if not text:
            continue
        containers = labels.frame(c.to_frame).containers if labels is not None else []
        step_id = step_of.get(c.id)
        nodes.append(Node(node_id=f"{vid}:{c.id}", video_id=vid, level="transition", item_id=c.id, frames=(c.from_frame, c.to_frame),
                          t=c.t, apps=sorted({k.app for k in containers if k.app}), step_id=step_id,
                          section_id=section_of.get(step_id) if step_id is not None else None, chapter_id=_chapter_id(run, c.t[1]),
                          text=text, payload={"change": c.model_dump(), "interpretation": ip.model_dump() if ip is not None else None}))
    return nodes


def summary_nodes(run: Run, steps: list[HierNode], sections: list[HierNode], video: HierNode | None) -> list[Node]:
    """Steps, sections, the video and the outline's chapters."""
    vid = run.video_id
    section_of = _parent_of(sections, [s.id for s in steps])
    nodes = [Node(node_id=f"{vid}:{s.id}", video_id=vid, level="step", item_id=s.id, frames=s.frames, t=s.t, step_id=s.id,
                  section_id=section_of.get(s.id), text=f"{s.label}\n{s.description}", payload=s.model_dump()) for s in steps]
    nodes += [Node(node_id=f"{vid}:{c.id}", video_id=vid, level="section", item_id=c.id, frames=c.frames, t=c.t, section_id=c.id,
                   text=f"{c.label}\n{c.description}", payload=c.model_dump()) for c in sections]
    if video is not None:
        nodes.append(Node(node_id=f"{vid}:V", video_id=vid, level="video", item_id="V", frames=video.frames, t=video.t,
                          text=f"{video.label}\n{video.description}", payload=video.model_dump()))
    nodes += [Node(node_id=f"{vid}:{c.id}", video_id=vid, level="chapter", item_id=c.id, frames=(0, 0), t=(c.start_s, c.end_s),
                   chapter_id=c.id, text=f"{c.title}\n{c.gist}", payload=c.model_dump()) for c in run.load_outline()]
    return nodes


def extract_nodes(run: Run) -> tuple[list[Node], dict]:
    """Every entry of a run, and what was extracted. It runs with any of the model stages' files absent."""
    labels, lifetimes = run.load_labels(), run.load_lifetimes()
    steps, sections = run.load_steps(), run.load_sections()
    nodes = frame_nodes(run, run.load_frames(), {fb.frame: fb for fb in run.load_boxes()}, lifetimes, labels)
    nodes += lifetime_nodes(run, lifetimes, labels)
    nodes += transition_nodes(run, run.load_changes(), run.load_interpretations(), labels, steps, sections)
    nodes += summary_nodes(run, steps, sections, run.load_video())
    by_level: dict[str, int] = {}
    for n in nodes:
        by_level[n.level] = by_level.get(n.level, 0) + 1
    return nodes, {"nodes": len(nodes), "by_level": by_level, "labels": labels is not None}
