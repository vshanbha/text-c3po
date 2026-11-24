---
ticket: 4
status: done
type: feature
title: "File decode path into the shared ASR entry point"
---

# File decode path into the shared ASR entry point

## Description

Add ffmpeg decode feeding picked audio/video files into the same ASR entry point as live utterances with readable pre-ASR errors for unsupported containers; works with no device and BlackHole absent per CAP-4.

## Verify

File path works with BlackHole absent and no device selected; unsupported containers error readably before any ASR call.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
