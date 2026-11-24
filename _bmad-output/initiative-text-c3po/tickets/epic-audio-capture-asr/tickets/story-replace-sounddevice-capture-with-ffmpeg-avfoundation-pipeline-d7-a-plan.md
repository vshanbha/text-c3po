---
ticket: 5
status: in-review
type: feature
title: "Replace sounddevice capture with ffmpeg avfoundation pipeline (D7-A)"
---

# Replace sounddevice capture with ffmpeg avfoundation pipeline (D7-A)

## Description

Rewrite runtimes/audio_devices to enumerate via ffmpeg -f avfoundation -list_devices, and services/live_runner.open_input_stream to spawn ffmpeg -f avfoundation -i ':DEVICE' -ac 1 -ar 16000 -f s16le - piped to the VAD; remove sounddevice from pyproject/requirements/lock and PortAudio from setup.sh; amend AD-9/AD-13/tech-lock; rewrite affected unit tests; verify TEST-PLAN F7 (BlackHole loopback) and F14 (unplug).

## Verify

Rewrite runtimes/audio_devices to enumerate via ffmpeg -f avfoundation -list_devices, and services/live_runner.open_input_stream to spawn ffmpeg -f avfoundation -i ':DEVICE' -ac 1 -ar 16000 -f s16le - piped to the VAD; remove sounddevice from pyproject/requirements/lock and PortAudio from setup.sh; amend AD-9/AD-13/tech-lock; rewrite affected unit tests; verify TEST-PLAN F7 (BlackHole loopback) and F14 (unplug)..

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `review` at migration time, mapped to `in-review`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
