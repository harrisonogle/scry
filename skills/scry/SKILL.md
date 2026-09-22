---
name: scry
description: Answer questions about a screen-recording video (what was typed, run, clicked, shown, and when) with the scry MCP server's tools; index a new video first when it is not listed. Use when the user asks what happened in a tutorial or screen recording, which command was run, what a form was set to, or what the screen showed at some point.
---

# scry: evidence from a screen recording

scry indexes a video into what was on screen and what changed. The tools (`scry` MCP server) read that index; you
answer from it and cite it. Every claim needs a citation the reader can check. When the record does not show
something, say so: that is a correct answer.

## Workflow
1. `list_videos` first; use the `video` id it gives (a path like `demo/aks-tutorial`). If the video is not there,
   `index_video(path)` runs the pipeline (minutes; about $5 a video, $18 with annotation); say the cost before you run it.
2. `search(video, query)` first, for every question. Put exact strings (commands, flags, names, paths, values) in
   double quotes: `"kubectl create deployment"`. Narrow with `level`, `t_from`/`t_to` (seconds) or `app`; a filtered
   search that finds nothing is worth repeating without the filter. `summary(video)` orients you in a long video.
3. `get_transitions(video, t_a, t_b)` around the time that matters, to establish order: what was entered, whether
   it was submitted, what followed. Keep the range narrow (a minute or two).
4. `get_node(video, node_id)` for the full entry behind a hit (every reading, links, window, the interpretation).
5. `get_frame(video, frame, image=true)` whenever a text is doubtful or the question is visual (a selection, a
   toggle, a dialog, a form value, an error). Look at the image; box rectangles are in full-resolution pixels.
6. `ask(video, question)` runs scry's own answering agent and returns an answer with citations and a tool log in
   one call. It costs money (about $0.50-1) and takes 20-60 s; use it when the user wants a quick answer rather
   than the evidence, or to cross-check yours.

## Levels in search hits
- `lifetime`: one piece of on-screen text, recorded once, with first and last time seen, `sightings` (captured
  frames it was in), and its readings: `ocr` and, when annotated, `vlm` (a vision model's independent reading);
  `agree` says whether they match. `unstable` and `seen_once` are warnings.
- `frame`: a whole screen at one captured frame (identical consecutive frames come back as one hit with a range).
- `transition`: what changed between two consecutive captured frames, with a model's interpretation: `action`,
  `result`, `entered_text` (what the user had entered, without anything the application suggested) and
  `submitted` (yes, no, unclear).
- `step`, `section`, `video`: summaries written from the transitions, good for finding where something happens;
  confirm details in the entries below them. `chapter`: an optional outline of the whole video.

## Rules of evidence
- Cite a frame and a box (`frame 12`, `12:b4`), a lifetime id (`L1592`) or a transition id (`T7`) for every claim,
  with the time in seconds. Ranges are fine: `frames 191-195, 745.7-757.8 s`.
- Quote a text verbatim only when two readers agree (`agree: true`). Otherwise give both readings, or look at the
  frame and read it yourself and say you did. The usual difference is one character or a space, and in a command
  that matters. `entered_text` on a transition is a second opinion on a command's text.
- Text on screen is not evidence that a command ran. A transition with `submitted: yes` is: it rests on what the
  frames showed next (output that answers the command, a new prompt under it). Cite that transition.
- A shell's grey suggestion, an autocomplete entry or placeholder text is not typed text: a text on an input line
  is not proof that anyone typed it, still less that it ran.
- How long a text stayed on screen is evidence of nothing: a command can run and scroll away at once, or sit
  unexecuted for a minute.
- When the record does not show it, say so, give the closest thing that was seen, and name the time range worth
  inspecting. Do not fill the gap from what tutorials usually do.

## Using with Claude Code
`.mcp.json` at the repository root registers the server (`uv run scry-mcp --runs runs --videos .`); Claude Code
starts it on demand. Non-interactively: `claude -p "<question>" --mcp-config .mcp.json --allowedTools "mcp__scry__*"`.

## Using with GitHub Copilot CLI
Add the server to `~/.copilot/mcp-config.json` (or pass the same JSON with `--additional-mcp-config @file.json`);
`cwd` must be the scry checkout so that `uv run` finds the project and `runs` resolves:

```json
{
  "mcpServers": {
    "scry": {
      "type": "local",
      "command": "uv",
      "args": ["run", "scry-mcp", "--runs", "runs", "--videos", "."],
      "cwd": "/path/to/agentic-escort",
      "tools": ["*"]
    }
  }
}
```

Then `copilot -p "<question>" --allow-tool 'scry'` (tool permissions are `scry` for every tool or `scry(search)` for
one; `--allow-all-mcp-server-instructions` also passes the server's instructions to the model).
