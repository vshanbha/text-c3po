---
ticket: 8
status: done
type: feature
title: "Refresh stale v1 docs and infra"
---

# Refresh stale v1 docs and infra

## Description

Update the parent workspace AGENTS.md (still describes Streamlit + OpenAI + secrets.toml), fix the .devcontainer (Python 3.11, nonexistent text-c3po/app.py, Streamlit 8501), remove the stale 'no test CI workflow' comment in pyproject.toml, and pin docs/requirements.txt. Include D1-A (ratify commentary cut: fix README.md:4 + E1 SPEC Success signal to formal/informal/origin_language) and D6-B (track uv.lock: remove from .gitignore + stale comment, commit lock).

## Verify

Update the parent workspace AGENTS.md (still describes Streamlit + OpenAI + secrets.toml), fix the .devcontainer (Python 3.11, nonexistent text-c3po/app.py, Streamlit 8501), remove the stale 'no test CI workflow' comment in pyproject.toml, and pin docs/requirements.txt.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
