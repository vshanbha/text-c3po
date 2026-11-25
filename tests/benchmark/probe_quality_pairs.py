"""Optional benchmark probe: blinded side-by-side quality pairs (probe layer 4).

Not a test — never collected by pytest (``probe_*`` matches no
``python_files`` pattern) and exits 0 whether or not any call succeeds.

Why this exists: the eval gate measures JSON-validity only (contract
conformance — an echo passes it) and the capability pack measures script
rendering. Neither says anything about whether a translation *means the
same thing*. This probe generates a BLINDED comparison sheet for an
LLM-as-judge or human read, following eval best practice:

- pairwise comparison (reliable) instead of absolute scoring;
- randomized A/B order per cell, mapping written to a SEPARATE key file
  the judge must not open until judgments are recorded (anti position
  and identity bias);
- fixed rubric: adequacy (meaning), completeness, fluency, register;
- multiple samples across register-critical languages (German Sie/du)
  and collapse-history languages (Spanish), plus one long input.

Run manually, serially (one LLM call at a time — policy in
eval_harness.py)::

    PYTHONPATH=src uv run python tests/benchmark/probe_quality_pairs.py [model_a] [model_b]

Optional flags (before or after the model names): ``--pairs N`` limits
the sheet to the first N pairs; ``--judge`` additionally scores every
generated pair with the tier-1 judge (tev1 via Ollama ``/v1/systemone``)
and writes ``judge-scores.md`` next to the sheet. Reporting-only: the
judge run never changes the exit code (always 0).

Defaults: lfm3 (current default) vs ornith-1.5:9b (incumbent with
months of human-checked output history). Outputs, under
``_bmad-output/planning-artifacts/research/quality-eval-2026-11-23/``:

- ``sheet.md``   — blinded pairs for the judge (this is the only file
                   the judge reads before writing judgments);
- ``judge-key.md`` — the A/B mapping; open ONLY after judging;
- ``judge-scores.md`` — (with ``--judge``) per-pair tev1 verdicts with
                   choice probabilities and margins.

The judgment itself (agent or owner) is recorded by hand in
``judge-report.md`` — ``--judge`` output is advisory tier-1 evidence
(owner spot-check stays layer 5).
"""

import json
import os
import random
import sys
import urllib.error
import urllib.request

# Probes are standalone scripts run via `uv run python tests/benchmark/...`;
# make sibling modules (eval_harness constants, probe_collapse paragraphs)
# importable regardless of how the runner sets sys.path[0].
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from text_c3po.runtimes.ollama_client import OLLAMA_BASE_URL
from text_c3po.services.eval_harness import SENTENCES
from probe_collapse import LIGHTHOUSE_PARAS

MODELS_DEFAULT = ("lfm3", "ornith-1.5:9b")
# German: register-sensitive (formal/informal both matter). Spanish: the
# collapse-history language (B6) and a long-output stress case.
JUDGE_LANGUAGES = ["German", "Spanish"]
SEED = 20261123  # reproducible A/B order per cell

# Tier-1 judge: tev1 decision model on Ollama (one-runtime rule, owner
# criterion). Question schema copied VERBATIM from the 2026-11-23 gate
# payloads ($TMPDIR/ollaya-eval/gate-p*.json): completeness comparative
# + per-side A/B + meaning + fluency — both completeness forms are
# mandatory (comparative alone missed the long-input collapse once; see
# _bmad-output/initiative-text-c3po/quality-eval-2026-11-23/gate-report.md).
JUDGE_MODEL = "tev1"
JUDGE_ENDPOINT = "/v1/systemone"
# Escalation rule (gate-report 2026-11-23, pre-registered): min top
# margin across meaning/fluency >= 0.5 auto-resolves the pair, else it
# escalates to the agent/human tier-2 judge. tev1's confidence field is
# unusable (0.02 on correct calls) — probability margins instead.
JUDGE_AUTO_RESOLVE_MARGIN = 0.5
JUDGE_QUESTIONS = {
    "completeness": {
        "type": "choice",
        "instructions": (
            "Which translation covers the ENTIRE source text "
            "(every paragraph and sentence)?"
        ),
        "criteria": {
            "A": "Only A is complete",
            "B": "Only B is complete",
            "both": "Both are complete",
            "neither": "Neither is complete",
        },
    },
    "completeness_a": {
        "type": "choice",
        "instructions": (
            "Does TRANSLATION A alone contain a translation of every part "
            "of the source text?"
        ),
        "criteria": {
            "yes": "A translates all of the source",
            "no": "A is missing parts of the source",
        },
    },
    "completeness_b": {
        "type": "choice",
        "instructions": (
            "Does TRANSLATION B alone contain a translation of every part "
            "of the source text?"
        ),
        "criteria": {
            "yes": "B translates all of the source",
            "no": "B is missing parts of the source",
        },
    },
    "meaning": {
        "type": "choice",
        "instructions": (
            "Which translation more faithfully preserves the source meaning, "
            "without dropping content, adding content that is not there, or "
            "substituting wrong words?"
        ),
        "criteria": {
            "A": "A is more faithful",
            "B": "B is more faithful",
            "tie": "About equally faithful",
        },
    },
    "fluency": {
        "type": "choice",
        "instructions": (
            "Which translation reads more naturally as {language}, without "
            "grammatical errors or made-up words?"
        ),
        "criteria": {
            "A": "A is more natural",
            "B": "B is more natural",
            "tie": "About equally natural",
        },
    },
}

_OUT_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "_bmad-output",
    "planning-artifacts",
    "research",
    "quality-eval-2026-11-23",
)


def _inputs():
    """Return [(label, kind, text)] — 5 short sentences + 1 long input."""
    items = [
        ("short-{}".format(i + 1), "short", sentence)
        for i, sentence in enumerate(SENTENCES)
    ]
    items.append(("lighthouse-10p", "long", "\n\n".join(LIGHTHOUSE_PARAS)))
    return items


def _run(text, language, model):
    """Translate once; never raise — errors become cell text."""
    try:
        from text_c3po.services.translation import translate_text

        result = translate_text(text, language, model)
        if not isinstance(result, dict):
            return {"error": "non-dict result"}
        if result.get("error"):
            return {"error": str(result.get("error"))}
        return {
            "formal": (result.get("formal") or "").strip(),
            "informal": (result.get("informal") or "").strip(),
        }
    except Exception as exc:  # noqa: BLE001 — probe reports, never raises
        return {"error": repr(exc)}


def _questions_for(language):
    """Deep-copy JUDGE_QUESTIONS with the fluency rubric bound to ``language``.

    The stored schema is language-neutral (copied verbatim from the gate
    payloads, which shipped one file per pair with "as German"/"as
    Spanish" already substituted).
    """
    questions = json.loads(json.dumps(JUDGE_QUESTIONS))
    questions["fluency"]["instructions"] = questions["fluency"]["instructions"].format(
        language=language
    )
    return questions


def _judge_state(language, text, out_a, out_b):
    """Build the System-1 ``state`` block for one blinded pair.

    Clean A-then-B format (the gate payloads accidentally interleaved
    markdown into TRANSLATION A — reconstructed per gate-report.md).
    """

    def field(out, key):
        if "error" in out:
            return "(error: {})".format(out["error"])
        return out.get(key) or "(blank)"

    return (
        "You are judging two translations of the same source text into "
        "{lang}. Judge only what is on the page.\n\n"
        "SOURCE TEXT:\n{text}\n\n"
        "TRANSLATION A (formal):\n{af}\n\n"
        "TRANSLATION A (informal):\n{ai}\n\n"
        "TRANSLATION B (formal):\n{bf}\n\n"
        "TRANSLATION B (informal):\n{bi}"
    ).format(
        lang=language,
        text=text,
        af=field(out_a, "formal"),
        ai=field(out_a, "informal"),
        bf=field(out_b, "formal"),
        bi=field(out_b, "informal"),
    )


def _post_systemone(state, language, timeout_s=300.0):
    """POST one pair to Ollama /v1/systemone; return the answers dict.

    Never raises: transport/HTTP/shape failures come back as
    ``{"error": ...}`` so the report always has something to write.
    """
    payload = {
        "model": JUDGE_MODEL,
        "state": state,
        "questions": _questions_for(language),
    }
    url = OLLAMA_BASE_URL.rstrip("/") + JUDGE_ENDPOINT
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        answers = data.get("answers")
        if not isinstance(answers, dict):
            return {"error": "no answers in response: {!r}".format(data)[:300]}
        return answers
    except Exception as exc:  # noqa: BLE001 — probe reports, never raises
        return {"error": repr(exc)}


def _top_margin(answer):
    """Top-1 minus top-2 probability for one choice answer; None if absent."""
    try:
        probs = (answer or {}).get("probabilities") or {}
        values = sorted((float(v) for v in probs.values()), reverse=True)
        if not values:
            return None
        if len(values) == 1:
            return values[0]
        return values[0] - values[1]
    except Exception:
        return None


def _format_margin(value):
    return "-" if value is None else "{:.2f}".format(value)


def _write_judge_report(path, judged, endpoint):
    """Write the per-pair score report (markdown). Reporting-only, never raises.

    ``judged`` is a list of ``(cell, answers_or_error)``. Includes the
    pre-registered escalation rule: min top-margin across meaning/fluency
    >= JUDGE_AUTO_RESOLVE_MARGIN auto-resolves, else escalate to tier-2.
    """
    try:
        lines = [
            "# tev1 judge scores — {}\n".format(_today()),
            "",
            "Reporting-only tier-1 evidence (exit 0 always) — advisory; the "
            "owner spot-check remains layer 5.",
            "",
            "Endpoint: `{}` model `{}`. A/B order comes from `judge-key.md` "
            "(blind).".format(endpoint, JUDGE_MODEL),
            "",
            "Escalation rule (gate-report 2026-11-23): min top-margin across "
            "meaning/fluency >= {} auto-resolves the pair; below that it "
            "escalates to the agent/human judge.".format(JUDGE_AUTO_RESOLVE_MARGIN),
            "",
        ]
        auto = 0
        escalate = 0
        judge_errors = 0
        winners = {"A": 0, "B": 0, "tie": 0}
        for cell, answers in judged:
            pair_no, language, label, _kind, _text, _outputs, _order = cell
            lines.append("## Pair {} — {} ({})".format(pair_no, language, label))
            lines.append("")
            if "error" in answers:
                judge_errors += 1
                lines.append("_judge error: {}_".format(answers["error"]))
                lines.append("")
                continue
            lines.append("| Question | Choice | Top margin |")
            lines.append("|---|---|---|")
            margins = {}
            for name, answer in answers.items():
                choice = (answer or {}).get("choice", "?")
                margin = _top_margin(answer)
                margins[name] = margin
                lines.append(
                    "| {} | {} | {} |".format(name, choice, _format_margin(margin))
                )
            lines.append("")
            meaning = (answers.get("meaning") or {}).get("choice")
            if meaning in winners:
                winners[meaning] += 1
            decisive = [
                margins.get("meaning"),
                margins.get("fluency"),
            ]
            decisive = [m for m in decisive if m is not None]
            if len(decisive) == 2:
                min_margin = min(decisive)
                resolved = min_margin >= JUDGE_AUTO_RESOLVE_MARGIN
                if resolved:
                    auto += 1
                else:
                    escalate += 1
                lines.append(
                    "min(meaning, fluency) margin = {:.2f} -> {}".format(
                        min_margin,
                        "AUTO-RESOLVE" if resolved else "ESCALATE to tier-2",
                    )
                )
            else:
                escalate += 1
                lines.append("ESCALATE to tier-2 (missing decisive margins)")
            lines.append("")
        lines.extend(
            [
                "## Summary",
                "",
                "- pairs judged: {} (judge errors: {})".format(
                    len(judged), judge_errors
                ),
                "- meaning winners: A={} B={} tie={}".format(
                    winners["A"], winners["B"], winners["tie"]
                ),
                "- auto-resolved: {} / escalated: {}".format(auto, escalate),
                "",
            ]
        )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
    except Exception as exc:  # noqa: BLE001 — reporting-only
        print("judge report write failed: {!r}".format(exc))


def _run_judge(cells, out_dir):
    """Judge every cell serially and write judge-scores.md; never raises."""
    endpoint = OLLAMA_BASE_URL.rstrip("/") + JUDGE_ENDPOINT
    print(
        "judge: POSTing {} pair(s) to {} model={} ...".format(
            len(cells), endpoint, JUDGE_MODEL
        )
    )
    judged = []
    for cell in cells:
        pair_no, language, _label, _kind, text, outputs, order = cell
        try:
            state = _judge_state(language, text, outputs[order[0]], outputs[order[1]])
            answers = _post_systemone(state, language)
        except Exception as exc:  # noqa: BLE001 — reporting-only
            answers = {"error": repr(exc)}
        judged.append((cell, answers))
        if "error" in answers:
            print("  pair {}: judge error {}".format(pair_no, answers["error"]))
        else:
            print(
                "  pair {}: meaning={} fluency={} completeness={}".format(
                    pair_no,
                    (answers.get("meaning") or {}).get("choice"),
                    (answers.get("fluency") or {}).get("choice"),
                    (answers.get("completeness") or {}).get("choice"),
                )
            )
    report_path = os.path.join(out_dir, "judge-scores.md")
    _write_judge_report(report_path, judged, endpoint)
    print("judge report: {}".format(report_path))
    return report_path


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    judge = "--judge" in argv
    argv = [arg for arg in argv if arg != "--judge"]
    pair_limit = None
    if "--pairs" in argv:
        try:
            index = argv.index("--pairs")
            pair_limit = int(argv[index + 1])
            del argv[index : index + 2]
        except (ValueError, IndexError):
            print("--pairs requires an integer — ignoring the flag.")
            pair_limit = None
    out_dir = os.path.abspath(_OUT_DIR)
    if "--out-dir" in argv:
        try:
            index = argv.index("--out-dir")
            out_dir = os.path.abspath(argv[index + 1])
            del argv[index : index + 2]
        except (IndexError, ValueError):
            print("--out-dir requires a path — using the default.")
    model_a = argv[0] if len(argv) > 0 else MODELS_DEFAULT[0]
    model_b = argv[1] if len(argv) > 1 else MODELS_DEFAULT[1]

    rng = random.Random(SEED)
    os.makedirs(out_dir, exist_ok=True)

    cells = []  # (pair_no, language, label, kind, text, {model: output})
    pair_no = 0
    for language in JUDGE_LANGUAGES:
        for label, kind, text in _inputs():
            pair_no += 1
            outputs = {}
            for model in (model_a, model_b):
                outputs[model] = _run(text, language, model)
            # Randomize which slot each model occupies, per cell.
            order = [model_a, model_b]
            rng.shuffle(order)
            cells.append((pair_no, language, label, kind, text, outputs, order))
    if pair_limit is not None:
        cells = cells[:pair_limit]

    sheet_path = os.path.join(out_dir, "sheet.md")
    key_path = os.path.join(out_dir, "judge-key.md")

    with open(sheet_path, "w", encoding="utf-8") as sheet:
        sheet.write(
            "# Quality pairs — blinded sheet\n\n"
            "Generated {} — models: `{}` (candidate) vs `{}` (incumbent). "
            "A/B order is randomized per pair.\n\n"
            "**Judge instructions:** for each pair, score A vs B on the "
            "rubric — *adequacy* (same meaning?), *completeness* (nothing "
            "dropped/added?), *fluency* (natural target-language output?), "
            "and *register* (formal/informal fit; German Sie/du matters). "
            "Pick a winner per dimension, then overall; cite the specific "
            "words/phrases that decided it. Ties are allowed. Do NOT open "
            "`judge-key.md` until your judgments are written down.\n\n"
            "Rubric counts as advisory evidence — the owner spot-checks "
            "finals (judges are model-dependent).\n".format(_today(), model_a, model_b)
        )
        for pair_no, language, label, kind, text, outputs, order in cells:
            sheet.write(
                "\n---\n\n## Pair {} — {} ({})\n\n".format(pair_no, language, label)
            )
            if kind == "long":
                sheet.write(
                    "*Long input, {} chars — completeness is the crux.*\n\n".format(
                        len(text)
                    )
                )
            sheet.write("**Input:**\n\n```\n{}\n```\n".format(text))
            for slot, model in zip(("A", "B"), order):
                out = outputs[model]
                sheet.write("\n**{} — formal:**\n\n".format(slot))
                if "error" in out:
                    sheet.write("_(error: {})_\n".format(out["error"]))
                else:
                    sheet.write("> {}\n".format(out["formal"]))
                sheet.write("\n**{} — informal:**\n\n".format(slot))
                if "error" in out:
                    sheet.write("_(error: {})_\n".format(out["error"]))
                else:
                    sheet.write("> {}\n".format(out["informal"] or "(blank)"))

    with open(key_path, "w", encoding="utf-8") as key:
        key.write("# Judge key — open ONLY after judging\n\n")
        for pair_no, language, label, _kind, _text, _outputs, order in cells:
            key.write(
                "Pair {} ({} {}): A = `{}` / B = `{}`\n".format(
                    pair_no, language, label, order[0], order[1]
                )
            )

    errors = sum(1 for c in cells for m in (model_a, model_b) if "error" in c[5][m])
    print(
        "pairs={} languages={} errors={} sheet={} key={}".format(
            len(cells), len(JUDGE_LANGUAGES), errors, sheet_path, key_path
        )
    )
    if judge:
        # Reporting-only: judge failures are printed, never raised — the
        # probe exits 0 whether or not tev1 answered.
        try:
            _run_judge(cells, out_dir)
        except Exception as exc:  # noqa: BLE001 — reporting-only
            print("judge run failed: {!r}".format(exc))
    return 0


def _today():
    import datetime

    return datetime.date.today().isoformat()


if __name__ == "__main__":
    sys.exit(main())
