---
ticket: 1
status: done
type: feature
title: "Session controller with owned caption list"
---

# Session controller with owned caption list

## Description

Add services/session as sole mutator of the ordered in-memory caption list draining the utterance queue; mode switch preserves the list while new Start or app close clears it per CAP-3.

## Verify

Mode switch away and back never clears the list; no cross-restart persistence required (memory-only).

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
