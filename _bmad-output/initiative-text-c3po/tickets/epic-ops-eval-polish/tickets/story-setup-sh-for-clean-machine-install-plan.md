---
ticket: 1
status: done
type: feature
title: "setup.sh for clean-machine install"
---

# setup.sh for clean-machine install

## Description

Add setup.sh covering Ollama install, model pull, ffmpeg check, and BlackHole guidance; clean-machine run completes in <=15 min with missing BlackHole as guidance per CAP-1.

## Verify

Clean-machine run completes in ≤15 min on broadband; missing BlackHole is guidance, never a failure.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
