---
name: text-c3po
description: Local-first desktop translator — one Flet window, three modes (text, live, file). Flet 0.86 Material is the UI system; this file specifies the brand-layer delta only.
status: final
updated: 2026-09-08
colors:
  background: '#F7F5F0'
  surface: '#FFFFFF'
  ink: '#1B1B1F'
  muted: '#6B7280'
  border: '#E2E0DA'
  primary: '#1F5FA8'
  primary-foreground: '#FFFFFF'
  live: '#D64541'
  live-foreground: '#FFFFFF'
  success: '#1E7E34'
  warning: '#B45309'
  background-dark: '#14181D'
  surface-dark: '#1E242B'
  ink-dark: '#E8EAED'
  muted-dark: '#9AA0A6'
  border-dark: '#2E353D'
  primary-dark: '#7AA7E0'
  primary-foreground-dark: '#0A1A2A'
typography:
  display:
    fontFamily: 'System'
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.25'
  body:
    fontFamily: 'System'
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label:
    fontFamily: 'System'
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.4'
  timestamp:
    fontFamily: 'monospace'
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
rounded:
  sm: 4px
  md: 8px
  lg: 12px
  full: 9999px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '6': 24px
  '8': 32px
components:
  mode-toggle:
    background: '{colors.surface}'
    foreground: '{colors.ink}'
    active-background: '{colors.primary}'
    active-foreground: '{colors.primary-foreground}'
    radius: '{rounded.md}'
  translate-button:
    background: '{colors.primary}'
    foreground: '{colors.primary-foreground}'
    radius: '{rounded.md}'
  output-card:
    background: '{colors.surface}'
    border: '{colors.border}'
    radius: '{rounded.md}'
  caption-row:
    background: '{colors.surface}'
    border: '{colors.border}'
    radius: '{rounded.sm}'
  status-dot-active:
    background: '{colors.live}'
    radius: '{rounded.full}'
  status-dot-ok:
    background: '{colors.success}'
    radius: '{rounded.full}'
---

## Brand & Style

text-c3po is a quiet local tool, not a chat app. One native Flet window, three mode toggles, no browser chrome, no marketing surface. The aesthetic posture is *workbench calm*: warm paper background, one brand blue for "this acts," one record red that means "capture is live" and nothing else. Everything else inherits Flet 0.86 Material defaults — Dropdowns, TextFields, ListViews, ProgressBars ship unstyled. Customizing Material beyond this brand layer is explicitly against the discipline; Flet's defaults are the contract.

## Colors

- **Paper (`#F7F5F0` light / `#14181D` dark)** is the app background. The window always reads as a desk, never as a feed.
- **Primary Blue (`#1F5FA8` light / `#7AA7E0` dark)** is the single action color. Used on the mode toggle's active segment, the Translate / Start buttons, and links. Never used for status.
- **Live Red (`#D64541`)** means exactly one thing: capture is running. Used on the Start/Stop toggle's active state and the capture status dot. Never used decoratively, never for errors (errors use Material `error` default), never for the model indicator.
- **Success Green (`#1E7E34`)** is for healthy states only: Ollama connected, whisper-server ready. Amber (`#B45309`) is for degraded states: retrying, restarting, high latency.
- **Ink / Muted / Border** carry all text and dividers. Muted text is for timestamps, commentary, and hints — never for primary output.

Avoid: gradients, per-language colors, colored caption bubbles, red anywhere except live capture.

## Typography

Body, label, and controls inherit Flet Material's system ramp. Only two roles are pinned:

- **Display** (System 20 / semibold) — the mode header line ("Text — type, pick, translate"). One line per mode, never in dialogs.
- **Timestamp** (monospace 12) — caption timestamps (`00:42`), latency readouts (`asr 0.4s`), model names in the status bar. Tabular figures keep the captions pane from jittering as rows append.

Rules: translated output always renders at `{typography.body.fontSize}` or larger. Never shrink output to fit chrome; the output scrolls, the chrome doesn't.

## Layout & Spacing

Single fixed window, minimum 960×640, resizable larger. Spacing scale is `{spacing.1}`–`{spacing.8}` (4–32px); default gaps are `{spacing.4}` (16px) between blocks, `{spacing.2}` (8px) inside rows.

- **Top strip:** mode toggle (`SegmentedButton`: Text / Live / File) left, Ollama status dot + model `Dropdown` right. One row, always visible, identical across modes.
- **Text mode:** two-column above 1100px (input left, output cards right), single stacked column below. Input `TextField` (multiline, min 6 lines) → row of target-language `Dropdown` + model `Dropdown` + Translate `FilledButton` → two output cards (formal / informal) + origin-language caption (commentary cut per D1-A 2026-09-13).
- **Live mode:** controls row (Start/Stop `FilledButton` toggle + device `Dropdown` + read-only Auto-detect source indicator + target `Dropdown`) → status row (three dots: capture / whisper / model + latency text) → captions `ListView` filling remaining height, newest at bottom, auto-follow with scroll-back escape.
- **File mode:** picker row (`FilePicker` button + chosen path label) → `ProgressBar` → results `ListView` reusing the caption-row pattern.

Avoid: sidebars, drawers, tabs-inside-tabs, multi-window flows. If it doesn't fit the single window, it doesn't ship in v1.

## Elevation & Depth

Inherited from Flet Material — no custom shadows. Output cards and caption rows separate by 1px `{colors.border}` outlines, not elevation. The only raised element is the active Translate/Start button (Material default). Depth never encodes meaning; position and labels do.

## Shapes

`{rounded.sm}` (4px) for caption rows, text fields, and dropdowns. `{rounded.md}` (8px) for output cards, buttons, and the mode toggle. `{rounded.lg}` (12px) unused in v1 — reserved for future dialogs. `{rounded.full}` (pill) appears only on status dots and the session-state pill (Listening / Idle / Processing file).

## Components

All Flet 0.86 Material widgets ship as-is except the brand-layer overrides below. Visual specs for unlisted widgets (SnackBar, Tooltip, ProgressRing) are inherited from Material untouched.

- **Mode toggle** (`SegmentedButton`, 3 segments) — `{colors.surface}` track, active segment `{colors.primary}` fill with `{colors.primary-foreground}` label, `{rounded.md}`. One tap switches modes; state (model pick, session list) is preserved, never reset.
- **Translate button / Start-Stop toggle** (`FilledButton`) — idle: `{colors.primary}` fill; live-capturing: `{colors.live}` fill with label flipping Start→Stop. The button label is the session state; no separate state banner.
- **Output card** (`Container` + `Text` + copy `IconButton`) — `{colors.surface}` fill, 1px `{colors.border}`, `{rounded.md}`, `{spacing.4}` padding. Three cards in text mode: Formal, Informal, Commentary. Failed/empty card shows its error inline (same card, muted text) — never a blocking dialog.
- **Caption row** (`ListTile`-equivalent in `ListView`) — monospace timestamp left (`{typography.timestamp}`, `{colors.muted}`), translated text right (`{typography.body}`). 1px bottom divider `{colors.border}`. No avatars, no bubbles, no per-speaker color (no diarization in v1).
- **Status dots** (`Container` 10px circle) — capture: `{colors.live}` when recording / muted when idle; whisper: `{colors.success}` ready / `{colors.warning}` restarting; model: `{colors.success}` with model name beside it. Dots are always paired with a text label — color is never the only signal.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Inherit Flet Material defaults for everything not in the brand layer | Restyle Dropdowns, SnackBars, or ProgressBars to "match the brand" |
| Use `{colors.live}` only for capture-active | Use red for errors, model state, or decoration |
| Keep the top strip identical across all three modes | Add per-mode headers, heroes, or onboarding copy |
| Render errors inline in the card/row that failed + `SnackBar` with retry | Block with `AlertDialog` for malformed JSON, missing device, or bad file |
| One window, 960×640 minimum, output scrolls | Open second windows, drawers, or nested tabs |
| Pair every status dot with a text label | Encode state in color alone |
