---
ticket: 7
status: done
type: feature
title: "Fix unit CI and repair sprint tracking"
---

# Fix unit CI and repair sprint tracking

## Description

Make the web-serve smoke runnable where uv is absent (invoke the test interpreter directly, install uv, or skip explicitly) and stop masking the empty-collection exit code, so the master unit run is green again; reconcile stories.yaml with sprint-status.yaml and track the Pages story.

## Verify

Make the web-serve smoke runnable where uv is absent (invoke the test interpreter directly, install uv, or skip explicitly) and stop masking the empty-collection exit code, so the master unit run is green again; reconcile stories.yaml with sprint-status.yaml and track the Pages story..

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
