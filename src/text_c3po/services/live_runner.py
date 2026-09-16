"""Live capture loop (E3-3, D7-A): ffmpeg frames to controller posts.

One ``LiveRunner`` owns one capture run: PCM frames from an ffmpeg
avfoundation pipe (``-ac 1 -ar 16000 -f s16le -``, the live-translate
pattern) flow into a ``VadChunker``; each flushed utterance is
transcribed and posted to the ``SessionController`` queue (AD-4: the
runner never touches Flet controls — it only posts dicts and fires the
``on_utterance`` callback, and the UI layer renders from controller
snapshots). Transcribe failures become labeled gap rows (AD-8), never
silent drops.

``request_stop`` terminates the ffmpeg child and sets the event so
capture halts promptly (Stop < 2 s); an in-flight transcribe may still
land its utterance afterwards — capture stops, the pipeline drains. The
stream factory is injectable so unit tests run headless and deterministic
with zero audio hardware. Nothing here raises.
"""

import logging
import subprocess
import threading

from text_c3po.services.vad import FRAME_SAMPLES, VadChunker, frame_rms

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1

# Capture-open status reasons (closed world — app.py matches on these
# constants, never on literals, so a rename breaks loudly at import).
REASON_OPEN = "open"
REASON_OPEN_FAILED = "open-failed"
REASON_STOP = "stop"
REASON_NO_AUDIO = "no-audio"

# Digital-silence trip: consecutive exact-zero-RMS frames before the run
# ends itself. A live mic never reads true zero (noise floor); an
# unrouted BlackHole reads 0.0 forever — so this means "nothing is
# routed into the device", not "quiet room". 120 frames × 0.5 s ≈ 60 s:
# long enough to survive meeting pauses, short enough to fail visibly.
NO_AUDIO_FRAMES = 120

NO_FFMPEG_MESSAGE = "ffmpeg not found — install it with `brew install ffmpeg`."
NO_DEVICE_MESSAGE = "No capture device — plug in a mic, then retry."

# Pipes carry no sound-device overflow flag; reads are exact-sized.
_NO_OVERFLOW = False


class FfmpegPipeStream:
    """Duck-typed capture stream over an ffmpeg avfoundation stdout pipe.

    Satisfies the contract ``LiveRunner`` needs: ``read(n)`` returns
    ``(bytes, overflow)``, plus ``close``. ``close`` terminates the child
    so a thread blocked in ``read`` releases promptly. Idempotent
    teardown; never raises.
    """

    def __init__(self, proc) -> None:
        self._proc = proc
        try:
            self._stdout = proc.stdout
        except Exception:
            self._stdout = None
        self._closed = False
        self._lock = threading.Lock()

    def start(self) -> None:
        return None

    def read(self, n_frames):
        """Return exactly ``n_frames`` of s16le mono PCM plus no-overflow.

        Raises IOError on EOF (child died) so the capture loop breaks and
        reports the stream end instead of spinning on empty reads.
        Release chain: request_stop terminates the child (SIGKILL
        fallback), the dead child closes the pipe, the blocked read
        returns EOF. Only an unkillable driver deadlock outlives that —
        beyond app-level repair; the capture thread is a daemon, so the
        app itself survives it.
        """
        try:
            count = int(n_frames)
        except Exception:
            count = 0
        want = max(0, count) * 2
        if want <= 0:
            return b"", _NO_OVERFLOW
        out = self._stdout
        if out is None:
            raise IOError("ffmpeg pipe has no stdout")
        chunks = []
        while want > 0:
            try:
                chunk = out.read(want)
            except Exception as exc:
                raise IOError("ffmpeg pipe read failed: {}".format(exc))
            if not chunk:
                raise IOError("ffmpeg pipe closed")
            chunks.append(chunk)
            want -= len(chunk)
        return b"".join(chunks), _NO_OVERFLOW

    def close(self) -> None:
        self._terminate()

    def _terminate(self) -> None:
        try:
            with self._lock:
                if self._closed:
                    return
                self._closed = True
                proc, out = self._proc, self._stdout
                self._proc, self._stdout = None, None
            try:
                if out is not None:
                    out.close()
            except Exception as exc:
                # Absorbed by design (never-raises contract): terminate
                # follows regardless, and a broken pipe already ends the
                # capture loop via read() raising IOError on EOF.
                logger.debug("ffmpeg pipe close failed (absorbed): %r", exc)
            try:  # stderr is ours now (PIPE, not DEVNULL) — don't leak the fd
                err_pipe = getattr(proc, "stderr", None)
                if err_pipe is not None:
                    err_pipe.close()
            except Exception:
                pass
            if proc is None:
                return
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.wait(timeout=2.0)
                return
            except Exception:
                pass
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=2.0)
            except Exception:
                pass
        except Exception:
            pass


def _resolve_av_index(device):
    """Return the avfoundation audio index for ``device``, or None."""
    try:
        if isinstance(device, bool):
            return None
        if isinstance(device, int):
            return device if device >= 0 else None
        if isinstance(device, str) and device:
            from text_c3po.runtimes.audio_devices import device_index

            return device_index(device)
        return None
    except Exception:
        return None


def open_input_stream(device=None, popen_factory=None):
    """Open a 16 kHz mono s16le capture pipe. Raises when unavailable.

    Resolves ``device`` (picker name or avfoundation audio index) to
    ``-i ":<index>"`` and spawns ffmpeg; ffmpeg owns device open plus
    resample (native rate in, 16 kHz mono out). Falls back to ffmpeg name
    resolution when the index lookup misses. Raises OSError with a
    readable message when ffmpeg is absent, no device resolves, or the
    child dies instantly.
    """
    index = _resolve_av_index(device)
    if index is None and isinstance(device, str) and device:
        # Last resort (device renamed/unplugged since launch enumeration):
        # let ffmpeg resolve the name. Output-only names fail here, but
        # the instant-death check below converts that to the same clean
        # "Couldn't open" OSError (ffmpeg's stderr goes to the debug log
        # only, never to the user raw).
        logger.warning(
            "capture device %r not in current listing; "
            "falling back to ffmpeg name resolution",
            device,
        )
        selector = ":{}".format(device)
    elif index is not None:
        selector = ":{}".format(index)
    else:
        raise OSError(NO_DEVICE_MESSAGE)
    argv = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-loglevel",
        "error",
        "-f",
        "avfoundation",
        "-i",
        selector,
        "-ac",
        str(CHANNELS),
        "-ar",
        str(SAMPLE_RATE),
        "-f",
        "s16le",
        "-",
    ]
    factory = popen_factory or (
        lambda a: subprocess.Popen(a, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    )
    try:
        proc = factory(argv)
    except FileNotFoundError:
        raise OSError(NO_FFMPEG_MESSAGE)
    except OSError:
        raise
    except Exception as exc:
        raise OSError("Couldn't open {} ({})".format(device, exc))
    try:
        alive = proc.poll() is None
    except Exception:
        alive = True
    if not alive:
        try:
            proc.wait(timeout=2.0)
        except Exception:
            pass
        try:
            err_text = ""
            err_pipe = getattr(proc, "stderr", None)
            if err_pipe is not None:
                err_raw = err_pipe.read()
                if isinstance(err_raw, bytes):
                    err_text = err_raw.decode("utf-8", "replace").strip()
                elif isinstance(err_raw, str):
                    err_text = err_raw.strip()
        except Exception:
            err_text = ""
        if err_text:
            logger.debug("ffmpeg capture failed for %r: %s", device, err_text[-500:])
        raise OSError("Couldn't open {} — check the device, then retry.".format(device))
    return FfmpegPipeStream(proc)


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
        self._callback_threads = []
        self._callback_lock = threading.Lock()
        self._in_overflow = False
        # Why the run ended: None (running/stopped/stream-died) or
        # REASON_NO_AUDIO (digital-silence trip). Read by the UI layer
        # after run() returns; never raises.
        self.end_reason = None

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

        Closes the stream (terminating the child so its stdout closes,
        releasing a thread blocked in read()); the latch is never
        cleared, so stop-before-run and stop-then-rerun both stay
        stopped.
        """
        try:
            self._stop_event.set()
        except Exception:
            pass
        try:
            stream, self._stream = self._stream, None
            if stream is not None:
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
        device, absent ffmpeg) or a stop is latched. In-progress
        speech still buffered in the chunker flushes through transcribe
        on loop exit instead of dropping. Never raises.
        """
        try:
            if self._running:
                return 0
            if self._stop_event.is_set():
                self._report_open(False, REASON_STOP)
                return 0
            try:
                factory = self._stream_factory
                if factory is None:
                    stream = open_input_stream(device=self.device)
                else:
                    stream = factory(self.device)
            except Exception as exc:
                self._report_open(False, "{}: {}".format(REASON_OPEN_FAILED, exc))
                return 0
            if stream is None:
                self._report_open(False, REASON_OPEN_FAILED)
                return 0
            self._stream = stream
            self._running = True
            self._in_overflow = False
            self._report_open(True, REASON_OPEN)
            posted = 0
            zero_run = 0
            try:
                while not self._stop_event.is_set():
                    try:
                        data, overflow = stream.read(FRAME_SAMPLES)
                    except Exception:
                        break
                    if overflow:
                        if not self._in_overflow:
                            self._in_overflow = True
                            try:
                                self.controller.mark_gap("capture overflow")
                            except Exception:
                                pass
                            try:
                                callback = self._on_utterance
                                if callable(callback):
                                    self._fire_callback_async(callback)
                            except Exception:
                                pass
                    else:
                        self._in_overflow = False
                    raw = _frame_bytes(data)
                    if not raw:
                        continue
                    try:
                        silent = frame_rms(raw) <= 0.0
                    except Exception:
                        silent = False
                    if silent:
                        zero_run += 1
                        if zero_run >= NO_AUDIO_FRAMES:
                            self.end_reason = REASON_NO_AUDIO
                            logger.warning(
                                "no audio from %r for ~%ds — ending session",
                                self.device,
                                NO_AUDIO_FRAMES // 2,
                            )
                            break
                    else:
                        zero_run = 0
                    try:
                        utterances = self._chunker.feed(raw)
                    except Exception:
                        utterances = []
                    if utterances:
                        zero_run = 0
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
                    stream.close()
                except Exception:
                    pass
                self._join_callbacks()
            return posted
        except Exception:
            try:
                self._running = False
            except Exception:
                pass
            return 0

    def _fire_callback_async(self, callback) -> None:
        """Run the drain/render callback off the capture read path (E3-6).

        Capture keeps reading frames while an in-flight translation drains
        in a daemon thread. Callbacks are serialized through
        _callback_lock so concurrent workers cannot interleave
        sync_captions on the same pane (review #2). run() joins these
        before returning so unit callers observe fired callbacks
        deterministically. Prunes finished threads to bound growth
        (review #7). Never raises.
        """
        try:
            try:
                self._callback_threads = [
                    t for t in self._callback_threads if t.is_alive()
                ]
            except Exception:
                pass

            def _serialized() -> None:
                try:
                    with self._callback_lock:
                        callback()
                except Exception:
                    pass

            worker = threading.Thread(target=_serialized, daemon=True)
            try:
                self._callback_threads.append(worker)
            except Exception:
                pass
            worker.start()
        except Exception:
            try:
                callback()
            except Exception:
                pass

    def _join_callbacks(self) -> None:
        try:
            threads, self._callback_threads = list(self._callback_threads), []
        except Exception:
            return
        for worker in threads:
            try:
                worker.join(timeout=30)
            except Exception:
                pass

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
                    self._fire_callback_async(callback)
            except Exception:
                pass
            return posted
        except Exception:
            return 0
