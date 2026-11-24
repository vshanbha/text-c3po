---
date: 2026-11-23
type: stabilization-run-sheet
owner: vshanbha
status: active — Phase 0 complete, Phase 1 awaiting owner battery
decisions:
  - "2026-11-23: §J is the v2-shippable gate, not the E4 epic gate (E4 close-out)"
  - "2026-11-23: E2 stays open until story 2-6 resolves; E6 proceeds after stabilization"
  - "D9: §H packaging stays E5-owned, excluded from this stabilization pass"
  - "2026-11-23: default model ornith-1.5:9b → lfm3 (VRAM); side-effect sweep closed via sub-agent create→fix→review→test loop"
  - "2026-11-23 owner: NO default revert — lfm3 stays; the long-input stop is OUR bug (verbose format instructions × reasoning-off); fix ticket dispatched via sub-agent loop"
gates_after: "E6 (system-wide translation overlay) planning may start once Phase 3 freezes"
---

# Stabilization Run-Sheet — text-c3po v2

Purpose: prove the product works as built before extending it. The defect
backlog is empty (verified 2026-11-23: no open defects in specs/retros/
memlogs; GitHub issues #2/#3 are E5 features, not bugs); the stability gap
is **unverified manual surface**, not known broken behavior. This pass runs
the human battery (TEST-PLAN §J), triages whatever it finds, and freezes
the verified state.

Suites as of 2026-11-23: **207 unit green, 6 integration green (live,
46 s), Pages row verified.**

## Phase 0 — Baseline (COMPLETE 2026-11-23)

| Item | Status | Evidence |
|---|---|---|
| Unit suite | ✅ | 207 passed, 6 deselected, 2.9 s |
| Integration suite (live Ollama/whisper) | ✅ | 6 passed, 45.98 s |
| GitHub Pages row (§J) | ✅ | API `build_type: workflow, status: built` + HTTP 200 MkDocs Material build; recorded in TEST-PLAN |
| E2/E4 retro addenda | ✅ | Post-retro work + owner decisions recorded |
| Default model → lfm3 (owner decision) | ✅ | `DEFAULT_MODEL_PREFIX` + unit test; 5x5 gate 25/25 PASS (`research.md`) |
| lfm3 side-effect sweep | ✅ | create→fix→review→test loop, 7 files: setup.sh dual-model pull (lfm3 default + ornith integration policy), TEST-PLAN ×5, README ×3, blueprint ×2, UX spine, AGENTS gate example, pyproject comment. Review verdict APPROVE (1 line-wrap nit fixed); final gates: 207 unit green, `bash -n` clean, zero stale default claims |
| lfm3 long-input fix (create→fix→review→test) | ✅ | Two prompt triggers removed from `translation.py` (compact 3-field instructions + "Respond strictly" template line — second trigger found by the fix agent; instruction-only ticket would have shipped broken). Review APPROVE with independent 2×2 reproduction. Battery: gate 25/25 lfm3+ornith, 23×5 115/115, capability 115/115, echo 4/4, probe_collapse **5/5 @851–873 chars** via app path (was 89–101) |
| Round-2 framing fix + hybrid thinking ladder ([R] `6420131`) | ✅ | Raw-first proved model innocent, pinned framing-CLASS trigger #3 → single-instruction prompt (review APPROVE). Residual ~10–20% model-side partial → hybrid ladder: >300-char inputs rung-2 think-off retry, rung-3 think-on @360s with thinking streamed to the UI (on_thinking, 500-char tail, AD-4). Review APPROVE + live rung-3 proof (8,662 deltas/180.5s). Battery 2026-11-24: gate 25/25 ×2, 23×5 115/115, probes green, **German long 5/5 incl. live rung1→2→3 (529→618→874)**, 218 unit |
| Ornith out of test path (`82d01e3`) | ✅ | Integration MODEL→lfm3 (prefix-tolerant guard), setup.sh single-pull, probe defaults, policy wording. Live integration 6/6 on lfm3; review APPROVE; quality comparator role preserved |

## Phase 1 — Owner battery (ordered)

Run top to bottom. Record evidence per TEST-PLAN convention: append
`Verified <date> by owner manual test (evidence)` to passing rows; failing
rows **stay open** until fixed and re-verified. est = elapsed active time.

### Row 0 — Full manual walk: the product as a user (~30–45 min) — FIRST

The §J battery is failure-path; this is the happy path a real user walks,
in order, with no tricks — the run the owner did on 2026-11-23 that found
Finding 1:

1. Launch → green Connected, model preselected (§A1).
2. Text mode: translate 2–3 real sentences, switch target languages,
   switch model once (§B1, §A4) — judge the *feel*: latency, spinner,
   in-place refresh (§B5).
3. Live mode: Start, speak, watch captions flow, Stop, Start again,
   switch Text↔Live↔File and back — state preservation (§C3).
4. File mode: pick a real recording, get translations back (§E1).
5. Quit clean — no orphans (`pgrep -f whisper-server` empty).
6. **Reproduce Finding 1 here:** while a Live session runs, start
   another mic-using call (Zoom/Teams/FaceTime) — see F16.

Record nothing unless something fails; findings go straight to the
findings log below. This row is also where "does it feel stable as a
daily driver" gets answered — the thing no edge-case row can answer.

### Row 1 — The two pending E4/E2 rows (15 min)

- **F14 — device unplug** (`TEST-PLAN.md` §F): Start Live on any device →
  unplug USB mic, or `sudo killall coreaudiod`. Expect: graceful session
  end, buttons reset to Idle, captions retained, no stuck red "Live".
  *Unblocks story 2-5.*
- **§J Log file (story 4-9)**: run any Live or File session, then verify
  `~/Library/Logs/text-c3po/text-c3po.log` exists (override
  `TEXT_C3PO_LOG` works); a Start refusal (C5/F11), whisper kill (D3/F4),
  or no-audio trip (F15) leaves a reason-naming line;
  `grep -i -E "guten morgen|good morning" <log>` is **empty** (privacy
  contract; payload content only with `TEXT_C3PO_DEBUG_PAYLOADS=1`).
  *Unblocks story 4-9 → E4 closure.*

### Row 2 — §F real-mic live session (1–2 h) — the biggest blind spot

The live path has **never run with a real microphone** (§J note). Minimum
set from the §J §F row, minus already-verified F7/F15:

| Row | Check | Pass means |
|---|---|---|
| F1 | Mic captions | Red Live dot, timestamped captions append in order, whisper dot ready |
| F2 + F13 | Stop mid-session / mid-sentence | Capture halts ≤2 s, list retained, no orphans |
| F5 | Scroll + Jump-to-latest under load | Follow stops on genuine scroll only; Jump re-enables; 1000+ rows usable. **Failure reopens E3-5** |
| F8 | Revoke mic (TCC) → Start | Clean failure, no hang, Stop re-arms |
| F9 | Change pickers mid-session | Running session unaffected; changes apply next Start |
| F10 | Kill Ollama mid-session → Retry | Error row → Retry flips to translation; SnackBar retry works |
| F11 + C5 | Start with no device/model | Readable refusal in status line, no spawn, buttons re-armed |
| F12 | Double-click Start | Exactly one capture thread (`lsof -i`), Stop cleans all |

Nice-to-have (same session, not gating): F3 restart-clears, F4 whisper
`kill -9` → gap rows, F6 VoiceOver announce-once (needs screen-reader
machine — may defer with a note).

### Row 3 — D1–D3 whisper subprocess timing (~20 min)

- **D1:** cold-model readiness vs the 30 s `READY_TIMEOUT_S` — first Start
  after boot must either become ready or fail fast (dead-child fast-fail,
  no full-budget burn).
- **D2:** `kill -9` whisper mid-session → subsequent utterances render as
  **labeled gap rows**, never silent drops.
- **D3:** quit app (Cmd-Q **and** Dock quit) → `pgrep -f whisper-server`
  empty — no orphans.

### Row 4 — E6 long-file soak (~10 min)

Pick a ~5-minute audio/video file. Expect: completes, UI responsive
afterward, no runaway memory (watch Activity Monitor / `ps` RSS). This is
the NFR-4 soak companion.

### Row 5 — S1/S2 fresh-machine `setup.sh` (~15 min + machine setup)

Full §0 run on a **clean Mac** (or clean macOS account — say so in the
evidence): installs finish, `models/ggml-small.bin` downloads once,
`lfm3` pulls, unit suite green, ≤15 min, exit 0; second run
prints "present, skipping" everywhere. Only idempotency is proven today —
this closes the E4 retro's "evidence inventory (missing)" gap. Also folds
in: BlackHole-absent enumeration (E2 open question 2) if the clean machine
lacks BlackHole.

### Row 6 — S3-D5 deployment-scope decision (5 min)

Record the decision in this file (or a one-line sprint-change note):
**ad-hoc-only distribution accepted** (no sign/notarize — consistent with
D5) → tick the §J row as a *decision*, not a test. If distribution IS
wanted later, that reopens as E5 scope.

### Explicitly out of scope for this pass

- **§H packaging (P1–P5):** E5-owned per D9 — runs only at the
  general-release decision.
- **F6 VoiceOver:** defer with a note if no screen-reader machine at hand;
  it is the one accessibility row and should not silently vanish.
- **Story 2-6 (dual capture):** E2-open item per 2026-11-23 decision —
  not stabilization, not on the E6 critical path.

## Phase 2 — Triage rules (agent-owned, fires on first finding)

Every finding lands in one of three buckets — no fourth option, no
"fix later" without a record:

1. **Defect** → fix story in the owning epic (historical pattern:
   audit → story → fresh-context review → TEST-PLAN row **re-verified**
   after the fix). Small fixes may land as one review pass; anything
   touching session/capture/queue concurrency gets the full fresh-context
   review treatment (see E3-5..3-7 precedent).
2. **Accepted behavior** → record explicitly: TEST-PLAN row gets an
   `Accepted <date>: <why this is not a bug>` note, or a retro finding
   disposition. Silent non-fixes are forbidden.
3. **Major finding** (changes scope/contracts) → `bmad-correct-course`
   sprint-change proposal before any code moves.

A **clean battery** (zero defects) is a valid outcome — record it as such
in this file and proceed to Phase 3.

## Phase 3 — Freeze (exit criteria)

- [ ] All §J rows ticked except §H packaging (E5-owned, D9) and any
      explicitly deferred row (e.g. F6) **named here with a reason**
- [ ] Every §F row carries a `Verified <date>` or `Accepted` record
- [ ] TEST-PLAN coverage counts recounted (`pytest --collect-only -q`)
- [ ] Phase 2 triage section below filled in (findings or "clean battery")
- [ ] sprint-status refreshed (`last_updated`, 2-5 → done, 4-9 → done,
      epic-4 → done, epic-4-retrospective → done)
- [ ] E2 remains `in-progress` on 2-6 alone (2026-11-23 decision) — noted,
      not blocking
- [ ] This file's `status:` flipped to `complete`

**Then: E6 planning starts** (spines exist at
`_bmad-output/planning-artifacts/ux-20261101-001/`; SPEC + epics/stories
still to be created).

## Appendix A — Full manual test-run script (added 2026-11-23)

The executable happy-path walk (Phase 1 Row 0) with evidence-capture
instructions. Run top to bottom; log every miss in the findings log.

### Pre-flight (2 min)

1. `ollama serve` up; `lfm3` pulled (`ollama list`).
2. Terminal A: `tail -f ~/Library/Logs/text-c3po/text-c3po.log`
   (or `$TEXT_C3PO_LOG` if overridden).
3. Terminal B: `pgrep -fl "whisper-server|ffmpeg"` — note the baseline
   (both should be empty before launch).
4. Note the build: `git log -1 --format="%h %ci %s"`.
5. Have ready: a mic, one mic-using call app (Zoom/Teams/FaceTime),
   a ~5-minute recording, and the sample-file command (Part 2).

### Part 1 — Launch + Text mode (~10 min)

| # | Do | Expect |
|---|---|---|
| 1 | `uv run text-c3po` | Green Connected dot, `lfm3` preselected, no snackbar (§A1) |
| 2 | Type a sentence, target German, Translate | Formal + Informal fill, "Translated · N chars" (§B1) |
| 3 | Translate again with output still showing | Spinner → live preview → final, **no window freeze** (§B5 — if UI freezes until refocus, loop-marshaling regressed) |
| 4 | Switch model in picker, Translate | New model answers — check `ollama ps` (§A4) |
| 5 | Press Stop mid-stream | "Stopped.", controls re-enable (§B2) |
| 6 | Translate with empty input | "Type or paste something first." (§B3) |
| 7 | Stop `ollama serve` while app open | **Exactly one** disconnect snackbar with working Retry; restart serve → dot green, no repeat (§A3) |

### Part 2 — File mode (~8 min)

Generate the sample first:
```sh
say -v Anna "Guten Morgen. Wie geht es dir heute?" -o /tmp/t.aiff && ffmpeg -y -i /tmp/t.aiff -ac 1 -ar 16000 /tmp/t.wav
```

| # | Do | Expect |
|---|---|---|
| 8 | File view → pick `/tmp/t.wav` | "Transcribing…" → "Good morning…" formal + informal (§E1) |
| 9 | Open picker, press Esc | Idle, button enabled, no status text (§E2) |
| 10 | Pick a `.txt` or `.aiff` | Readable "Unsupported container", no subprocess (§E3) |
| 11 | *(optional)* pick your ~5-min recording | Completes, UI responsive after, no memory creep (§E6/soak) |

### Part 3 — Live mode + THE hang repro (~15 min)

| # | Do | Expect |
|---|---|---|
| 12 | Live view: check device picker | Inputs listed verbatim, speakers absent, a mic preselected (§C1/C2) |
| 13 | Start, speak German with pauses | Red Live dot, timestamped captions append in order (§F1) |
| 14 | Stop mid-sentence; list retained; Start again | Halts ≤2 s; restart = fresh session, pane clears (§F2/F3) |
| 15 | Double-click Start rapidly | Exactly one capture thread; Stop cleans everything (§F12) |
| 16 | **F16 — the hang:** Live session running + captions flowing → open your call app, join a call, speak normally 30–60 s | **No system hang.** Worst acceptable: text-c3po captions degrade to gaps/no-audio trip while the call keeps working |
| 17 | **F16 reverse order:** call running first → then Start text-c3po Live | Same expectation |

### Part 4 — Lifecycle + cleanliness (~5 min)

| # | Do | Expect |
|---|---|---|
| 18 | `curl -X POST http://127.0.0.1:9001/inference` | HTTP response ≤5 s warm (§D1) |
| 19 | Quit the app (Cmd-Q), then `pgrep -fl "whisper-server\|ffmpeg"` | **Empty** — no orphans (§D2) |
| 20 | Check Terminal A log tail | Session/translate lines present; `grep -i -E "guten morgen\|good morning" ~/Library/Logs/text-c3po/text-c3po.log` → **empty** (privacy contract, §J log row) |

### Bug-detail kit — capture for EVERY miss

1. **Step #** and exact actions (what you clicked/typed)
2. **Expected vs actual**, verbatim
3. **Screenshot** (UI issues) / **log tail**: last ~30 lines from Terminal A
4. **Reproduce count** — try it 2–3×: `fails n/3`
5. **Scope** — app only, or whole machine?

### F16-specific sheet (fill in when the hang happens)

```
Other call app: ______________  (Zoom / Teams / FaceTime / browser / other)
text-c3po state: ______________  (Live capturing / Live view idle / Text / File)
Hang scope: ______________  (whole machine / app only / fans spin + slow)
Reproducible: ____ / 3 attempts  (both orders tried: yes / no)
Recovery: ______________  (force-quit which app / wait / reboot)
After recovery, check: top -l1 | grep -E "ffmpeg|whisper|ollama" → CPU%: ______________
Log tail around the event (Terminal A): ______________________________
```

### Decisions I need back (per finding)

For each logged finding: **bucket** — defect (fix story) / accepted
behavior (record why) / major (correct-course). Plus, specifically for
F16: fix now as a stabilization story, or correct-course first if triage
shows the D7-A capture design needs rework.

## Phase 2 findings log

| Date | Row | Finding | Bucket | Disposition |
|---|---|---|---|---|
| 2026-11-23 | Side-effect audit (lfm3 switch) | 7 surfaces still claimed ornith as default — **setup.sh functional gap**: clean machines silently fell back to ornith; TEST-PLAN §A1 would report a false failure; stale README/blueprint/UX-spine/AGENTS/pyproject gate claims | Defect — cause and fix clear | Fixed via create→fix→review→test sub-agent loop; review APPROVE (1 nit fixed); setup.sh now pulls lfm3 (default) + ornith (integration policy); 207 unit + `bash -n` green; every remaining "ornith" hit classified intentional/historical. **Closed.** |
| 2026-11-23 | F16 (new row) | **Machine hangs when text-c3po runs in parallel with another call using audio/mic.** Found during owner's full manual walk — no prior row exercised parallel audio use (coverage gap now closed by F16). | Defect — triage open | Owner hypothesis: ornith VRAM pressure — default now lfm3 (1.7 GB vs 6.6 GB); **F16 re-test pending on lfm3** (run-sheet Appendix A, Parts 3). If hang persists, hypothesis rejected; D7-A ffmpeg capture path stays prime suspect. |
| 2026-11-23 | lfm3 removal battery (owner conditional) | **FAIL on long-input eval**: 23×5 matrix 115/115 ✅, capability 115/115 ✅, echo probe 4/4 RENDERED ✅ — but multi-paragraph input (776 chars) returns **paragraph 1 only** (89 ES / 79 DE chars), `done_reason='stop'`, 7/7 attempts deterministic. Owner's F4 pain (cut-off translation) would return as a hard default-model limitation. Plus: probe_collapse "full" label is signature-specific and hid this (printed 5× "full" at ~90 chars) | Defect — our wiring (see root-cause row) | **CLOSED 2026-11-23**: fix landed (compact format instructions + "Respond strictly" line removed), review APPROVE, battery green — probe_collapse 5/5 at **851–873 chars** (was 89–101), gate 25/25 both models, 23×5 115/115, echo 4/4. B6 re-verified with evidence. |
| 2026-11-23 | Root cause (owner challenge: 256k context) | **Cause pinned — not capacity, not prompt-wording, not thinking**: lfm3 full long translation works with plain/minimal/compact prompts at think-off (824–866 chars @ 4.5–13.5s); fails ONLY with langchain's verbose 3-field `format_instructions` at think-off. Think-on masks it (18.8s short / 94s long > 60s timeout — not app-viable). Ornith under current code: long 845–856 full @ 41s warm. Context confirmed 262144 | Root-cause evidence complete; **fix in flight** | **CLOSED 2026-11-23** — fix + evidence recorded in E1 memlog; B6 re-verified **for Spanish only** (German re-opened by the quality eval — see next row). The fix agent's second-trigger finding ("Respond strictly" line) was adjudicated by independent review with its own reproduction matrix. Remaining related nit: probe_collapse signature-specific label (tooling, candidate mini-ticket). |
| 2026-11-23 | Quality eval layer 4 (blinded judge, 12 pairs DE+ES) | **ornith 9 – lfm3 0 – 3 ties.** lfm3 systematic: question→statement w/ invented content (DE+ES), "Gracias mucho" unidiomatic, informal content drop, worse Sie/du trap error, junk vocab ES long ("alomoches"), **German long first-sentence collapse (P6)** | Meaning-level evidence — ornith wins | **CLOSED 2026-11-24** — the German-long bug it exposed is fixed ([R] `6420131`: framing-class prompt fix + hybrid thinking ladder; battery 5/5 incl. live rung1→2→3). Ornith stays installed as quality comparator (9-0-3 evidence), out of the test path. Probe: `tests/benchmark/probe_quality_pairs.py`; artifacts in `research/quality-eval-2026-11-23/`. Caveat stands: n=12, advisory judges, owner spot-check invited |
| 2026-11-24 | Owner manual test: informal renders in ENGLISH | **Informal field in wrong language** on EN→DE (stochastic: owner long-input hit + 1/3 fresh app-path shorts; formal always correct). Round-2 instruction never states informal's language; gate validates `formal` only — informal language has **zero automated coverage**. First amendment candidate **rejected raw-first**: ", both written entirely in German" re-triggered the German-long first-sentence bug (79–85 ×3) | Defect — our prompt + battery blind spot | **Open, awaiting loop dispatch.** Fix requires per-candidate full matrix (DE/ES long ×5 completeness + shorts ×12 informal-language), raw-first. Trap landscape recorded in E1 memlog 2026-11-24 |
