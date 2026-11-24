---
ticket: 4
status: done
type: feature
title: "Live pickers, file surface, and session-state polish"
---

# Live pickers, file surface, and session-state polish

## Description

Bind device, source, and target Dropdowns to the E2 enumeration and the 23-language constant with auto-detect-where-supported source default; compose the file surface (picker row, progress, results list reusing the caption-row pattern) on the E2 decode path; verify mode-switch retention and memory-only session labeling per CAP-4 and CAP-3.

## Verify

Mode switch away and back never clears the list; no cross-restart persistence required (memory-only).

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
