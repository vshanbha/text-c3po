---
id: SPEC-e4-ops-eval-polish
companions:
  - ../../planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md
  - ../../planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/EXPERIENCE.md
sources:
  - ../../planning-artifacts/prds/prd-text-c3po-2026-09-08/prd.md
  - ../../../../blueprint.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# E4 — Ops, Eval & Polish

## Why

E1–E3 produce a working app on vshanbha's machine that nobody else can install, whose 23-language quality claims are unmeasured, and which still carries cloud-key remnants. E4 makes v2 installable and trustworthy: one-script setup, a full language-quality matrix, a signed mic-capable bundle, regression tests, published docs, and a codebase with zero cloud surface — the gates in §6 of the blueprint all close here.

## Capabilities

- **CAP-1**
  - **intent:** New user can run `setup.sh` covering Ollama install, model pull, PortAudio/sounddevice, and BlackHole guidance.
  - **success:** Clean-machine run completes in ≤15 min on broadband; missing BlackHole is guidance, never a failure.
- **CAP-2**
  - **intent:** Builder can run the full 23-language eval harness recording per-language scores and JSON-validity per installed model.
  - **success:** Full matrix recorded in `research.md`; re-running with a new model appends a comparable row with no code changes.
- **CAP-3**
  - **intent:** User can install a macOS bundle that prompts for mic access with an explanatory string and runs loopback-only.
  - **success:** First Live start shows the `NSMicrophoneUsageDescription` prompt; bundle reaches only `127.0.0.1:11434` and `127.0.0.1:9001` after download.
- **CAP-4**
  - **intent:** Builder can run regression tests covering VAD flush paths, JSON parsing, and whisper-server health.
  - **success:** Suite passes on a clean checkout after `setup.sh`; failures name the subsystem and the retry or fix action.
- **CAP-5**
  - **intent:** System contains no cloud LLM surface and docs describe the true v2 run and eval commands.
  - **success:** `grep -ri openai` over product code and `secrets.toml` presence check both return empty; README/AGENTS.md document the wired run and harness commands.
- **CAP-6**
  - **intent:** Project documentation (run guide, eval research, architecture) is published to GitHub Pages, replacing the stub `docs/index.html` hosting experiment.
  - **success:** Push to master updates the Pages site via the existing `static.yml` workflow; the landing page reflects the current v2 README content, not the old stub.

## Constraints

- `setup.sh` owns environment (Ollama install, model pull, PortAudio/sounddevice, BlackHole guidance); bundle carries `NSMicrophoneUsageDescription` (AD-13).
- Eval harness reuses the E1 translation service with model passed as parameter; quality variance never gates the UI (AD-6).
- After first-run download, zero outbound: loopback to `127.0.0.1:11434` and `127.0.0.1:9001` only; `langchain-openai` banned, no secrets files (AD-11).
- Latency budget <3s end-to-end per utterance at flush granularity; 5-min soak with no unbounded memory growth (NFR-1, NFR-4).
- All product code inside `text-c3po/`; OpenAI code and `secrets.toml` deleted, never merely unreferenced.
- Never commit secrets; verify by grep plus absence check in this epic.

## Non-goals

- New modes, new pickers, new translation behavior (E1–E3 own; E4 only measures and packages them).
- Token streaming, diarization, translation memory, history persistence (deferred past v1).
- Non-macOS bundles (guides welcome, untested).

## Success signal

From a clean machine, `setup.sh` finishes in budget, the 23-language matrix is recorded, the installed bundle prompts for mic once and runs offline on loopback only, tests pass, the Pages site shows current v2 docs, and no OpenAI string or secrets file remains — v2 is installable, measured, documented, and cloud-free.

## Assumptions

- Assumed Apple-silicon reference hardware for latency/soak budgets (PRD §8).
- Assumed `flet build macos` vs PyInstaller `--windowed` decision lands in this epic with AD-13 holding either way.
