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

WIRING_HINT = "Something's off with this view — restart the app."
"""View-wiring break notice: result parsed fine, controls missing."""
