"""whisper-server transcribe client over loopback HTTP using stdlib only.

POSTs WAV bytes as multipart ``file`` to ``/inference`` (transcribe mode
is server-side: the manager never passes ``--translate``) and returns the
verbatim ``text``. Transport failures, timeouts, and malformed bodies
yield ``{"error", "retryable"}`` and never raise.
"""

import json
import urllib.request
import uuid

from .process_manager import WHISPER_HOST, WHISPER_INFERENCE_PATH, WHISPER_PORT

WHISPER_INFERENCE_URL = "http://{}:{}{}".format(
    WHISPER_HOST, WHISPER_PORT, WHISPER_INFERENCE_PATH
)
TRANSCRIBE_TIMEOUT_S = 120.0
TRANSPORT_MESSAGE = "Couldn't reach whisper-server. Retry."


def _multipart_wav(wav_bytes: bytes):
    """Return (body, content_type) for a single-file multipart POST."""
    boundary = uuid.uuid4().hex
    head = (
        "--" + boundary + "\r\n"
        'Content-Disposition: form-data; name="file"; filename="u.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n"
    ).encode("ascii")
    tail = ("\r\n--" + boundary + "--\r\n").encode("ascii")
    return head + bytes(wav_bytes) + tail, ("multipart/form-data; boundary=" + boundary)


def transcribe_wav(wav_bytes, inference_url=None, urlopen_fn=None) -> dict:
    """Transcribe WAV bytes; ``{"text"}`` or ``{"error", "retryable"}``.

    ``urlopen_fn`` is injectable for headless tests (receives the request,
    returns an object with ``.read()``). Never raises.
    """
    try:
        if not wav_bytes:
            return {"error": TRANSPORT_MESSAGE, "retryable": True}
        url = inference_url or WHISPER_INFERENCE_URL
        try:
            body, content_type = _multipart_wav(wav_bytes)
        except Exception:
            return {"error": TRANSPORT_MESSAGE, "retryable": True}
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": content_type}
        )
        opener = urlopen_fn or (
            lambda req: urllib.request.urlopen(req, timeout=TRANSCRIBE_TIMEOUT_S)
        )
        try:
            response = opener(request)
            raw = response.read()
        except Exception:
            return {"error": TRANSPORT_MESSAGE, "retryable": True}
        try:
            payload = json.loads(raw)
        except Exception:
            return {"error": TRANSPORT_MESSAGE, "retryable": True}
        if not isinstance(payload, dict):
            return {"error": TRANSPORT_MESSAGE, "retryable": True}
        text = payload.get("text")
        if not isinstance(text, str):
            return {"error": TRANSPORT_MESSAGE, "retryable": True}
        return {"text": text.strip()}
    except Exception:
        return {"error": TRANSPORT_MESSAGE, "retryable": True}
