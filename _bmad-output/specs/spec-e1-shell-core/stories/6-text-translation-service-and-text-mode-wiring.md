---
title: 'Text translation service and Text mode wiring'
type: 'feature'
created: '2026-09-08'
status: 'done'
baseline_revision: 'e70869cfd7da94f8f70a146ae0cc0a3dc32e8129'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/specs/spec-e1-shell-core/SPEC.md
  - _bmad-output/planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/EXPERIENCE.md
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** The shell has an input field, language pickers, and a model picker, but no translation path exists, so Text mode cannot serve CAP-3 and pasted text goes nowhere.

**Approach:** Add `services/translation` on `ChatOllama` with enforced JSON format plus `JsonOutputParser` to the full `Translation` schema, then wire the Text surface (input, Translate button, three output cards plus origin caption) with inline retryable errors and an empty-input guard.

## Boundaries & Constraints

**Always:** All product code inside `text-c3po/`; `ui` never imports `runtimes` internals (AD-1/AD-2) — `app.py` passes plain values plus callbacks, the text view exposes its controls via `view.data` refs; `services/translation` owns `ChatOllama` + parser with the model as an opaque runtime parameter (AD-6, reused by story 7); `ChatOllama` JSON format enforced with `JsonOutputParser` to the full schema (AD-5); malformed JSON is a retryable `{error, retryable}` error with the raw payload logged, never raw to the UI; empty input is rejected client-side with a hint and no LLM call (FR-3); Translate is disabled while a call is in flight and re-enabled on result or error; recoverable failures render inline in the failing card plus `SnackBar` retry, no modal dialogs (AD-12); loopback only to `http://127.0.0.1:11434` by reusing `OLLAMA_BASE_URL` (AD-11); model and target language are read at call time so mid-session changes apply to the next call only; status dot always paired with a text label; `flet==0.86.5` exact stays untouched; no secrets files.

**Never:** No whisper, sounddevice, VAD, or file-pipeline code (E2/E3 scope); no eval harness (owned by story 7); no hard-coded model names anywhere — the `lfm2.5` literal stays only in `runtimes/ollama_client.py`; no `langchain-openai` (AD-11 banned); no cross-imports from `live-translate/` (re-implement the v1 system+human prompt pattern only); no changes to `streamlit_app.py` or `languages.py`; no persisted history; no restyling of Flet Material defaults.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Valid text + target + model, Ollama up | Three cards render formal / informal / commentary plus `origin: <lang>` caption | No error expected |
| Empty input | Blank/whitespace input, Translate tapped | Inline hint under the field; no LLM call issued | Client-side guard, no error state |
| Unparseable JSON | Model returns malformed JSON | All three cards show "Couldn't parse that one. Retry." plus `SnackBar` with retry; raw payload goes to logs only | Retryable `{error, retryable: True}`; retry re-issues the same prompt without retyping |
| Partial fields | JSON parses but a field is missing/blank | Present fields display; only the missing field's card shows the retry hint | Same retry path as above |
| Ollama down at call time | `ollama serve` stopped when Translate tapped | Failing cards show the retry hint plus `SnackBar`; no traceback, no dialog | Retryable error; Retry re-probes then re-issues |
| In-flight guard | Translate tapped twice quickly | Button disabled during the call; second tap issues no second call; re-enabled on result or error | No error expected |
| Mid-session model change | Different model picked after launch, then Translate | Call uses the picker's current value; prior results untouched until replaced | No error expected |
| Headless build | Load app module with a FakePage | Text view builds with input + target picker + Translate + three cards + origin caption, no window launched | ImportError surfaces with missing-dep message |

</intent-contract>

## Code Map

- `streamlit_app.py:23-51` -- READ-ONLY v1 pattern source: `Translation` schema fields, system+human prompt with `{format_instructions}`, `parser.parse(response.content)`; re-implement against `ChatOllama`, never import.
- `text-c3po/services/translation.py` -- DOES NOT EXIST; the CAP-3 service: `Translation` pydantic schema (`formal`, `informal`, `commentary`, `origin_language`), `ChatOllama(model=..., format="json", base_url=OLLAMA_BASE_URL)` with `temperature=0.2`, `translate_text(text, target_language, model)` returning a parsed dict on success or `{error, retryable: True}` on any parse/transport failure (never raises, never returns raw payloads); reuses `OLLAMA_BASE_URL` from `runtimes.ollama_client` (services→runtimes allowed).
- `text-c3po/services/__init__.py` -- services layer marker (AD-1); EXTEND re-export with the translation entry point.
- `text-c3po/ui/text_view.py` -- story-3 Text surface (`build_text_view()` returning `Column` with `Text` + multiline `TextField` min 6 lines + target-picker row); EXTEND to mount the Translate `FilledButton` plus three output cards (`Container` + `Text` + copy `IconButton` per DESIGN output-card) plus the origin-language caption, exposing all controls via `view.data` refs; cards render independently.
- `text-c3po/app.py` -- story-5 entry (once-built views with `visible` toggling, `current_model` store, `on_model_change` next-call-only); EXTEND with the Translate `on_click`: empty-input guard (hint, no call), disable-in-flight, read target-dropdown value + `current_model["value"]` at call time, invoke `translate_text`, render cards + caption, `SnackBar` retry on failure.
- `text-c3po/ui/__init__.py` -- UI re-export surface (never imports `runtimes`); EXTEND only if the text view exposes new named builders/refreshers.
- `requirements.txt` -- exact `flet==0.86.5` pin; EXTEND by appending `langchain-ollama` exact-pinned at the version resolving at implementation time (`1.1.0` verified resolvable 2026-09-08 via dry-run; transitive `langchain-core` arrives with it).
- `_bmad-output/specs/spec-e1-shell-core/stories/5-model-picker-with-lfm2-5-default-rule.md` -- prior-story continuity: reuse its FakePage-headless verification pattern, its `current_model` next-call-only store, and its forbidden-token grep (now allowing `translat`/`ChatOllama`/`JsonOutputParser` in `services/translation.py` + `app.py` wiring + `ui/text_view.py` only); `whisper`/`sounddevice` stay forbidden; carry forward its residual risk (native one-window eyeball still needs a Mac run).
- `_bmad-output/specs/spec-e1-shell-core/stories/4-ollama-client-with-launch-connectivity-check.md` -- prior-story continuity: the never-raises probe contract the service's transport-failure path mirrors.

## Tasks & Acceptance

**Execution:**
- `text-c3po/services/translation.py` -- create the `Translation` schema + `translate_text(text, target_language, model)` on JSON-enforced `ChatOllama` (never raises; failures yield retryable `{error, retryable}`; raw payload to logs only) -- the CAP-3/AD-5 service story 7 reuses with model as parameter.
- `requirements.txt` -- append the exact `langchain-ollama` pin (keep `flet==0.86.5` untouched, no `langchain-openai`) -- the only new dependency this epic needs.
- `text-c3po/services/__init__.py` -- extend re-exports with the translation entry point -- keeps the services layer's single import surface per AD-1.
- `text-c3po/ui/text_view.py` -- extend `build_text_view()` with the Translate `FilledButton`, three independent output cards with copy buttons, and the origin caption over `view.data` refs (no `runtimes` import) -- the CAP-3 surface.
- `text-c3po/app.py` -- wire Translate `on_click` (empty guard, disable-in-flight, call-time model+target read, render, inline error + `SnackBar` retry) -- the CAP-3 no-restart call path.

**Acceptance Criteria:**
- Given valid input with a target language and model while Ollama runs, when the implementer taps Translate, then all three cards plus the origin caption render with the four schema fields.
- Given blank input, when the implementer taps Translate, then an inline hint shows and no LLM call is issued.
- Given malformed model JSON, when a call completes, then the failing cards show the retry hint with `SnackBar` retry, the raw payload appears only in logs, and retry re-issues without retyping.
- Given the finished tree, when the implementer greps under `text-c3po/`, then no import of `runtimes` appears in `ui/`, the `lfm2.5` literal appears only in `runtimes/ollama_client.py`, no `langchain-openai` exists anywhere, and no `whisper` or `sounddevice` symbols exist outside comments and placeholder copy.
- Given a headless environment, when the implementer loads the app module with a FakePage, then the Text view plus Translate plus three cards plus origin caption build with no window launched.

## Spec Change Log

## Review Triage Log

### 2026-09-08 — Review pass
- verdicts: 27 findings — high 0, medium 5, low 15, false 6, maybe-false 1
- findings:
  - `[medium]` `[patch]` Blind: SnackBar retry re-issues without re-probing while top-strip retry re-probes without re-issuing, so the spec Ollama-down Retry (re-probe then re-issue) never happens in one action — chained into on_translate_retry (reprobe then re-issue); grouped with Edge retry-claim below; matrix retry-reissues still 78/78 OK.
  - `[medium]` `[defer]` Blind: Translate runs blocking translate_text on the UI thread with no thread/async/progress, so startup and Translate freeze the window — real but threading is epic-wide and spec-silent; deferred: threading model for Flet + live Ollama calls; settle with a Flet-threaded spike plus story-7 harness needs.
  - `[false]` `[reject]` Blind: renderer discards specific service error text for a generic card hint — refuted: generic retry hint is the spec design (raw never reaches UI; empty-input hint handled pre-call).
  - `[low]` `[reject]` Blind: retry/error strings duplicated across app/services/ui with drift risk — rejected: values identical today and sharing would couple AD-1 layers; unlikely met everyday, fix more than direct correction.
  - `[low]` `[reject]` Blind: SnackBar appended per failure with no dedupe plus manual overlay API — rejected: minor stacking cosmetic; API rework more than direct correction.
  - `[medium]` `[defer]` Blind: new ChatOllama per call with no timeout/reuse/parse-retry — grouped with Edge timeout below; deferred (unverified ChatOllama timeout/client_kwargs API; parse-retry by design is UI retry, reuse negligible per-click).
  - `[low]` `[patch]` Blind: copy buttons copy the retry placeholder verbatim — guarded _make_copy_handler to no-op on empty/whitespace or RETRY_HINT; real text still copies.
  - `[false]` `[reject]` Blind: absolute imports assume sys.path plus missing runtimes file — refuted: established text-c3po/ sys.path pattern from stories 4/5; ollama_client exists outside the story-scoped diff.
  - `[low]` `[reject]` Blind: Row/cards with no wrap/expand/scroll overflow narrow windows — rejected: 960px minimum plus Material-default ban; unlikely everyday, fix adds complexity.
  - `[low]` `[reject]` Blind: prompt lacks no-fences line and _normalize skips trim/camelCase aliases — rejected: format=json rarely fences and retry is spec-compliant for malformed; auto-fix not required.
  - `[low]` `[defer]` Edge app.py:144-149: unknown mode value hides all views — pre-existing story-2 scope, not caused here; defer to mode-switch owner.
  - `[low]` `[defer]` Edge app.py:165-188: page.update outside try in reprobe could crash Retry — pre-existing story-4/5 reprobe scope; defer with that owner.
  - `[low]` `[patch]` Edge app.py:196-253: second Translate tap could re-enter while disabled — added disabled-at-entry early return (framework still primary guard); headless-direct-call demonstrable.
  - `[false]` `[reject]` Edge translation __str__ raises escapes never-raises — refuted: parser yields JSON-only plain types whose str() never raises.
  - `[false]` `[reject]` Edge _normalize raises escapes to UI — refuted: dict-only with guarded key lowering plus safe coercions; JSON shapes cannot raise.
  - `[false]` `[reject]` Edge whitespace-padded model/target fails — refuted: Dropdown values never pad; UI cannot reach the trigger.
  - `[medium]` `[defer]` Edge Ollama hangs with no timeout, button stuck — same entry as Blind timeout above (carried); deferred pending verified timeout API.
  - `[low]` `[reject]` Edge megabyte paste with no length guard — rejected: no limit in spec and adding one adds a new rejecting branch; hypothetical.
  - `[low]` `[patch]` Edge large raw payload logged verbatim (PII/bloat) — truncated both raw-bearing logger.error calls to raw[:2000]; returns unchanged (never raw).
  - `[low]` `[reject]` Edge clipboard-missing copy silently no-ops — rejected: fallback affordance adds surface beyond direct correction.
  - `[false]` `[reject]` Edge requirements swap breaks streamlit_app v1 — refuted: v1 retirement by E1 design (blueprint/AGENTS.md); Flet replaces streamlit entry.
  - `[medium]` `[patch]` Edge claim: believed combined reprobe+reissue never happens — same defect as Blind retry above (carried); fixed by on_translate_retry chaining.
  - `[maybe-false]` `[defer]` Edge claim: queued second tap duplicates after re-enable — unsettled (needs Flet event-queue proof whether disabled drops or queues); if true medium; settle with a live double-tap run.
  - `[low]` `[patch]` Verification-gap: translate_text guards/normalize/error shapes had no asserting check — ran ephemeral /tmp/story6_check.py service sections plus live lfm2.5 call; no product change (runner-less repo practice).
  - `[low]` `[patch]` Verification-gap: on_translate wiring had no FakePage asserts — ran ephemeral /tmp/story6_check.py wiring sections (empty-guard, disable/re-enable, call-time read, full/partial cards, snackbar retry) 78/78 OK.
  - `[low]` `[patch]` Verification-gap: view structure/refs had no asserts — ran ephemeral view-structure section (all view.data keys, card/copy bindings, on_click attach) 78/78 OK.
  - `[low]` `[patch]` Verification-gap: requirements swap had no installing check — verified flet 0.86.5 import plus langchain-ollama resolve path used by live call; no product change.

## Verification

**Commands:**
- `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['text-c3po/services/translation.py', 'text-c3po/ui/text_view.py', 'text-c3po/app.py', 'text-c3po/services/__init__.py']]"` -- expected: parses clean.
- `grep -rn "runtimes" text-c3po/ui/ || true` -- expected: no matches.
- `grep -rniE "langchain-openai|whisper|sounddevice" text-c3po/ || true` -- expected: no matches outside comments and placeholder copy.
- `grep -rn "lfm2\.5" text-c3po/ || true` -- expected: only the default-rule constant in `runtimes/ollama_client.py`.
- `uv run --with 'flet==0.86.5' python -c "import flet; print(flet.__version__)"` -- expected: prints `0.86.5`.
- `python3 -c "import sys; sys.path.insert(0, 'text-c3po'); from services.translation import translate_text; print(translate_text('Hello, how are you?', 'German', 'lfm2.5:latest'))"` -- expected: prints a dict with formal/informal/commentary/origin_language while `ollama serve` runs.

## Auto Run Result

- Summary: CAP-3 Text translation path delivered and review-hardened. `services/translation` owns ChatOllama (JSON-enforced) + JsonOutputParser to the full Translation schema with never-raises retryable errors; Text surface mounts input + Translate + three copyable cards + origin caption over view.data refs; app.py wires empty-guard, disable-in-flight, call-time model/target read, per-field render, and reprobe-then-reissue SnackBar retry. Four review patches applied with full re-verification.
- Files changed: `text-c3po/services/translation.py` (schema + translate_text + truncated raw logging); `text-c3po/services/__init__.py` (re-exports); `text-c3po/ui/text_view.py` (Translate + cards + caption + copy guard); `text-c3po/app.py` (on_translate + on_translate_retry reprobe-then-reissue + disabled entry guard); `requirements.txt` (flet==0.86.5 kept, langchain-ollama==1.1.0 added; streamlit/langchain-openai retired by E1 design).
- Review findings: 27 findings — 9 rows patched (1 medium retry-chain entry + 3 low product entries + 4 low verification-only rows + 1 grouped medium row carried), 6 rows deferred (UI-thread freeze, ChatOllama timeout API, mode-switch scope, reprobe scope, queued-tap queue proof), 12 rows rejected (6 false with refutations, 6 low-reject as unlikely everyday with costlier-than-correction fixes).
- Follow-up review recommendation: false. Patched entries this pass: 1 medium (retry chain, verified by matrix retry-reissues) and 7 low (3 product + 4 verification-only). No patched high; only one patched medium entry, so convergence holds. Deferred timeout/threading remain epic-level concerns for story 7, not this story's gate.
- Verification performed: AST parses clean; `grep runtimes text-c3po/ui/` clean; `langchain-openai` clean; `whisper` only in `runtimes/__init__.py` layer docstring (comment scope); `sounddevice` clean; `lfm2.5` only in `runtimes/ollama_client.py` (+ pycache); `flet 0.86.5` prints; `/tmp/story6_check.py` MATRIX 78/78 OK post-patch; `/tmp/story6_midmodel.py` SUPPLEMENT 2/2 OK (mid-session model honored); live `translate_text('Hello, how are you?','German','lfm2.5:latest')` returned formal/informal/commentary/origin_language (Guten Tag / Hallo / register note / English) against live 127.0.0.1:11434 with lfm2.5:latest present.
- Residual risks: native one-window Mac eyeball still unrun (carried from story 5); live Ollama-down reprobe+reissue exercised via fakes + live-up reprobe, not with serve stopped mid-call; ChatOllama timeout/threading deferred — a hung daemon would still freeze the window until the call returns.
