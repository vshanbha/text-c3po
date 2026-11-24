# Ollaya agreement gate — winnow:e4b vs established verdicts (2026-11-23)

Question: can an Ollaya System-1 decision model replace the agent judge on
translation quality pairs? Method: all 12 quality-eval pairs, raw
`curl` → `localhost:11435/v1/systemone`, typed choice questions
(completeness comparative + per-side A/B, meaning, fluency), scored
against the sealed-then-decoded blind verdicts in `judge-report.md`.

## Raw long-pair pre-test (before the gate)

| Pair | My verdict | laya:multilingual | winnow:e4b |
|---|---|---|---|
| P6 DE long | B decisive | STATE_TRUNCATED (cannot fit long inputs) | overall B ✓, but comparative completeness missed the collapse |
| P12 ES long | B decisive | STATE_TRUNCATED | B/B/B all dims ✓ |
| P10 identical control | TIE | A/A/A — position bias on identical inputs | both/tie/tie @0.92+ ✓ |

**laya:multilingual disqualified**: context too small for long pairs
(the core use case) + biased on the identity control.

## Full gate — winnow:e4b, 12 pairs

| Pair | My overall | winnow meaning/fluency | winnow overall | Match |
|---|---|---|---|---|
| P1 | B | tie / B | B | ✓ |
| P2 | A | A / tie | A | ✓ |
| P3 | TIE | tie / tie | tie | ✓ |
| P4 | A (narrow) | tie / tie | tie | ✗ conservative |
| P5 | B (narrow) | tie / tie | tie | ✗ conservative |
| P6 | B | B / B (per-side: A=no, B=yes) | B | ✓ |
| P7 | A | A / tie | A | ✓ |
| P8 | A | tie / tie | tie | ✗ conservative |
| P9 | A (narrow) | tie / tie | tie | ✗ conservative |
| P10 | TIE | tie / tie | tie | ✓ |
| P11 | TIE | tie / tie | tie | ✓ |
| P12 | B | B / B (per-side: A=no, B=yes) | B | ✓ |

### Scores
- **Direction agreement: 12/12** — winnow NEVER preferred the model I
  judged worse. Zero wrong-direction calls.
- **Strict pair agreement: 8/12 (67%)** — all 4 misses are
  *conservative ties* on pairs I called narrow ornith wins. Failure
  mode is safe: under-calls winners, never crowns the wrong one.
- **Long-input collapse detection: 2/2** — the per-side completeness
  questions fixed the pre-test miss (P6: `cmp_a=no`, `cmp_b=yes`;
  P12: `cmp_a=no`).
- **Identity control: perfect** (P10 tie @0.93; P11 tie; P3 tie).
- **Confidence is informative**: every strict miss had a decisive-dim
  confidence < 0.5 on the tie answer (P4 0.28/0.16, P5 0.17/0.31,
  P8 0.28/0.43, P9 0.48) — the misses are detectable at runtime.

## Escalation rule (evaluated post-hoc, pre-registered for next round)

**Auto-resolve a pair only when min(meaning, fluency) confidence ≥ 0.55;
otherwise escalate to the deep judge (agent/human).**

| | Pairs | Result |
|---|---|---|
| Auto-resolved | P3, P7, P10, P11 (4/12) | **4/4 correct (100%)** |
| Escalated | 8/12 | deep judge decides |

Observed: zero wrong auto-calls. Auto-rate grows with a larger labeled
set and threshold tuning.

## Verdict

- **ADOPT `winnow:e4b` as tier-1 judge** with: per-side completeness
  questions (mandatory), the 0.55 escalation rule, and the tie-control
  kept as a standing canary. It runs every eval iteration locally in
  milliseconds; low-confidence pairs escalate to agent/human at
  milestones.
- **REJECT `laya:multilingual`** for translation judging (truncation +
  identity bias).
- **Not a full replacement**: n=12, calibrated against one agent judge;
  the human spot-check stays the calibration line. Every future eval
  round appends pairs to the labeled set — agreement stats get re-run
  then.

## Caveats
- Agreement target was my blind verdicts (agent judge, advisory by
  policy) — two fallible judges agreeing is evidence, not truth; owner
  spot-check of flagged pairs remains layer 5.
- State format matters: comparative completeness alone missed the P6
  collapse; per-side yes/no caught it. Keep both in future rounds.

---

# Round 2 — tev1 via Ollama (single-dependency challenge), 2026-11-23

Owner proposal: Ollama's `tev1` decision model could replace Ollaya and
keep ONE runtime. Verified: Ollama 0.40.17 exposes `/v1/systemone`
natively; `tev1` pulled (4.4 GB, eval-time load only); identical 12
payloads re-run against `localhost:11434`.

## Three-way scorecard

| Metric | my verdicts | winnow:e4b (Ollaya) | **tev1 (Ollama)** |
|---|---|---|---|
| Strict pair agreement | — | 8/12 (67%) | **9/12 (75%)** |
| Wrong-direction calls | — | 0 | 1 (P9 — a *narrow* call, margin 0.01) |
| Decisive pairs (P1,6,7,8,12) | 5 | 4/5 | **5/5** |
| Long-collapse detection | — | cmp_a=no @0.43 | **cmp_a=no @0.94** |
| Identity control (P10) | tie | tie @0.93 | tie (margin 0.58) |
| Run-to-run choice stability | — | not measured | **stable across 2 runs** |
| Escalation signal | — | confidence field (usable) | confidence field (unusable: 0.02 on correct calls) — **use probability margins instead** |
| Runtime | — | second dependency (Ollaya :11435) | **Ollama only (:11434)** |

## Escalation rule (tev1): min top-margin across meaning/fluency ≥ 0.5 → auto-resolve, else escalate

- Auto-resolved: P1, P6, P10, P12 → **4/4 correct (100%)**
- All 3 strict misses (P5 0.01, P9 0.01, P11 0.10) → **escalated**,
  none auto-resolved
- Profile identical to winnow's rule (4/4 auto, 100%) but derived from
  margins, which are meaningful for tev1 while its `confidence` field is
  not.

## Verdict (supersedes the round-1 adoption note)

**ADOPT `tev1` via Ollama as tier-1 judge** — higher strict agreement,
perfect decisive-pair record, best collapse detection, stable choices,
margin-based escalation with zero wrong auto-calls, and **one runtime
for the whole project** (owner's dependency criterion). **Ollaya leaves
the eval design** (winnow's numbers remain recorded above; the binary
may stay installed until the owner opts to remove it).

Standing caveats unchanged: n=12 against one agent judge; per-side
completeness questions mandatory; tie-control pair kept as canary;
agreement re-run every time the labeled set grows; owner spot-check is
still layer 5.
