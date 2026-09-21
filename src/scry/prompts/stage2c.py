VERSION = "s2c-v1"

SYSTEM = """You transcribe and structure screenshots of computer tutorials (terminals, code editors, browsers, dialogs).

You are shown the same screenshot twice. Image 1 is the clean frame. Image 2 is the same frame with numbered boxes drawn around detected text lines; each number sits beside its box and is NOT part of the screen's text. Transcribe from Image 1; use Image 2 only to know which number refers to which line. A number is written as a mark id: l1, l2, ...

Produce a JSON object with these fields.

regions: the screen as a tree of regions: windows (top-level application windows), panes (areas inside a window: editor, terminal pane, navigation, content blade, toolbar, title bar), and popups (menus, dialogs, tooltips, toasts). Name each region and its application. Every mark id must appear in exactly one row of exactly one region, or in unassigned_line_ids.

rows: within a region, its visual lines in reading order. A row is one visual line: text that sits on one line (a prompt and its command, a table's cells, tabs side by side, a label and its value) is one row, listed left to right. A line the boxes missed is an empty row []. Do not put marks from different lines in one row.

vlm_lines: the verbatim text of each row, one entry per row, same order and length as rows. Preserve case, punctuation, whitespace and symbols exactly as displayed. Never correct, complete, or normalize commands, code, paths, or identifiers. Use ? for any character you cannot resolve. Do not omit rows. Icons are not text: do not transcribe them.

focused_region, focused_conf, focused_cues: the window with keyboard focus, your 0-1 confidence, and the visual cues you used (title bar highlight, caret visible, dialog modality).

occludes: for each region, the ids of regions it visually covers, in whole or in part.

description: anything the rows cannot express: selections, highlights, toggles, icons, diagram relationships, dialogs, animating regions.

Marks listed as animating are inside regions that were changing continuously when the frame was captured; their text is low confidence — say so rather than guessing."""

# Group-only variant (`[model] stage2c_transcribe = false`, §8.3): the region tree, rows, focus and description without a
# transcription. Identical to SYSTEM except the opening lines no longer say "transcribe", the rows paragraph asks only for
# the grouping, and the vlm_lines paragraph is one sentence declining the transcription; test_perceive pins the rest.
SYSTEM_GROUP_ONLY = """You structure screenshots of computer tutorials (terminals, code editors, browsers, dialogs).

You are shown the same screenshot twice. Image 1 is the clean frame. Image 2 is the same frame with numbered boxes drawn around detected text lines; each number sits beside its box and is NOT part of the screen's text. Read the screen from Image 1; use Image 2 only to know which number refers to which line. A number is written as a mark id: l1, l2, ...

Produce a JSON object with these fields.

regions: the screen as a tree of regions: windows (top-level application windows), panes (areas inside a window: editor, terminal pane, navigation, content blade, toolbar, title bar), and popups (menus, dialogs, tooltips, toasts). Name each region and its application. Every mark id must appear in exactly one row of exactly one region, or in unassigned_line_ids.

rows: within a region, its visual lines in reading order. A row is one visual line: the marks whose text sits on one line (a prompt and its command, a table's cells, tabs side by side, a label and its value) form one row, listed left to right. Do not put marks from different lines in one row.

Do not transcribe any text: the OCR reading of each mark will be used.

focused_region, focused_conf, focused_cues: the window with keyboard focus, your 0-1 confidence, and the visual cues you used (title bar highlight, caret visible, dialog modality).

occludes: for each region, the ids of regions it visually covers, in whole or in part.

description: anything the rows cannot express: selections, highlights, toggles, icons, diagram relationships, dialogs, animating regions.

Marks listed as animating are inside regions that were changing continuously when the frame was captured; their text is low confidence — say so rather than guessing."""


# Structural variants (`[model] stage2c_panes = false`, `stage2c_rows = "boxes"`): the same prompt with one or two
# paragraphs swapped. build() derives each from SYSTEM / SYSTEM_GROUP_ONLY so every other paragraph stays shared
# verbatim; test_perceive pins the paragraph indices. The schema variants in schemas.py carry the same wording.
REGIONS_NOPANES = """regions: the screen as a list of regions of two kinds only: windows (top-level application windows) and popups (menus, dialogs, tooltips, toasts). Do not create panes: everything inside a window (its title bar, tabs, toolbar, navigation, editor, terminal, content) belongs to the window's own rows. A window's parent is null; a popup's parent is the window it belongs to, or null. Name each region and its application. Every mark id must appear in exactly one row of exactly one region, or in unassigned_line_ids."""

ROWS_BOXES = """rows: within a region, one row per mark, in reading order (top to bottom, left to right along a visual line). Each row is a list holding exactly one mark id; never put two marks in one row. A line the boxes missed entirely is an empty row []."""

VLM_LINES_BOXES = """vlm_lines: the verbatim text of each row's mark (of the missed line, for an empty row), one entry per row, same order and length as rows. Preserve case, punctuation, whitespace and symbols exactly as displayed. Never correct, complete, or normalize commands, code, paths, or identifiers. Use ? for any character you cannot resolve. Do not omit rows. Icons are not text: do not transcribe them."""

ASSOCIATIONS = """associations: within a region, the groups of mark ids that belong together as one label-and-value pair (a property name and its value, a form field and its content, a prompt and its command) or as one table row (its cells), each group listed left to right. A mark belongs to at most one group; do not list marks that stand alone."""

PARAGRAPH = {"regions": 3, "rows": 4, "vlm_lines": 5}  # indices into SYSTEM.split("\n\n")


def build(transcribe: bool = True, panes: bool = True, rows: str = "lines") -> str:
    paras = (SYSTEM if transcribe else SYSTEM_GROUP_ONLY).split("\n\n")
    if not panes:
        paras[PARAGRAPH["regions"]] = REGIONS_NOPANES
    if rows == "boxes":
        paras[PARAGRAPH["rows"]] = ROWS_BOXES
        if transcribe:
            paras[PARAGRAPH["vlm_lines"]] = VLM_LINES_BOXES
        paras.insert(PARAGRAPH["vlm_lines"] + 1, ASSOCIATIONS)
    return "\n\n".join(paras)


SYSTEM_NOPANES = build(panes=False)
SYSTEM_BOXES = build(rows="boxes")
SYSTEM_NOPANES_BOXES = build(panes=False, rows="boxes")
