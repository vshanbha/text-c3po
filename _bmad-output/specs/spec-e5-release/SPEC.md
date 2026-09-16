---
id: SPEC-e5-release
companions:
  - ../../planning-artifacts/architecture/architecture-text-c3po-2026-09-08/ARCHITECTURE-SPINE.md
  - ../../planning-artifacts/ux-designs/ux-text-c3po-2026-09-08/EXPERIENCE.md
sources:
  - ../../planning-artifacts/prds/prd-text-c3po-2026-09-08/prd.md
  - ../../../../blueprint.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# E5 — General Release Readiness

## Why

text-c3po v2 is an open-source side project: run-from-source via setup.sh
is the distribution model and nothing requires an installable artifact.
E5 opens only on an explicit owner decision to release for general use.
It holds the packaging story moved out of E4 (D9, 2026-09-16) plus any
future release work; E1–E4 stay side-project scope and never absorb it.

## Capabilities

- **CAP-1**
  - **intent:** Owner can produce an installable macOS bundle that prompts
    for mic access on first Live start.
  - **success:** `flet build macos` bundle carries
    NSMicrophoneUsageDescription; first Live start shows the TCC prompt;
    denial yields the clean F8 failure; bundle runs loopback-only after
    download; Gatekeeper copy path documented for another Mac.

## Constraints

- Ad-hoc local bundle only per D5-A (no sign/notarize); revisiting D5 is
  an E5 decision, not an E4 one.
- Bundle runs loopback-only to 127.0.0.1:11434 and 127.0.0.1:9001 after
  download (AD-11 holds in the bundle).
- Manual session per TEST-PLAN section H; needs Xcode, a signing
  identity for distribution (ad-hoc suffices locally), and the
  interactive Flutter SDK install.

## Non-goals

- Notarization, auto-update, Linux/Windows packaging (welcome, untested).
- Any product behavior change — E5 ships what E1–E4 built.

## Success signal

TEST-PLAN section H runs green on a second Mac from a copied bundle.

## Assumptions

- Apple Developer context exists when distribution (not just local use)
  is wanted; otherwise ad-hoc per D5-A.

## Open Questions

- None. E5 scope grows only by owner decision at release time.
