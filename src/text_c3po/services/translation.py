"""CAP-3 translation service: ChatOllama with enforced JSON format (AD-5/AD-6).

Owns the ``Translation`` schema plus ``translate_text()``. The model arrives
as an opaque runtime string (the model picker's call-time value); the only
loopback peer is ``OLLAMA_BASE_URL`` reused from ``runtimes.ollama_client``.

The service never raises and never returns raw model payloads: any transport
or parse failure yields a retryable ``{error, retryable}`` dict while the raw
payload goes to the logs only. Story 7 reuses this entry point with the model
passed as a parameter.
"""

import logging
import os
import threading
from typing import List, Union

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from text_c3po.messages import (
    EMPTY_INPUT_HINT as EMPTY_INPUT_MESSAGE,
    LOOP_MESSAGE,
    MISSING_MODEL_MESSAGE,
    MISSING_TARGET_MESSAGE,
    RETRY_HINT as RETRY_MESSAGE,
)
from text_c3po.runtimes.ollama_client import OLLAMA_BASE_URL

logger = logging.getLogger(__name__)


TRANSLATION_TEMPERATURE = 0.2

# Payload privacy gate: translated user content reaches the log only with
# explicit opt-in. Read at call time (not import) so tests can flip it.
DEBUG_PAYLOADS_ENV = "TEXT_C3PO_DEBUG_PAYLOADS"


def _debug_payloads() -> bool:
    """True when raw model payloads may be logged. Never raises."""
    try:
        return os.getenv(DEBUG_PAYLOADS_ENV) == "1"
    except Exception:
        return False


# Context window: deliberately NOT overridden. An earlier revision pinned
# num_ctx=4096 on the theory that small local models are memory-bound, but
# live `ollama ps` shows lfm2.5 loaded at 128K fully on GPU (7.6 GB) — the
# premise was wrong for this hardware. Worse, pinning a small value forces an
# Ollama model reload whenever it differs from the loaded context, adding
# seconds to every Translate. Let the server/model default decide.

# Hung Ollama must not freeze the caller forever: sync httpx timeout (s)
# forwarded via sync_client_kwargs (ollama Client -> httpx). UI also runs
# translate off the Flet UI thread (see app.on_translate).
TRANSLATION_TIMEOUT_S = 60.0

# Stop support: every live ChatOllama registers here so Stop can close its
# underlying HTTP client mid-request. Python threads can't be killed, so this
# is the real abort — the blocked stream fails fast instead of running to
# the 60s timeout. Stale results are still ignored by generation in app.py.
# Streaming is the transport, JSON stays the contract: one prompt per chunk,
# tokens accumulate, the full string parses once at the end.
_ACTIVE_LOCK = threading.Lock()
_ACTIVE_LLMS: set = set()
_ACTIVE_STREAMS: set = set()


def _close_stream(stream) -> None:
    """Best-effort generator close so the server sees the disconnect."""
    try:
        close = getattr(stream, "close", None)
        if callable(close):
            close()
    except Exception:
        pass


def cancel_inflight() -> int:
    """Abort all in-flight translations; return how many streams were hit.

    Closes active stream iterators first (server aborts mid-generation on
    disconnect), then the underlying HTTP clients (frees the blocked worker).
    Never raises. Call from the UI Stop handler before bumping the
    generation counter — the worker then returns ``{"cancelled": True}`` and
    its late result is dropped by is_current_request().
    """
    try:
        with _ACTIVE_LOCK:
            streams = list(_ACTIVE_STREAMS)
            live = list(_ACTIVE_LLMS)
    except Exception:
        return 0
    hit = 0
    for stream in streams:
        try:
            _close_stream(stream)
            hit += 1
        except Exception:
            pass
    for llm in live:
        try:
            client = getattr(llm, "_client", None)
            close = getattr(client, "close", None)
            if callable(close):
                close()
                hit += 1
        except Exception:
            pass
    return hit


class Translation(BaseModel):
    """Text-mode translation schema (AD-5): formal/informal plus origin."""

    formal: str = Field(description="Formal version of the translated output")
    informal: str = Field(description="Informal version of the translated output")
    origin_language: Union[str, List[str]] = Field(
        description="Autodetected language(s) of the input text"
    )


_SYSTEM_TEMPLATE = """You are a translator. Translate the input text below into {language}.
This input is one part of a longer document; translate only this part, preserving its full meaning.
The ENTIRE output must be written in {language} — every sentence, no exceptions, no English paraphrase.
Respond strictly with the translation of the complete input text in {language}.
Where possible provide both formal and informal versions.
Translated output must follow the JSON schema per the below instructions.
{format_instructions}"""


def _build_request(text, target_language, parser):
    """Return the v1 system+human message list with format instructions bound."""
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(_SYSTEM_TEMPLATE),
            HumanMessagePromptTemplate.from_template("{text}"),
        ]
    )
    return prompt.format_prompt(
        text=text,
        language=target_language,
        format_instructions=parser.get_format_instructions(),
    ).to_messages()


def _as_text(value):
    """Coerce a parsed field to display text (blank unless a non-empty string)."""
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(part) for part in value)
    return str(value)


def _normalize(parsed):
    """Return the schema fields as a plain dict, or None when shapeless."""
    try:
        items = parsed.items()
    except Exception:
        return None
    lowered = {}
    for key, value in items:
        try:
            lowered[str(key).lower()] = value
        except Exception:
            continue
    return {
        "formal": _as_text(lowered.get("formal", "")),
        "informal": _as_text(lowered.get("informal", "")),
        "origin_language": _as_text(lowered.get("origin_language", "")),
    }


def _decode_json_prefix(body) -> str:
    """Decode a possibly-cut JSON string body; never raises.

    Prefers real JSON unescaping (so ``\\"`` and ``\\uXXXX`` resolve
    instead of leaking debris), then flattens newlines to spaces to
    preserve the long-standing preview contract (single-line preview
    and partial text).
    """
    try:
        import json as _json

        decoded = _json.loads('"' + body + '"')
    except Exception:
        try:
            decoded = body.replace('\\"', '"').replace("\\n", " ")
        except Exception:
            decoded = body
    try:
        return decoded.replace("\n", " ")
    except Exception:
        return decoded


def _cut_at_closing_quote(body) -> tuple:
    """Split a JSON string body at its first unescaped quote.

    Returns (before, complete): ``complete`` is True when a closing
    quote was found (the field closed — anything after is trailing
    junk from later fields), False when the stream simply cut
    mid-value. Escape-aware so ``\\"`` never ends the scan early.
    """
    try:
        escaped = False
        for index, char in enumerate(body):
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                return body[:index], True
        return body, False
    except Exception:
        return body, False


def extract_partial_formal(raw) -> str:
    """Best-effort ``formal`` value prefix from partial JSON.

    Streaming tokens accumulate as raw JSON which won't parse until complete,
    so the UI shows this instead of a char count — real words as they arrive.
    Returns "" when no usable prefix exists yet. Serves the live preview
    AND the ceiling-cut final serializer (D8): a closed formal followed by
    later-field junk is cut at the closing quote so trailing JSON debris
    never renders as translation.
    """
    try:
        if not isinstance(raw, str) or not raw:
            return ""
        marker = '"formal"'
        idx = raw.find(marker)
        if idx < 0:
            return ""
        rest = raw[idx + len(marker) :]
        colon = rest.find(":")
        if colon < 0:
            return ""
        rest = rest[colon + 1 :].lstrip()
        if rest.startswith('"'):
            rest = rest[1:]
        else:
            return ""
        body, _complete = _cut_at_closing_quote(rest)
        # Drop a trailing dangling escape (chunk cut mid-\\u / \\") so the
        # output never shows a stray backslash.
        if body.endswith("\\"):
            body = body[:-1]
        return _decode_json_prefix(body).strip()
    except Exception:
        return ""


def _compression_ratio(text) -> float:
    """zlib size over raw size; 1.0 for junk input. Never raises."""
    try:
        if not isinstance(text, str) or not text:
            return 1.0
        import zlib

        raw = text.encode("utf-8", "replace")
        return len(zlib.compress(raw)) / max(1, len(raw))
    except Exception:
        return 1.0


def _looks_looped(text, source_text="") -> bool:
    """True when text is almost surely degenerate repetition; never raises.

    Loop-junk compresses to nearly nothing while real prose does not, so
    a zlib ratio below 0.2 separates them deterministically across
    scripts (no language-specific word lists). The comparison is
    *relative* to the source when given: faithful repetition (lyrics,
    chants, boilerplate) repeats because its input repeats, so it is
    not flagged — only output that loops while its input does not, or
    output dwarfing its input, counts. Guards the ceiling-cut partial
    path and the full-parse path alike: looped "content" must error,
    never render as copyable translation. Known blind spot:
    paraphrase-drift loops (same sentence reworded each time) compress
    poorly and evade any compression check.
    """
    try:
        if not isinstance(text, str) or len(text) < 200:
            return False
        if _compression_ratio(text) >= 0.2:
            return False
        if not isinstance(source_text, str) or not source_text.strip():
            return True
        if _compression_ratio(source_text) >= 0.2:
            # Repetitive output from non-repetitive input: the loop case.
            return True
        # Both repeat: faithful unless the output dwarfs the input.
        try:
            return len(text) > 4 * len(source_text)
        except Exception:
            return False
    except Exception:
        return False


def _chunk_text(chunk) -> str:
    """Extract display text from a stream chunk (str or content blocks)."""
    try:
        content = getattr(chunk, "content", "")
    except Exception:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            try:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    parts.append(str(block.get("text", "")))
                else:
                    parts.append(str(getattr(block, "text", "") or ""))
            except Exception:
                pass
        return "".join(parts)
    try:
        return str(content or "")
    except Exception:
        return ""


def _translate_single(
    text, target_language, model, parser, on_token=None, stop_event=None
):
    """One streaming LLM round trip; same single prompt, JSON parsed at end.

    Tokens accumulate into one string; ``on_token(piece, total_chars)`` fires
    per chunk for progress (never allowed to raise). If ``stop_event`` is set
    mid-stream the iterator is closed — the server sees the disconnect and
    aborts — and ``{"cancelled": True}`` returns. Otherwise the full string
    parses through the unchanged JSON contract.
    """
    try:
        llm = ChatOllama(
            model=model,
            format="json",
            base_url=OLLAMA_BASE_URL,
            temperature=TRANSLATION_TEMPERATURE,
            # No thinking phase: translation is a direct rewrite, and the
            # reasoning trace costs ~10s per call with zero quality gain.
            reasoning=False,
            # Prophylactic, not a cutoff fix: the server default caps
            # output at 128 tokens (per the installed langchain_ollama
            # docstring), so request infinite generation. Live F4 evidence
            # showed the Spanish cutoff stopping clean (done_reason='stop',
            # cap never engaged) — retry remains the affordance there.
            num_predict=-1,
            sync_client_kwargs={"timeout": TRANSLATION_TIMEOUT_S},
        )
        messages = _build_request(text, target_language, parser)
    except Exception as exc:
        logger.error("translate_text setup failure: %r", exc)
        return {"error": RETRY_MESSAGE, "retryable": True}

    try:
        with _ACTIVE_LOCK:
            _ACTIVE_LLMS.add(llm)
    except Exception:
        pass
    try:
        try:
            stream = llm.stream(messages)
        except Exception as exc:
            logger.error("translate_text transport failure: %r", exc)
            return {"error": RETRY_MESSAGE, "retryable": True}
        try:
            with _ACTIVE_LOCK:
                _ACTIVE_STREAMS.add(stream)
        except Exception:
            pass
        # Backstop only, set far above legitimate output: duplication
        # across formal/informal plus JSON escapes inflates raw chars well
        # beyond the input length, so a tight ceiling would kill valid
        # near-threshold translations with no recourse (non-retryable).
        try:
            output_ceiling = max(60000, 12 * len(text))
        except Exception:
            output_ceiling = 60000
        pieces = []
        raw_len = 0
        last_meta: dict = {}
        try:
            for chunk in stream:
                try:
                    stopped = bool(stop_event is not None and stop_event.is_set())
                except Exception:
                    stopped = False
                if stopped:
                    _close_stream(stream)
                    return {"cancelled": True}
                try:
                    piece = _chunk_text(chunk)
                except Exception:
                    piece = ""
                # Keep the latest response metadata: done_reason="length"
                # tells a length-limit stop apart from a clean "stop" when
                # diagnosing cut-off translations (see the end-of-stream
                # logs below, including the parse-failure branch).
                try:
                    meta = getattr(chunk, "response_metadata", None)
                    if isinstance(meta, dict) and meta:
                        last_meta = meta
                except Exception:
                    pass
                if piece:
                    pieces.append(piece)
                    raw_len += len(piece)
                    if raw_len > output_ceiling:
                        # Degenerate repetition loop: each chunk beats the
                        # per-read timeout forever. Stop, but keep what did
                        # arrive: the streamed raw JSON usually holds a
                        # usable formal prefix (same extractor as the live
                        # preview), returned with truncated=True so renderers
                        # mark it partial instead of retrying a doomed call.
                        # Only when nothing usable arrived is it an error.
                        logger.warning(
                            "translate_text output ceiling hit: raw_chars=%d "
                            "done_reason=%r model=%s target=%s",
                            raw_len,
                            last_meta.get("done_reason"),
                            model,
                            target_language,
                        )
                        _close_stream(stream)
                        try:
                            partial = extract_partial_formal("".join(pieces))
                        except Exception:
                            partial = ""
                        if (
                            isinstance(partial, str)
                            and partial.strip()
                            and not _looks_looped(partial, text)
                        ):
                            return {
                                "formal": partial,
                                "informal": "",
                                "origin_language": "",
                                "truncated": True,
                            }
                        return {
                            "error": (
                                "Translation ran too long — try a shorter input."
                            ),
                            "retryable": False,
                        }
                    if callable(on_token):
                        try:
                            on_token(piece, sum(len(p) for p in pieces))
                        except Exception:
                            pass
        except GeneratorExit:
            return {"cancelled": True}
        except Exception as exc:
            try:
                stopped = bool(stop_event is not None and stop_event.is_set())
            except Exception:
                stopped = False
            if stopped:
                return {"cancelled": True}
            logger.error("translate_text transport failure: %r", exc)
            return {"error": RETRY_MESSAGE, "retryable": True}
        finally:
            try:
                with _ACTIVE_LOCK:
                    _ACTIVE_STREAMS.discard(stream)
            except Exception:
                pass
            _close_stream(stream)
    finally:
        try:
            with _ACTIVE_LOCK:
                _ACTIVE_LLMS.discard(llm)
        except Exception:
            pass

    raw = "".join(pieces)
    if not isinstance(raw, str):
        try:
            raw = str(raw)
        except Exception:
            raw = ""
    try:
        parsed = parser.parse(raw)
    except Exception as exc:
        # A length-truncated mid-JSON payload dies here, before the
        # end-of-stream debug log below — so emit the stream metadata
        # with the failure or the cutoff case stays undiagnosable.
        # Content-free by design: langchain's exception repr embeds the
        # raw payload, so only the exception type is logged; payload
        # content itself only with TEXT_C3PO_DEBUG_PAYLOADS=1.
        exc_name = type(exc).__name__
        if _debug_payloads():
            logger.error(
                "translate_text parse failure: %s; done_reason=%r eval_count=%r; "
                "raw payload: %r",
                exc_name,
                last_meta.get("done_reason"),
                last_meta.get("eval_count"),
                raw[:2000],
            )
        else:
            logger.error(
                "translate_text parse failure: %s; done_reason=%r eval_count=%r; "
                "raw_chars=%d",
                exc_name,
                last_meta.get("done_reason"),
                last_meta.get("eval_count"),
                len(raw),
            )
        return {"error": RETRY_MESSAGE, "retryable": True}
    normalized = _normalize(parsed)
    if normalized is None:
        if _debug_payloads():
            logger.error(
                "translate_text unexpected payload shape; raw payload: %r", raw[:2000]
            )
        else:
            logger.error(
                "translate_text unexpected payload shape; raw_chars=%d", len(raw)
            )
        return {"error": RETRY_MESSAGE, "retryable": True}
    # Full-parse loop check (L1): a repetition loop that ends cleanly
    # under the ceiling still parses — screen it against the input the
    # same relative way the ceiling path does, or loop junk ships as a
    # copyable successful translation.
    try:
        formal_out = normalized.get("formal", "")
        if _looks_looped(formal_out, text):
            logger.warning(
                "translate_text looped output rejected: in=%d chars model=%s target=%s",
                len(text),
                model,
                target_language,
            )
            return {"error": LOOP_MESSAGE, "retryable": False}
    except Exception:
        pass
    try:
        logger.debug(
            "translate_text stream end: done_reason=%r eval_count=%r raw_chars=%d",
            last_meta.get("done_reason"),
            last_meta.get("eval_count"),
            len(raw),
        )
    except Exception:
        pass
    return normalized


def translate_text(text, target_language, model, on_token=None, stop_event=None):
    """Translate ``text`` into ``target_language`` with the given Ollama ``model``.

    Exactly one prompt, one streamed call, whatever the length: tokens stream
    in — ``on_token(piece, total_chars)`` per piece for live progress — and
    the accumulated string parses once through the unchanged JSON schema.
    (An earlier revision split long input into one call per paragraph; live
    measurement showed the per-call first-token wait dominating, and a single
    call translates cleanly, so the splitter was removed.)

    Returns a parsed ``{formal, informal, origin_language}`` dict on
    success, ``{error, retryable}`` on any transport/parse failure, or
    ``{cancelled: True}`` when ``stop_event`` fires mid-stream. A
    degenerate stream stopped by the output ceiling returns its usable
    formal prefix as ``{formal, truncated: True}`` (no error key) so
    renderers show partial content instead of failing. Never raises
    and never returns raw model payloads.
    """
    try:
        if not isinstance(text, str) or not text.strip():
            return {"error": EMPTY_INPUT_MESSAGE, "retryable": False}
        if not isinstance(target_language, str) or not target_language.strip():
            return {"error": MISSING_TARGET_MESSAGE, "retryable": False}
        if not isinstance(model, str) or not model.strip():
            return {"error": MISSING_MODEL_MESSAGE, "retryable": False}
    except Exception:
        return {"error": RETRY_MESSAGE, "retryable": True}

    try:
        parser = JsonOutputParser(pydantic_object=Translation)
    except Exception as exc:
        logger.error("translate_text setup failure: %r", exc)
        return {"error": RETRY_MESSAGE, "retryable": True}

    result = _translate_single(
        text.strip(),
        target_language,
        model,
        parser,
        on_token=on_token,
        stop_event=stop_event,
    )
    if not isinstance(result, dict):
        return {"error": RETRY_MESSAGE, "retryable": True}
    try:
        if isinstance(result.get("formal"), str):
            logger.info(
                "translate_text ok: in=%d chars out=%d chars model=%s target=%s",
                len(text),
                len(result["formal"]),
                model,
                target_language,
            )
    except Exception:
        pass
    return result
