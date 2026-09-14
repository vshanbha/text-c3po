---
id: SPEC-e5-translation-quality
companions: []
sources:
  - ../../planning-artifacts/prds/prd-text-c3po-2026-09-08/prd.md
  - ../../../../blueprint.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# E5 — Translation Quality Evals

## Why

The eval harness gates JSON contract conformance only: lfm2.5 scored 100% while echoing Kannada in English, and a one-sentence collapse of a ten-paragraph Spanish translation passes as valid. Contract proof keeps the UI crash-free but says nothing about meaning, so model choice (lfm2.5 vs gemma4:e4b-mlx, 23/23 on the capability survey) currently rests on eyeball spot-checks. E5 adds meaning-level measurement with public open-source benches so the max-languages answer is scored, not felt.

## Capabilities

- **CAP-1**
  - **intent:** Operator can score any installed model on FLORES-200 devtest references with sacrebleu chrF++ per language.
  - **success:** One command runs EN→{es,pt,de,fr,hi,kn,mr} (subset-flagged for more) and appends a per-language chrF++ table to research.md; reruns are comparable sentence-for-sentence.
- **CAP-2**
  - **intent:** Operator can score arbitrary source-hypothesis pairs with a local reference-free QE model (COMETKIWI family).
  - **success:** A source sentence plus a model hypothesis yields a quality score with no reference text and no network beyond the first weights download.

## Constraints

- Local-first holds: datasets and metric weights download once, then loopback-only; no cloud judge APIs ever (AD-11).
- Serial single-request LLM discipline and manual-only execution (never CI) extend to every E5 run; gate math and gate table shape stay untouched (AD-6).
- lfm2.5-first evidence; memory hogs (gemma4:e4b-mlx) manual-only by owner override (2026-09-14).
- All product code inside `src/text_c3po/`; E5 reuses `services.translate_text` as the only LLM entry point.

## Non-goals

- Cross-model LLM judging (lfm output scored by gemma and vice versa): aspirational, deferred — revisit when a regression-grade need (e.g. model-upgrade comparison) justifies the 2× serial call cost and the who-judges-the-judge circularity.
- Human-eval operations (XSTS/MQM panels); TEST-PLAN §B rows remain the sampled ground truth.
- Any change to the E1/E4 gate contract, the 23-language picker, or translation prompting.

## Success signal

An operator picks two installed models, runs the E5 commands, and reads which renders more languages better from research.md — deterministically for bench sentences (CAP-1), scored for arbitrary text (CAP-2) — with zero outbound traffic after setup.

## Assumptions

- FLORES-200 covers kn/mr/es/pt/hi/de under CC-BY-SA and sacrebleu plus COMETKIWI weights are pip/HF-installable — verify at build.

## Open Questions

- FLORES devtest is 1012 sentences per language — what sample size per language keeps local Ollama runs tractable?
- COMETKIWI needs torch — accept the heavy dep or prefer the deferred gemma-as-judge instead?
