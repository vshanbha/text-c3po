---
ticket: 7
status: done
type: feature
title: "Fix session queue and seq races on start and gap"
---

# Fix session queue and seq races on start and gap

## Description

Assign the mark_gap sequence number and append the caption under one lock acquisition so an interleaved drain cannot reorder rows, and stop start_session silently discarding queued utterances — label them as a gap per AD-8 instead per CAP-3.

## Verify

Mode switch away and back never clears the list; no cross-restart persistence required (memory-only).

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
