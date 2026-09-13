"""Live capture loop (E3-3): mic frames to controller posts.

One ``LiveRunner`` owns one capture run: frames from a sounddevice
``InputStream`` flow into a ``VadChunker``; each flushed utterance is
transcribed and posted to the ``SessionController`` queue (AD-4: the
runner never touches Flet controls — it only posts dicts and fires the
``on_utterance`` callback, and the UI layer renders from controller
snapshots). Transcribe failures become labeled gap rows (AD-8), never
silent drops.

``request_stop`` closes the stream and sets the event so capture halts
promptly (Stop < 2 s); an in-flight transcribe may still land its
utterance afterwards — capture stops, the pipeline drains. The stream
factory is injectable so unit tests run headless and deterministic with
zero audio hardware. Nothing here raises.
"""

import threading

from text_c3po.services.vad import FRAME_SAMPLES, VadChunker

SAMPLE_RATE = 16000
CHANNELS = 1


def open_input_stream(device=None, blocksize=FRAME_SAMPLES):
    """Open a 16 kHz mono int16 capture stream. Raises when unavailable."""
    import sounddevice as sd

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=blocksize,
        device=device,
    )
    try:
        stream.start()
    except Exception:
        try:
            stream.close()
        except Exception:
            pass
        raise
    return stream


def _frame_bytes(data) -> bytes:
    """Coerce one stream read to raw s16le bytes (ndarray or bytes)."""
    try:
        if data is None:
            return b""
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        to_bytes = getattr(data, "tobytes", None)
        if callable(to_bytes):
            return bytes(to_bytes())
        return bytes(data)
    except Exception:
        return b""


class LiveRunner:
    """Owns one capture→VAD→transcribe→post run for a live session."""

    def __init__(
        self,
        controller,
        device=None,
        source_lang=None,
        transcribe_fn=None,
        chunker=None,
        stream_factory=None,
        on_utterance=None,
        on_status=None,
    ) -> None:
        self.controller = controller
        self.device = device
        self.source_lang = source_lang
        self._transcribe_fn = transcribe_fn
        self._chunker = chunker or VadChunker()
        self._stream_factory = stream_factory
        self._on_utterance = on_utterance
        self._on_status = on_status
        self._stop_event = threading.Event()
        self._stream = None
        self._running = False

    def is_running(self) -> bool:
        """True while the run loop is active. Never raises."""
        try:
            return bool(self._running)
        except Exception:
            return False

    def was_stopped(self) -> bool:
        """True when a stop was latched (vs the stream ending on its own).

        Lets the UI tell user-initiated Stop apart from a died stream
        (unplugged device): the latter must reset the running chrome
        instead of lying "Live". Never raises.
        """
        try:
            return bool(self._stop_event.is_set())
        except Exception:
            return False

    def request_stop(self) -> None:
        """Halt capture promptly and latch stopped. Never raises.

        Abort-first (PortAudio's thread-safe abort) so a thread blocked
        in read() releases; the latch is never cleared, so stop-before-run
        and stop-then-rerun both stay stopped.
        """
        try:
            self._stop_event.set()
        except Exception:
            pass
        try:
            stream, self._stream = self._stream, None
            if stream is not None:
                try:
                    abort = getattr(stream, "abort", None)
                    if callable(abort):
                        abort()
                except Exception:
                    pass
                try:
                    stream.stop()
                except Exception:
                    pass
                try:
                    stream.close()
                except Exception:
                    pass
        except Exception:
            pass

    def _report_open(self, opened: bool, reason: str = "") -> None:
        try:
            callback = self._on_status
            if callable(callback):
                callback(bool(opened), reason)
        except Exception:
            pass

    def run(self) -> int:
        """Capture until stopped or the stream ends; return utterances posted.

        Returns 0 without starting when no stream is available (missing
        device, absent sounddevice) or a stop is latched. In-progress
        speech still buffered in the chunker flushes through transcribe
        on loop exit instead of dropping. Never raises.
        """
        try:
            if self._running:
                return 0
            if self._stop_event.is_set():
                self._report_open(False, "stop")
                return 0
            try:
                factory = self._stream_factory
                if factory is None:
                    stream = open_input_stream(device=self.device)
                else:
                    stream = factory(self.device)
            except Exception:
                self._report_open(False, "open-failed")
                return 0
            if stream is None:
                self._report_open(False, "open-failed")
                return 0
            self._stream = stream
            self._running = True
            self._report_open(True, "open")
            posted = 0
            try:
                while not self._stop_event.is_set():
                    try:
                        data, _overflow = stream.read(FRAME_SAMPLES)
                    except Exception:
                        break
                    raw = _frame_bytes(data)
                    if not raw:
                        continue
                    try:
                        utterances = self._chunker.feed(raw)
                    except Exception:
                        utterances = []
                    for wav in utterances:
                        if self._stop_event.is_set():
                            break
                        posted += self._submit(wav)
                # Flush in-progress speech even when stopping: a late post
                # lands only if the session is still open, otherwise the
                # closed session drops it — never wedged, never corrupt.
                try:
                    tail = self._chunker.flush()
                except Exception:
                    tail = None
                if tail:
                    posted += self._submit(tail)
            finally:
                self._running = False
                self._stream = None
                try:
                    stream.stop()
                except Exception:
                    pass
                try:
                    stream.close()
                except Exception:
                    pass
            return posted
        except Exception:
            try:
                self._running = False
            except Exception:
                pass
            return 0

    def _submit(self, wav: bytes) -> int:
        """Transcribe one utterance WAV and post it; gap on failure."""
        try:
            if self._transcribe_fn is None:
                return 0
            try:
                result = self._transcribe_fn(wav)
            except Exception:
                result = {"error": "whisper unreachable", "retryable": True}
            if isinstance(result, dict) and result.get("error"):
                try:
                    self.controller.mark_gap("whisper unreachable")
                except Exception:
                    pass
                posted = 0
            else:
                text = ""
                try:
                    text = result.get("text", "") if isinstance(result, dict) else ""
                except Exception:
                    text = ""
                # Blank transcripts are VAD-level silence, not missed
                # audio: post_utterance drops them without a gap row.
                if self.controller.post_utterance(
                    text if isinstance(text, str) else "", self.source_lang
                ):
                    posted = 1
                else:
                    posted = 0
            try:
                callback = self._on_utterance
                if callable(callback):
                    callback()
            except Exception:
                pass
            return posted
        except Exception:
            return 0
