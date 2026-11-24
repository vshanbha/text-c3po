---
type: migration
title: Move v6 planning and implementation artifacts into the v7 initiative layout
status: done
created: 2026-11-24
---

# Migration plan and verification record — text-c3po

Method migration `migration-1.toml` (method module, from `6` to `7`), executed
2026-11-24 under owner-authorized Option C.

## Backup

`.v6-v7-migration-backup-20261124-1835/` at the project root, holding a full copy
of `_bmad/` (58/58 files) and the whole output folder (59/59 files), with a
`.gitignore` holding `*` so it is never committed. Verified complete before any
move was made. It is the owner's to delete once satisfied.

## Questions and answers

| Question | Answer | Reason |
|---|---|---|
| Your planning content is `_bmad-output/planning-artifacts` and your implementation content is `_bmad-output/implementation-artifacts`. Right, and is there any elsewhere? | Yes; none elsewhere | Both folders named in `modules.bmm.*` were present and held every source file; no third location exists. |
| Will this work touch other repositories, or should the planning files keep their own git history apart from the code? (`workspace`) | No | Default. Everything stays in the single project repository; no store repository or workspace was created. |
| Stories in progress or in review — finish them in v6 first? | Migrate now | Owner pre-authorized the migration. In-flight statuses are carried across unchanged (see status map below). |
| Fold unstarted stories' files into their entries? | Yes (default) | Applied; unstarted stories have no build record to fold. |

Status map applied: `backlog` → entry only; `ready-for-dev`/`drafted`/`contexted`
→ `ready-for-dev`; `in-progress` → `in-progress`; `review`/`in-review` →
`in-review`; `done` → `done`; `blocked` → `blocked`.

## Inventory — what moved where

59 tracked files in the output folder before the move: **57 renamed, 2 left in
place, 0 deleted.**

- `planning-artifacts/` → `initiative-text-c3po/` (folder renamed).
- Grouping folders flattened to the initiative root: `prds/`, `briefs/`,
  `architecture/`, `ux-designs/`, `research/`. Each run folder kept its v6 name.
- Main files renamed to match their folder: `prd.md` →
  `prd-text-c3po-2026-09-08.md`, `brief.md` → `brief-text-c3po-2026-09-08.md`,
  `ARCHITECTURE-SPINE.md` → `architecture-text-c3po-2026-09-08.md`, and
  `research.md` → the folder name in both `technical-*` run folders.
- Routers written for folders with no single main file:
  `ux-text-c3po-2026-09-08/`, `ux-20261101-001/`, `quality-eval-2026-11-23/`.
- `implementation-artifacts/sprint-status.yaml` and
  `implementation-artifacts/epic-1-retro-2026-09-09.md` → `archive-v6/`.
  `epic-1-retro-2026-09-09.md` was a byte-identical mirror of
  `spec-e1-shell-core/RETROSPECTIVE.md`, so the epic retro is stored once.
- `epics.md` → `archive-v6/`.
- Each converted SPEC: `SPEC.md`, `stories.yaml`, `.memlog.md` →
  `archive-v6/specs/<slug>/` (grouped by folder name to keep six identically
  named `SPEC.md` files apart; contents unchanged).
- Each spec `RETROSPECTIVE.md` → `tickets/epic-<slug>/epic-<slug>-retrospective.md`.
- Eight story build records → `tickets/epic-<slug>/tickets/story-<slug>-plan.md`.
- `specs/spec-e5-translation-quality/` (no `stories.yaml`) → moved into the
  initiative as a document, not converted to an epic.

New files: the initiative envelope, `tickets/tickets.toml`, five epic envelopes,
five epic `tickets.toml`, 23 minimal plans, three routers, two `.gitkeep`.

## Coverage map (PRD requirement → epic capability → entries)

The PRD carries no written coverage map; this is the map the migration built from
the PRD sections, the SPEC capability lists and the `CAP-` references in each
story. Every FR reaches at least one entry.

| FR | Initiative R | Realised by | Entries |
|---|---|---|---|
| FR-1 | R1 | e1 CAP-1 | 1.1, 1.2 |
| FR-2 | R2 | e1 CAP-2 | 1.4 |
| FR-3 | R3 | e1 CAP-3 | 1.6 |
| FR-4 | R4 | e1 CAP-4 | 1.5 |
| FR-5 | R5 | e1 CAP-5 | 1.3 |
| FR-6 | R6 | e2 CAP-1 | 2.1 |
| FR-7 | R7 | e2 CAP-2 | 2.2 |
| FR-8 | R8 | e2 CAP-3 | 2.3 |
| FR-9 | R9 | e2 CAP-4 | 2.4 |
| FR-10 | R10 | e3 CAP-1 | 3.2, 3.5, 3.6 |
| FR-11 | R11 | e3 CAP-2 | 3.3 |
| FR-12 | R12 | e3 CAP-3 | 3.1, 3.4, 3.7 |
| FR-13 | R13 | e4 CAP-1 | 4.1 |
| FR-14 | R14 | e1 CAP-6 **and** e4 CAP-2 | 1.7, 4.2 |
| FR-15 | R15 | e5 CAP-1 | 5.1 |
| FR-16 | R16 | e4 CAP-5 | 4.5 |

`FR-14` is split across two epics: E1 story 1.7 builds the 5x5 exit gate, E4
story 4.2 extends it to the full 23-language matrix. `FR-15` moved from E4 to E5
per decision D9 (2026-09-16), so epic 4 covers `R13, R14, R16` and epic 5
covers `R15`. Epic requirements are the SPEC `CAP-` lines; story `covers` cites
the epic-local R id of the CAP its text names.

## Checklist results

1. **Every file from the v6 source folders is under an initiative, `backlog/`,
   or `archive/`, or listed as left in place** — pass. 57 renamed, 2 left in
   place (below), 0 deleted.
2. **Every moved document folder kept its v6 name and every file, and holds a
   main file named after the folder or a router; `initiative-<slug>/`,
   `backlog/` and `archive/` exist with `.gitkeep` when empty** — pass.
3. **Dated or numbered versions of one document are all present** — pass. All
   three `sprint-change-proposal-*` files, both `technical-*` runs and the
   `quality-eval-*` run are present under their own names.
4. **`tickets.py status <initiative folder>` exits 0 and story counts match the
   archived tracking sources** — pass. `total 38, done 29, review 2, planned 7`;
   sprint-status.yaml holds 38 story keys (29 `done`, 2 `review`, 7 `backlog`),
   excluding epic and retrospective keys. `order_conflict`, `undeclared_after`
   and `unpinned_after` are all empty.
5. **Every classic or spec story is one entry with one plan; no epic story files
   were written** — pass. 38 entries; 31 plans (8 moved build records + 23
   minimal); no `epic-*-story-*.md` files exist.
6. **Every plan has a build type and a mapped status; done stays done, review
   stays in-review; baselines kept where supported and missing ones disclosed;
   retrospectives sit directly in their epic with an evidenced verdict and no
   ticket or leaf type** — pass. Statuses carried from sprint-status.yaml.
   **23 plans have no baseline** (they have no v6 build record) — disclosed in
   the report below. Four retrospectives sit in their epic folders with their
   original `verdict: accepted-with-open-items` frontmatter.
7. **Every epic `covers` id is a line in the initiative's Requirements, every
   entry `covers` id one in its epic's Requirements, and every requirement in
   the PRD's coverage map has at least one entry** — pass, per the coverage map
   above.
8. **No pre-release `spec-<slug>/spec-<slug>.md` folder remains** — pass.
   None existed in this project, so `--fold-specs` was not run.
9. **Every live path in `sources:`, `companions:`, References sections and
   prose links resolves; a path already dead in v6 is listed apart** — pass.
   127 references checked, 1 unresolved: `_bmad-output/.../ARCHITECTURE-SPINE.md`
   in the story 3.9 plan. That literal ellipsis was already unresolvable in v6
   (original wording, unchanged by this migration), so it does not fail this item.
10. **`_bmad/custom/config.user.toml` names the active initiative under `[core]`,
    and `core.output_folder` resolves to the store** — pass.
11. **Every module config key whose folder moved names its new location** —
    pass. `modules.bmm.planning_artifacts` and `implementation_artifacts` are
    left untouched: `bmad setup` owns `_bmad/`, and the migration reads those
    keys rather than rewriting them.
12. **The store is under git, no file is tracked by two repositories** — pass.
    Single project repository; no workspace or store repository was created.
13. **The backup holds every source file and no commit includes it** — pass.
    58/58 `_bmad` files, 59/59 output files, `.gitignore` holding `*`.
14. **The plan records every question, its answer and reason, the backup path,
    every identified file and each item's result** — pass (this document).

## Left in place, with the reason

- `brainstorming/brainstorm-blackhole-call-capture-failure-2026-09-15/` — a
  brainstorming session, which the migration lists under "What stays in place";
  the plan does not assign it to the initiative.
- `specs/spec-e5-translation-quality/` — moved into the initiative as a document
  rather than an epic: it has no `stories.yaml` and no matching `## Epic N:` in
  epics.md, so there is no entry set to convert it into. It is the one v6
  artifact converted to a document instead of a ticket tree.

## Missing baseline revisions (disclosed)

23 plans carry no `baseline_revision` because no v6 build record exists for
them; the migration never infers a baseline from HEAD.

- `epic-audio-capture-asr`: entries 1, 2, 3, 4, 5
- `epic-live-captions-ui-session-state`: entries 1-8, 10
- `epic-ops-eval-polish`: entries 1, 2, 4, 5, 6, 7, 8, 9, 10

The eight plans that do have records carry
`baseline_revision: e70869cfd7da94f8f70a146ae0cc0a3dc32e8129`, the value their
v6 records held.
