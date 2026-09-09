---
name: text-c3po
status: final
updated: 2026-09-08
sources:
  - _bmad-output/planning-artifacts/prds/prd-text-c3po-2026-09-08/prd.md
  - _bmad-output/planning-artifacts/prds/prd-text-c3po-2026-09-08/addendum.md
  - _bmad-output/planning-artifacts/briefs/brief-text-c3po-2026-09-08/brief.md
  - blueprint.md
---

# text-c3po — Experience Spine

> Single Flet 0.86 desktop window, three modes (text / live / file), local-only. Paired with `DESIGN.md` (visual identity). Spine wins on conflict with any mock or wireframe — none produced in this fast-path run.

## Foundation

Single-surface desktop app: one native Flet window (minimum 960×640), no webserver, no browser, no accounts. UI system is **Flet 0.86 Material** — `DESIGN.md` is the visual identity reference and names the brand-layer delta (paper background, primary blue, live red, display + timestamp type roles); this spine is the behavior. Single tenant, single user (vshanbha, solo builder), memory-only sessions, zero outbound after first-run model download (loopback to Ollama `:11434` and whisper-server `:9001` only). Backend is model-agnostic across the 23-language constant; quality variance is surfaced by the eval harness, never gated in the UI.

## Information Architecture

| Surface | Reached from | Purpose |
|---|---|---|
| Text mode | Mode toggle → Text (default at launch) | Type/paste input → target language + model → structured formal / informal / commentary + origin language |
| Live mode | Mode toggle → Live | Pick device + source/target → Start/Stop session → timestamped translated captions accumulate |
| File mode | Mode toggle → File | Pick audio/video file → same ASR→translate pipeline → caption results with progress |
| Top strip | Always visible | Mode toggle + Ollama status + model picker; identical on all three surfaces |

Mode switching never kills the process, never clears the active session list, and never resets the model pick (PRD FR-1, FR-12). All three surfaces reachable within 2 taps from launch. No deeper navigation exists in v1 — no settings screen (setup is `setup.sh`), no history screen (memory-only), no dialogs except the OS file picker.

## Voice and Tone

Microcopy. Brand voice and aesthetic posture live in `DESIGN.md` (Brand & Style).

| Do | Don't |
|---|---|
| "Pick a model — lfm2.5 is the default." | "Select your AI engine! ✨" |
| "Ollama isn't running. Start `ollama serve`, then Retry." | "Connection failed (ECONNREFUSED 11434)." |
| "Couldn't parse that one. Retry." | "JSON validation error: expected formal:string." |
| "Listening — captions appear below." | "Session initialized successfully ✓" |
| "No capture device found. Plug in a mic or pick a file instead." | "No audio input devices enumerated." |

Error strings name the fix and the retry action, never the exception. Commentary output keeps the model's register notes verbatim — the app doesn't bowdlerize or re-explain them.

## Component Patterns

Behavioral. Visual specs live in `DESIGN.md` (Components) or in Flet Material defaults when inherited.

| Component | Use | Behavioral rules |
|---|---|---|
| Mode toggle | Top strip, all surfaces | `SegmentedButton` Text / Live / File. Switching preserves input text, model pick, and live session list. Text is the launch default. |
| Input area | Text mode | Multiline `TextField`, min 6 lines. Empty submit is rejected client-side with hint ("Type or paste something first.") — no LLM call issued (FR-3). Input text survives mode switches. |
| Language pickers | All modes | `Dropdown`s bound to the 23 `{code, name}` constant verbatim (FR-5). Target required everywhere; source picker in live/file preselects auto-detect where the pipeline supports it, else English [ASSUMPTION — see Open Questions]. Any model×language combo is submittable; quality is measured, not gated. |
| Model picker | Top strip | `Dropdown` listing exactly what `/api/tags` returns at launch plus a Refresh action. Default preselects lfm2.5 when present, else first available (FR-4). Changing mid-session applies to the next call, never retroactively. |
| Translate button | Text mode | `FilledButton` "Translate". Disabled while a call is in flight; re-enabled on result or retryable error. Malformed model JSON never reaches the UI raw — the card shows "Couldn't parse that one. Retry." with the raw payload logged, not displayed. |
| Output cards | Text mode | Three cards (Formal / Informal / Commentary) + origin-language caption. Each card has its own copy button. Cards render independently — a good formal shows even if commentary failed. |
| Start/Stop toggle | Live mode | `FilledButton` whose label IS the state: "Start" (idle, `{colors.primary}`) → "Stop" (capturing, `{colors.live}`). Stop halts capture within 2s; restart begins a new session list without relaunch (FR-11). First Live start in the packaged app triggers the macOS mic prompt with the `NSMicrophoneUsageDescription` string. |
| Device picker | Live mode | `Dropdown` listing available sounddevice devices queried each launch — no hard-coded names (FR-6). BlackHole shown only when present; its absence is never an error. File mode needs no device at all. |
| Captions pane | Live mode | `ListView`, utterance-flush granularity only (no token streaming, FR-10). Rows append in utterance-completion order with `{typography.timestamp}` timestamps. Auto-follows newest; any manual scroll-back pauses follow until the user returns to bottom. Session list survives mode switches; cleared only by new Start or app close (FR-12). |
| Status indicators | Live mode + top strip | Three dot+label pairs: capture-active, whisper latency, active model (FR-11, FR-2). Values reflect live subprocess/model state, not cached startup values. Ollama down at launch shows not-running guidance in the top strip within 5s with a Retry action; recovery flips to connected without restart. |
| File picker + progress | File mode | OS `FilePicker` → path label → `ProgressBar` (indeterminate for ASR, determinate where chunk counts exist) → results `ListView` reusing the caption-row pattern (FR-9). Unsupported container errors before any ASR call ("That file type isn't supported yet — try mp3, wav, m4a, or mp4." [ASSUMPTION — container set to confirm]). Works with BlackHole absent and no device selected. |

## State Patterns

| State | Surface | Treatment |
|---|---|---|
| Cold launch, Ollama down | Top strip | Warning dot + "Ollama isn't running. Start `ollama serve`, then Retry." Retry action re-probes; no restart needed. |
| Cold launch, whisper starting | Live mode | Status row: whisper dot amber, "Starting speech engine…" Ready (~2s ggml-small) flips dot green. Translate/file calls are not blocked by whisper state except live/file runs. |
| Empty input | Text mode | Inline hint under the field; Translate issues no call. |
| Translating | Text mode | Button disabled + `ProgressRing` inline in button; cards show `Skeleton`-style shimmer rows (max 3). Prior results stay visible until replaced. |
| Parse failure | Text mode | Failed card shows "Couldn't parse that one. Retry." Retry re-issues the same prompt; raw JSON goes to logs, never the UI. |
| No devices | Live mode | Device dropdown shows "No capture device found. Plug in a mic or pick a file instead." Start disabled; File mode unaffected. |
| Live capturing | Live mode | Button red "Stop", capture dot `{colors.live}`, rows streaming. Latency text per utterance ("asr 0.4s · llm 1.1s") in muted mono. |
| Session ended | Live mode | Button flips to "Start", pill shows "Idle — {N} captions kept". List stays scrollable. |
| Empty session | Live mode | Pane shows "Press Start and speak — captions appear here." No fake rows. |
| File translating | File mode | `ProgressBar` + "Working through {filename}…" Cancel action halts the pipeline and keeps partial rows. |
| Unsupported file | File mode | Readable error before ASR: "That file type isn't supported yet — try mp3, wav, m4a, or mp4." No partial session created. |

## Interaction Primitives

**Mouse-first desktop, keyboard as accelerator.** No vim bindings, no command palette — this is a three-surface utility, not an editor.

- `Enter` (`Ctrl+Enter` in the multiline field) submits text-mode translation; `Esc` cancels an in-flight call or stops capture.
- `Tab` order matches reading order on every surface: mode toggle → inputs → pickers → primary button → output.
- Copy buttons per card/row (`Ctrl+C` on focused row copies its text).
- Auto-follow in captions/file lists with scroll-back escape; "Jump to latest" appears when unfollowed.
- **Banned everywhere:** token-streaming partial rendering, modal `AlertDialog` for recoverable errors, hover-only affordances, any flow requiring a second window or a browser.

## Accessibility Floor

Behavioral. Visual contrast lives in `DESIGN.md` (brand overrides target WCAG AA against both paper and dark surfaces).

- WCAG 2.2 AA on the desktop surface; status dots always paired with text labels (color never the sole signal).
- Screen reader announces surface on mode switch ("Text mode", "Live mode, idle", "File mode") and announces each new caption row via live region (utterance granularity, not token).
- Full keyboard operability: every control reachable and activatable by keyboard; `Esc` always stops the topmost activity (call → capture → file run).
- Focus visible at all times (Material focus ring inherited); focus returns to the primary button after dialog/file-picker dismissal.
- Timestamps and latency in tabular monospace so assistive-tech buffers and sighted scanning stay stable as rows append.

## Local-First & Trust

Product-specific. The offline promise is a UX contract, not just an NFR.

- After first-run download the app makes zero outbound connections; the UI never shows accounts, keys, sign-ins, or usage meters. If a model pull is needed, it happens via Ollama locally with explicit user action — never silently.
- The top strip model label always names the exact model serving the current surface (e.g., "lfm2.5"). No "auto" or "best" abstraction — the eval harness earns trust, the picker states facts.
- Commentary output is labeled as model opinion ("Model notes:"), visually subordinate to formal/informal results.
- No persistence across restarts in v1 (memory-only). The UI states this once per session list ("Kept until you close the app") rather than implying history.

## Responsive & Platform

Desktop-only v1 (macOS packaged bundle; Linux/Windows guides welcome, untested). Minimum window 960×640; content reflows, chrome doesn't.

| Width | Behavior |
|---|---|
| ≥ 1100px | Text mode two-column (input left, output cards right). |
| < 1100px | Text mode stacks: input → pickers → button → cards. Live/file surfaces unchanged (controls wrap to two rows). |
| Any | Captions/results `ListView` takes all leftover height; window grows vertically into list space, never into wider chrome. |

macOS specifics: packaged bundle carries `NSMicrophoneUsageDescription`; first Live start prompts with the explanatory string. No menu-bar extra, no dock badge counts, no notifications in v1 — the window is the whole product.

## Key Flows

### Flow 1 — Translate before sending (vshanbha, Tuesday morning, UJ-1)

1. vshanbha opens the app; Text mode is up, top strip shows Ollama connected + lfm2.5 preselected.
2. He pastes an English paragraph, picks German as target, hits Translate (`Ctrl+Enter`).
3. Three cards render: formal (Sie), informal, and commentary noting the register choice, plus an "origin: English" caption.
4. **Climax:** vshanbha copies the formal card with one tap and pastes it into his message — the structured output meant he never had to guess which register the model used; the app told him, side by side.
5. He switches to Live mode and back; his input and results are still there.

Failure: model returns malformed JSON → the commentary card shows "Couldn't parse that one. Retry." Formal/informal still display. Retry re-issues without retyping.

### Flow 2 — Follow a live talk (vshanbha, afternoon tech talk over BlackHole, UJ-2)

1. vshanbha flips to Live mode, picks BlackHole (present), source auto-detect, target English, and presses Start — the button turns red and reads Stop.
2. Timestamped translated utterances append in order; status row shows capture live, whisper 0.4s, model lfm2.5.
3. He scrolls back to re-read an earlier caption; auto-follow pauses. A "Jump to latest" chip appears.
4. **Climax:** He taps "Jump to latest" mid-talk and lands exactly on the current utterance as the next caption streams in — he lost nothing by looking back; the session held its place and caught him up in one tap.
5. He presses Stop; the full ordered list stays readable. Switching to Text and back doesn't clear it.

Failure: whisper subprocess crashes mid-talk → dot turns amber, "Speech engine restarted — catching up…" Captions resume; missed utterances are not backfilled and the gap is labeled, not hidden.

### Flow 3 — Translate a recorded clip (vshanbha, evening, no BlackHole, UJ-3)

1. vshanbha opens File mode on a machine with no BlackHole and no mic plugged in — the surface doesn't care.
2. He picks a `.m4a` lecture clip; the path label confirms it and progress starts.
3. Caption rows accumulate with timestamps, same row pattern as live.
4. **Climax:** The last row lands with the final timestamp and progress completes — the same pipeline that served the live talk just served a file, with no device to configure and no second UI to learn.
5. He copies the rows he needs; closing the app discards the session (memory-only, as labeled).

Failure: he picks an unsupported container → "That file type isn't supported yet — try mp3, wav, m4a, or mp4." before any ASR call. No partial session, no spinner limbo.

## Open Questions

1. `flet==0.86.5` pin at E1 kickoff, or re-pin to newer stable with changelog note? (PRD Q1 — assumed 0.86.5 for this spine.)
2. File-mode container floor: is mp3 / wav / m4a / mp4 the E2 must-pass set? (PRD Q2 — assumed yes in microcopy.)
3. Source-language UX in live mode: auto-detect default vs explicit picker default? (PRD Q3 — spine assumes picker preselected to auto-detect where supported, else English.)
