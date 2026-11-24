---
ticket: 1
status: done
type: feature
title: "Sounddevice device enumeration and picker source"
---

# Sounddevice device enumeration and picker source

## Description

Add runtimes/audio_devices querying sounddevice each launch with no hard-coded names; expose the list for the E3 device picker with BlackHole present-only per CAP-1. Historical (done pre-D7-A): superseded by story 5, which reimplements enumeration on ffmpeg.

## Verify

With BlackHole absent the picker lists remaining devices and live capture still starts on mic; no hard-coded device names.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
