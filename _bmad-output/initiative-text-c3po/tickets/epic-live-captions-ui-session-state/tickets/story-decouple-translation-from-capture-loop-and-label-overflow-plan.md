---
ticket: 6
status: done
type: feature
title: "Decouple translation from capture loop and label overflow"
---

# Decouple translation from capture loop and label overflow

## Description

Keep the LLM drain off the capture read path so LiveRunner keeps reading frames during an in-flight translation, and surface capture overflow / dropped frames as labeled gap rows per AD-8 rather than discarding the read overflow flag per CAP-1 and NFR-1. (Done pre-D7-A against the PortAudio stream; the gap path is mechanism-agnostic and survives the ffmpeg pipe, which reports no overflow.)

## Verify

Each caption shows translated text plus timestamp in utterance-completion order; utterance-flush granularity only, no token streaming.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
