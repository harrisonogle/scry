# Review (with context): boxes-mode re-base proposal

Reviewed: `docs/proposals/2026-09-21-boxes-mode-rebase.md`, 2026-09-21. Reviewer had the full session history.
Method: prototyped §5 Stage 4 exactly as written, on OCR alone, over both spans (no model calls); then checked
the document against the ledger, the code and the conversation. Prototype and raw output:
`scratchpad/rebase-prototype/` (`stage4_proto.py`, `variant.py`, `smoke.txt`, `span2.txt`, `variant.txt`).
Inputs: RapidOCR boxes and frames of `runs/smoke-rapid` (145–155) and `runs/span2-before` (155–187).

**Verdict: accept with changes.** The architecture holds on real data: the veto at any fraction, areas,
`visual_only` and transients-by-pixels all work. The change-kind and chaining rules as specified do not, and the
evaluation plan should start with a free Stage 4 check it currently lacks. Changes listed at the end.

## 1. What the prototype showed

### Works as specified
- **Veto at any fraction.** Window switches 147→148 and 153→154 (25 % changed): 92/113 and 95/135 boxes vetoed;
  near-static pairs veto all but 1–4 boxes; full-screen cuts veto nothing. No case found where a vetoed box had changed.
- **Keystroke 154→155:** one area, `appended`, `PS C:\Users\msadmin>` ⇒ `… az login`. Correct.
- **`visual_only`.** Cursor-only transitions come out `visual_only` or text-free (158→159, 159→160, 162→163,
  167→168, 180→181). Areas touching no box in either frame occur 4–16 times per large change; the spec has no
  name for them. I folded them into `visual_only`; say so.
- **Transients by pixels.** Frame 151 (taskbar tooltip): its one area shows no change between 150 and 152, hold
  0.6 s ⇒ transient, without the model. The Cloud Shell tooltip (149) is not caught: held 2.8 s > `transient_max_s`
  and the pointer moved, same as today.
- **Large changes.** Myers over the before/after lists behaves: 186→187 (terminal scrolled one command off) gives
  equal 25, delete 7, insert 7.

### Fails as specified
| # | Failure | Evidence (frame pair) |
|---|---|---|
| F1 | **`appended` on the joined list has false positives.** Any unrelated box that precedes new boxes in reading order makes the join a prefix. | 148→149 `G` ⇒ `G oud Shell` (tooltip); 157→158 `Encryption at-re` ⇒ `… PS C:\Users\msadmin>` (occluded browser text + new prompt); 182→183 twice. 4 of the 9 `appended` records over both spans are this artifact, and each would emit a `text_appended` event. |
| F2 | **`appended` has false negatives from asymmetric area membership.** A 2-px OCR box jitter at the margin boundary puts a neighbour box in one list only. | 155→156: title-bar box bottom is y=344 in f155, 346 in f156; the dilated component starts at 345, so the title is in `after` only. Same pattern with `Standard_DS2_V`/`Standard_DS2_` at 176→177. |
| F3 | **The changed box is re-read whole, so OCR jitter in its unchanged part breaks the prefix.** The veto cannot help: the box is under changed pixels. | 156→157 `PS C:\…>` ⇒ `C:\…> az account show` ("PS " dropped); 171→172 ⇒ `PSC:\…> kubect1rollout undo …`; 169→170 `Overwrite? (y/n):■` ⇒ `… : Y` (cursor glyph). Of ~8 command entries in span 2, `appended` fired for 3; 3 misses are this jitter, the rest are genuine replacements (history recall, ghost text), which `changed` labels honestly. |
| F4 | **Pure OCR jitter is recorded as a text change** when only the cursor or ghost text moved under the box. | 172→173→174: `kubect1rollout` ⇒ `kubectl_rollout` ⇒ `kubectlrollout`; 161→162 and 175→176 differ only in spaces. 5 of 32 span-2 transitions. |
| F5 | **Chaining buys nothing here.** 7 chains on span 2, one longer than a single transition: 31 Stage 5 calls for 32 transitions (the current pipeline: 30 for 32). Stage 1's settle already merges keystrokes; F3/F4 break the rest. | `span2.txt`, last lines |
| F6 | **Area count is unbounded on animated or unsettled frames.** "Areas sharing a box merge" does not bound it. | 181→182: 35 areas; 182→183 (1.8 % changed, a page rendering in): 67 areas, 43 single-box `appeared`; 183→184: 47. A `kubectl get nodes` table arrives as 4 records (one per column), 179→180. |
| F7 | **Transient rule is ambiguous** (any area, or all?). With "any", 181→182 (4/35 areas revert) and 182→183 (28/67) would be transients. | I used: every area of i−1→i reverts and hold < max. Make it per-area, or all text-bearing areas. |

A variant I tested (`variant.py`): drop from both lists every box with an identical counterpart in the other frame
(IoU ≥ 0.8, same text), then classify the residue, with `grew` only when one old box remains. It removes all four
F1 false positives (they become `appeared`) and keeps both true keystroke cases. It does not fix F2 unless
membership is made symmetric (include a box's counterpart whenever the box is included), and it does not fix F3:
three more keystroke cases are recoverable only by a whitespace-insensitive prefix, which the owner disliked when
it was proposed for the typed rule. That is a decision, not a detail: see Q-A below.

### New evidence bearing on the owner's Q1 (is a second reading wanted)
On the live command line RapidOCR is materially worse than L34–L35 measured (one prompt line there). Span 2:
`azconfigure --defaultsgroup=…`, `kubect1rollout`, `kubect1configcurrent-context`, `PSC:`, dropped `PS `; the spacing
guard did not fire on any. The before-run's model reading was correct on all six sampled command lines (f161,
f172–f175) and `agree=false` flagged each. The honest contract as drafted records OCR's string as the text change,
so "what command did they run" would answer `kubect1rollout`. Either the recorded text of a changed box prefers
the model's reading (§22 #15, third occurrence, now on the core deliverable) or the contract's strings are
searchable-but-wrong. The proposal treats transcription as a cost ablation (E3); this makes it a correctness one.
Also seen in that run: an id shuffle in row mode at f178 (the model's `Merged "AKS1…` attached to the prompt box).

## 2. The document

### Should-fix
1. **Build Stage 4 first and test it free.** After the re-base Stage 4 needs only OCR and PNGs; containers and
   links are labels. §8 builds it fourth, behind a paid E0. Reorder: schemas → Stage 4 on OCR-only data over both
   spans (what this review did, in minutes) → Stage 2c. Add a phase before E0: "Stage 4 on OCR alone, both spans,
   against the owner's command list". It would have caught F1–F7 for $0.
2. **"Stage 6 untouched" is wrong, and §6 omits consumers.** `hierarchy.py` (`_state_line` uses `units()`,
   `render_transition_line` renders `typed`/`output_appended`), `agent.py` (`get_transitions` returns events,
   `get_node` payload of lines), `prompts/agent.py`, `prompts/stage5.py` and `interpret.validate_refs`
   (`line_ids()`) all consume the deleted records. §6's per-module lists are otherwise accurate: every symbol
   named exists; unlisted and also dying are `_make_line`, `region_bbox`, `_h`, `_median_h`, `_build`, `diff_pair`.
   `rows_rejected`/`grouping_repairs` are dict keys, not functions.
3. **E2 picks "the best two arms" at full scale, then E5 sweeps scale on those two.** L42 showed the coordinate
   list is neutral at 1.0 and decisive at 0.67, so the arm that loses at full scale may win below it. Carry A plus
   both single-image arms (C, D) into E5, or screen arms at two scales (1.0 and 0.5). This is the owner's
   sequencing concern in miniature.
4. **E5 is conditional on Q1/E3.** If a second reading is kept, scale is bounded near 0.67 and most of E5
   (36 runs) is moot. Say "E5 only if transcription is off, or run as the price of keeping it".
5. **Icon boxes.** The prompt tells the model to return `""` for an icon, and L41 left "what does `""` mean" open.
   With RapidOCR that is ~5 glyph boxes per frame (`口`, `中`, `区`), which also dominate the vanish/appear residue
   in the box-stability result. State it: model `""` ⇒ box flagged non-text, out of agreement denominators and
   out of index text.
6. **Container appeared/disappeared:** "most of its boxes are after-only" is undefined (after-only = in an area
   with no identical counterpart?) and the majority threshold is a constant without evidence. Testable for free on
   the existing row-mode containers before building; not done here.
7. **Costs.** Group-only output alone is ≈ $0.034 per frame (1,342 tokens), so "$0.031 at scale 0.2" is below the
   floor; boxes mode will emit more (≈ 110 single ids plus links). E2 is nearer $21–27 than $17 and E5 nearer
   $21–25. Put one group-only boxes-mode run in E0 (≈ $0.70) to fix the estimates before committing. Total is
   more likely $80–95.
8. **Watch-list items already have evidence** and should move to "decide": cursor glyph read as text (169→170),
   pointer clipping a box (151→152, 152→153, `891c` ⇒ ` c`), occlusion clipping at a window edge (185→186
   `Identit` ⇒ `Identity`). Each produces `changed` records today. The proposal's own rule is "logic on evidence".

### Nits
- §1: "rejected 116 real rows" was measured on Vision boxes (L29-era), the 0.365→0.752 swing on Rapid boxes.
- `transient_max_s = 2.0` is an absolute time constant that missed a 2.8-s tooltip; principle 5 covers geometry only.
- Stage 7 lists "both readings of a disagreeing box" unconditionally; it exists only when transcribing.
- No phase decides which link kinds survive; say E1 reports `link_consistency` per kind and the cut is made there.
- Reading order is still the L31 banding heuristic; it now also decides prefix-ness (F1), so it is not harmless
  outside `visual_only`.
- The spacing guard (owner: keep enabled) is outside the proposal but its 0.25 ratio did not fire on any span-2
  dropped space; worth a line under risks.

### Checked and fine
Vocabulary and rename table; principles 1–6 against the conversation (caret attribution dropped, blink tracker
kept, no UI tree, cold-run policy, scales 0.5–0.2, selective factorial, pairs as key/value, frame node with all
box texts, four referencing arms, position-and-similarity assignment); `missed` texts never entering a change
(removes the L41 phantom); ledger citations L31, L32, L38, L41 (+20 % cost), L42; E0/E1 arithmetic.

## 3. Questions this review adds for the owner
- **Q-A.** For the `grew`/`appended` label, is a whitespace-insensitive prefix acceptable now that the label is a
  convenience and the record is before/after? Without it 3 of 6 real keystroke entries in span 2 are `changed`.
- **Q-B.** Which string does a text change record when the readers disagree on the changed box? Span 2 says OCR's
  is often wrong exactly there.

## 4. Changes requested before acceptance
1. Replace the joined-list prefix rule: symmetric membership, drop identical counterparts, classify the residue
   (F1, F2); decide Q-A for F3; say how F4 (jitter-only changes) is labelled.
2. Bound or aggregate areas on large or animated changes (F6); define text-free areas; make transients per-area (F7).
3. Reorder the build so Stage 4 lands first on OCR-only data, and add the free Stage 4 phase (should-fix 1).
4. Fix the E2→E5 arm selection and make E5 conditional (should-fix 3, 4).
5. Correct "Stage 6 untouched" and extend §6 to hierarchy, agent and prompts (should-fix 2).
6. Reframe Q1/E3 as correctness, with the span-2 command-line evidence, and answer Q-B.
7. Drop the claim that chaining keeps Stage 5 calls down; measure it, or drop chaining until it earns its place (F5).
