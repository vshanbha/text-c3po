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

Scope (2026-09-14): this gate is deterministic contract conformance ONLY —
it proves the model speaks our JSON schema, which is what the UI needs to
never crash on a response. An echo (formal == input) is contract-conformant;
it says nothing about rendering ability and fails nothing here. The
``--capability`` rescoring is an informational rendering survey for
comparing models (which targets come back non-echoed), not a correctness
verdict. Meaning-equivalence between input and output cannot be checked
deterministically: it needs a judge model (fuzzy, model-dependent) or a
human (TEST-PLAN §B rows). Do not read a gate PASS as "translates well".

Extension (2026-11-25): the gate additionally checks TARGET-LANGUAGE
consistency on both ``formal`` and ``informal`` of every rendered cell —
a deterministic function-word/script heuristic (see the design note above
:func:`is_target_language`), not a quality judgment. It exists because the
2026-11-24 informal-language bug (``informal`` stochastically rendering in
English) had zero automated coverage. Lang-threshold policy (owner
decision, 2026-11-25): the dimension passes when confident mismatches
<= allowed = max(1, lang_total // 100), i.e. >=99% language consistency
with a one-cell floor (25 cells -> 1 allowed; 115 -> 1; 200 -> 2; and
lang_total == 0 passes because there are no rendered cells to check).
Every mismatch still prints as a ``LANG-FAIL`` line and still lands in
the research block — only the verdict is softened, never the reporting.
Undetermined heuristic cases pass as before.

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
import re
import sys
import unicodedata


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

# The SENTENCES below are fixed English input, so an English-target cell is
# an identity translation: echo there is correct output, not an unsupported
# target, and the echo check below is skipped for it.
SOURCE_LANGUAGE = "English"

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
    "initiative-text-c3po",
    "technical-model-quality-2026-09-08",
    "technical-model-quality-2026-09-08.md",
)


def is_valid(result):
    """Return True when a translate call counts JSON-valid: a dict with no error key."""
    return isinstance(result, dict) and "error" not in result


def _norm_text(value) -> str:
    """Normalize for echo comparison: collapse whitespace, casefold."""
    try:
        if not isinstance(value, str):
            return ""
        return " ".join(value.split()).casefold()
    except Exception:
        return ""


# Public alias: integration tripwires import the normalizer; the leading
# underscore keeps the primary name private by convention.
normalize_text = _norm_text


def is_supported(result, sentence) -> bool:
    """Return True when a cell counts as genuine target-language output.

    Stronger than :func:`is_valid`: the result must be JSON-valid AND its
    formal text must differ from the input sentence. An English echo
    (lfm2.5 into Kannada/Marathi) is schema-conformant but proves the
    model cannot render the target — it scores valid for the gate,
    unsupported for capability. Never raises.
    """
    try:
        if not is_valid(result):
            return False
        formal = result.get("formal")
        if not isinstance(formal, str) or not formal.strip():
            return False
        return _norm_text(formal) != _norm_text(sentence)
    except Exception:
        return False


def passes_gate(valid, total):
    """Return True when valid/total meets the >=95% gate (>=24 of 25)."""
    try:
        if not isinstance(total, int) or total <= 0:
            return False
        return (valid / total) >= GATE_THRESHOLD
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Target-relative language-consistency check (formal AND informal).
#
# Why (open bug 2026-11-24): the instruction never states the LANGUAGE of
# the two rendered versions, so on EN->DE the ``informal`` field
# stochastically renders in English while ``formal`` stays correct (owner
# manual hit on a long input; 1/3 fresh sample on shorts). The gate used
# to validate JSON-validity + formal non-echo only — ``informal`` had
# ZERO automated coverage anywhere (the integration test never read it
# either). This deterministic heuristic closes that blind spot.
#
# Design — conservative: it may only FAIL a cell it is sure of.
# 1. Script families (Devanagari, Han, Cyrillic, ...) compare against the
#    target's script first: a Latin result for a Hindi target (or
#    Devanagari for a German target) is a mismatch regardless of words.
# 2. Latin-script text is scored against per-language function-word
#    marker sets (all 10 Latin-script targets of the 23-language constant
#    have one, so a proper render always scores its own language). A
#    confident best match that differs from the target is a mismatch;
#    "confident" means >= _MIN_MARKER_HITS hits AND at least
#    _MARKER_MARGIN ahead of the runner-up. Anything else (short text,
#    heavy cross-language overlap, unknown target, no letters) is
#    undetermined and passes — the check never guesses, so a heuristic
#    miss can only under-flag, never break a legitimate gate run.
#
# Identity/English-target cells follow the same target-relative rule:
# English output for an English target matches; the echo/blank/malformed
# kinds keep their existing meaning and stay OUT of this dimension (a
# cell that did not render the target is already scored by its kind).
# ---------------------------------------------------------------------------
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# High-precision function words (plus a few discourse markers) per Latin
# target language. Tokens shared across languages are deliberate: they
# score for every language that uses them and stay neutral in the margin.
_FUNCTION_MARKERS = {
    "English": {
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "am",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "of",
        "to",
        "in",
        "on",
        "at",
        "for",
        "with",
        "as",
        "by",
        "from",
        "or",
        "and",
        "but",
        "if",
        "then",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "they",
        "their",
        "them",
        "we",
        "our",
        "us",
        "you",
        "your",
        "he",
        "she",
        "his",
        "her",
        "i",
        "my",
        "me",
        "who",
        "whom",
        "whose",
        "which",
        "what",
        "when",
        "where",
        "how",
        "why",
        "not",
        "no",
        "yes",
        "very",
        "too",
        "just",
        "also",
        "than",
        "more",
        "most",
        "some",
        "any",
        "all",
        "every",
        "each",
        "both",
        "such",
        "own",
        "same",
        "other",
        "another",
        "only",
        "into",
        "over",
        "under",
        "after",
        "before",
        "between",
        "through",
        "during",
        "while",
        "because",
        "though",
        "although",
        "about",
        "up",
        "down",
        "out",
        "off",
        "there",
        "here",
        "so",
        "can",
        "could",
        "will",
        "would",
        "shall",
        "should",
        "may",
        "might",
        "must",
        "man",
        "war",
        "thanks",
        "please",
        "hello",
        "hi",
        "bye",
        "welcome",
        "good",
        "morning",
        "evening",
        "today",
        "tomorrow",
        "yesterday",
    },
    "German": {
        "der",
        "die",
        "das",
        "den",
        "dem",
        "des",
        "ein",
        "eine",
        "einer",
        "eines",
        "einem",
        "kein",
        "keine",
        "keinen",
        "und",
        "oder",
        "aber",
        "denn",
        "weil",
        "dass",
        "nicht",
        "ist",
        "sind",
        "war",
        "waren",
        "wird",
        "werden",
        "wurde",
        "wurden",
        "bei",
        "aus",
        "nach",
        "über",
        "unter",
        "vor",
        "für",
        "mit",
        "von",
        "zu",
        "zum",
        "zur",
        "im",
        "am",
        "an",
        "auf",
        "um",
        "auch",
        "noch",
        "schon",
        "sehr",
        "wie",
        "wo",
        "wer",
        "was",
        "wir",
        "ich",
        "du",
        "sie",
        "es",
        "man",
        "so",
        "in",
        "mir",
        "mich",
        "dir",
        "dich",
        "sich",
        "mein",
        "meine",
        "dein",
        "deine",
        "sein",
        "seine",
        "seinen",
        "ihr",
        "ihre",
        "ihren",
        "unser",
        "unsere",
        "habe",
        "hat",
        "haben",
        "hatte",
        "kann",
        "können",
        "muss",
        "müssen",
        "möchte",
        "möchten",
        "heute",
        "morgen",
        "abend",
        "dort",
        "hier",
        "ja",
        "nein",
        "danke",
        "bitte",
        "leider",
        "dieser",
        "diese",
        "dieses",
        "diesen",
        "diesem",
    },
    "Spanish": {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "que",
        "y",
        "en",
        "es",
        "son",
        "está",
        "están",
        "estoy",
        "estamos",
        "era",
        "eran",
        "fue",
        "fueron",
        "ser",
        "estar",
        "soy",
        "por",
        "para",
        "con",
        "sin",
        "sobre",
        "entre",
        "hacia",
        "como",
        "pero",
        "más",
        "muy",
        "también",
        "ya",
        "no",
        "sí",
        "mal",
        "bien",
        "porque",
        "cuando",
        "dónde",
        "quién",
        "qué",
        "este",
        "esta",
        "estos",
        "estas",
        "ese",
        "esa",
        "esos",
        "esas",
        "yo",
        "tú",
        "usted",
        "ustedes",
        "nosotros",
        "nosotras",
        "vosotros",
        "ellos",
        "ellas",
        "le",
        "les",
        "lo",
        "me",
        "te",
        "se",
        "si",
        "mi",
        "mis",
        "tu",
        "tus",
        "su",
        "sus",
        "a",
        "hay",
        "hoy",
        "gracias",
        "siempre",
        "nunca",
        "gusta",
        "gustaría",
    },
    "French": {
        "le",
        "la",
        "les",
        "des",
        "une",
        "un",
        "du",
        "au",
        "aux",
        "de",
        "et",
        "ou",
        "est",
        "sont",
        "étais",
        "était",
        "étaient",
        "être",
        "suis",
        "sommes",
        "êtes",
        "ai",
        "a",
        "as",
        "ont",
        "mais",
        "donc",
        "or",
        "ni",
        "car",
        "que",
        "qui",
        "quoi",
        "où",
        "ne",
        "pas",
        "je",
        "tu",
        "il",
        "elle",
        "nous",
        "vous",
        "ils",
        "elles",
        "mon",
        "ma",
        "mes",
        "ton",
        "ta",
        "tes",
        "son",
        "sa",
        "ses",
        "notre",
        "nos",
        "votre",
        "vos",
        "leur",
        "leurs",
        "ce",
        "cet",
        "cette",
        "ces",
        "en",
        "on",
        "sur",
        "par",
        "pour",
        "avec",
        "dans",
        "chez",
        "sans",
        "entre",
        "sous",
        "vers",
        "plus",
        "moins",
        "très",
        "bien",
        "mal",
        "si",
        "y",
        "me",
        "te",
        "se",
        "lui",
        "eux",
        "tout",
        "tous",
        "toute",
        "toutes",
        "chaque",
        "ici",
        "là",
        "quand",
        "comme",
        "comment",
        "oui",
        "non",
    },
    "Portuguese": {
        "não",
        "você",
        "vocês",
        "isto",
        "isso",
        "estão",
        "estamos",
        "têm",
        "também",
        "muito",
        "muita",
        "muitos",
        "muitas",
        "então",
        "ainda",
        "sempre",
        "onde",
        "quando",
        "através",
        "embora",
        "portanto",
        "pela",
        "pelo",
        "num",
        "numa",
        "está",
        "já",
        "até",
        "porém",
        "obrigado",
        "obrigada",
        "a",
        "em",
        "mais",
    },
    "Dutch": {
        "het",
        "een",
        "van",
        "en",
        "is",
        "met",
        "voor",
        "op",
        "te",
        "dat",
        "niet",
        "ook",
        "maar",
        "zijn",
        "wordt",
        "kan",
        "als",
        "door",
        "bij",
        "uit",
        "naar",
        "over",
        "tot",
        "dan",
        "hun",
        "zich",
        "dit",
        "deze",
        "die",
        "geen",
        "wel",
        "wat",
        "wie",
        "waar",
        "toen",
        "omdat",
        "altijd",
        "hier",
        "man",
        "in",
    },
    "Danish": {
        "det",
        "den",
        "de",
        "og",
        "ikke",
        "med",
        "for",
        "er",
        "en",
        "et",
        "på",
        "til",
        "i",
        "som",
        "vil",
        "kan",
        "har",
        "være",
        "denne",
        "disse",
        "hvor",
        "når",
        "hvis",
        "der",
        "her",
        "nu",
        "også",
        "meget",
        "tak",
        "ja",
        "man",
    },
    "Swedish": {
        "det",
        "den",
        "de",
        "och",
        "inte",
        "att",
        "en",
        "ett",
        "på",
        "till",
        "i",
        "som",
        "är",
        "har",
        "kan",
        "vill",
        "vara",
        "denna",
        "dessa",
        "var",
        "när",
        "om",
        "där",
        "här",
        "nu",
        "också",
        "mycket",
        "tack",
        "ja",
        "man",
    },
    "Afrikaans": {
        "die",
        "en",
        "is",
        "van",
        "vir",
        "met",
        "op",
        "in",
        "te",
        "dat",
        "nie",
        "ook",
        "maar",
        "wat",
        "wie",
        "waar",
        "hier",
        "dit",
        "hierdie",
        "hy",
        "sy",
        "ons",
        "julle",
        "hulle",
        "kan",
        "sal",
        "moet",
        "wees",
        "goed",
        "dankie",
        "het",
    },
    "Vietnamese": {
        "của",
        "và",
        "là",
        "không",
        "có",
        "người",
        "những",
        "các",
        "cho",
        "với",
        "này",
        "được",
        "một",
        "tôi",
        "bạn",
        "nó",
        "họ",
        "sẽ",
        "từ",
        "đến",
        "trong",
        "trên",
        "về",
        "khi",
        "nhưng",
        "vì",
        "đã",
        "đang",
        "rất",
        "nhiều",
        "hơn",
        "hay",
        "nào",
        "đó",
        "phải",
        "như",
        "ở",
        "ra",
        "vào",
        "lại",
        "cũng",
        "thì",
        "mà",
    },
}

# Confidence thresholds for the Latin word check: a classification must
# accumulate this many marker hits AND beat the runner-up by this much,
# or the text is treated as undetermined (pass).
_MIN_MARKER_HITS = 2
_MARKER_MARGIN = 2

# Character ranges per script family (the 23-language constant needs
# exactly these; Latin includes the Vietnamese precomposed block).
_SCRIPT_RANGES = (
    ("Han", ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF))),
    ("Devanagari", ((0x0900, 0x097F),)),
    ("Bengali", ((0x0980, 0x09FF),)),
    ("Gujarati", ((0x0A80, 0x0AFF),)),
    ("Tamil", ((0x0B80, 0x0BFF),)),
    ("Telugu", ((0x0C00, 0x0C7F),)),
    ("Kannada", ((0x0C80, 0x0CFF),)),
    (
        "Arabic",
        (
            (0x0600, 0x06FF),
            (0x0750, 0x077F),
            (0x08A0, 0x08FF),
            (0xFB50, 0xFDFF),
            (0xFE70, 0xFEFF),
        ),
    ),
    ("Greek", ((0x0370, 0x03FF), (0x1F00, 0x1FFF))),
    ("Cyrillic", ((0x0400, 0x04FF), (0x0500, 0x052F))),
    ("Latin", ((0x0041, 0x024F), (0x1E00, 0x1EFF), (0x2C60, 0x2C7F))),
)

# Every language of the 23-language constant maps to its script; all
# Latin-script targets additionally have a _FUNCTION_MARKERS entry.
_TARGET_SCRIPT = {
    "Afrikaans": "Latin",
    "Arabic": "Arabic",
    "Bangla": "Bengali",
    "Chinese": "Han",
    "Danish": "Latin",
    "Dutch": "Latin",
    "English": "Latin",
    "French": "Latin",
    "German": "Latin",
    "Greek": "Greek",
    "Gujarati": "Gujarati",
    "Hindi": "Devanagari",
    "Kannada": "Kannada",
    "Marathi": "Devanagari",
    "Persian": "Arabic",
    "Portuguese": "Latin",
    "Russian": "Cyrillic",
    "Spanish": "Latin",
    "Swedish": "Latin",
    "Tamil": "Tamil",
    "Telugu": "Telugu",
    "Urdu": "Arabic",
    "Vietnamese": "Latin",
}


def _char_family(char) -> "str | None":
    """Return the script family name for a character, or None when unlisted."""
    try:
        code = ord(char)
        for family, ranges in _SCRIPT_RANGES:
            for low, high in ranges:
                if low <= code <= high:
                    return family
        return None
    except Exception:
        return None


def _dominant_script(text) -> "str | None":
    """Script family with the most letters, or None when no letter maps."""
    counts = {}
    for char in text:
        try:
            if not char.isalpha():
                continue
            family = _char_family(char)
        except Exception:
            continue
        if family:
            counts[family] = counts.get(family, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda item: item[1])[0]


def _classify_latin(text) -> "str | None":
    """Best Latin-language match for ``text``, or None when undetermined.

    Scores every marker set; a winner must reach _MIN_MARKER_HITS and
    beat the runner-up by _MARKER_MARGIN or the text stays undetermined.
    Never raises.
    """
    try:
        tokens = _WORD_RE.findall(text.casefold())
        if not tokens:
            return None
        ranked = sorted(
            (
                (language, sum(1 for tok in tokens if tok in markers))
                for language, markers in _FUNCTION_MARKERS.items()
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        if ranked[0][1] < _MIN_MARKER_HITS:
            return None
        if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < _MARKER_MARGIN:
            return None
        return ranked[0][0]
    except Exception:
        return None


def classify_language(text) -> "str | None":
    """Best-effort language of ``text`` for reporting, or None.

    Returns a language name for Latin-script text (via the function-word
    marker check) and the script-family name (e.g. ``"Han"``,
    ``"Devanagari"``) for non-Latin text; None for blank, letterless, or
    undetermined input. Pure; never raises. The gate itself uses
    :func:`is_target_language`, not this report helper.
    """
    try:
        if not isinstance(text, str) or not text:
            return None
        normalized = unicodedata.normalize("NFC", text.casefold())
        family = _dominant_script(normalized)
        if family is None:
            return None
        if family != "Latin":
            return family
        return _classify_latin(normalized)
    except Exception:
        return None


def is_target_language(text, language) -> bool:
    """Return True when ``text`` is in (or indistinguishable from) ``language``.

    The target-relative language-consistency check (see the design note
    above): script comparison first, then the Latin function-word check;
    undetermined cases pass. Blank/letterless text passes (blank/malformed
    cells are scored by their own kinds in run_matrix). Never raises.
    """
    try:
        if not isinstance(text, str) or not text.strip():
            return True
        normalized = unicodedata.normalize("NFC", text.casefold())
        family = _dominant_script(normalized)
        if family is None:
            return True
        target_script = _TARGET_SCRIPT.get(language)
        if target_script is None:
            # Unknown target: nothing to compare against — never guess.
            return True
        if family != target_script:
            return False
        if family != "Latin":
            return True
        guess = _classify_latin(normalized)
        return guess is None or guess == language
    except Exception:
        return True


def allowed_lang_failures(lang_total) -> int:
    """Allowed language mismatches for a run of ``lang_total`` cells.

    Owner threshold policy (2026-11-25): Lang passes at >=99% consistency
    with a one-cell floor — ``max(1, lang_total // 100)``. The exact
    consequences the gate implements:

    - 25 cells -> 1 allowed: a literal ">=99%" rule on a small matrix
      would be zero-tolerance in disguise (24/25 = 96% must not fail);
    - 115 cells -> 1 allowed: 114/115 = 99.1% passes, 113/115 = 98.3%
      fails;
    - larger matrices scale proportionally (200 -> 2, 300 -> 3, ...);
    - ``lang_total == 0`` -> allowed 1 with zero mismatches, so a run
      with no rendered cells passes (same as before the threshold).

    Pure; never raises.
    """
    try:
        return max(1, int(lang_total) // 100)
    except Exception:
        return 1


def lang_gate_ok(lang_total, mismatches) -> bool:
    """Return True when ``mismatches`` is within the Lang threshold.

    Lang passes iff ``mismatches <= allowed_lang_failures(lang_total)``
    where ``mismatches`` is the count of confident target-language
    mismatches (the ``lang_failures`` entries of a run summary, counted
    per failing field). Mismatches are printed/reported either way —
    this only decides the gate verdict. Pure; never raises.
    """
    try:
        return int(mismatches) <= allowed_lang_failures(lang_total)
    except Exception:
        return True


def _lang_mismatch_count(summary) -> int:
    """Mismatch count for a run summary.

    Prefers ``len(lang_failures)`` (the exact count the threshold rule
    keys on); falls back to ``lang_total - lang_ok`` for summaries that
    carry only the cell counts. Never raises.
    """
    try:
        failures = summary.get("lang_failures")
        if failures is not None:
            return len(failures)
        lang_total = int(summary.get("lang_total") or 0)
        lang_ok = int(summary.get("lang_ok") or 0)
        return max(0, lang_total - lang_ok)
    except Exception:
        return 0


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

    Returns ``{model: {valid, total, per_language, failures, echoes,
    lang_ok, lang_total, lang_failures}}`` where
    ``per_language`` maps each language name to its valid count,
    ``failures`` holds one ``{model, language, sentence_index}`` dict per
    invalid cell (sentence_index is 0-based), and ``echoes`` holds the same
    shape plus ``kind`` for JSON-valid cells that do not render the
    target: ``"echo"`` (rendered the input back), ``"blank"`` (empty
    formal string), or ``"malformed"`` (missing/non-string formal).
    All kinds count valid for the gate; all are unsupported for
    capability. Gate math is untouched.

    The language dimension (2026-11-25, informal-language blind spot):
    every JSON-valid cell whose ``kind`` is ``""`` (it rendered a usable,
    non-echo formal) is checked target-relatively on BOTH ``formal`` and
    ``informal`` via :func:`is_target_language`. ``lang_total`` counts
    those checked cells, ``lang_ok`` the ones where both fields pass, and
    ``lang_failures`` holds ``{model, language, sentence_index, field}``
    per failing field. Echo/blank/malformed cells stay out of the
    dimension (their kind already scores them); undetermined heuristic
    cases pass. Mismatches are scored against the Lang threshold in
    :func:`main` (``lang_failures <= max(1, lang_total // 100)`` — see
    :func:`allowed_lang_failures`); every mismatch is recorded here for
    reporting regardless of the verdict.
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
        echoes = []
        lang_failures = []
        valid = 0
        total = 0
        lang_ok = 0
        lang_total = 0
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
                    try:
                        formal = result.get("formal")
                    except Exception:
                        formal = None
                    if not isinstance(formal, str):
                        # Valid JSON with a missing/non-string formal: not
                        # blank and not an echo — its own malformed kind.
                        # Unreachable live (the pipeline normalizes to str);
                        # reachable via stubs and future service shapes.
                        kind = "malformed"
                    elif not formal.strip():
                        kind = "blank"
                    elif language != SOURCE_LANGUAGE and not is_supported(
                        result, sentence
                    ):
                        kind = "echo"
                    else:
                        kind = ""
                    if kind:
                        echoes.append(
                            {
                                "model": model,
                                "language": language,
                                "sentence_index": index,
                                "kind": kind,
                            }
                        )
                    else:
                        # Rendered cell: both text fields are checked
                        # against the target language (target-relative
                        # check — the informal-EN blind spot this closes).
                        # Mismatches are recorded per field and scored
                        # against the Lang threshold in main, not here.
                        lang_total += 1
                        try:
                            informal = result.get("informal")
                        except Exception:
                            informal = None
                        if not isinstance(informal, str):
                            informal = ""
                        cell_ok = True
                        if not is_target_language(formal, language):
                            cell_ok = False
                            lang_failures.append(
                                {
                                    "model": model,
                                    "language": language,
                                    "sentence_index": index,
                                    "field": "formal",
                                }
                            )
                        if not is_target_language(informal, language):
                            cell_ok = False
                            lang_failures.append(
                                {
                                    "model": model,
                                    "language": language,
                                    "sentence_index": index,
                                    "field": "informal",
                                }
                            )
                        if cell_ok:
                            lang_ok += 1
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
            "echoes": echoes,
            "lang_ok": lang_ok,
            "lang_total": lang_total,
            "lang_failures": lang_failures,
        }
    return results


def _code_for(language: str) -> str:
    """Return the blueprint code for a language name (name itself as fallback)."""
    try:
        return _LANGUAGE_CODES.get(language, language)
    except Exception:
        return language


def format_table(results, languages=None):
    """Return the gate table as markdown rows (header + one row per model).

    Columns: per-language valid cells, Valid, Lang (the target-language
    check: passed/checked rendered cells — ``-`` for summaries without
    the dimension), Score, Gate. Gate is FAIL when the JSON-valid math
    fails OR the Lang dimension exceeds its threshold (mismatches >
    ``max(1, lang_total // 100)`` — see :func:`allowed_lang_failures`).
    A row that passes overall with a non-zero (but within-threshold)
    mismatch count renders ``PASS (within threshold)`` so the softened
    verdict is unambiguous in logs; mismatches themselves always print
    as ``LANG-FAIL`` lines elsewhere regardless of the verdict.
    Counting bases deliberately differ: the Lang column counts CELLS
    (passed/checked) while the verdict counts failing FIELDS
    (``len(lang_failures)``), so a cell failing both fields can render
    ``24/25`` alongside a FAIL — per-field counting is the stricter
    basis and can only ever over-flag a fully broken cell, never hide
    one behind the one-cell floor.
    """
    if languages is None:
        languages = MATRIX_LANGUAGES
    else:
        languages = list(languages)
    header = (
        "| Model | "
        + " | ".join(_code_for(language) for language in languages)
        + " | Valid | Lang | Score | Gate |"
    )
    separator = "|" + "---|" * (len(languages) + 5)
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
        lang_total = summary.get("lang_total")
        lang_ok = summary.get("lang_ok")
        if lang_total is None:
            lang_cell = "-"
            lang_fail = False
            lang_within = False
        else:
            lang_cell = "{}/{}".format(lang_ok, lang_total)
            mismatches = _lang_mismatch_count(summary)
            lang_fail = not lang_gate_ok(lang_total, mismatches)
            lang_within = not lang_fail and mismatches > 0
        try:
            score = "{}%".format(round(100 * valid / total)) if total else "0%"
        except Exception:
            score = "0%"
        gate = "PASS" if passes_gate(valid, total) and not lang_fail else "FAIL"
        if gate == "PASS" and lang_within:
            # Mismatches present but within threshold: label the verdict
            # so logs cannot be misread as a zero-mismatch run.
            gate = "PASS (within threshold)"
        lines.append(
            "| {} | {} | {}/{} | {} | {} | {} |".format(
                model, " | ".join(cells), valid, total, lang_cell, score, gate
            )
        )
    return "\n".join(lines)


def support_counts(summary, languages):
    """Map each language to its supported (valid non-echo) cell count."""
    try:
        per_language = summary.get("per_language", {})
    except Exception:
        per_language = {}
    try:
        echoes = summary.get("echoes", [])
    except Exception:
        echoes = []
    echo_per_language: dict = {}
    for echo in echoes or []:
        try:
            language = echo.get("language")
            echo_per_language[language] = echo_per_language.get(language, 0) + 1
        except Exception:
            pass
    return {
        language: max(
            0, per_language.get(language, 0) - echo_per_language.get(language, 0)
        )
        for language in languages
    }


def format_support_table(results, languages=None):
    """Return the capability table as markdown rows, models ranked best-first.

    Cells are supported/total per language (valid non-echo cells); the
    trailing column totals supported cells for the max-languages ranking.
    Pure rescoring of gate results — no extra LLM calls.
    """
    if languages is None:
        languages = MATRIX_LANGUAGES
    else:
        languages = list(languages)
    header = (
        "| Model | "
        + " | ".join(_code_for(language) for language in languages)
        + " | Supported |"
    )
    separator = "|" + "---|" * (len(languages) + 2)
    ranked = sorted(
        results.items(),
        key=lambda item: (
            sum(support_counts(item[1], languages).values()),
            item[1].get("valid", 0) if isinstance(item[1], dict) else 0,
        ),
        reverse=True,
    )
    lines = [header, separator]
    for model, summary in ranked:
        supported = support_counts(summary, languages)
        cells = [
            "{}/{}".format(supported.get(language, 0), len(SENTENCES))
            for language in languages
        ]
        lines.append(
            "| {} | {} | {} |".format(model, " | ".join(cells), sum(supported.values()))
        )
    return "\n".join(lines)


def record_support(results, path, date=None, languages=None, label=None):
    """Append the dated capability section to the model-quality research file.

    Append-only like :func:`record_results` and under its own label, so
    gate sections keep their exact shape. Lists every unsupported cell
    (model, language, sentence, kind) — the per-language evidence. Pass
    ``label`` to discriminate same-day re-runs (e.g. corrected reruns);
    without it same-day sections share a heading, so prefer distinct
    labels when re-running. Returns the path written.
    """
    if date is None:
        date = datetime.date.today().isoformat()
    if languages is None:
        languages = MATRIX_LANGUAGES
    else:
        languages = list(languages)
    if label is None:
        label = "Model capability — support matrix"
    lines = [
        "",
        "## {} ({})".format(label, date),
        "",
        "Supported = JSON-valid with a usable formal that differs from the "
        "input sentence (echo/blank/malformed cells prove the model did "
        "not render the target). Rescored from the gate run above — no "
        "extra calls.",
        "",
        format_support_table(results, languages),
        "",
    ]
    echoes = [
        echo for summary in results.values() for echo in summary.get("echoes", [])
    ]
    if echoes:
        lines.append("Unsupported cells (valid JSON, target not rendered):")
        lines.append("")
        for echo in echoes:
            try:
                kind = echo.get("kind", "echo")
            except Exception:
                kind = "echo"
            lines.append(
                "- {} {} | {} | sentence {}".format(
                    str(kind).upper(),
                    echo.get("model"),
                    echo.get("language"),
                    echo.get("sentence_index", 0) + 1,
                )
            )
        lines.append("")
    else:
        lines.append("No unsupported cells — every valid cell rendered the target.")
        lines.append("")
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return path


def record_results(results, path, date=None, languages=None, label=None):
    """Append the dated gate section to the model-quality research file.

    Append-only: existing content is never read or rewritten. Adds the
    per-model table plus a one-line failure detail per invalid cell
    (model, language, sentence index) and, when the run produced any, a
    language-mismatch detail per failing field (the Lang dimension —
    section shape is unchanged for clean runs). Mismatches are appended
    even when they sit within the Lang threshold: reporting never depends
    on the verdict (see :func:`allowed_lang_failures`). Defaults preserve
    the exact E1 section shape; pass ``languages`` plus ``label`` for
    wider gates. Returns the path written.
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
        lines.append("No invalid cells — every cell JSON-valid.")
        lines.append("")
    lang_failures = [
        mismatch
        for summary in results.values()
        for mismatch in summary.get("lang_failures", [])
    ]
    if lang_failures:
        lines.append(
            "Language mismatches (target-relative check on formal+informal "
            "— reported always; the gate fails only over the Lang "
            "threshold):"
        )
        lines.append("")
        for mismatch in lang_failures:
            lines.append(
                "- LANG-FAIL {} | {} | {} | sentence {}".format(
                    mismatch.get("model"),
                    mismatch.get("language"),
                    mismatch.get("field"),
                    mismatch.get("sentence_index", 0) + 1,
                )
            )
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
    parser.add_argument(
        "--capability",
        action="store_true",
        help=(
            "Also score target-language support (valid non-echo cells), "
            "print the ranked support table, and append a capability "
            "section to the research file. Model-comparison pack: combine "
            "with --models and --languages. Never affects the gate."
        ),
    )
    parser.add_argument(
        "--label",
        default=None,
        help=(
            "Custom section label for the appended research.md sections "
            "(gate and capability alike). Without it same-day re-runs "
            "share a heading and cannot be told apart — always pass one "
            "when re-running."
        ),
    )
    return parser.parse_args(argv)


def main(argv=None, translate_fn=None):
    """Wire --models/--research-path/--languages; exit 0 iff the gate passes.

    ``translate_fn`` is injectable for offline tests (same signature as
    ``translate_text``); the CLI path always uses the live service.

    Exit gate = >=95% JSON-valid AND target-language mismatches within
    threshold (the Lang column passes iff ``lang_failures <= max(1,
    lang_total // 100)`` — see :func:`allowed_lang_failures`; an
    over-threshold model fails the run with ``EXIT_GATE_FAIL``). Every
    mismatch still prints as a ``LANG-FAIL`` line and is appended to the
    research block either way; a within-threshold run reports PASS with
    its table row labeled ``(within threshold)``.
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
    if getattr(args, "label", None):
        label = args.label
        cap_label = "{} — capability".format(args.label)
    else:
        # Default runs stamp the wall-clock time into the label so
        # same-day re-runs never share a heading in the append-only file.
        try:
            stamp = datetime.datetime.now().strftime("%H:%M")
        except Exception:
            stamp = "rerun"
        if languages == MATRIX_LANGUAGES:
            label = "E1 gate — 5x5 smoke"
        elif len(languages) == len(ALL_LANGUAGES):
            label = "E4 gate — {}x{} full matrix".format(len(languages), len(SENTENCES))
        else:
            label = "E4 gate — {}x{} matrix".format(len(languages), len(SENTENCES))
        label = "{} {}".format(label, stamp)
        cap_label = "{} — capability".format(label)

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
    for summary in results.values():
        for mismatch in summary.get("lang_failures", []):
            print(
                "LANG-FAIL {} | {} | {} | sentence {}".format(
                    mismatch.get("model"),
                    mismatch.get("language"),
                    mismatch.get("field"),
                    mismatch.get("sentence_index", 0) + 1,
                )
            )
    record_results(results, args.research_path, languages=languages, label=label)
    print("")
    print("Appended gate section to {}".format(args.research_path))
    if getattr(args, "capability", False):
        print("")
        print("Support matrix (valid non-echo cells — which model renders what):")
        print("")
        print(format_support_table(results, languages))
        print("")
        record_support(
            results, args.research_path, languages=languages, label=cap_label
        )
        print("Appended capability section to {}".format(args.research_path))
    failed = [
        model
        for model, summary in results.items()
        if not passes_gate(summary.get("valid", 0), summary.get("total", 0))
        or not lang_gate_ok(summary.get("lang_total", 0), _lang_mismatch_count(summary))
    ]
    if failed:
        print(
            "Gate FAIL (<95% JSON-valid or target-language mismatches over "
            "the Lang threshold): {}".format(", ".join(failed))
        )
        return EXIT_GATE_FAIL
    print(
        "Gate PASS (>=95% JSON-valid and target-language mismatches within "
        "the Lang threshold) for every model."
    )
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
