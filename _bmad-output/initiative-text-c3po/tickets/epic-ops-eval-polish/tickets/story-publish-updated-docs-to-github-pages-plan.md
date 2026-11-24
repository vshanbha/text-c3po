---
ticket: 6
status: done
type: feature
title: "Publish updated docs to GitHub Pages"
---

# Publish updated docs to GitHub Pages

## Description

Replace the stub docs/index.html hosting experiment with a real docs landing page reflecting current v2 content (run guide, eval research, architecture); push to master updates the site via the existing static.yml Pages workflow per CAP-6.

## Verify

Push to master updates the Pages site via the existing `static.yml` workflow; the landing page reflects the current v2 README content, not the old stub.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
