"""Services layer: session, translation, VAD, eval harness (AD-1)."""

from .eval_harness import (
    GATE_THRESHOLD,
    MATRIX_LANGUAGES,
    SENTENCES,
    format_table,
    is_valid,
    record_results,
    run_matrix,
)
from .translation import Translation, translate_text

__all__ = [
    "Translation",
    "translate_text",
    "SENTENCES",
    "MATRIX_LANGUAGES",
    "GATE_THRESHOLD",
    "is_valid",
    "run_matrix",
    "format_table",
    "record_results",
]
