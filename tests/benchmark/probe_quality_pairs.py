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

Defaults: lfm3 (current default) vs ornith-1.5:9b (incumbent with
months of human-checked output history). Outputs, under
``_bmad-output/planning-artifacts/research/quality-eval-2026-11-23/``:

- ``sheet.md``   — blinded pairs for the judge (this is the only file
                   the judge reads before writing judgments);
- ``judge-key.md`` — the A/B mapping; open ONLY after judging.

The judgment itself (agent or owner) is recorded by hand in
``judge-report.md`` — this script never scores anything.
"""

import os
import random
import sys

# Probes are standalone scripts run via `uv run python tests/benchmark/...`;
# make sibling modules (eval_harness constants, probe_collapse paragraphs)
# importable regardless of how the runner sets sys.path[0].
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from text_c3po.services.eval_harness import SENTENCES
from probe_collapse import LIGHTHOUSE_PARAS

MODELS_DEFAULT = ("lfm3", "ornith-1.5:9b")
# German: register-sensitive (formal/informal both matter). Spanish: the
# collapse-history language (B6) and a long-output stress case.
JUDGE_LANGUAGES = ["German", "Spanish"]
SEED = 20261123  # reproducible A/B order per cell

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


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    model_a = argv[0] if len(argv) > 0 else MODELS_DEFAULT[0]
    model_b = argv[1] if len(argv) > 1 else MODELS_DEFAULT[1]

    rng = random.Random(SEED)
    out_dir = os.path.abspath(_OUT_DIR)
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
    return 0


def _today():
    import datetime

    return datetime.date.today().isoformat()


if __name__ == "__main__":
    sys.exit(main())
