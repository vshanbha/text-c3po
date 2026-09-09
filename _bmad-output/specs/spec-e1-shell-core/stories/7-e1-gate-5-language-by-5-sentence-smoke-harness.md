---
title: 'E1 gate — 5-language by 5-sentence smoke harness'
type: 'feature'
created: '2026-09-08'
status: 'done'
baseline_revision: 'e70869cfd7da94f8f70a146ae0cc0a3dc32e8129'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/specs/spec-e1-shell-core/SPEC.md
  - _bmad-output/planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/research/technical-model-quality-2026-09-08/research.md
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** No repeatable runner exists for the CAP-6/SM-1 5-language × 5-sentence matrix, so the E1 exit gate (≥95% JSON-valid per model) cannot be executed or recorded and model quality variance has nowhere to land.

**Approach:** Add `services/eval_harness` reusing `services.translate_text` with the model passed as a parameter over a fixed 5-sentence × 5-language matrix across every model from `runtimes.list_models()`; score per-model JSON-validity and append the table to the model-quality `research.md`.

## Boundaries & Constraints

**Always:** All product code inside `text-c3po/`; the harness lives in `services/` and reuses `translate_text(text, target_language, model)` with the model as an opaque runtime string (AD-6, no model-specific branches); model list comes live from `runtimes.list_models()` so a newly pulled model joins with no code changes; the five target languages are names from the `LANGUAGES` constant (German, French, Spanish, Hindi, Chinese — Latin, Devanagari, and CJK scripts); JSON-valid means the result dict carries no `error` key; per-model score is valid/25 with the gate at ≥95% (≥24 of 25); results append a dated `## E1 gate` section to the model-quality `research.md` (append, never rewrite) and print a matching stdout table; headless-runnable via `python text-c3po/services/eval_harness.py` with `--models` and `--research-path` overrides; loopback only via reused `OLLAMA_BASE_URL` (AD-11); `flet==0.86.5` exact stays untouched with no new dependencies (stdlib plus installed `langchain-ollama` only); no secrets files.

**Never:** No full 23-language matrix (E4 scope); no whisper, sounddevice, VAD, or file-pipeline code; no UI changes (`ui/` untouched); no `langchain-openai` (AD-11 banned); no cross-imports from `live-translate/`; no changes to `streamlit_app.py`, `languages.py`, or `requirements.txt`; no persisted state beyond the `research.md` append.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Ollama up with N installed models | 25 calls per model (5 sentences × 5 languages); stdout table plus appended `research.md` section with per-model per-language counts and pass/fail vs 95% | No error expected |
| New model, no code change | Model pulled after the harness ships, harness re-run | New model appears automatically via `list_models()` with a comparable appended row | No error expected |
| Single-model re-run | `--models mistral:latest` | Only that model runs; appended row stays comparable | Unknown name runs anyway (opaque string); transport failures count invalid, never abort |
| Ollama down | `ollama serve` stopped | Guidance printed, no scores written, non-zero exit | Never raises; refused/timeout counts as harness-abort, not as invalid calls |
| Zero models | 200 with empty `models` list | Connected-but-empty message, no scores written, non-zero exit | No error expected |
| Invalid call mid-matrix | One call returns `{error, retryable}` | Counted invalid for that cell; matrix continues to completion | Abort never; failures listed per cell in the result detail |
| Headless import | Import harness module without running | `SENTENCES`, `MATRIX_LANGUAGES`, `run_matrix`, `is_valid` available with no side effects or LLM calls | ImportError surfaces with missing-dep message |

</intent-contract>

## Code Map

- `text-c3po/services/translation.py` -- story-6 CAP-3 service; REUSE `translate_text(text, target_language, model)` (never raises; `{error, retryable}` on any transport/parse failure, raw payload to logs only) as the harness's only LLM entry point with model as parameter.
- `text-c3po/runtimes/ollama_client.py` -- live probe layer; REUSE `list_models()` (verbatim `/api/tags` names, `[]` when down/malformed, never raises) plus `OLLAMA_BASE_URL` loopback constant; no new probe code.
- `text-c3po/languages.py` -- READ-ONLY AD-10 constant; the five harness language names (German, French, Spanish, Hindi, Chinese) must each match a `name` entry verbatim.
- `text-c3po/services/eval_harness.py` -- DOES NOT EXIST; the CAP-6/SM-1 runner: `SENTENCES` (5 fixed English sentences), `MATRIX_LANGUAGES` (5 names), `GATE_THRESHOLD = 0.95`, `is_valid(result)` (no `error` key), `run_matrix(models=None, translate_fn=translate_text)` returning per-model `{valid, total, per_language, failures}` with injectable `translate_fn` for headless tests, `format_table(results)` markdown rows, `record_results(results, path)` appends the dated gate section, `main(argv=None)` wiring `--models`/`--research-path`, exit 0 iff every model passes the gate.
- `text-c3po/services/__init__.py` -- services layer marker (AD-1); EXTEND re-exports with the harness entry points.
- `_bmad-output/planning-artifacts/research/technical-model-quality-2026-09-08/research.md` -- READ plus APPEND target: prior recon (20/20 JSON-valid on 2 models × 2 languages) is the continuity baseline; the harness appends the dated E1-gate 5×5 section without touching existing content.
- `_bmad-output/specs/spec-e1-shell-core/stories/6-text-translation-service-and-text-mode-wiring.md` -- prior-story continuity: reuse its never-raises contract and its `/tmp` ephemeral-check verification pattern (no committed tests; repo has no runner); carry forward its residual risk (native Mac eyeball unrun).
- `_bmad-output/specs/spec-e1-shell-core/stories/5-model-picker-with-lfm2-5-default-rule.md` -- prior-story continuity: model opacity (AD-6) plus the forbidden-token grep baseline (`lfm2.5` only in `runtimes/ollama_client.py`, no `langchain-openai`/`whisper`/`sounddevice` outside comments and placeholder copy).

## Tasks & Acceptance

**Execution:**
- `text-c3po/services/eval_harness.py` -- create the 5×5 runner (`SENTENCES` + `MATRIX_LANGUAGES` + `is_valid` + `run_matrix` with injectable translate fn + `format_table` + `record_results` append + `main` with `--models`/`--research-path`, exit 0 iff all models ≥95%) -- the CAP-6/SM-1 E1 exit gate.
- `text-c3po/services/__init__.py` -- extend re-exports with the harness entry points -- keeps the services layer's single import surface per AD-1.
- `_bmad-output/planning-artifacts/research/technical-model-quality-2026-09-08/research.md` -- append the dated E1-gate section with the live per-model table -- the recorded gate evidence.

**Acceptance Criteria:**
- Given Ollama running with the installed models, when the implementer runs the harness, then every model completes 25 calls and the stdout table plus appended `research.md` section show per-model per-language valid counts with a pass/fail verdict at ≥95%.
- Given a model pulled after the harness ships, when the implementer re-runs with no code changes, then the new model runs with a comparable appended row.
- Given `ollama serve` stopped or zero models installed, when the implementer runs the harness, then guidance prints, no scores are written, and the exit is non-zero.
- Given a mid-matrix call returning `{error, retryable}`, when the run completes, then that cell counts invalid without aborting the matrix and appears in the failure detail.
- Given the finished tree, when the implementer greps under `text-c3po/`, then no import of `runtimes` appears in `ui/`, the `lfm2.5` literal appears only in `runtimes/ollama_client.py`, and no `langchain-openai`, `whisper`, or `sounddevice` symbols exist outside comments and placeholder copy.
- Given a headless environment, when the implementer imports the harness with a stubbed translate function, then `run_matrix` scores the stubbed outcomes deterministically with zero LLM calls.

## Spec Change Log

## Review Triage Log

### 2026-09-09 — Review pass (resume: no prior recorded findings; all four layers run fresh via bmad-dev on a 4-file story-scoped diff)
- verdicts: 21 findings — high 0, medium 0, low 4, false 17, maybe-false 0
- findings:
  - `[low]` `[patch]` Duplicate sys.path guard block in eval_harness.py — second identical insert is dead code; deleted (2 lines), re-verified AST/import/stub-matrix green.
  - `[false]` `[reject]` services/__init__ omits passes_gate/EXIT_* re-exports — internal gate use works; spec requires no external surface; no demonstrated harm.
  - `[false]` `[reject]` is_valid skips shape/content check — translate_text normalizes success to the 4-field schema by construction and the spec Design Notes mandate the narrow no-error-key check.
  - `[false]` `[reject]` run_matrix failures lack sentence text/error payload — spec defines the one-line detail as exactly model, language, sentence index.
  - `[false]` `[reject]` record_results stacks duplicate dated sections / no newline guard / no latency — append-only is spec-mandated; the leading newline separates correctly; latency is not in the spec.
  - `[false]` `[reject]` format_table hard-codes separator / no runtime check vs LANGUAGES — fixed consistent constants (German/de, French/fr, Spanish/es, Hindi/hi, Chinese/zh verified verbatim in languages.py); loud failure on an unreachable edit is correct behavior.
  - `[false]` `[reject]` --models bare-flag fallback / no dedupe / silent unknown names — spec mandates opaque unknown names; bare-flag-to-all is a safe default; duplicates echo operator input predictably.
  - `[false]` `[reject]` main double-probes Ollama / no latency log / no timestamps — check_ollama plus list_models yield the two distinct abort messages; latency/timestamps are not in the spec.
  - `[false]` `[reject]` cwd-anchored project root / makedirs on --research-path parent — degrades to the spec-allowed ImportError; makedirs honors the explicit override flag required for /tmp ephemeral checks.
  - `[false]` `[reject]` research.md gate section shows only lfm2.5, no mistral row or latency — row reflects the live installed list (only lfm2.5 present per AGENTS.md); spec table shape has no latency column.
  - `[low]` `[reject]` run_matrix(models) as a bare string iterates characters — real Python semantics but off-contract input (every caller passes lists); unlikely met in everyday use and the guard adds a branch.
  - `[false]` `[reject]` MATRIX_LANGUAGES entry missing from _LANGUAGE_CODES raises KeyError — unreachable with fixed constants; loud failure is correct.
  - `[false]` `[reject]` separator column mismatch if matrix resized — same unreachable static state, not a defect.
  - `[low]` `[reject]` pipe/newline in model names splits the markdown table — Ollama tag names disallow such characters; otherwise operator self-inflicted; sanitizer adds complexity.
  - `[false]` `[reject]` bare --models flag runs all models — safe default that runs correctly; scope surprise is not breakage.
  - `[false]` `[reject]` duplicate --models names duplicate runs/rows — echoed operator input with predictable outcome.
  - `[false]` `[reject]` hanging translate_fn stalls the whole harness — violates the translate function return-or-raise contract; timeouts would need threads banned by the serial-only execution policy.
  - `[false]` `[reject]` unwritable research path escapes as traceback — operator error exits non-zero loudly; spec defines no exit code for it.
  - `[false]` `[reject]` --research-path outside the project tree — explicit operator override by design (required for /tmp ephemeral checks).
  - `[false]` `[reject]` check_ollama unexpected shape or raise breaks unpack — contract verified in ollama_client.py: always returns a (bool, list) tuple, never raises.
  - `[low]` `[reject]` deleted cwd or >8-level nesting breaks root anchoring — pathological; unlikely met and the fix adds complexity.
- layer notes: verification-gap returned zero findings. Intent-alignment audit (descriptive, no prescriptive findings) confirms the diff implements readings R1+R3+R4 literally with repo hygiene intact; single-model live evidence is environment truth, and multi-model/new-model/abort paths are defined but exercised only via stubs — carried as residual risk, not a finding.

## Auto Run Result

Status: done

Summary: CAP-6/SM-1 E1 exit-gate runner shipped — `text-c3po/services/eval_harness.py` runs the fixed 5-sentence x 5-language matrix per live model via `translate_text` with the model as an opaque parameter, scores JSON-validity at a >=95% (>=24/25) gate, prints a stdout table, and appends a dated `## E1 gate` section to the model-quality research.md. Review pass triaged 21 findings (1 low patched, 3 low rejected, 17 false rejected) plus two small self-review patches (dead-code deletion, docstring literal cleanup); no intent_gap or bad_spec; no loopback needed.

Files changed:
- `text-c3po/services/eval_harness.py` — created: SENTENCES, MATRIX_LANGUAGES, GATE_THRESHOLD, is_valid, passes_gate, run_matrix (injectable translate_fn), format_table, record_results (append-only), main (--models/--research-path, exit 0/1/2); review patches: removed duplicated sys.path guard and two lfm2.5 docstring literals (acceptance grep now clean).
- `text-c3po/services/__init__.py` — extended re-exports with the harness entry points (AD-1 import surface).
- `_bmad-output/planning-artifacts/research/technical-model-quality-2026-09-08/research.md` — appended dated E1-gate 5x5 section (lfm2.5:latest 25/25 PASS) from the prior live run; untouched by this resume pass.

Review findings breakdown: patches applied — B1 duplicate-guard deletion and the lfm2.5 docstring-literal cleanup (acceptance-hygiene, no behavior change). Deferred — none. Rejected — 20 findings with spec/contract evidence recorded in the triage log above (10 blind-hunter on spec-mandated behavior or unreachable states; 10 edge-case off-contract/pathological inputs where fixes would add branches against the serial-only policy).

Follow-up review recommendation: false (first pass; patched entries: one low; zero high and zero medium patched).

Verification performed (live harness NOT re-run per dispatch):
- `ast.parse` on eval_harness.py + services/__init__.py — clean.
- `grep -rn runtimes text-c3po/ui/` — no matches.
- `grep -rniE langchain-openai|whisper|sounddevice text-c3po/` — only a pre-existing `whisper_client` mention in runtimes/__init__.py placeholder docstring (prior-story scope, untouched).
- `grep -rn lfm2.5 text-c3po/ --include=*.py` — only runtimes/ollama_client.py (default-rule constant + docstring).
- `uv run --with flet==0.86.5 python -c import flet` — 0.86.5.
- Headless import via uv-run env (`uv run --with langchain-ollama python`, system python3 lacks the dep): SENTENCES/MATRIX_LANGUAGES print `5 5`, no side effects, zero LLM calls.
- Stubbed run_matrix determinism (zero LLM): good-model 25/25 PASS, bad-model 20/25 FAIL with 5 per-cell Hindi failure lines; passes_gate(24,25) true, passes_gate(23,25) false; format_table + record_results smoke-written to /tmp and removed.

Residual risks: multi-model, new-model-no-code-change, Ollama-down, and zero-model paths are code-defined but live-exercised only via stubs (live re-run explicitly out of scope for this pass); single live research row reflects the lfm2.5-only install; repo has no test runner so regression cover is the headless stub pattern. Commit step skipped per never-commit repo policy — working tree retains the reviewed changes uncommitted.

## Design Notes

JSON-validity is deliberately narrow: `translate_text` already normalizes shape, so a result without an `error` key is a schema-conformant dict by construction and counts valid; anything else (transport failure, malformed JSON, unexpected shape) counts invalid. Gate math: 95% of 25 is 23.75, so a model passes with ≥24 valid cells. Appended section shape:

```markdown
## E1 gate — 5x5 smoke (2026-09-08)

| Model | de | fr | es | hi | zh | Valid | Score | Gate |
|---|---|---|---|---|---|---|---|---|
| lfm2.5:latest | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 25/25 | 100% | PASS |
```

plus a one-line failure detail per invalid cell (model, language, sentence index).

## Verification

**Commands:**
- `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['text-c3po/services/eval_harness.py', 'text-c3po/services/__init__.py']]"` -- expected: parses clean.
- `grep -rn "runtimes" text-c3po/ui/ || true` -- expected: no matches.
- `grep -rniE "langchain-openai|whisper|sounddevice" text-c3po/ || true` -- expected: no matches outside comments and placeholder copy.
- `grep -rn "lfm2\.5" text-c3po/ || true` -- expected: only the default-rule constant in `runtimes/ollama_client.py`.
- `uv run --with 'flet==0.86.5' python -c "import flet; print(flet.__version__)"` -- expected: prints `0.86.5`.
- `python3 -c "import sys; sys.path.insert(0, 'text-c3po'); from services.eval_harness import SENTENCES, MATRIX_LANGUAGES; print(len(SENTENCES), len(MATRIX_LANGUAGES))"` -- expected: prints `5 5`.
- `python text-c3po/services/eval_harness.py` -- expected: live 5×5 run per installed model with stdout table, `research.md` appended, exit 0 iff every model ≥95% (slow: ~125 LLM calls; allow a long timeout).
