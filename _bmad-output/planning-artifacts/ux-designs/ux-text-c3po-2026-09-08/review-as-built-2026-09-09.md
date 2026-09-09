# As-Built Review — text-c3po Text Mode (2026-09-09)

Reviewer: Sally (bmad-agent-ux-designer) under bmad-ux Validate intent.
Scope: built Text mode (commits through `0da7e7a`) vs `DESIGN.md` + `EXPERIENCE.md`
(`status: final`, 2026-09-08) plus the operator's screenshot critique log of 2026-09-09.
Method: spine citations per finding; severity = downstream impact. No subagents
available in this environment — single-reviewer pass, rubric adapted to as-built.

## Overall verdict

The spines are sound; the build drifted from them. Every operator complaint
traces to either a drift the spine already forbade (wrapping → the stacking
rule; mystery icons → the hover-only ban; label-less dot → the pairing rule)
or a stale spine section (commentary, three cards). The design was not bad —
it was abandoned file by file under screenshot pressure. Fix = reconcile:
either honor the spines or record explicit overrides. Silent drift is the
only unacceptable option.

## Findings by severity

### High

- **[Spine contradiction] Dot lost its text label.** DESIGN.md Components
  ("Dots are always paired with a text label"), Do's/Don'ts ("Pair every
  status dot with a text label"), EXPERIENCE.md Accessibility Floor (WCAG AA,
  "status dots always paired with text labels"), and Interaction Primitives
  ("hover-only affordances" banned). Built: dot-only + tooltip. The operator
  asked for dot-only; the spine forbids it. *Fix:* restore a compact label
  ("Down"/"Connected") OR record an override accepting tooltip + disconnect
  SnackBar as the paired signal. Decide, don't drift.
- **[Spine contradiction] Sub-1100px stacking rule ignored.** EXPERIENCE.md
  Responsive: below 1100px Text mode stacks (input → pickers → button →
  cards); minimum window is 960 — so the spine wants Text mode stacked,
  always, in v1. Every wrap/overflow bug in the critique log came from
  disobeying this. *Fix:* honor it (stacked layout kills the whole fit-bug
  class at once) OR revise the spine with a two-column-at-960 rule plus
  minimum control widths. This is the single highest-leverage decision open.
- **[Spine contradiction] Live partial preview vs streaming ban.**
  EXPERIENCE.md bans "token-streaming partial rendering" everywhere; built
  streams the formal value into its tab live. *Fix:* narrow the ban to
  live/file utterance lists (its original context, FR-10) and bless Text-mode
  progressive preview with the "final cards render from parsed JSON" rule.

### Medium

- **[Ambiguous] Red for Ollama-down.** DESIGN.md: "Live Red means exactly
  one thing: capture is running… never for errors (errors use Material
  `error` default)". Down-state red is defensible under the error-default
  clause, or a violation under the degraded-amber (`#B45309`) clause.
  *Fix:* pick one reading and write it into Colors; current `#B3261E`
  matches Material error default, amber matches "retrying/restaring" states.
- **[Token drift] Background.** Built `#EDF1F6` vs token paper `#F7F5F0`
  (DESIGN.md Colors). One-line revert.
- **[Layout drift] Two chrome rows.** DESIGN.md Layout: "Top strip: mode
  toggle left, Ollama status dot + model Dropdown right. One row". Built:
  AppBar row + toggle row, model picker in AppBar instead of the text row.
  *Fix:* either collapse to one row per spine or update Layout to the
  AppBar pattern with its rationale (frees text-row width).
- **[Stale spine] Commentary dropped.** Flow 1's climax and the Local-Trust
  section depend on commentary/register notes; operator dropped the field.
  *Fix:* restore it or update Flow 1 + Local-Trust + Output-cards rows.
- **[Missing] Keyboard accelerators.** Interaction Primitives require
  `Ctrl+Enter` submit and `Esc` cancel; neither is wired. *Fix:* wire both
  (Esc already has the stop-event machinery waiting).

### Low

- Block spacing 8–12px vs spine default 16px between blocks (fit-driven;
  harmless if recorded).
- Cards use `elevation=1`; spine wants 1px border outlines, no elevation.
- Mode header display line absent ("Text — type, pick, translate").
- "Detected: English" microcopy not in the Voice table (add a row).
- Tab order vs reading order unverified headless; needs one keyboard pass.

## Operator scorecard (critique log vs spine)

| Complaint | Verdict |
|---|---|
| Wrapping/overflow rows | Spine agrees (stacking rule); build disobeyed |
| Undiscoverable icons | Spine agrees (hover-only ban); fixed per spine |
| Mystery status, stale green | Spine agrees (paired label, live values); half-fixed |
| Dot-only, no sentence | Operator vs spine — needs override decision |
| Red for down state | Ambiguous spine — needs reading decision |
| Speed (thinking, context, splitter) | Outside spines' scope; engineering, resolved |

## Proposed spine updates (Update mode)

1. Responsive: stacked Text mode always (or two-column-at-960 with minima).
2. Streaming ban narrowed to utterance lists; Text preview blessed.
3. Status pattern: dot-only + tooltip + SnackBar recorded as the paired signal (override), or compact label restored.
4. Colors: red reading decided; background token re-affirmed.
5. Layout: AppBar pattern recorded if kept; commentary fate decided; Voice row for detected-language; accelerators scheduled.

## Operator decisions (2026-09-09)

1. Dot-only rejected where space allows: compact Connected/Down label restored (no override needed).
2. Connection loss = unrecoverable in-app error: Material error-red reading adopted.
3. Streaming ban narrowed to utterance lists; Text progressive preview blessed.
