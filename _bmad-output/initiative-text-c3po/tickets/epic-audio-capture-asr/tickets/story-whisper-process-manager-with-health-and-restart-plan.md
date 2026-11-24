---
ticket: 3
status: done
type: feature
title: "Whisper process manager with health and restart"
---

# Whisper process manager with health and restart

## Description

Add runtimes/process_manager plus runtimes/whisper_client owning spawn (ggml-small.bin default), readiness check, restart-on-crash with visible status, and cleanup-on-exit; transcribe-only on 127.0.0.1:9001 per CAP-3.

## Verify

Readiness check passes within ~5s of launch; killing the subprocess triggers a restart attempt with visible status; app exit leaves no orphan process.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
