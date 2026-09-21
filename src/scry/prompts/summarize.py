"""The prompt contracts of `summarize`: a boundary call over one-line items, then one elaboration call per segment.
Every example is invented; nothing in them comes from a video under evaluation."""

VERSION = "summarize-v1"

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
known). For a transition an item holds what was measured (the text before and after each change) and a model's
interpretation: action, result, entered (what the user had entered, as far as the frames showed) and submitted (yes,
no or unclear: whether what was entered took effect). Return a short label and a description. Every sentence of the
description carries, in square brackets, the ids of the items it rests on, e.g. [T13]. Quote commands, paths and
identifiers exactly as the items give them; do not paraphrase or correct them. Say that a command was run, or a form
was sent, where an item says submitted: yes. Where it says no or unclear, say what was entered or shown instead: text
on an input line may have been a suggestion, or may have been cleared. List every cited id in refs.

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
without a bracketed id."""
