"""CAP-6/SM-1 E1 exit-gate runner: 5-language x 5-sentence smoke harness (AD-6).

Reuses ``services.translate_text(text, target_language, model)`` as the only
LLM entry point with the model passed as an opaque runtime string (no
model-specific branches). The model list comes live from
``runtimes.list_models()`` so a newly pulled model joins with no code
changes. Loopback only via the reused ``OLLAMA_BASE_URL`` (AD-11).

JSON-valid is deliberately narrow: ``translate_text`` already normalizes
shape, so a result without an ``error`` key is a schema-conformant dict by
construction and counts valid; anything else counts invalid. Gate math: 95%
of 25 is 23.75, so a model passes with >= 24 valid cells.

Headless-runnable: ``PYTHONPATH=src python -m text_c3po.services.eval_harness`` with
``--models`` and ``--research-path`` overrides. Importing this module has no
side effects and issues no LLM calls. Stdlib plus installed
``langchain-ollama`` (via ``services.translation``) only.

Manual-only integration entry point: each run issues ~25 live Ollama calls
per model, which is expensive on CPU/GPU — invoke explicitly when gate
evidence is needed, never from CI (plain ``pytest`` deselects integration
tests by default; see pyproject.toml).

Execution policy (hardware-bound, do not relax):
- Serial only: ``run_matrix`` is a plain single-threaded nested loop with no
  threads, asyncio, or worker pools — one LLM request at a time. Never
  parallelize (no pytest-xdist, no concurrent clients); the Mac can hold one
  loaded model at a time (a 9GB MLX model already OOMs Metal on its own).
- Model first: gate on the default product model (pass it via ``--models``);
  add further models only deliberately, one at a time.
  Memory hogs (e.g. gemma4:e4b-mlx) stay out of the gate matrix.
- Languages first: the 5 matrix languages (German, French, Spanish, Hindi,
  Chinese) are the mainstream set compatible with the default model; extend to the
  remaining blueprint languages only via the E4 full-matrix story.
"""

import argparse
import datetime
import os
import sys


# src layout: every product import here is absolute (``text_c3po.*``).
# Supported invocations (all from the project root):
# - ``python -m text_c3po.services.eval_harness ...`` (installed, preferred)
# - ``python src/text_c3po/services/eval_harness.py ...`` (script form)
# - headless ``import text_c3po.services.eval_harness`` with src/ on sys.path
#   (pytest provides this via pythonpath). Never raises for a missing dep:
#   the ImportError surfaces to the caller per the headless-import contract.
#
# Root resolution lives in text_c3po.paths (A6 shared helper) so E2 reuses
# one implementation instead of copying __file__ joins. Kept here as a thin
# alias for story-7 callers that import _find_project_root directly.
try:
    from text_c3po.paths import (
        ensure_src_on_path,
        find_project_root as _find_project_root,
    )
except ImportError:  # script-form before install: locate src by existence
    import os
    import sys

    def _find_project_root():
        here = os.path.dirname(os.path.realpath(__file__))
        path = here
        for _ in range(8):
            if os.path.isfile(
                os.path.join(path, "src", "text_c3po", "services", "eval_harness.py")
            ):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
        return os.path.abspath(os.getcwd())

    def ensure_src_on_path():
        import os
        import sys

        src_root = os.path.join(_find_project_root(), "src")
        if src_root not in sys.path:
            sys.path.insert(0, src_root)
        return src_root


_PROJECT_ROOT = _find_project_root()
_SRC_ROOT = ensure_src_on_path()

from text_c3po.runtimes.ollama_client import (
    OLLAMA_BASE_URL,
    check_ollama,
    list_models,
)
from text_c3po.services.translation import translate_text

# Five fixed English sentences covering varied constructs (question, thanks,
# timed statement, polite request, habitual statement). Fixed so re-runs are
# comparable across models and over time.
SENTENCES = [
    "Where is the train station?",
    "Thank you very much for your help.",
    "The meeting starts at three o'clock.",
    "I would like a coffee, please.",
    "She reads a book every evening.",
]

# Five target language names, each verbatim from the AD-10 LANGUAGES constant
# (Latin, Devanagari, and CJK scripts). Order matches the gate-table columns.
MATRIX_LANGUAGES = ["German", "French", "Spanish", "Hindi", "Chinese"]

# E4-2: the full 23-language matrix, verbatim from the same constant.
from text_c3po.languages import LANGUAGES as _LANGUAGES

ALL_LANGUAGES = [entry["name"] for entry in _LANGUAGES]

# Short codes for the gate-table column headers (blueprint §2.1 codes),
# derived from the constant so the full matrix needs no second source.
_LANGUAGE_CODES = {
    entry["name"]: entry["code"]
    for entry in _LANGUAGES
    if isinstance(entry, dict) and entry.get("name") and entry.get("code")
}


def resolve_languages(spec) -> "list[str] | None":
    """Resolve a --languages value to language names, or None when invalid.

    ``None``/``"matrix"`` → the 5-language E1 gate; ``"all"`` → all 23;
    otherwise a comma-separated subset validated against the constant.
    Pure helper; never raises.
    """
    try:
        if spec is None:
            return list(MATRIX_LANGUAGES)
        text = str(spec).strip()
        if not text or text.lower() == "matrix":
            return list(MATRIX_LANGUAGES)
        if text.lower() == "all":
            return list(ALL_LANGUAGES)
        names = [part.strip() for part in text.split(",") if part.strip()]
        known = set(ALL_LANGUAGES)
        if not names or any(name not in known for name in names):
            return None
        seen = []
        for name in names:
            if name not in seen:
                seen.append(name)
        return seen
    except Exception:
        return None


GATE_THRESHOLD = 0.95

# Exit codes: 0 every model passes the gate; 1 gate failure; 2 harness abort
# (Ollama down or zero models: no scores written).
EXIT_PASS = 0
EXIT_GATE_FAIL = 1
EXIT_ABORT = 2

# The research file lives in the project's own _bmad-output tree:
# <project-root>/_bmad-output/... (a double dirname off _PRODUCT_ROOT here
# was a past bug compensating for a doubled root — see _find_project_root).
_DEFAULT_RESEARCH_PATH = os.path.join(
    _PROJECT_ROOT,
    "_bmad-output",
    "planning-artifacts",
    "research",
    "technical-model-quality-2026-09-08",
    "research.md",
)


def is_valid(result):
    """Return True when a translate call counts JSON-valid: a dict with no error key."""
    return isinstance(result, dict) and "error" not in result


def passes_gate(valid, total):
    """Return True when valid/total meets the >=95% gate (>=24 of 25)."""
    try:
        if not isinstance(total, int) or total <= 0:
            return False
        return (valid / total) >= GATE_THRESHOLD
    except Exception:
        return False


def run_matrix(models=None, translate_fn=translate_text, languages=None):
    """Run the 5-sentence x N-language matrix per model; never aborts mid-matrix.

    ``models`` defaults to the live ``list_models()`` output. ``languages``
    defaults to the 5-language E1 gate (``MATRIX_LANGUAGES``); pass
    ``ALL_LANGUAGES`` for the E4 full matrix. ``translate_fn``
    is injectable (same ``(text, target_language, model)`` signature) so
    headless checks can score stubbed outcomes with zero LLM calls. Any
    per-cell failure (``{error, retryable}`` result or a raising stub) counts
    that cell invalid and is recorded in the model's ``failures`` detail;
    the matrix always runs to completion.

    Returns ``{model: {valid, total, per_language, failures}}`` where
    ``per_language`` maps each language name to its valid count and
    ``failures`` holds one ``{model, language, sentence_index}`` dict per
    invalid cell (sentence_index is 0-based).
    """
    if models is None:
        models = list_models()
    if translate_fn is None:
        translate_fn = translate_text
    if languages is None:
        languages = MATRIX_LANGUAGES
    else:
        languages = list(languages)
    results = {}
    for model in models:
        per_language = {language: 0 for language in languages}
        failures = []
        valid = 0
        total = 0
        for language in languages:
            for index, sentence in enumerate(SENTENCES):
                total += 1
                try:
                    result = translate_fn(sentence, language, model)
                except Exception:
                    result = {"error": "harness-caught exception", "retryable": True}
                if is_valid(result):
                    valid += 1
                    per_language[language] += 1
                else:
                    failures.append(
                        {
                            "model": model,
                            "language": language,
                            "sentence_index": index,
                        }
                    )
        results[model] = {
            "valid": valid,
            "total": total,
            "per_language": per_language,
            "failures": failures,
        }
    return results


def _code_for(language: str) -> str:
    """Return the blueprint code for a language name (name itself as fallback)."""
    try:
        return _LANGUAGE_CODES.get(language, language)
    except Exception:
        return language


def format_table(results, languages=None):
    """Return the gate table as markdown rows (header + one row per model)."""
    if languages is None:
        languages = MATRIX_LANGUAGES
    else:
        languages = list(languages)
    header = (
        "| Model | "
        + " | ".join(_code_for(language) for language in languages)
        + " | Valid | Score | Gate |"
    )
    separator = "|" + "---|" * (len(languages) + 4)
    lines = [header, separator]
    for model, summary in results.items():
        try:
            per_language = summary.get("per_language", {})
        except Exception:
            per_language = {}
        cells = [
            "{}/{}".format(per_language.get(language, 0), len(SENTENCES))
            for language in languages
        ]
        valid = summary.get("valid", 0)
        total = summary.get("total", 0)
        try:
            score = "{}%".format(round(100 * valid / total)) if total else "0%"
        except Exception:
            score = "0%"
        gate = "PASS" if passes_gate(valid, total) else "FAIL"
        lines.append(
            "| {} | {} | {}/{} | {} | {} |".format(
                model, " | ".join(cells), valid, total, score, gate
            )
        )
    return "\n".join(lines)


def record_results(results, path, date=None, languages=None, label=None):
    """Append the dated gate section to the model-quality research file.

    Append-only: existing content is never read or rewritten. Adds the
    per-model table plus a one-line failure detail per invalid cell
    (model, language, sentence index). Defaults preserve the exact E1
    section shape; pass ``languages`` plus ``label`` for wider gates.
    Returns the path written.
    """
    if date is None:
        date = datetime.date.today().isoformat()
    if languages is None:
        languages = MATRIX_LANGUAGES
    else:
        languages = list(languages)
    if label is None:
        label = "E1 gate — 5x5 smoke"
    lines = [
        "",
        "## {} ({})".format(label, date),
        "",
        "Target: {} (loopback only). Matrix: {} sentences x {} languages.".format(
            OLLAMA_BASE_URL, len(SENTENCES), len(languages)
        ),
        "",
        format_table(results, languages),
        "",
    ]
    failures = [
        failure
        for summary in results.values()
        for failure in summary.get("failures", [])
    ]
    if failures:
        lines.append("Failures:")
        lines.append("")
        for failure in failures:
            lines.append(
                "- FAIL {} | {} | sentence {}".format(
                    failure.get("model"),
                    failure.get("language"),
                    failure.get("sentence_index", 0) + 1,
                )
            )
        lines.append("")
    else:
        lines.append("No invalid cells — every model cell JSON-valid.")
        lines.append("")
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return path


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "E1 exit gate: 5-language x 5-sentence smoke matrix across the "
            "live Ollama model list; appends the gate table to research.md."
        )
    )
    parser.add_argument(
        "--models",
        nargs="*",
        default=None,
        help=(
            "Run only these models (space- and/or comma-separated opaque "
            "/api/tags names). Default: every model from list_models()."
        ),
    )
    parser.add_argument(
        "--research-path",
        default=_DEFAULT_RESEARCH_PATH,
        help="research.md file to append the gate section to.",
    )
    parser.add_argument(
        "--languages",
        default="matrix",
        help=(
            "'matrix' (default 5-language E1 gate), 'all' (full 23-language "
            "E4 matrix), or comma-separated language names from the constant."
        ),
    )
    return parser.parse_args(argv)


def main(argv=None, translate_fn=None):
    """Wire --models/--research-path/--languages; exit 0 iff the gate passes.

    ``translate_fn`` is injectable for offline tests (same signature as
    ``translate_text``); the CLI path always uses the live service.
    """
    args = _parse_args(argv)
    if args.models:
        models = []
        for chunk in args.models:
            models.extend(
                part.strip() for part in str(chunk).split(",") if part.strip()
            )
    else:
        models = None

    languages = resolve_languages(getattr(args, "languages", None))
    if languages is None:
        print(
            "Unknown --languages value {!r} — use 'matrix', 'all', or "
            "comma-separated names from the 23-language constant. "
            "No scores written.".format(getattr(args, "languages", None))
        )
        return EXIT_ABORT
    if languages == MATRIX_LANGUAGES:
        label = "E1 gate — 5x5 smoke"
    elif len(languages) == len(ALL_LANGUAGES):
        label = "E4 gate — {}x{} full matrix".format(len(languages), len(SENTENCES))
    else:
        label = "E4 gate — {}x{} matrix".format(len(languages), len(SENTENCES))

    connected, _ = check_ollama()
    if not connected:
        print(
            "Ollama is not reachable at {} — start it with "
            "`ollama serve`, then re-run. No scores written.".format(OLLAMA_BASE_URL)
        )
        return EXIT_ABORT

    if models is None:
        models = list_models()
    if not models:
        print(
            "Ollama is connected at {} but no models are installed — "
            "pull one with `ollama pull <model>`, then re-run. "
            "No scores written.".format(OLLAMA_BASE_URL)
        )
        return EXIT_ABORT

    print(
        "Gate {}x{}: {} model(s) x {} sentences x {} languages via {} ...".format(
            len(languages),
            len(SENTENCES),
            len(models),
            len(SENTENCES),
            len(languages),
            OLLAMA_BASE_URL,
        )
    )
    results = run_matrix(models=models, translate_fn=translate_fn, languages=languages)
    table = format_table(results, languages)
    print("")
    print(table)
    print("")
    for summary in results.values():
        for failure in summary.get("failures", []):
            print(
                "FAIL {} | {} | sentence {}".format(
                    failure.get("model"),
                    failure.get("language"),
                    failure.get("sentence_index", 0) + 1,
                )
            )
    record_results(results, args.research_path, languages=languages, label=label)
    print("")
    print("Appended gate section to {}".format(args.research_path))
    failed = [
        model
        for model, summary in results.items()
        if not passes_gate(summary.get("valid", 0), summary.get("total", 0))
    ]
    if failed:
        print("Gate FAIL (<95% JSON-valid): {}".format(", ".join(failed)))
        return EXIT_GATE_FAIL
    print("Gate PASS (>=95% JSON-valid) for every model.")
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
