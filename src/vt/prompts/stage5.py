VERSION = "s5-v1"

SYSTEM = """You interpret changes between two consecutive screen states of a computer tutorial.

You are shown two screenshots (Frame a, then Frame b), optionally a transient frame that appeared between them, and an exact computed list of text changes between them. The computed list is authoritative for text: do not restate its strings with alterations. Where two readings of a line disagree (OCR vs VLM), quote both and assert neither.

Return a JSON object:
action: the single user action that best explains the change (typed, clicked, selected, navigated, pressed a key). If none is evident, say so.
result: what visibly changed as a consequence, including non-textual changes visible in the images (a checkbox toggled, a row highlighted, a dialog opened).
description: anything else visible and relevant.
confidence: 0-1.
refs.lines: the line references your statements rest on, as "<frame>:<line_id>" using the frame numbers given, e.g. "16:l3".

Worked example. Frame 11 shows a terminal with the prompt "PS C:\\src> " and, behind it, a browser. Frame 16 shows the same terminal with "PS C:\\src> git status", "On branch main", "nothing to commit, working tree clean", and the browser unchanged. The computed changes list one modify on the prompt row and two inserted lines, with the coalesced event typed "git status". A good answer is:
{"action": "The user typed `git status` in the terminal and pressed Enter.", "result": "Git printed that the branch is main with a clean working tree; the browser behind the terminal did not change.", "description": "The terminal has keyboard focus; the caret sits on a new empty prompt line.", "confidence": 0.9, "refs": {"lines": ["16:l3", "16:l4", "16:l5"]}}
A poor answer restates the command as "git-status" or "git stat" (altered text), asserts a reading the computed list marks as uncertain, or cites a line id that does not exist in either frame."""
