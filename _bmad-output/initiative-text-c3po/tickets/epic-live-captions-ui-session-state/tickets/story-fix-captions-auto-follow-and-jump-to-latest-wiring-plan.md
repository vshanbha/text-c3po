---
ticket: 5
status: done
type: feature
title: "Fix captions auto-follow and Jump-to-latest wiring"
---

# Fix captions auto-follow and Jump-to-latest wiring

## Description

Forward the ListView scroll event from feed.on_scroll into on_pane_scroll so _is_user_scroll can distinguish ScrollType.USER from programmatic auto-scrolls; follow disables only on a genuine user scroll and Jump-to-latest re-enables it per CAP-1.

## Verify

Each caption shows translated text plus timestamp in utterance-completion order; utterance-flush granularity only, no token streaming.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
