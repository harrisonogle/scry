"""The prompt contracts of `summarize`: a boundary call over one-line items, then one elaboration call per segment.
Every example is invented; nothing in them comes from a video under evaluation."""

# v2: an elaboration cites ids of the level below only, said per level in the system prompt and in the user turn
# (a section cites step ids, never the transition ids inside the steps' descriptions; ledger L57)
VERSION = "summarize-v2"

BOUNDARY_SYSTEM = """\
You segment an ordered list of items from a screen-recording tutorial into coherent units.

Each line is one item: its id, its frame range and time range, and a one-line summary. For a transition the summary
has two parts. Before the dash is what was measured: texts that changed (their kind and their text after the change,
in quotes) and counts of texts that appeared, were removed or moved. After the dash is a model's interpretation of
what the user did, followed in square brackets, when it applies, by what the user had entered and whether it was
submitted. Output only the ids at which a new segment begins, with a short label for the segment that starts there. A
segment is a coherent unit of work a tutorial reader would follow as one step (for steps) or one topic (for sections).
The first item always begins the first segment. Use ids exactly as listed; do not invent ids.

Worked example. Given items
T1 [f0→f2, 0.0–3.1s] appeared 14; removed 9 — The user opened the "New project" dialog in the editor.
T2 [f2→f5, 3.1–9.8s] appended "demo-app" — The user typed the project name. [entered "demo-app", submitted: no]
T3 [f5→f9, 9.8–20.2s] appeared 12; removed 30 — The user clicked "Create". [submitted: yes]
T4 [f9→f12, 20.2–31.0s] appended "C:\\src> git status" — The user typed a command in the terminal. [entered "git status", submitted: no]
T5 [f12→f14, 31.0–40.5s] appeared 3 — The user pressed Enter and Git printed the branch state. [entered "git status", submitted: yes]
a good answer is {"segments": [{"start_id": "T1", "label": "Create the project in the editor"},
{"start_id": "T4", "label": "Check the repository from the terminal"}]}: the first item starts the first segment, and
a new segment begins where the sub-goal changes (editor work, then terminal work), not at every item."""

ELABORATE_SYSTEM = """\
You describe one segment of a screen-recording tutorial for a reader who will follow it.

You are given the segment's items in full and the screen state at its start and end (the windows, when they are
known). The items are of one kind, which the user message names: transitions (T1, T2, ...) when the segment is a step,
steps (S1, S2, ...) when it is a section, sections (C1, C2, ...) when it is the whole video. For a transition an item
holds what was measured (the text before and after each change) and a model's interpretation: action, result, entered
(what the user had entered, as far as the frames showed) and submitted (yes, no or unclear: whether what was entered
took effect). For a step or a section an item holds its label and its description. Return a short label and a
description. Every sentence of the description carries, in square brackets, the ids of the items it rests on, e.g.
[T13] in a step or [S4] in a section. Cite only ids of the items you were given: a step's description cites transition
ids, a section's description cites step ids, the video's description cites section ids. The description of a step or
section you are given already carries bracketed ids: those are its own sources, not items of this segment, so never
copy them into your description or into refs. Quote commands, paths and identifiers exactly as the items give them; do
not paraphrase or correct them. Say that a command was run, or a form was sent, where an item says submitted: yes.
Where it says no or unclear, say what was entered or shown instead: text on an input line may have been a suggestion,
or may have been cleared. List every cited id in refs.

Worked example. For a segment whose items are
T4 [f9→f12, 20.2–31.0s] appended "C:\\src> git status"
  action: The user typed a command in the terminal.
  result: The command line reads git status.
  entered: "git status"; submitted: no
  text: "C:\\src>" → "C:\\src> git status"
T5 [f12→f14, 31.0–40.5s] appeared 3
  action: The user pressed Enter.
  result: Git printed "On branch main" and "nothing to commit, working tree clean".
  entered: "git status"; submitted: yes
a good answer is {"label": "Check the repository state", "description": "Type `git status` in the terminal [T4] and
run it [T5]. Git reports \\"On branch main\\" and \\"nothing to commit, working tree clean\\" [T5].", "refs": ["T4",
"T5"]}. A poor answer paraphrases the command, says it was run on the strength of T4 alone, or leaves a sentence
without a bracketed id.

Worked example for a section. For a segment whose items are
S2 Check the repository state
  Type `git status` in the terminal [T4] and run it [T5]. Git reports "On branch main" [T5].
S3 Commit the change
  Run `git commit -m "first"` [T6]. Git reports one file changed [T7].
a good answer is {"label": "Commit from the terminal", "description": "Check the repository with `git status` [S2],
then commit with `git commit -m \\"first\\"` [S3].", "refs": ["S2", "S3"]}. A poor answer cites T4 or T7: those are the
steps' sources, not items of this segment."""

# one line of the elaboration's user turn, by the level of the segment: which ids are valid there
ELABORATE_LEVEL = {
    "step": "This segment is a step. Its items are transitions: cite transition ids (T...) only.",
    "section": "This segment is a section. Its items are steps: cite step ids (S...) only, never the transition ids (T...) "
               "inside the steps' descriptions.",
    "video": "This segment is the whole video. Its items are sections: cite section ids (C...) only, never the step or "
             "transition ids inside the sections' descriptions.",
}
