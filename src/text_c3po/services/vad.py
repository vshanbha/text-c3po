"""RMS-silence utterance chunker (E2-2): port of the live-translate PoC VAD.

Segments a 16 kHz mono s16le PCM stream into utterances: a frame whose
int16 RMS is at or above ``silence_rms`` counts as speech, anything below
as silence. An utterance flushes after 2 consecutive silent frames (≈1 s
of trailing silence, kept in the payload) or when speech reaches
``max_utterance_s``. Leading silence is ignored.

Pure DSP with stdlib only (no numpy, no audio hardware): ``feed`` takes
one frame of raw bytes and returns completed utterances as immutable WAV
bytes ready to POST to whisper-server. Never raises on audio content —
short/odd-length frames are padded with silence, empty frames ignored.
"""

import io
import math
import struct
import wave

SAMPLE_RATE = 16000
FRAME_SAMPLES = SAMPLE_RATE // 2  # 0.5 s frames, matching the PoC
SILENCE_RMS = 350.0
MAX_UTTERANCE_S = 15.0
SILENCE_FRAMES_TO_FLUSH = 2


def frame_rms(frame: bytes) -> float:
    """Return the int16 RMS level of one raw s16le frame (0.0 when empty).

    Pure helper; never raises. Matches the PoC's
    ``sqrt(mean(square(int16)))`` math without numpy.
    """
    try:
        if not frame:
            return 0.0
        data = bytes(frame)
        if len(data) % 2:
            data += b"\x00"
        count = len(data) // 2
        if count == 0:
            return 0.0
        total = 0
        for (sample,) in struct.iter_unpack("<h", data):
            total += sample * sample
        return math.sqrt(total / count)
    except Exception:
        return 0.0


def utterance_to_wav(samples: list[int]) -> bytes:
    """Encode int16 samples as 16 kHz mono s16le WAV bytes. Never raises."""
    try:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(struct.pack("<" + "h" * len(samples), *samples))
        return buf.getvalue()
    except Exception:
        return b""


class VadChunker:
    """Stateful RMS-silence chunker; one instance owns one PCM stream."""

    def __init__(
        self,
        silence_rms: float = SILENCE_RMS,
        max_utterance_s: float = MAX_UTTERANCE_S,
        silence_frames_to_flush: int = SILENCE_FRAMES_TO_FLUSH,
    ) -> None:
        try:
            self.silence_rms = float(silence_rms)
        except Exception:
            self.silence_rms = SILENCE_RMS
        try:
            self.max_utterance_s = float(max_utterance_s)
        except Exception:
            self.max_utterance_s = MAX_UTTERANCE_S
        try:
            self.silence_frames_to_flush = max(1, int(silence_frames_to_flush))
        except Exception:
            self.silence_frames_to_flush = SILENCE_FRAMES_TO_FLUSH
        self._pending: list[int] = []
        self._speech_secs = 0.0
        self._silence_chunks = 0

    def _decode(self, frame: bytes) -> list[int]:
        """Decode one raw s16le frame to int16 samples; never raises."""
        try:
            data = bytes(frame or b"")
            if len(data) % 2:
                data += b"\x00"
            return [s for (s,) in struct.iter_unpack("<h", data)]
        except Exception:
            return []

    def _take_utterance(self) -> bytes:
        """Emit pending samples as WAV bytes and reset stream state."""
        try:
            payload = utterance_to_wav(self._pending)
        except Exception:
            payload = b""
        self._pending = []
        self._speech_secs = 0.0
        self._silence_chunks = 0
        return payload

    def feed(self, frame: bytes) -> list[bytes]:
        """Feed one raw s16le frame; return completed utterance WAVs (0..1).

        Never raises.
        """
        try:
            samples = self._decode(frame)
            if not samples:
                return []
            if frame_rms(frame) >= self.silence_rms:
                self._pending.extend(samples)
                self._speech_secs += len(samples) / SAMPLE_RATE
                self._silence_chunks = 0
            elif self._pending:
                self._pending.extend(samples)
                self._silence_chunks += 1
            else:
                return []
            if self._silence_chunks >= self.silence_frames_to_flush:
                return [self._take_utterance()]
            if self._speech_secs >= self.max_utterance_s:
                return [self._take_utterance()]
            return []
        except Exception:
            return []

    def flush(self) -> "bytes | None":
        """Emit any pending speech without waiting for trailing silence.

        Returns None when nothing is pending (leading silence or idle).
        Never raises.
        """
        try:
            if not self._pending:
                return None
            return self._take_utterance()
        except Exception:
            return None
