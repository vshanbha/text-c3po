---
date: 2026-09-09
verdict: accepted-with-open-items
criteria: declared
headless: true
---

# E1 Retrospective — Flet Shell + Local Text Translation Core

## Epic summary

- **Epic:** E1 (Flet shell plus local translation core), stories-mode spec folder `_bmad-output/specs/spec-e1-shell-core/` (`SPEC.md` + `stories.yaml` ids 1–7 in list order).
- **Stories completed:** 7/7 — every story artifact carries `status: done` frontmatter (1-scaffold, 2-top-strip, 3-languages, 4-ollama-client, 5-model-picker, 6-translation-service, 7-eval-harness). `pending_stories` is empty.
- **Diff range:** no per-story commits exist by design (never-commit repo policy; spec `.memlog.md` lines 12, 15, 18). All seven artifacts record the identical `baseline_revision: e70869cfd7da94f8f70a146ae0cc0a3dc32e8129`, so the evidence range is worktree-vs-`e70869c`, shared by all stories. `git_evidence.py` was not run: with zero story commits there is no commit attribution to derive, and inventing a range would be guessing.
- **Evidence inventory (available):** `SPEC.md` with declared Capabilities CAP-1–CAP-6 plus Success signal; `stories.yaml`; seven story artifacts each with Review Triage Log, Auto Run Result, and Verification sections; spec `.memlog.md` (28 entries); E1 gate section in `_bmad-output/planning-artifacts/research/technical-model-quality-2026-09-08/research.md` (lines 33–41: lfm2.5 25/25 PASS); product tree `text-c3po/` (~1300 lines across app, languages, runtimes, services, ui); `requirements.txt` (`flet==0.86.5`, `langchain-ollama==1.1.0`); untracked `pyproject.toml` pytest/integration policy.
- **Evidence inventory (missing / narrowed):** session/conversation logs for the story runs are absent, so process-lesson analysis reads only story-file evidence plus invocation context — recorded as narrowed, not as checked-and-clean. `sprint-status.yaml` exists but is stale (every E1 key still `backlog`, predating the stories-mode run) and is not authoritative for this epic. There is no committed test suite (repo has no runner by design; verification is per-story headless matrices plus manual-only integration).

## Findings

### Aggregate views

- **F1 — Architecture delta: checked and clean.** The layered monolith survived all seven stories: `ui/` never imports `runtimes` (retro re-check `grep -rn "runtimes" text-c3po/ui/` clean, corroborating story 6/7 verification greps); the allowed `services → runtimes` direction is the only cross-layer import (`services/translation.py:25` reuses `OLLAMA_BASE_URL`; `services/eval_harness.py:75-76` reuses `check_ollama, list_models`); `app.py:9-14` is the single sanctioned wiring point passing plain values plus callbacks into the strip. No layering violation, no new cross-cutting dependency, no cycle. Disposition: accept.
- **F2 — Duplication map: two instances, both accept-as-is.** (a) Retry-hint strings are duplicated across `app.py` / `services/translation.py` / `ui/text_view.py`; story 6 triage explicitly rejected sharing as AD-1 layer coupling (story 6 artifact triage log, Blind low/reject on drift risk). (b) The `_LANGUAGE_CODES` short-code map in `eval_harness.py:94-100` restates blueprint §2.1 codes; story 7 triage verified them verbatim against `languages.py` (story 7 triage log, format_table reject). Both are recorded here so later retros stop re-flagging them. Disposition: accept.
- **F3 — Size growth: checked and clean, no god-class.** Largest files are `services/eval_harness.py` (361 lines) and `app.py` (270 lines). The harness was read in full: docstring policy block, fixed `SENTENCES`/`MATRIX_LANGUAGES`, `run_matrix` / `format_table` / `record_results` / `main` — exactly the spec-enumerated surface, a standalone runner rather than a class, and it did not grow across stories (created once in story 7). No file accumulated cross-story bulk. Disposition: accept.
- **F4 — Pattern divergence (intentional, promote to convention).** `eval_harness.py:48-67` anchors the project root to the current working directory via `_find_project_root()` and documents why `__file__` is not trusted (relative invocations and doubled/synthetic paths observed). `pyproject.toml`'s header comment corroborates a real incident (a `[project]` table shadowing `services` as `text-c3po/text-c3po` and mis-resolving file locations). This is the in-repo evidence for the invocation's "relative-`__file__` path doubling that misdirected one gate write," and the cwd-anchored fix already landed. Disposition: accept as the pattern to reuse (see action item A6).
- **F5 — Spec-to-implementation reconciliation: no divergence.** All six capabilities trace to stories (CAP-1→stories 1–2, CAP-2→story 4, CAP-3→story 6, CAP-4→story 5, CAP-5→story 3, CAP-6→story 7) and the Success signal is met: Text mode returns formal/informal/commentary plus origin language (story 6 live call evidence), and the 5×5 matrix is recorded (research.md gate section). Non-goals held: banned-token greps clean for `langchain-openai` / `whisper` / `sounddevice` in product code (sole `whisper_client` hit is the pre-existing `runtimes/__init__.py` placeholder docstring, prior-story scope, untouched). Disposition: accept.

### Diff-scope review (narrowed)

- Per-story 4-layer reviews already ran via `bmad-dev` on every story (triage totals: story 1: 15 findings; story 2: 18; story 3: 20; story 4: 26; story 5: 23; story 6: 27 with 9 rows patched including the medium retry-chain fix; story 7: 21 with 1 low patched plus dead-code cleanup — zero high findings anywhere, all recorded in the story artifacts). This retro did not re-invoke review lenses over the worktree diff; it read the recorded triage logs and weighted story boundaries instead. That narrowing is stated here.
- **F6 — Boundary carry-overs (the cross-story defects this view exists to catch):** story 3 deferred V3 (mode-switch visibility branching ships without a check in that change; carries to the next story touching `app.py` — story 3 artifact deferred list); story 6 deferred the Flet UI-thread freeze and `ChatOllama` timeout questions as epic-level (story 6 auto-run result), and story 7 encoded the answer's first half as the serial-only execution policy (`eval_harness.py:24-31`). Both land as open items below, not as defects. Disposition: defer with owners.

### Process lessons (what worked / what hurt)

- **P1 — Repeatable harness pattern worked.** Every story shipped an ephemeral `/tmp` matrix script (story 4: 16/16, story 5: 26/26, story 6: 78/78 plus 2/2 supplement, story 7: stubbed determinism) in a repo with no test runner, and story 7 graduated the pattern into `pyproject.toml` pytest policy (fast unit by default, `@pytest.mark.integration` manual-only, serial-only). Source: story artifacts' verification sections; `pyproject.toml`.
- **P2 — Review discipline worked.** 150 findings triaged across seven stories with zero highs, patches verified by re-running the matrices, and rejections citing spec/contract evidence rather than taste. Source: the seven triage logs.
- **P3 — Serial lfm2.5-first policy worked.** After the MLX memory incident (a 9 GB MLX model OOMing Metal on its own), the harness docstring (`eval_harness.py:24-31`) and `pyproject.toml` both encode serial-only, lfm2.5-first, memory-hogs-out. Source: in-repo docstrings, corroborating the invocation's "serial lfm2.5-first policy after MLX OOM."
- **P4 — Contributor-tier SSE timeouts requiring retries.** Orchestrator-reported (no in-repo artifact; story logs record timeout-shaped probe handling as designed behavior, e.g. story 4 matrix refused/timeout→`(False,[])`, but not the tier incident itself). Carried as an unverified assumption into action item A1 rather than a sourced finding.
- **P5 — Orchestrator timeouts killing parents mid-review.** Orchestrator-reported, no in-repo artifact. Carried into action item A1 (background-plus-poll) as an assumption, not a finding.
- **P6 — `__file__` path doubling.** Sourced (F4 above): the doubled-root gate-write incident is evidenced by the `_find_project_root` comment block and the `pyproject.toml` shadowing comment. Resolved in-tree; the lesson is reuse (A6).

## Behavior verification

- **Exercised by this retro (first-hand, zero LLM calls):** `ast.parse` clean on `eval_harness.py`, `translation.py`, `app.py`, `ollama_client.py`; `grep runtimes text-c3po/ui/` clean; `lfm2.5` literal only in `runtimes/ollama_client.py` (default-rule constant plus docstring); banned-token grep clean outside comments/placeholder copy; stubbed `run_matrix` via `uv run --with langchain-ollama` scored 25/25 with `passes_gate` true and no side effects.
- **Inherited live evidence (from story artifacts, not re-run):** story 6 live `translate_text('Hello, how are you?','German','lfm2.5:latest')` returned all four schema fields against `127.0.0.1:11434`; story 5 live `check_ollama()` returned connected with 5 models; story 7 gate section records lfm2.5:latest 25/25 (100%) PASS.
- **Explicitly not exercised:** native macOS window eyeball (carried as residual risk through all seven stories); multi-model, new-model-no-code-change, Ollama-down, and zero-model paths live (stub-defined only); a full live harness re-run (25 LLM calls per model — skipped per the story 7 dispatch, and manual-only by `pyproject.toml` policy).

## Previous-retro follow-through

No prior retrospective exists in the tree (search for `*retro*` under `_bmad-output` returns only `sprint-status.yaml` keys, all `optional`/untouched). There is nothing to follow through on — recorded as "no prior retro," not as "no outstanding items."

## Action items

Proposed remediation and process lessons for E2–E4; none auto-applied. Owners are roles, and every item awaits human acceptance.

- **A1 — Long runs use background-plus-poll (owner: orchestrator).** Detach expensive executions (full harness, multi-model matrices, E2 audio pipelines) from the dispatching parent and poll for completion, so orchestrator timeouts never kill a parent mid-review. Motivated by P5 (orchestrator-reported).
- **A2 — Needs-operator escalation stays a hard rule (owner: orchestrator).** Anything outside in-worktree read/edit/write, bash, web, and `/tmp` scratch halts with status `needs-operator` plus path/operation/reason — never forced, never retried through a rejection. Standing constraint, restated for E2–E4.
- **A3 — `/tmp`-only ephemeral checks (owner: implementers).** All scratch verification scripts live under `/tmp` (the stories 1–7 practice); nothing scratch lands in the worktree. Standing constraint, restated for E2–E4.
- **A4 — Manual-only integration tests (owner: E2 spec + implementers).** Keep the `pyproject.toml` policy: plain `pytest` runs fast unit tests only; Ollama/whisper-server paths are `@pytest.mark.integration`, serial-only, manual invocation. Extend the marking to E2 audio/ASR tests; the eval harness stays a manual script, never CI.
- **A5 — Serial lfm2.5-first execution (owner: E2–E4 implementers).** Keep the `eval_harness.py` / `pyproject.toml` policy: one LLM request at a time, gate on the default product model first, memory hogs out of the matrix. Revisit only with hardware evidence.
- **A6 — Reuse the cwd-anchored root pattern in E2 (owner: E2 implementers).** File-decode and whisper-server paths must resolve from the working directory (`_find_project_root` pattern), never from `__file__`-relative joins. Source: F4.
- **A7 — Native Mac window eyeball still owed (owner: vshanbha / orchestrator).** Fold a real `python text-c3po/app.py` pass (Ollama stopped/started plus Retry, mode round-trip) into E3 acceptance or an E2 checkpoint; headless FakePage builds are not a substitute forever.
- **A8 — Carried code defers (owner: E3 spec).** Story 3 V3 mode-switch visibility assertion lands in the next change touching `app.py`; the Flet threading/timeout model for live calls (story 6 defer) gets a spike decision before E3 live-call wiring.

## Acceptance verdict

**accepted-with-open-items** — criteria **declared** (SPEC CAP-1–CAP-6 success clauses plus the Success signal). Evidence: 7/7 stories `done` with `pending_stories` empty; E1 gate 25/25 (≥24/25 required) PASS recorded in `research.md:33-41`; layering and loopback/ban greps clean on re-check; live translation and probe evidence on record in stories 5–6. The machine verdict is not forced-rejected (no unfinished stories). The named open items are A6–A8 (code/verification carries) with A1–A5 as standing process rules; none blocks E1's exit, and no human override was available in this headless run.

## Open questions

1. Does vshanbha accept the unrun native eyeball (A7) riding into E3, or is a Mac pass wanted before E2 starts? The answer moves A7 between epics.
2. Are action items A1–A8 accepted as tracked? Stories mode performs no `sprint-status.yaml` write, so tracking lives in this document until the orchestrator dispatches them.

## Assumptions

- Headless run: epic taken from the invocation (spec folder `spec-e1-shell-core`); no auto-detect performed and none needed.
- `pending_stories` derived from `stories.yaml` list order crossed with each artifact's `status: done` frontmatter: empty. Machine verdict therefore eligible for acceptance; rendered `accepted-with-open-items` (not `accepted`) because deferred/carried items F6/A6–A8 exist, with no human decision available to override.
- P4 (SSE/contributor-tier retries) and P5 (orchestrator timeouts killing parents) are orchestrator-reported context with no in-repo artifact; they shape action item A1 but are not findings. P6 (path doubling) and the MLX OOM policy are artifact-evidenced (F4, P3).
- Diff-scope review relied on recorded per-story triage logs rather than a fresh `bmad-review` pass; live LLM behavior and the native GUI were not re-exercised this run (see Behavior verification).
- Report placement: canonical document here at `{spec-folder}/RETROSPECTIVE.md` per the skill's stories-mode rule, plus a verbatim mirror at `_bmad-output/implementation-artifacts/epic-1-retro-2026-09-09.md` per the invocation's implementation-artifacts requirement. No `sprint-status.yaml` write, no edits to `SPEC.md`, `stories.yaml`, or story artifacts.
