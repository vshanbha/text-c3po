---
ticket: 4
status: done
type: feature
title: "Regression tests for VAD parser and whisper health"
---

# Regression tests for VAD parser and whisper health

## Description

Add tests covering VAD silence-threshold and max-utterance flush paths, JSON parser valid-plus-malformed cases, and whisper-server health; suite passes post-setup.sh per CAP-4.

## Verify

Suite passes on a clean checkout after `setup.sh`; failures name the subsystem and the retry or fix action.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
