"""Local capture-device enumeration over sounddevice (stdlib-shaped wrapper).

Lists input-capable devices verbatim each launch. BlackHole appears only
when present (no special-casing: it is just another device in the list).
Any missing sounddevice/PortAudio, query failure, or malformed entry
yields [] and never raises, so the app always starts and the file-upload
path keeps working without a capture device.
"""


def _query_all_devices(query_fn=None):
    """Return the raw sounddevice device list, or None when unavailable.

    ``query_fn`` is injectable for headless tests; the default lazily
    imports sounddevice so a missing PortAudio never breaks module import.
    """
    try:
        if query_fn is not None:
            return query_fn()
        import sounddevice as sd

        return sd.query_devices()
    except Exception:
        return None


def _verbatim_input_names(raw):
    """Return verbatim names of input-capable devices, or None when malformed."""
    try:
        entries = list(raw)
    except Exception:
        return None
    names = []
    for entry in entries:
        try:
            name = entry.get("name") if isinstance(entry, dict) else entry.name
            inputs = (
                entry.get("max_input_channels")
                if isinstance(entry, dict)
                else entry.max_input_channels
            )
        except Exception:
            return None
        if not isinstance(name, str) or not name:
            return None
        if not isinstance(inputs, int) or inputs <= 0:
            continue
        names.append(name)
    return names


def list_devices(query_fn=None) -> list[str]:
    """Return verbatim input-capable device names, or [] when unavailable.

    Never raises: missing sounddevice/PortAudio, query failures, and
    malformed entries all yield [].
    """
    try:
        raw = _query_all_devices(query_fn)
    except Exception:
        return []
    if raw is None:
        return []
    names = _verbatim_input_names(raw)
    return names if names is not None else []


def has_blackhole(names) -> bool:
    """True when any listed device name contains 'blackhole' (case-insensitive).

    Pure helper with no I/O; never raises. Later stages use this to decide
    whether loopback capture is available.
    """
    try:
        if not isinstance(names, list):
            return False
        return any(isinstance(n, str) and "blackhole" in n.lower() for n in names)
    except Exception:
        return False


def pick_default_device(names) -> "str | None":
    """Return the default capture pick: first non-BlackHole input else first else None.

    Pure helper with no I/O; never raises. Prefers a microphone so live
    capture starts on mic with or without BlackHole present, without
    hard-coding any device name.
    """
    try:
        if not isinstance(names, list) or not names:
            return None
        for name in names:
            if isinstance(name, str) and name and "blackhole" not in name.lower():
                return name
        first = names[0]
        return first if isinstance(first, str) and first else None
    except Exception:
        return None
