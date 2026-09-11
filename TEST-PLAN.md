# text-c3po manual Test Plan

Human-run checks that unit tests (`pytest`) and the E1 eval gate cannot
cover: real windows, dialogs, snackbars, device hardware, subprocess
lifecycle, and end-to-end speech. Run top to bottom after any epic lands;
regressions fixed in review are tagged **[R]** with their commit.

Environment: macOS Apple Silicon, `ollama serve` running, `brew install
ffmpeg whisper-cpp portaudio`, `brew install --cask blackhole-2ch`,
Python 3.12 with `uv`. Fast model for all live checks: `lfm2.5:latest`.
Serial only — one LLM call at a time; keep `gemma4:e4b-mlx` unloaded.

## 0. Setup (E4-1)

- **S1 — clean-machine install.** On a fresh Mac: `./setup.sh`.
  Expect: brews install, `models/ggml-small.bin` downloads once,
  `lfm2.5` pulls, unit suite ends green, exit 0. Re-run: every step
  prints "present, skipping".
- **S2 — setup failure modes.** No Homebrew → readable abort naming
  https://brew.sh; `ollama serve` down at pull time → warning naming
  the retry, everything else still completes.

## A. Launch and connectivity (E1 + snackbar fix)

- **A1 — healthy launch.** `ollama serve` up, then `uv run text-c3po`.
  Expect: green Connected dot, picker lists installed models with
  `lfm2.5` preselected, no snackbar.
- **A2 — launch with Ollama down.** Stop `ollama serve`, launch.
  Expect: red Down dot; hover reads "start it with `ollama serve`".
  Start `ollama serve`: dot flips green within ~15 s (background poll),
  **no snackbar appears** **[R]** `3e59d98` (the poll used to re-probe
  and desync, firing bogus disconnect snackbars).
- **A3 — mid-run disconnect.** With the app open, stop `ollama serve`.
  Expect: **exactly one** "Ollama disconnected" snackbar with a working
  Retry action. Restart `ollama serve`: dot returns green, no repeat.
- **A4 — model switch sticks.** Pick another installed model, press
  Translate. Expect: the new model answers (check `ollama ps`).
  **[R]** `0906a98` (Dropdown `on_change` never fired in flet 0.86;
  now `on_select` — before the fix the picker was decorative).

## B. Text translation (E1)

- **B1 — happy path.** Type a sentence, target German, Translate.
  Expect: formal/informal tabs fill plus "Translated · N chars" tally.
- **B2 — stop.** Press Stop mid-stream. Expect: "Stopped.", controls
  re-enable, no late result overwrites the next request.
- **B3 — input guards.** Empty input → "Type or paste something first.";
  overlong paste scrolls the window instead of clipping.

## C. Capture devices (E2-1)

- **C1 — picker lists inputs.** Open Live view. Expect: every
  input-capable device verbatim (mics, headsets, BlackHole 2ch when
  installed); output-only devices (speakers) absent.
- **C2 — default is a mic.** Fresh launch: preselected device is the
  first non-BlackHole input, never BlackHole itself.
- **C3 — selection sticks.** Change the device, switch Text→Live→File
  and back. Expect: selection preserved **[R]** `0906a98`.
- **C4 — no capture hardware path.** (Machine without sounddevice /
  PortAudio is hard to fake — code-reviewed instead: `list_devices`
  yields `[]`, app starts, file mode works.)

## D. whisper-server lifecycle (E2-3)

- **D1 — auto-spawn.** Launch, then `curl -X POST
  http://127.0.0.1:9001/inference`. Expect: HTTP response within ~5 s
  warm (cold model load longer on first run).
- **D2 — no orphans.** Quit the app, then `pgrep -f whisper-server`.
  Expect: empty.
- **D3 — crash recovery.** `kill -9 <whisper pid>` while the app runs,
  then use file mode. Expect: transport error surfaces readably; in a
  live session, gap rows appear and the whisper dot flips to down.
  (No mid-session auto-restart by design — restart happens on next Start.)

## E. File mode end-to-end (E2-4)

- **E1 gate reference sample.** Generate German speech when needed:
  `say -v Anna "Guten Morgen. Wie geht es dir heute?" -o /tmp/t.aiff
  && ffmpeg -i /tmp/t.aiff -ac 1 -ar 16000 /tmp/t.wav`.
- **E1 — happy path.** File view → Pick audio file → choose a German
  `.wav`/`.mp3`/`.m4a`/`.mp4`. Expect: "Transcribing…" then formal
  ("Good morning…") + informal + char tally.
- **E2 — dialog cancel.** Open the picker, press Esc/cancel. Expect:
  idle, button enabled, no status text.
- **E3 — unsupported container.** Pick a `.txt`/`.aiff`. Expect:
  readable "Unsupported container" error, button re-enabled, no
  subprocess launched.
- **E4 — corrupt file.** Truncate an mp3 to 1 KB, pick it. Expect:
  decode error surfaces, mode never wedges (300 s ffmpeg cap).
- **E5 — silence-only file.** 2 s of zeros as wav. Expect: "No speech
  found in that file."
- **E6 — long file.** ~5 min recording. Expect: completes, UI
  responsive afterwards, no runaway memory.
- **E7 — double-pick.** Double-click Pick rapidly. Expect: single
  worker (second open suppressed while busy) **[R]** `0906a98`.

## F. Live session (E3)

- **F1 — mic captions.** Live view → Start, speak German sentences
  with pauses. Expect: red Live dot, timestamped formal captions
  append in order; whisper dot stays "ready".
- **F2 — stop and retain.** Press Stop mid-session. Expect: capture
  halts within ~2 s, dot returns Idle, caption list stays readable.
- **F3 — restart is a new session.** Press Start again. Expect: pane
  clears, seq restarts, old session gone without relaunch.
- **F4 — whisper crash mid-session.** `kill -9 <whisper pid>` while
  live. Expect: subsequent utterances render as labeled gap rows,
  never silent drops.
- **F5 — scroll and jump.** During a long session, scroll up.
  Expect: auto-follow stops, "Jump to latest" appears; pressing it
  returns to the newest row and re-enables follow.
- **F6 — screen reader.** VoiceOver on, one utterance. Expect: the
  new row announced once (translation + timestamp).
- **F7 — BlackHole loopback.** Pick BlackHole 2ch, play a German
  video, Start. Expect: system audio captioned without a mic.
- **F8 — no mic permission.** Revoke mic access (TCC), Start.
  Expect: clean failure, no hang, Stop re-arms.
- **F9 — picker timing.** Change device/target/model mid-session.
  Expect: running session unaffected; changes apply on the next Start.
- **F10 — caption retry.** Kill Ollama mid-session, speak (error row
  appears), restart Ollama, press row Retry. Expect: row flips to the
  translation; persistent failure raises a SnackBar whose Retry works.
- **F11 — start guards.** With no capture device (or no model),
  press Start. Expect: readable refusal in the status line, no spawn,
  buttons re-armed.
- **F12 — double-start.** Double-click Start rapidly (and again
  during the ~2 s whisper-ensure window). Expect: exactly one
  capture thread (`lsof -i` shows one stream); Stop halts everything,
  mic released, no orphaned runner.
- **F13 — stop timing.** Start, speak, press Stop mid-sentence.
  Expect: capture halts within ~2 s; trailing speech may still land
  one final caption; list retained.

## G. Eval gate (E1, repeatable)

- **G1.** `PYTHONPATH=src uv run python -m
  text_c3po.services.eval_harness --models lfm2.5:latest`.
  Expect: exit 0, every model ≥95% JSON-valid, dated section appended
  to the model-quality `research.md`. Slow (25 LLM calls per model:
  5 sentences × 5 languages; use `--languages all` for the 23×5 full).

## H. Packaging (E4-3, manual session)

Prereqs: Xcode + Apple Developer signing identity for distribution;
ad-hoc signature suffices for local runs.

- **P1 — bundle build.** Approve the Flutter SDK 3.44.8 install when
  `flet build` prompts (it duplicates `~/src/flutter` — that's
  expected), then: `uv run flet build macos --project text-c3po
  --product text-c3po --org <you> --bundle-id <you>.textc3po`.
  Expect: `build/macos/` bundle, exit 0.
- **P2 — mic permission.** Add `NSMicrophoneUsageDescription` to the
  macOS Info.plist, rebuild, launch, press Start. Expect: the macOS
  mic prompt appears once; denying yields the clean F8 failure.
- **P3 — ad-hoc run.** Launch the `.app` with no terminal present.
  Expect: window opens, Connected dot green, file mode translates.
- **P4 — no strays.** Quit via Cmd-Q and via Dock. Expect: `pgrep -f
  whisper-server` empty both ways.
- **P5 — first launch on another Mac.** Copy the bundle over.
  Expect: Gatekeeper path documented (ad-hoc vs signed).

## I. Browser testing (agents / headless review)

- **I1.** `FLET_FORCE_WEB_SERVER=true FLET_SERVER_PORT=8555
  PYTHONPATH=src uv run python -m text_c3po.app`, open
  `http://localhost:8555` in BrowserOS neo.
  Expect: full UI interactive via snapshot/act. Kill the auto-launched
  Flet desktop client if it gets in the way (`pkill flet-desktop`).

## Coverage map (what automation owns)

- `pytest` (131 unit tests, all headless/deterministic — recount with
  `pytest --collect-only -q`): VAD chunking rules, device/VAD/decode/
  transcribe pure logic, manager lifecycle with fake processes,
  session ordering/gaps/retry, captions sync, pipeline short-circuits,
  UI construction.
- `pytest -m integration` (manual, serial, loopback-only): live
  Ollama/whisper/ffmpeg checks — see `tests/test_integration.py`.
- This note: everything above a unit cannot reach (windows,
  dialogs, snackbars, hardware, subprocess timing, real speech).
