---
type: epic
title: "Ops, Eval & Polish"
parent: initiative-text-c3po
covers: [R13, R14, R16]
sources:
  - _bmad-output/initiative-text-c3po/archive-v6/specs/spec-e4-ops-eval-polish/SPEC.md
  - _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
companions:
  - _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
  - _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
risk: medium
---

# Ops, Eval & Polish

## Description

E1–E3 produce a working app on vshanbha's machine that nobody else can install, whose 23-language quality claims are unmeasured, and which still carries cloud-key remnants. E4 makes v2 installable and trustworthy: one-script setup, a full language-quality matrix, a signed mic-capable bundle, regression tests, published docs, and a codebase with zero cloud surface — the gates in §6 of the blueprint all close here.

## Outcome

From a clean machine, `setup.sh` finishes in budget, the 23-language matrix is recorded, the installed bundle prompts for mic once and runs offline on loopback only, tests pass, the Pages site shows current v2 docs, and no OpenAI string or secrets file remains — v2 is installable, measured, documented, and cloud-free.

## Requirements

1. **R1 (CAP-1):** New user can run `setup.sh` covering Ollama install, model pull, ffmpeg check, and BlackHole guidance (PortAudio/sounddevice retired per D7-A). Success: Clean-machine run completes in ≤15 min on broadband; missing BlackHole is guidance, never a failure.
2. **R2 (CAP-2):** Builder can run the full 23-language eval harness recording per-language scores and JSON-validity per installed model. Success: Full matrix recorded in `research.md`; re-running with a new model appends a comparable row with no code changes.
3. **R3 (CAP-3):** User can install a macOS bundle that prompts for mic access with an explanatory string and runs loopback-only. Success: First Live start shows the `NSMicrophoneUsageDescription` prompt; bundle reaches only `127.0.0.1:11434` and `127.0.0.1:9001` after download.
4. **R4 (CAP-4):** Builder can run regression tests covering VAD flush paths, JSON parsing, and whisper-server health. Success: Suite passes on a clean checkout after `setup.sh`; failures name the subsystem and the retry or fix action.
5. **R5 (CAP-5):** System contains no cloud LLM surface and docs describe the true v2 run and eval commands. Success: `grep -ri openai` over product code and `secrets.toml` presence check both return empty; README/AGENTS.md document the wired run and harness commands.
6. **R6 (CAP-6):** Project documentation (run guide, eval research, architecture) is published to GitHub Pages, replacing the stub `docs/index.html` hosting experiment. Success: Push to master updates the Pages site via the existing `static.yml` workflow; the landing page reflects the current v2 README content, not the old stub.

## Constraints

- `setup.sh` owns environment (Ollama install, model pull, ffmpeg check, BlackHole guidance — PortAudio/sounddevice retired per D7-A); bundle carries `NSMicrophoneUsageDescription` (AD-13, bundle deferred to E5 per D9).
- Eval harness reuses the E1 translation service with model passed as parameter; quality variance never gates the UI (AD-6).
- After first-run download, zero outbound: loopback to `127.0.0.1:11434` and `127.0.0.1:9001` only; `langchain-openai` banned, no secrets files (AD-11).
- Latency budget <3s end-to-end per utterance at flush granularity; 5-min soak with no unbounded memory growth (NFR-1, NFR-4).
- All product code inside `text-c3po/`; OpenAI code and `secrets.toml` deleted, never merely unreferenced.
- Never commit secrets; verify by grep plus absence check in this epic.

## Done when

- From a clean machine, `setup.sh` finishes in budget, the 23-language matrix is recorded, the installed bundle prompts for mic once and runs offline on loopback only, tests pass, the Pages site shows current v2 docs, and no OpenAI string or secrets file remains — v2 is installable, measured, documented, and cloud-free.

## Boundaries

- New modes, new pickers, new translation behavior (E1–E3 own; E4 only measures and packages them).
- Token streaming, diarization, translation memory, history persistence (deferred past v1).
- Non-macOS bundles (guides welcome, untested).

## References

- parent — _bmad-output/initiative-text-c3po/initiative-text-c3po.md, section Requirements
- spec — _bmad-output/initiative-text-c3po/archive-v6/specs/spec-e4-ops-eval-polish/SPEC.md
- prd — _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
- architecture — _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
- design — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
- experience — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/EXPERIENCE.md

