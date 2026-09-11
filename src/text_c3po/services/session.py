"""Live-session controller (E3-1): owned caption list plus utterance queue.

The single owner of the ordered in-memory caption list (AD-3). Pipeline
threads never touch Flet controls (AD-4): they post lightweight
``{text, source_lang}`` dicts via ``post_utterance`` and the main thread
alone calls ``drain``, which translates each entry and appends captions
in completion order. Malformed LLM output becomes a retryable error
caption, never raw payload to the UI (AD-5). Gaps (restart windows,
missed audio) are labeled rows, never silent drops.

Pure logic with stdlib only: clock and translate function injectable so
unit tests run headless and deterministic. Nothing here raises.
"""

import datetime
import queue

from text_c3po.services.translation import translate_text

UTTERANCE_CONTRACT_KEYS = ("text", "source_lang")


def _utcnow():
    """Return the current UTC time. Indirection point for tests."""
    try:
        return datetime.datetime.now(datetime.timezone.utc)
    except Exception:
        return datetime.datetime.now()


class SessionController:
    """Owns one live session: utterance queue in, ordered captions out."""

    def __init__(
        self,
        target_language="English",
        model=None,
        translate_fn=None,
        clock=None,
    ) -> None:
        self.target_language = target_language
        self.model = model
        self._translate_fn = translate_fn or translate_text
        self._clock = clock or _utcnow
        self._queue = queue.Queue()
        self._captions = []
        self._seq = 0
        self._active = False
        self._session_id = 0

    def start_session(self) -> int:
        """Begin a new session: clear captions, reset sequence. Never raises."""
        try:
            self._drain_queue()
            self._captions = []
            self._seq = 0
            self._active = True
            self._session_id += 1
            return self._session_id
        except Exception:
            return self._session_id

    def end_session(self) -> None:
        """Freeze the session: later posts are ignored. Never raises."""
        try:
            self._active = False
        except Exception:
            pass

    def is_active(self) -> bool:
        """True while a session is open. Never raises."""
        try:
            return bool(self._active)
        except Exception:
            return False

    def post_utterance(self, text, source_lang=None) -> bool:
        """Enqueue one utterance from any thread. Never raises.

        Blank payloads are dropped at the door (VAD already filters
        silence; double-guard here). Returns False when dropped or the
        session is closed.
        """
        try:
            if not self._active:
                return False
            if not isinstance(text, str) or not text.strip():
                return False
            self._queue.put({"text": text.strip(), "source_lang": source_lang})
            return True
        except Exception:
            return False

    def mark_gap(self, reason="missed audio") -> "dict | None":
        """Append a labeled gap row (restart windows, dropped audio).

        Never raises. Returns the gap caption, or None when closed.
        """
        try:
            if not self._active:
                return None
            self._seq += 1
            caption = {
                "seq": self._seq,
                "kind": "gap",
                "text": "…({})…".format(reason),
                "translation": "",
                "source_lang": "",
                "at": self._now_iso(),
            }
            self._captions.append(caption)
            return dict(caption)
        except Exception:
            return None

    def drain(self) -> list:
        """Translate every queued utterance, appending captions in order.

        Main-thread only by convention (AD-4). Translate failures become
        retryable error captions. Never raises. Returns the new captions.
        """
        added = []
        try:
            while True:
                try:
                    item = self._queue.get_nowait()
                except Exception:
                    break
                caption = self._render(item)
                if caption is not None:
                    self._captions.append(caption)
                    added.append(dict(caption))
        except Exception:
            pass
        return added

    def captions(self) -> list:
        """Return an immutable-feeling snapshot (copies) of the list."""
        try:
            return [dict(caption) for caption in self._captions]
        except Exception:
            return []

    def pending(self) -> int:
        """Return the queued utterance count. Never raises."""
        try:
            return self._queue.qsize()
        except Exception:
            return 0

    def _now_iso(self) -> str:
        try:
            moment = self._clock()
            return moment.isoformat(timespec="seconds")
        except Exception:
            return ""

    def _drain_queue(self) -> None:
        try:
            while True:
                self._queue.get_nowait()
        except Exception:
            pass

    def _render(self, item) -> "dict | None":
        """Translate one queued item into a caption dict. Never raises."""
        try:
            if not isinstance(item, dict):
                return None
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                return None
            source = item.get("source_lang") or ""
            try:
                result = self._translate_fn(
                    text.strip(), self.target_language, self.model
                )
            except Exception:
                result = {"error": "Couldn't parse that one. Retry.", "retryable": True}
            self._seq += 1
            if isinstance(result, dict) and result.get("error"):
                return {
                    "seq": self._seq,
                    "kind": "error",
                    "text": str(
                        result.get("error") or "Couldn't parse that one. Retry."
                    ),
                    "translation": "",
                    "source_lang": str(source),
                    "at": self._now_iso(),
                }
            formal = ""
            try:
                formal = result.get("formal", "") if isinstance(result, dict) else ""
            except Exception:
                formal = ""
            return {
                "seq": self._seq,
                "kind": "caption",
                "text": text.strip(),
                "translation": formal if isinstance(formal, str) else "",
                "source_lang": str(source),
                "at": self._now_iso(),
            }
        except Exception:
            return None
