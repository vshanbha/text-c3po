"""Audio/video file decode into the shared ASR entry point (E2-4).

ffmpeg decodes containers into 16 kHz mono s16le WAV bytes — the same
shape the VAD chunker emits — so file mode feeds the identical
transcribe path with no capture device present. Unsupported containers
error readably before any subprocess or ASR call. Nothing here raises.
"""

import os
import subprocess

SUPPORTED_EXTENSIONS = (".mp3", ".wav", ".m4a", ".mp4")

NOT_FOUND_MESSAGE = "Pick a file first."
MISSING_MESSAGE = "File not found: {}."
UNSUPPORTED_MESSAGE = "Unsupported container '{}' \u2014 use mp3, wav, m4a or mp4."
NO_FFMPEG_MESSAGE = (
    "ffmpeg not found \u2014 install it with `brew install ffmpeg`, then retry."
)
DECODE_FAILED_MESSAGE = "Could not decode '{}'."
EMPTY_MESSAGE = "Decoded '{}' to empty audio."


def supported_extensions() -> tuple:
    """Return the accepted container extensions. Never raises."""
    try:
        return tuple(SUPPORTED_EXTENSIONS)
    except Exception:
        return (".mp3", ".wav", ".m4a", ".mp4")


def decode_to_wav(path, ffmpeg_exe="ffmpeg", run_fn=None) -> dict:
    """Decode ``path`` to WAV bytes; ``{"wav"}`` or ``{"error", "retryable"}``.

    ``run_fn`` is injectable for headless tests (receives the argv, returns
    an object with ``returncode``/``stdout``/``stderr``). Never raises.
    """
    try:
        if not path or not isinstance(path, str):
            return {"error": NOT_FOUND_MESSAGE, "retryable": False}
        try:
            if not os.path.isfile(path):
                return {"error": MISSING_MESSAGE.format(path), "retryable": False}
        except Exception:
            return {"error": MISSING_MESSAGE.format(path), "retryable": False}
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return {
                "error": UNSUPPORTED_MESSAGE.format(ext or path),
                "retryable": False,
            }
        argv = [
            ffmpeg_exe or "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            path,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            "-",
        ]
        runner = run_fn or (lambda a: subprocess.run(a, capture_output=True))
        try:
            completed = runner(argv)
        except FileNotFoundError:
            return {"error": NO_FFMPEG_MESSAGE, "retryable": True}
        except Exception:
            return {
                "error": DECODE_FAILED_MESSAGE.format(path),
                "retryable": True,
            }
        try:
            code = completed.returncode
            out = completed.stdout or b""
        except Exception:
            return {
                "error": DECODE_FAILED_MESSAGE.format(path),
                "retryable": True,
            }
        if code != 0:
            detail = ""
            try:
                err = (completed.stderr or b"").decode("utf-8", "replace").strip()
                if err:
                    detail = ": " + err.splitlines()[-1][:200]
            except Exception:
                detail = ""
            return {
                "error": DECODE_FAILED_MESSAGE.format(path) + detail,
                "retryable": False,
            }
        if not out:
            return {"error": EMPTY_MESSAGE.format(path), "retryable": False}
        return {"wav": bytes(out)}
    except Exception:
        return {"error": DECODE_FAILED_MESSAGE.format(path), "retryable": True}
