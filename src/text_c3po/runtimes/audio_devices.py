"""Local capture-device enumeration over ffmpeg avfoundation (D7-A).

Lists input-capable audio devices verbatim each launch by parsing
``ffmpeg -f avfoundation -list_devices true -i ""`` (macOS; the device
table prints to stderr), intersected with ``system_profiler
SPAudioDataType`` input-channel counts so output-only devices
(speakers) stay out of the picker per TEST-PLAN C1. BlackHole appears
only when present (no special-casing: it is just another device in the
list). Any missing binary, query failure, or malformed entry yields []
and never raises, so the app always starts and the file-upload path
keeps working without a capture device.

Device identity is the avfoundation *audio index* (stable per
enumeration); names are display-only. ``device_index`` resolves a picker
name back to its index so capture opens ``-i ":<index>"`` instead of
relying on ffmpeg name resolution (duplicate/aggregate names collide).
"""

import json
import re
import subprocess
import threading
import time

LIST_TIMEOUT_S = 10.0

# Short-lived cache: one enumeration costs two subprocesses (ffmpeg plus
# system_profiler, ~1 s together), and Start re-resolves the device index
# right after launch enumeration. Cached on the production path only
# (run_fn=None) so injected test doubles always run fresh. Never raises.
_CACHE_TTL_S = 60.0
_cache = {"at": 0.0, "devices": []}
_cache_lock = threading.Lock()

_AUDIO_SECTION_MARKER = "AVFoundation audio devices:"
_VIDEO_SECTION_MARKER = "AVFoundation video devices:"
# ffmpeg prefixes every -list_devices line with its log tag
# ("[AVFoundation indev @ 0x...] [0] Name"), so anchor on the trailing
# "[index] name" instead of the line start.
_DEVICE_LINE_RE = re.compile(r"\]\s+\[(\d+)\]\s+(.+?)\s*$")


def _run(argv, run_fn=None):
    """Run ``argv`` via ``run_fn`` or subprocess; return completed or None."""
    try:
        runner = run_fn or (
            lambda a: subprocess.run(a, capture_output=True, timeout=LIST_TIMEOUT_S)
        )
        return runner(argv)
    except Exception:
        return None


def _query_raw_devices(run_fn=None):
    """Return ffmpeg -list_devices stderr text, or None when unavailable.

    ``run_fn`` is injectable for headless tests (receives the argv,
    returns an object with ``stderr``); the default runs ffmpeg with a
    short timeout. Never raises.
    """
    try:
        argv = [
            "ffmpeg",
            "-hide_banner",
            "-f",
            "avfoundation",
            "-list_devices",
            "true",
            "-i",
            "",
        ]
        completed = _run(argv, run_fn=run_fn)
        if completed is None:
            return None
        try:
            err = completed.stderr
        except Exception:
            return None
        if err is None:
            return None
        if isinstance(err, bytes):
            try:
                return err.decode("utf-8", "replace")
            except Exception:
                return None
        if isinstance(err, str):
            return err
        return None
    except Exception:
        return None


def _parse_audio_devices(text):
    """Parse (index, name) audio devices from -list_devices output.

    Only lines after the ``AVFoundation audio devices:`` marker count —
    video devices share the same ``[N] name`` shape with overlapping
    indexes and must never leak into the picker. Returns [] on malformed
    input; never raises.
    """
    try:
        if not isinstance(text, str) or not text:
            return []
        in_audio = False
        devices = []
        for raw_line in text.splitlines():
            try:
                line = raw_line.strip()
            except Exception:
                continue
            if _AUDIO_SECTION_MARKER in line:
                in_audio = True
                continue
            if _VIDEO_SECTION_MARKER in line:
                in_audio = False
                continue
            if not in_audio:
                continue
            match = _DEVICE_LINE_RE.search(line)
            if not match:
                continue
            try:
                index = int(match.group(1))
            except Exception:
                continue
            name = match.group(2)
            if not isinstance(name, str) or not name:
                continue
            devices.append((index, name))
        return devices
    except Exception:
        return []


def _query_input_names(run_fn=None):
    """Return (capable, seen) profiler name sets, or None when unusable.

    ``capable`` holds names with >0 input channels; ``seen`` holds every
    device name the profiler reported. Callers keep a device when it is
    capable OR unseen (naming skew must never hide a mic); only devices
    positively identified as output-only drop out. None means "unknown,
    keep everything" so one bad source never empties the picker. Never
    raises.
    """
    try:
        completed = _run(["system_profiler", "SPAudioDataType", "-json"], run_fn=run_fn)
        if completed is None:
            return None
        try:
            raw = completed.stdout
        except Exception:
            return None
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8", "replace")
            except Exception:
                return None
        if not isinstance(raw, str) or not raw:
            return None
        try:
            doc = json.loads(raw)
        except Exception:
            return None
        try:
            groups = doc.get("SPAudioDataType") or []
        except Exception:
            return None
        capable = set()
        seen = set()
        seen_any = False
        try:
            items_iter = list(groups)
        except Exception:
            return None
        for group in items_iter:
            try:
                items = group.get("_items") or []
            except Exception:
                continue
            try:
                entries = list(items)
            except Exception:
                continue
            for entry in entries:
                try:
                    name = entry.get("_name")
                    inputs = entry.get("coreaudio_device_input")
                except Exception:
                    continue
                if not isinstance(name, str) or not name:
                    continue
                seen_any = True
                seen.add(name)
                try:
                    if isinstance(inputs, bool):
                        continue
                    if isinstance(inputs, (int, float)) and inputs > 0:
                        capable.add(name)
                except Exception:
                    continue
        if not seen_any:
            return None
        return (capable, seen)
    except Exception:
        return None


def _query_audio_devices(run_fn=None):
    """Return [(index, name)] input-capable audio devices, or [] when unavailable."""
    try:
        if run_fn is None:
            try:
                now = time.monotonic()
            except Exception:
                now = 0.0
            try:
                with _cache_lock:
                    at = _cache.get("at", 0.0)
                    devices = _cache.get("devices")
                if now - at < _CACHE_TTL_S and isinstance(devices, list):
                    return list(devices)
            except Exception:
                pass
        text = _query_raw_devices(run_fn=run_fn)
        if text is None:
            return []
        parsed = _parse_audio_devices(text)
        tri = _query_input_names(run_fn=run_fn)
        if tri is None:
            result = parsed
        else:
            try:
                capable, seen = tri
                result = [(i, n) for i, n in parsed if n in capable or n not in seen]
            except Exception:
                result = parsed
        if run_fn is None and result:
            try:
                with _cache_lock:
                    _cache["at"] = time.monotonic()
                    _cache["devices"] = list(result)
            except Exception:
                pass
        return result
    except Exception:
        return []


def list_devices(run_fn=None) -> list[str]:
    """Return verbatim input-capable audio device names, or [] when unavailable.

    Never raises: missing ffmpeg, query failures, and malformed entries
    all yield [].
    """
    try:
        return [name for _, name in _query_audio_devices(run_fn=run_fn)]
    except Exception:
        return []


def device_index(name, run_fn=None):
    """Return the avfoundation audio index for ``name``, or None.

    First exact match wins (mirrors the picker's verbatim names). Pure
    lookup over a fresh query; never raises.
    """
    try:
        if not isinstance(name, str) or not name:
            return None
        for index, listed in _query_audio_devices(run_fn=run_fn):
            try:
                if listed == name:
                    return int(index)
            except Exception:
                continue
        return None
    except Exception:
        return None


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
