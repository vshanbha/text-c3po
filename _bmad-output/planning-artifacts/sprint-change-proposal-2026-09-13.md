---
date: 2026-09-13
type: sprint-change-proposal
trigger: 2026-09-13 spec/code audit of text-c3po v2
status: approved 2026-09-13 — all D1-D6 decided by owner, recorded to owning memlogs
owner: vshanbha
decided: 2026-09-13
decisions:
  D1: A — ratify commentary cut (fix docs only)
  D2: A — relabel/remove source picker to Auto-detect (v1)
  D3: B — build real main-thread render pump (overrides recommendation A)
  D4: A — keep global Stop abort (overrides recommendation B, intentional)
  D5: A — ad-hoc local bundle only
  D6: B — track uv.lock
epics_impacted: [E1, E2, E3, E4]
artifacts_impacted: [spec-e1-shell-core, spec-e2-audio-asr, spec-e3-live-ui, spec-e4-ops-eval-polish, ARCHITECTURE-SPINE, PRD, DESIGN, EXPERIENCE, TEST-PLAN]
mode: batch
---

# Sprint Change Proposal — text-c3po v2 (2026-09-13)

Produced by the `bmad-correct-course` flow from the 2026-09-13 spec/code
audit. This proposal covers **Set 3**: the findings that cannot be built
until a human makes a scope/architecture/UX/behavior decision. Set 1
(automation-unreachable verification) is drafted in `TEST-PLAN.md` §J; Set 2
(non-decision remediation) is drafted as stories E3-5–E3-7 and E4-7–E4-8 and
tracked `backlog` in `sprint-status.yaml`. **This proposal requires explicit
approval (bmad-correct-course step 5) before any decision is implemented.**

## Section 1 — Issue Summary

**Trigger.** A full review after the BMAD flow reached an apparently finished
app: E1–E3 `done`, E4 `in-progress` with only packaging backlog. Re-auditing
the code against the SPECs and ARCHITECTURE-SPINE (plus a live browser E2E)
found the planning and the implementation partially diverged, and surfaced
five decisions that were assumed rather than made.

**Problem statement (precise).** Several capabilities were implemented with a
different contract than the specs record, or with a design tolerance that was
never ratified. Each has a defensible option on both sides, so choosing
silently would create exactly the "silent drift" the 2026-09-09 UX as-built
review called unacceptable. They must be decided, recorded, and then built.

**Evidence.**
- `commentary` is absent from code (`grep -rin commentary src/` = 0) while
  `README.md:4` and `spec-e1-shell-core/SPEC.md:29-30` still promise it; the
  E1 retro (2026-09-09) records a "CAP-3 ruling" cutting it.
- The Live/File source-language dropdown is inert: whisper is spawned once as
  `-l auto` (`app.py:277`, `process_manager.py:150`), `transcribe_wav` sends no
  language, and File mode's source value is never read (`app.py:600-612`).
- AD-4 is a documented deviation, not met: multiple background threads mutate
  Flet controls and call `page.update()` (`app.py:460-499`, `:743-763`,
  `:851-882`, `:1076-1124`); E3 retro F4 records the tolerance.
- `on_stop_translate` calls `cancel_inflight()` (`app.py:558`), which aborts
  **every** registered stream/HTTP client, not just the Text request.
- Packaging (`SPEC-e4` CAP-3 / AD-13) has no bundle; distribution scope
  (ad-hoc vs signed/notarized) is undefined and notarization is unmentioned.
- `uv.lock` is gitignored while `[project]` exists, with a now-false rationale.

## Section 2 — Impact Analysis

**Epic impact.**
- **E1** — CAP-3/AD-5 contract text vs implementation (commentary).
- **E2** — source-language choice never reaches whisper (CAP-3 boundary).
- **E3** — Live/File source picker UX (CAP-4), AD-4 tolerance; Stop scope.
- **E4** — packaging/distribution (CAP-3), CI/tracking/docs hygiene, lockfile.

**Artifact conflicts.** `spec-e1-shell-core/SPEC.md` (CAP-3, Success signal),
`spec-e2-audio-asr/SPEC.md` (CAP-3), `spec-e3-live-ui/SPEC.md` (CAP-4,
Assumptions/Open Questions Q3), `ARCHITECTURE-SPINE.md` (AD-4, AD-10, AD-13),
PRD Q3 (live source default), `DESIGN.md`/`EXPERIENCE.md` (commentary,
source picker, status behavior), `README.md`, `TEST-PLAN.md`.

**Technical impact.** D2 touches `runtimes/process_manager`, `whisper_client`,
`services/asr`, `services/live_runner`, `app.py`, `ui/language_pickers`.
D3 touches `app.py` threading/render surface. D4 touches
`services/translation.cancel_inflight` and its callers. D5 adds build infra
outside source. D6 changes install reproducibility only.

**No rollback, no MVP reduction required.** All options are forward
adjustments; nothing completed needs reverting.

## Section 3 — Recommended Approach

**Option 1: Direct Adjustment (recommended).** No completed work is
invalidated; the decisions either (a) ratify what was built and update the
specs/README to match, or (b) add small, well-scoped stories. Effort: Low–Medium
per item; risk: Low. Option 2 (rollback) is not viable — nothing is blocking.
Option 3 (MVP review) is unnecessary — these are contract-tightening, not
scope-destroying.

Approved decisions become stories (Set-2 mechanism: owning SPEC `stories.yaml`
+ `.memlog.md`, then `bmad-sprint-planning` refresh of `sprint-status.yaml`).

## Section 4 — Detailed Change Proposals

### D1 — `commentary` contract: ratify the cut vs restore the field
- **Affected:** E1 CAP-3, AD-5, `README.md:4`, `spec-e1-shell-core/SPEC.md:29-30,61`.
- **Options.**
  - **A (recommended) — ratify the 2026-09-09 CAP-3 cut.** Schema stays
    `formal / informal / origin_language`; update README and E1 SPEC Success
    signal to match; log the ruling to `spec-e1-shell-core/.memlog.md`.
    Effort Low, risk Low.
  - **B — restore commentary.** Add the field back to `services/translation`
    schema, `_normalize`, and the Text UI; re-run the E1 gate. Effort Medium,
    risk Medium (re-opens a passed epic; commentary quality was the reason for
    the cut).
- **Rationale:** the operator already ruled (E1 retro, "CAP-3 ruling"); the
  only defect is documentation drift. B re-adds scope without new evidence.

### D2 — Live/File source-language picker
- **Affected:** E3 CAP-4, E2 CAP-3, AD-10, PRD Q3, `ui/language_pickers.py`, `app.py`.
- **Options.**
  - **A (recommended for v1) — remove/relabel.** Drop the source dropdown from
    Live and File, or mark it read-only "Auto-detect"; the honest UI matches
    `-l auto` behavior. Effort Low, risk Low.
  - **B — make it functional via whisper.** Pass the source code to
    `ProcessManager` and restart whisper on change; requires a restart policy
    and gap handling mid-session. Effort Medium–High, risk Medium.
  - **C — translation-prompt hint only.** Send the source as context to the
    LLM without touching ASR; cheap but does not change transcription, so the
    UI would still over-promise. Effort Low, risk Low.
- **Rationale:** B is the only option that truly delivers per-language ASR;
  choose it only if multi-language accuracy is a v1 goal. Otherwise A removes
  the false affordance. Decide: is explicit source-language ASR control in v1?

### D3 — AD-4 UI-thread confinement
- **Affected:** AD-4, `app.py` render paths, E3 retro F4.
- **Options.**
  - **A (recommended) — ratify the deviation.** Update AD-4 to the shipped
    "single render function, pipeline threads post dicts" tolerance; the
    Set-2 E3-6 decoupling shrinks the concurrency surface anyway. Effort Low
    (doc + E3-6), risk Low.
  - **B — implement a real main-thread render pump.** Serialize all UI
    mutation through one queue/pump. Effort Medium–High, risk Medium.
- **Rationale:** the deviation has shipped without observed corruption across
  three epics; E3-6 removes the worst blocking case. Revisit B only if F5/F1
  manual checks show flicker or lost rows.

### D4 — Stop scope in Text mode
- **Affected:** `services/translation.cancel_inflight`, `app.py:542-563`,
  E3/F10 caption retry, file mode.
- **Options.**
  - **A — keep global abort** (one Stop cancels any in-flight LLM request).
  - **B (recommended) — scope Stop to Text mode**, letting concurrent File or
    caption-retry work finish; a global abort should be explicit.
- **Rationale:** least surprise; mode controls should act on their own mode.
  Decide which behavior is intended.

### D5 — macOS distribution scope
- **Affected:** E4 CAP-3, AD-13, TEST-PLAN §H P5.
- **Options.**
  - **A (recommended for v1) — ad-hoc local bundle only.** Document the
    Gatekeeper path for copying to another Mac; no notarization. Effort Low.
  - **B — sign + notarize** for frictionless distribution; requires an Apple
    Developer Program identity and CI/manual notarization. Effort Medium.
- **Rationale:** the blueprint scopes v2 to a local-first personal tool; pick
  B only if the bundle is meant to be distributed externally.

### D6 — `uv.lock`
- **Affected:** `.gitignore`, install reproducibility, `setup.sh`.
- **Options.**
  - **A — keep gitignored** (current).
  - **B (recommended) — track `uv.lock`** so `uv sync` is reproducible on a
    clean machine; remove the stale rationale comment. Effort Low.
- **Rationale:** reproducibility is a stated clean-machine goal; the lock is
  already generated.

### Decision register (approve / edit / skip each)

| ID | Decision to make | Recommendation | Proposed downstream story |
|----|------------------|----------------|---------------------------|
| D1 | commentary: ratify cut or restore | A — ratify, fix docs | E1 memlog re-derive + docs (E4-8 if ratify) |
| D2 | Source picker: functional / relabel / remove | A — relabel/remove (B if v1) | New E3 story (after choice) |
| D3 | AD-4: ratify deviation or build pump | A — ratify + E3-6 | E3-6 + spine update |
| D4 | Stop scope: global or per-mode | B — per-mode | New E3 story |
| D5 | Distribution: ad-hoc or notarized | A — ad-hoc | E4-3 invoke note |
| D6 | uv.lock: ignore or track | B — track | E4-8 (infra) |

## Section 5 — Implementation Handoff

- **Scope classification:** **Moderate** overall — backlog additions across
  E3/E4 and one spine/spec doc reconciliation; no fundamental replan.
- **Minor items** (Developer agent, direct): D1 doc reconciliation, D3 spine
  note, D5 TEST-PLAN note, D6 lockfile.
- **Decision-dependent items** (Developer agent after your choice): D2 and D4
  become E3 stories; D5 may expand E4-3.
- **PM/Architect** sign-off only if D2=B (new ASR restart policy) or D5=B
  (signing/notarization).
- **Spec ownership rule:** SPEC.md is derived by `bmad-spec`; decisions are
  first appended to the owning `.memlog.md`, then re-derived — never hand-edit
  SPEC.md.
- **Tracking:** after approval, run `bmad-sprint-planning` to validate
  `sprint-status.yaml`; the already-drafted backlog keys (E3-5–E3-7, E4-7–E4-8)
  are present.
- **Success criteria:** every decision above is recorded in the owning memlog
  and reflected in the SPEC/README/spine; approved changes have stories; CI is
  green; `TEST-PLAN.md` §J is executed before v2 is declared shippable.

## Post-approval next steps (decided 2026-09-13)

Decisions recorded — ready to fold into stories + memlogs, then build.

1. [x] Mark each register row approve/edit/skip — DONE, see `decided` frontmatter:
   D1=A, D2=A, D3=B (override), D4=A (override, keep global), D5=A, D6=B (track).
2. Fold approved decisions into the owning `stories.yaml` + `.memlog.md`.
3. Run `bmad-sprint-planning` to refresh tracking.
4. Dispatch Set-2 stories with `bmad-build`; then run `TEST-PLAN.md` §J.

## Approval record (2026-09-13, owner vshanbha)

- D1 A — ratify commentary cut. Rationale accepted: operator already ruled 2026-09-09; docs-only fix.
- D2 A — source picker relabel/remove to Auto-detect for v1. Functional whisper restart deferred out of v1.
- D3 B — build real main-thread render pump. Owner overrides recommendation A (ratify): prefers correctness over low-effort tolerance despite medium-high cost. E3-6 still lands first to shrink surface, then pump.
- D4 A — keep global Stop abort. Owner overrides recommendation B (per-mode): one Stop cancels any in-flight LLM request, including File/caption-retry. Document as intended behavior.
- D5 A — ad-hoc local bundle only. No notarization; document Gatekeeper copy path.
- D6 B — track uv.lock. .gitignore rationale ("no [project] table") is stale — [project] exists since E1 hardening; uv.lock (288KB) exists locally untracked. Standard for apps: commit for reproducible clean-machine installs.

## Post-approval next steps (original)

1. Mark each register row approve/edit/skip (or reply with the D-IDs and
   choices).
2. Fold approved decisions into the owning `stories.yaml` + `.memlog.md`.
3. Run `bmad-sprint-planning` to refresh tracking.
4. Dispatch Set-2 stories with `bmad-build`; then run `TEST-PLAN.md` §J.
