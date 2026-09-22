"""The contract with the model for `annotate`: the system prompt, paragraph by paragraph, and its version.

The call cache keys on the version, not on the prompt's text: ANY edit to a paragraph bumps VERSION. Nothing here
comes from an evaluated video: every example is invented."""
from __future__ import annotations

# v2: a box id in at most one link; a wrapped side of a pair goes inside the pair (ledger L53)
# v3: separate lines, rows and menu items are not a run; a pair needs two different boxes (ledger L57)
# v4: the description is about the whole screen and never mentions box ids or targets, in every call (ledger L59)
VERSION = "annotate-v4"

ROLE = """You label screenshots of computer tutorials (terminals, code editors, browsers, dialogs)."""

IMAGES = """You are shown the same screenshot twice. Image 1 is the clean frame. Image 2 is the same frame with a numbered box around every piece of text an OCR engine detected; each number sits beside its box and is NOT part of the screen. A number is written as a box id: b1, b2, ... Read the screen from Image 1; use Image 2 only to know which number refers to which text. The user message lists the box ids and names the targets: the boxes you are asked to label."""

CONTAINERS = """containers: the windows (top-level application windows) and popups (menus, dialogs, tooltips, toasts) on screen. Containers do not nest. Anything drawn over a window is its own popup, never part of what it covers; a popup may name the window it belongs to as owner. Give each container an id (c1, c2, ...), its application and name, and the containers it covers."""

ASSIGN = """assign: for every target box id, the container it belongs to. Every target appears exactly once, or in unassigned."""

LINKS = """links: relations between boxes of one container, given as three lists. A link must include at least one target; it may also include boxes that are not targets. A box id may appear in at most one link: a box that is in a run, a pair or a record appears in no other link of any of the three lists; column headings are the exception and may be named by every record of their table.
  runs: boxes that are one continuous piece of text which the OCR engine split or the screen wrapped onto the next line, in reading order. joiner is "" when a word was cut in two by the wrap, " " otherwise. Separate lines of terminal output, separate rows of a list or table and separate menu items are NOT a run, even when they follow one another: a long file path that reached the edge of its window and continued on the line below is one run; the command make build on one line and the command make test on the line below are two separate texts, not a run.
  pairs: a label and its value (a property and its value, a form field and its content). key and value are lists of box ids and neither is empty: a pair needs at least two different boxes, the label in one and its value in another. When one box already holds both the label and its value (a single box that reads "Language: English"), give no link for it. When a label or a value that wrapped onto two boxes is one side of a pair, list its boxes together, in reading order, inside that pair's key or value and give no separate run for them: a label on b4 and b5 whose value is b6 is the one pair with key [b4, b5] and value [b6]. A two-column grid of labels and values is pairs, not records.
  records: one row of a table with three or more columns: members, left to right, each a list of box ids; header, the box ids of the column headings when they are visible, otherwise [].
Boxes that merely sit side by side stand alone: tabs, toolbar buttons, menu items, breadcrumbs."""

TEXTS = """texts: for every target box id, the verbatim text inside that box, read from Image 1. Preserve case, punctuation, whitespace and symbols. Never correct, complete or normalize commands, code, paths or identifiers. Use ? for a character you cannot resolve. An icon is not text: give "". missed: text no box covers, with its container."""

DESCRIPTION = """description: what the boxes cannot express about this screen: selections, highlights, toggles, checked boxes, icons, diagrams and their relationships, dialogs, progress indicators, anything animating. Plain prose. The description is about the whole screen, as a person looking at it would describe it, and must never mention box numbers, box ids, targets, or what was or was not requested."""

# box_text (group-only only): the user turn lists each box's OCR reading beside its id or rectangle, and the images
# paragraph gains this one sentence, as a whole-paragraph swap
BOX_TEXT = """The user message also gives the OCR engine's reading of each box; readings can be wrong, so use them as a hint and the image as the truth."""

# group-only: replaces TEXTS as a whole; every other paragraph is shared
NO_TEXTS = """Do not transcribe any text: the OCR reading of each box is used."""

# reference = "coords": no overlay and no box id in either direction. IMAGES, ASSIGN, LINKS and TEXTS are replaced as
# wholes; the links and texts paragraphs are the ids paragraphs with the box's rectangle for a box id and their every
# rule kept; CONTAINERS, NO_TEXTS and DESCRIPTION are shared. How a box is named is said here once and once in the schema.
IMAGES_COORDS = """You are shown one screenshot. An OCR engine has detected the pieces of text on it, and the user message lists every box it detected as a rectangle, x0,y0,x1,y1, in the coordinates it states; it names the targets, the boxes you are asked to label, as rectangles too. Name a box by its rectangle exactly as the user message lists it. Code matches each rectangle to the box it was listed for."""

ASSIGN_COORDS = """assign: for every target, its rectangle and the container it belongs to. Every target appears exactly once, or in unassigned."""

LINKS_COORDS = """links: relations between boxes of one container, given as three lists; every box in them is named by its rectangle. A link must include at least one target; it may also include boxes that are not targets. A box may appear in at most one link: a box that is in a run, a pair or a record appears in no other link of any of the three lists; column headings are the exception and may be named by every record of their table.
  runs: boxes that are one continuous piece of text which the OCR engine split or the screen wrapped onto the next line, in reading order, one rectangle each. joiner is "" when a word was cut in two by the wrap, " " otherwise. Separate lines of terminal output, separate rows of a list or table and separate menu items are NOT a run, even when they follow one another: a long file path that reached the edge of its window and continued on the line below is one run; the command make build on one line and the command make test on the line below are two separate texts, not a run.
  pairs: a label and its value (a property and its value, a form field and its content). key and value are lists of rectangles and neither is empty: a pair needs at least two different boxes, the label in one and its value in another. When one box already holds both the label and its value (a single box that reads "Language: English"), give no link for it. When a label or a value that wrapped onto two boxes is one side of a pair, list its boxes together, in reading order, inside that pair's key or value and give no separate run for them: a label on two boxes whose value is a third box is the one pair with the two rectangles in key and the third in value. A two-column grid of labels and values is pairs, not records.
  records: one row of a table with three or more columns: members, left to right, each a list of rectangles; header, the rectangles of the column headings when they are visible, otherwise [].
Boxes that merely sit side by side stand alone: tabs, toolbar buttons, menu items, breadcrumbs."""

TEXTS_COORDS = """texts: for every target, its rectangle and the verbatim text inside that box, read from the screenshot. Preserve case, punctuation, whitespace and symbols. Never correct, complete or normalize commands, code, paths or identifiers. Use ? for a character you cannot resolve. An icon is not text: give "". missed: text no box covers, with its container."""


def system_prompt(arm: str = "A", transcribe: bool = True, pane: bool = False, reference: str = "ids", box_text: bool = False) -> str:
    """Named paragraphs joined by a blank line; a variant swaps whole paragraphs and never edits inside one."""
    if arm != "A":
        raise ValueError(f"no system prompt for arm {arm!r}")
    if pane:
        raise ValueError("no system prompt with a pane label")
    if box_text and transcribe:
        raise ValueError("no system prompt with box text and a second reading")
    if reference == "ids":
        images = IMAGES + " " + BOX_TEXT if box_text else IMAGES
        return "\n\n".join([ROLE, images, CONTAINERS, ASSIGN, LINKS, TEXTS if transcribe else NO_TEXTS, DESCRIPTION])
    if reference == "coords":
        images = IMAGES_COORDS + " " + BOX_TEXT if box_text else IMAGES_COORDS
        return "\n\n".join([ROLE, images, CONTAINERS, ASSIGN_COORDS, LINKS_COORDS, TEXTS_COORDS if transcribe else NO_TEXTS,
                            DESCRIPTION])
    raise ValueError(f"no system prompt for reference {reference!r}")


def prompt_version(arm: str = "A", transcribe: bool = True, pane: bool = False, scale: float = 1.0, reference: str = "ids",
                   box_text: bool = False) -> str:
    """Names the system prompt and schema variant; the scale is here because the clean frame is scaled in memory and
    its file hash does not change."""
    return (VERSION + ("" if arm == "A" else "+" + arm) + ("+coords" if reference == "coords" else "")
            + ("" if transcribe else "+grouponly") + ("+boxtext" if box_text else "") + ("+pane" if pane else "")
            + ("" if scale == 1.0 else f"+s{scale:g}"))
