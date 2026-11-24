---
ticket: 5
status: done
type: feature
title: "Remove cloud surface and refresh docs"
---

# Remove cloud surface and refresh docs

## Description

Delete all langchain-openai code and secrets.toml, then refresh README and AGENTS.md with the true Flet run, smoke, and harness commands; grep plus absence check both return empty per CAP-5.

## Verify

`grep -ri openai` over product code and `secrets.toml` presence check both return empty; README/AGENTS.md document the wired run and harness commands.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
