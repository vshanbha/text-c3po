---
ticket: 2
status: done
type: feature
title: "Captions pane with history and timestamps"
---

# Captions pane with history and timestamps

## Description

Build ui/live_view captions ListView appending rows in utterance-completion order with mono timestamps, auto-follow plus scroll-back escape and Jump-to-latest, utterance-flush only per CAP-1.

## Verify

Each caption shows translated text plus timestamp in utterance-completion order; utterance-flush granularity only, no token streaming.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
