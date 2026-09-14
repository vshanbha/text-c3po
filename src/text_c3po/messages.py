"""Single-sourced user-facing message strings (D9).

Every human-readable message the app renders lives here exactly once;
product layers import (never retype) them. Rationale: duplicated
wording drifts silently, and drift here is behavioral, not cosmetic —
the copy guard compares control text against these constants, so a
reworded copy that no longer matches becomes copyable error prose.
Leaf module: imports nothing, so services, runtimes-adjacent code,
and UI can all depend on it without layer cycles.
"""

RETRY_HINT = "Couldn't parse that one. Retry."
"""Transport/parse failure placeholder plus retry affordance copy."""

EMPTY_INPUT_HINT = "Type or paste something first."
"""Empty-translate guard hint."""

NO_VARIANT_HINT = "No separate informal version for this translation — see Formal."
"""Non-error placeholder: good formal, no separate informal variant."""

TRUNCATED_INFORMAL_HINT = "Informal unavailable — output was cut short."
"""Truncation placeholder: informal missing because the stream was cut,
not because the language lacks the distinction (see NO_VARIANT_HINT)."""

WIRING_HINT = "Something's off with this view — restart the app."
"""View-wiring break notice: result parsed fine, controls missing."""

LOOP_MESSAGE = "Translation degenerated into repetition — try rephrasing the input."
"""Loop-detector rejection: output loops while the input does not."""

TRUNCATED_TALLY = "Partial · {} chars (output limit — shorten input for the full text)."
"""Status tally for ceiling-cut partial renders (has a count slot)."""

DISCONNECT_SNACKBAR_HINT = "Ollama disconnected — start it with `ollama serve`."
"""Background-poll disconnect notice with the one-tap fix."""

MISSING_TARGET_MESSAGE = "Pick a target language first."
"""Translate called without a target language."""

MISSING_MODEL_MESSAGE = "Pick a model first."
"""Translate called without a model selected."""

NO_SPEECH_MESSAGE = "No speech found in that file."
"""Whisper returned blank audio on a file decode."""
