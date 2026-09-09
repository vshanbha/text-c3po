"""Local Ollama probe over loopback HTTP using stdlib only.

Queries http://127.0.0.1:11434/api/tags with a short timeout and reports a
plain (connected, models) pair. Any refused connection, timeout, or
malformed body yields connected=False and never raises.
"""

import json
import urllib.error
import urllib.request

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_TAGS_URL = OLLAMA_BASE_URL + "/api/tags"
PROBE_TIMEOUT_S = 2.0

DEFAULT_MODEL_PREFIX = "lfm2.5"


def pick_default_model(models) -> "str | None":
    """Return the default model pick: first ``lfm2.5*`` hit else first else None.

    Pure helper with no I/O; never raises. ``models`` is the verbatim
    ``/api/tags`` name list.
    """
    try:
        if not isinstance(models, list) or not models:
            return None
        for name in models:
            if isinstance(name, str) and name.startswith(DEFAULT_MODEL_PREFIX):
                return name
        first = models[0]
        return first if isinstance(first, str) else None
    except Exception:
        return None


def _fetch_tags_payload():
    """Return the decoded /api/tags body, or None when unreachable or non-JSON."""
    try:
        with urllib.request.urlopen(
            OLLAMA_TAGS_URL, timeout=PROBE_TIMEOUT_S
        ) as response:
            return json.load(response)
    except Exception:
        return None


def _verbatim_names(payload):
    """Return verbatim model names from a decoded body, or None when malformed."""
    if not isinstance(payload, dict):
        return None
    entries = payload.get("models")
    if not isinstance(entries, list):
        return None
    names = []
    for entry in entries:
        if not isinstance(entry, dict):
            return None
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            return None
        names.append(name)
    return names


def list_models() -> list[str]:
    """Return verbatim /api/tags model names, or [] when unreachable or malformed.

    Never raises.
    """
    try:
        payload = _fetch_tags_payload()
    except Exception:
        return []
    if payload is None:
        return []
    names = _verbatim_names(payload)
    return names if names is not None else []


def check_ollama() -> tuple[bool, list[str]]:
    """Probe the local runtime once; return (connected, models).

    connected is True only for a well-formed /api/tags body (an empty
    models list still counts as connected). Never raises: refused
    connections, timeouts, and malformed bodies yield (False, []).
    """
    try:
        payload = _fetch_tags_payload()
    except Exception:
        return (False, [])
    if payload is None:
        return (False, [])
    names = _verbatim_names(payload)
    if names is None:
        return (False, [])
    return (True, names)
