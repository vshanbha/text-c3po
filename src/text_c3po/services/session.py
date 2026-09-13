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
import threading

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
        # Serializes drain/mark_gap/retry/start_session: drain runs on the
        # capture thread while a caption retry may drain from another, and
        # unguarded seq assignment dropped rows (review). Posts stay
        # lock-free (queue.Queue is thread-safe).
        self._lock = threading.Lock()
        self._queue = queue.Queue()
        self._captions = []
        self._seq = 0
        self._active = False
        self._session_id = 0

    def start_session(self) -> int:
        """Begin a new session: clear captions, reset sequence. Never raises."""
        try:
            with self._lock:
                dropped = self._drain_queue()
                self._captions = []
                self._seq = 0
                self._active = True
                self._session_id += 1
                if dropped:
                    self._seq += 1
                    self._captions.append(
                        {
                            "seq": self._seq,
                            "kind": "gap",
                            "text": "…(session restarted, {} queued utterance{} discarded)…".format(
                                dropped, "" if dropped == 1 else "s"
                            ),
                            "translation": "",
                            "source_lang": "",
                            "at": self._now_iso(),
                        }
                    )
                return self._session_id
        except Exception:
            pass
        try:
            return self._session_id
        except Exception:
            return 0

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
        session is closed. Each item is tagged with the current session id
        (review #6) so a drain racing a restart drops stale utterances
        instead of landing them in the new session.
        """
        try:
            if not self._active:
                return False
            if not isinstance(text, str) or not text.strip():
                return False
            try:
                session = self._session_id
            except Exception:
                session = 0
            self._queue.put(
                {
                    "text": text.strip(),
                    "source_lang": source_lang,
                    "session": session,
                }
            )
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
            with self._lock:
                self._seq += 1
                seq = self._seq
                caption = {
                    "seq": seq,
                    "kind": "gap",
                    "text": "…({})…".format(reason),
                    "translation": "",
                    "source_lang": "",
                    "at": self._now_iso(),
                }
                try:
                    self._captions.append(caption)
                except Exception:
                    pass
            return dict(caption)
        except Exception:
            return None

    def drain(self) -> list:
        """Translate every queued utterance, appending captions in order.

        Main-thread only by convention (AD-4). Translate failures become
        retryable error captions. The lock covers seq-assign plus append
        only — never the translate call itself. Never raises. Returns
        the new captions.
        """
        added = []
        try:
            while True:
                try:
                    item = self._queue.get_nowait()
                except Exception:
                    break
                built = self._build(item)
                if built is None:
                    continue
                try:
                    with self._lock:
                        try:
                            item_session = (
                                item.get("session") if isinstance(item, dict) else None
                            )
                        except Exception:
                            item_session = None
                        if (
                            item_session is not None
                            and item_session != self._session_id
                        ):
                            continue
                        self._seq += 1
                        built["seq"] = self._seq
                        self._captions.append(built)
                except Exception:
                    continue
                added.append(dict(built))
        except Exception:
            pass
        return added

    def captions(self) -> list:
        """Return an immutable-feeling snapshot (copies) of the list."""
        try:
            return [dict(caption) for caption in self._captions]
        except Exception:
            return []

    def retry_caption(self, seq) -> "dict | None":
        """Re-translate one error caption's retained source in place.

        Returns the updated caption, or None for unknown seqs. Allowed
        on closed sessions (it mutates a row, never adds one). Never
        raises.
        """
        try:
            target = None
            for caption in self._captions:
                try:
                    if caption.get("seq") == seq:
                        target = caption
                        break
                except Exception:
                    continue
            if target is None:
                return None
            try:
                if target.get("kind") != "error":
                    return dict(target)
                source = target.get("source") or ""
                if not source:
                    return dict(target)
            except Exception:
                return None
            try:
                result = self._translate_fn(source, self.target_language, self.model)
            except Exception:
                result = {
                    "error": "Couldn't parse that one. Retry.",
                    "retryable": True,
                }
            try:
                with self._lock:
                    if isinstance(result, dict) and result.get("error"):
                        target["text"] = str(
                            result.get("error") or "Couldn't parse that one. Retry."
                        )
                    else:
                        formal = ""
                        try:
                            formal = (
                                result.get("formal", "")
                                if isinstance(result, dict)
                                else ""
                            )
                        except Exception:
                            formal = ""
                        if not isinstance(result, dict):
                            target["text"] = "Couldn't parse that one. Retry."
                        else:
                            target["kind"] = "caption"
                            target["text"] = source
                            target["translation"] = (
                                formal if isinstance(formal, str) else ""
                            )
                    try:
                        target["at"] = self._now_iso()
                    except Exception:
                        pass
                    return dict(target)
            except Exception:
                return None
        except Exception:
            return None

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

    def _drain_queue(self) -> int:
        try:
            dropped = 0
            while True:
                self._queue.get_nowait()
                dropped += 1
        except Exception:
            pass
        try:
            return dropped
        except Exception:
            return 0

    def _build(self, item) -> "dict | None":
        """Translate one queued item into an unsequenced caption dict.

        Non-dict translate results are contract violations, surfaced as
        retryable error captions (AD-5) rather than blank rows. Never
        raises. Callers assign ``seq`` and append under the lock.
        """
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
            if isinstance(result, dict) and result.get("error"):
                return {
                    "kind": "error",
                    "text": str(
                        result.get("error") or "Couldn't parse that one. Retry."
                    ),
                    "translation": "",
                    "source": text.strip(),
                    "source_lang": str(source),
                    "at": self._now_iso(),
                }
            if not isinstance(result, dict):
                return {
                    "kind": "error",
                    "text": "Couldn't parse that one. Retry.",
                    "translation": "",
                    "source": text.strip(),
                    "source_lang": str(source),
                    "at": self._now_iso(),
                }
            formal = ""
            try:
                formal = result.get("formal", "")
            except Exception:
                formal = ""
            return {
                "kind": "caption",
                "text": text.strip(),
                "translation": formal if isinstance(formal, str) else "",
                "source_lang": str(source),
                "at": self._now_iso(),
            }
        except Exception:
            return None
