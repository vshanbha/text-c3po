---
ticket: 9
status: in-review
type: feature
title: "File logging with rotation and per-module diagnostics"
---

# File logging with rotation and per-module diagnostics

## Description

Give the packaged app a persistent log: _configure_logging keeps the console handler and adds a stdlib RotatingFileHandler at ~/Library/Logs/text-c3po/text-c3po.log (1 MB x 3, TEXT_C3PO_LOG path override, console-only fallback when the dir is unwritable). Wire per-module loggers into the silent zones the 2026-09 audit ranked: process_manager spawn/ready/stop/restart reasons, whisper_client transport cause, asr decode/transcribe causes, live_runner stream-end and transcribe-failure causes, audio_devices enumeration failure, ollama_client probe reason, and the app.py whisper boot thread; gate the translate parse-failure raw-payload dump so translated content never reaches the file log; never log audio bytes or transcripts; keep TEST-PLAN translate_text ok and done_reason lines at their current levels and add a log-file cross-check row per CAP.

## Verify

Give the packaged app a persistent log: _configure_logging keeps the console handler and adds a stdlib RotatingFileHandler at ~/Library/Logs/text-c3po/text-c3po.log (1 MB x 3, TEXT_C3PO_LOG path override, console-only fallback when the dir is unwritable).

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `review` at migration time, mapped to `in-review`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
