---
type: epic
title: "General Release Readiness"
parent: initiative-text-c3po
covers: [R15]
sources:
  - _bmad-output/initiative-text-c3po/archive-v6/specs/spec-e5-release/SPEC.md
  - _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
companions:
  - _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
  - _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
risk: medium
---

# General Release Readiness

## Description

text-c3po v2 is an open-source side project: run-from-source via setup.sh is the distribution model and nothing requires an installable artifact. E5 opens only on an explicit owner decision to release for general use. It holds the packaging story moved out of E4 (D9, 2026-09-16) plus any future release work; E1–E4 stay side-project scope and never absorb it.

## Outcome

TEST-PLAN section H runs green on a second Mac from a copied bundle.

## Requirements

1. **R1 (CAP-1):** Owner can produce an installable macOS bundle that prompts for mic access on first Live start. Success: `flet build macos` bundle carries NSMicrophoneUsageDescription; first Live start shows the TCC prompt; denial yields the clean F8 failure; bundle runs loopback-only after download; Gatekeeper copy path documented for another Mac.

## Constraints

- Ad-hoc local bundle only per D5-A (no sign/notarize); revisiting D5 is
- Bundle runs loopback-only to 127.0.0.1:11434 and 127.0.0.1:9001 after
- Manual session per TEST-PLAN section H; needs Xcode, a signing

## Done when

- TEST-PLAN section H runs green on a second Mac from a copied bundle.

## Boundaries

- Notarization, auto-update, Linux/Windows packaging (welcome, untested).
- Any product behavior change — E5 ships what E1–E4 built.

## References

- parent — _bmad-output/initiative-text-c3po/initiative-text-c3po.md, section Requirements
- spec — _bmad-output/initiative-text-c3po/archive-v6/specs/spec-e5-release/SPEC.md
- prd — _bmad-output/initiative-text-c3po/prd-text-c3po-2026-09-08/prd-text-c3po-2026-09-08.md
- architecture — _bmad-output/initiative-text-c3po/architecture-text-c3po-2026-09-08/architecture-text-c3po-2026-09-08.md
- design — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/DESIGN.md
- experience — _bmad-output/initiative-text-c3po/ux-text-c3po-2026-09-08/EXPERIENCE.md

