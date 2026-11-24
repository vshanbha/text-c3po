---
ticket: 10
status: done
type: feature
title: "Remediate Dependabot dependency vulnerabilities"
---

# Remediate Dependabot dependency vulnerabilities

## Description

Clear the 5 open Dependabot alerts on master (2 high, 3 moderate) by raising the two flagged transitive packages to their first-patched versions in uv.lock: oauthlib 3.3.1 -> 4.0.0 (GHSA-hj66-6f7g-4r5v, GHSA-xpv3-w29h-x7cv) and urllib3 2.7.0 -> 2.8.0 (GHSA-8988-9cw3-xx77, GHSA-vxq7-64xx-v4gw, GHSA-gh4c-6fx4-qh6g) per D16-A. oauthlib is a flet dependency (>=3.2.2, no upper bound) and urllib3 a requests dependency; neither is used at runtime by this loopback-only app. No direct-dependency, src/, or tests/ change.

## Verify

Clear the 5 open Dependabot alerts on master (2 high, 3 moderate) by raising the two flagged transitive packages to their first-patched versions in uv.lock: oauthlib 3.3.1 -> 4.0.0 (GHSA-hj66-6f7g-4r5v, GHSA-xpv3-w29h-x7cv) and urllib3 2.7.0 -> 2.8.0 (GHSA-8988-9cw3-xx77, GHSA-vxq7-64xx-v4gw, GHSA-gh4c-6fx4-qh6g) per D16-A.

## Notes

- Unknown: no v6 build record exists for this story. sprint-status.yaml reported
  `done` at migration time, mapped to `done`. No baseline revision can be carried;
  evidence for the work lives in the epic, the SPEC and the archived v6 sources.
