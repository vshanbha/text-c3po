"""Shared ASR entry point (E2-4): file path to translated result.

One call runs the full file pipeline — ffmpeg decode, whisper-server
transcribe, LLM translate — reusing the E1 translation service so file
mode and (later) live mode share the identical ASR\u2192translate path.
Decode and transcribe stages are injectable for headless deterministic
tests; every failure surfaces as a readable ``{"error"}`` dict and never
raises.
"""

from text_c3po.runtimes.audio_file import decode_to_wav
from text_c3po.runtimes.whisper_client import transcribe_wav
from text_c3po.services.translation import translate_text

NO_SPEECH_MESSAGE = "No speech found in that file."
BLANK_MARKERS = ("[BLANK_AUDIO]",)


def _is_blank(text) -> bool:
    """True for empty transcripts and whisper blank-audio markers."""
    try:
        if not isinstance(text, str) or not text.strip():
            return True
        lowered = text.strip().lower()
        return any(marker.lower() in lowered for marker in BLANK_MARKERS)
    except Exception:
        return True


def transcribe_file(
    path,
    target_language,
    model,
    decode_fn=None,
    transcribe_fn=None,
    translate_fn=None,
) -> dict:
    """Transcribe ``path`` and translate it; translation-shaped result dict.

    Returns the ``translate_text`` result on success, else ``{"error",
    "retryable"}``. Never raises.
    """
    try:
        decode = decode_fn or decode_to_wav
        transcribe = transcribe_fn or transcribe_wav
        translate = translate_fn or translate_text
        try:
            decoded = decode(path)
        except Exception as exc:
            return {
                "error": "Could not decode '{}': {!r}".format(path, exc),
                "retryable": True,
            }
        if not isinstance(decoded, dict) or "wav" not in decoded:
            if isinstance(decoded, dict) and decoded.get("error"):
                return decoded
            return {"error": "Could not decode '{}'.".format(path), "retryable": True}
        try:
            result = transcribe(decoded["wav"])
        except Exception as exc:
            return {"error": "Couldn't reach whisper-server. Retry.", "retryable": True}
        if not isinstance(result, dict) or "text" not in result:
            if isinstance(result, dict) and result.get("error"):
                return result
            return {"error": "Couldn't reach whisper-server. Retry.", "retryable": True}
        if _is_blank(result.get("text")):
            return {"error": NO_SPEECH_MESSAGE, "retryable": False}
        try:
            return translate(result["text"], target_language, model)
        except Exception:
            return {"error": "Couldn't parse that one. Retry.", "retryable": True}
    except Exception:
        return {"error": "Couldn't parse that one. Retry.", "retryable": True}
