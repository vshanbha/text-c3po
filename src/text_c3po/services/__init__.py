"""Services layer: session, translation, VAD, eval harness (AD-1).

Single import surface via lazy re-exports: ``from text_c3po.services import
translate_text`` works, while ``python -m text_c3po.services.eval_harness``
does not double-import the submodule (which emits a runpy RuntimeWarning).
"""

__all__ = [
    "Translation",
    "translate_text",
    "VadChunker",
    "frame_rms",
    "utterance_to_wav",
    "SENTENCES",
    "MATRIX_LANGUAGES",
    "GATE_THRESHOLD",
    "is_valid",
    "run_matrix",
    "format_table",
    "record_results",
]

_LAZY = {
    "Translation": ".translation",
    "translate_text": ".translation",
    "VadChunker": ".vad",
    "frame_rms": ".vad",
    "utterance_to_wav": ".vad",
    "SENTENCES": ".eval_harness",
    "MATRIX_LANGUAGES": ".eval_harness",
    "GATE_THRESHOLD": ".eval_harness",
    "is_valid": ".eval_harness",
    "run_matrix": ".eval_harness",
    "format_table": ".eval_harness",
    "record_results": ".eval_harness",
}


def __getattr__(name):
    """Lazily re-export service entry points (PEP 562). Never raises KeyError."""
    try:
        module_name = _LAZY[name]
    except KeyError:
        raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
    import importlib

    try:
        module = importlib.import_module(module_name, __name__)
        return getattr(module, name)
    except Exception as exc:
        raise AttributeError(
            "module {!r} has no attribute {!r} ({!r})".format(__name__, name, exc)
        )
