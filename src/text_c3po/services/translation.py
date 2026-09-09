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

from text_c3po.runtimes.ollama_client import OLLAMA_BASE_URL

logger = logging.getLogger(__name__)

RETRY_MESSAGE = "Couldn't parse that one. Retry."
EMPTY_INPUT_MESSAGE = "Type or paste something first."
MISSING_TARGET_MESSAGE = "Pick a target language first."
MISSING_MODEL_MESSAGE = "Pick a model first."

TRANSLATION_TEMPERATURE = 0.2

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


def extract_partial_formal(raw) -> str:
    """Best-effort live preview: the ``formal`` value prefix in partial JSON.

    Streaming tokens accumulate as raw JSON which won't parse until complete,
    so the UI shows this instead of a char count — real words as they arrive.
    Returns "" when no usable prefix exists yet. Preview only; the final
    cards always render from the fully parsed contract.
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
        # Drop a trailing dangling escape (chunk cut mid-\\u / \\") so the
        # preview never shows a stray backslash.
        if rest.endswith("\\"):
            rest = rest[:-1]
        try:
            rest = rest.replace('\\"', '"').replace("\\n", " ")
        except Exception:
            pass
        return rest.strip()
    except Exception:
        return ""


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
        pieces = []
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
                if piece:
                    pieces.append(piece)
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
        logger.error(
            "translate_text parse failure: %r; raw payload: %r", exc, raw[:2000]
        )
        return {"error": RETRY_MESSAGE, "retryable": True}
    normalized = _normalize(parsed)
    if normalized is None:
        logger.error(
            "translate_text unexpected payload shape; raw payload: %r", raw[:2000]
        )
        return {"error": RETRY_MESSAGE, "retryable": True}
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
    ``{cancelled: True}`` when ``stop_event`` fires mid-stream. Never raises
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
