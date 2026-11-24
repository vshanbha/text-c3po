---
ticket: 2
status: done
type: feature
title: "Port VAD chunker with unit tests"
---

# Port VAD chunker with unit tests

## Description

Add services/vad re-implementing the PoC RMS-silence plus flush-on-2-silent-frames-or-max-utterance logic emitting immutable 16 kHz mono s16le utterance bytes; cover both flush paths with unit tests per CAP-2.

## Verify

Continuous speech yields ≥1 utterance per sentence cluster, 2s silence forces a flush; unit tests cover silence-threshold and max-utterance paths.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
