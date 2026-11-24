---
ticket: 3
status: done
type: feature
title: "Start-Stop toggle with live status indicators"
---

# Start-Stop toggle with live status indicators

## Description

Wire the Start/Stop FilledButton (label is the state) with capture, whisper-latency, and model dot-plus-label indicators reflecting live state; Stop halts capture within 2s and restart needs no relaunch per CAP-2.

## Verify

Stop halts capture within 2s; restart begins a new session without relaunch; indicators reflect live subprocess/model state, not cached values.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
