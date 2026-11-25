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
# live `ollama ps` (2026-10-08) shows ornith-1.5:9b resident fully on GPU at
# its native context (262144 per `ollama show`) — the premise was wrong for
# this hardware. Worse, pinning a small value forces an Ollama model reload
# whenever it differs from the loaded context, adding seconds to every
# Translate. Let the server/model default decide.

# Hung Ollama must not freeze the caller forever: sync httpx timeout (s)
# forwarded via sync_client_kwargs (ollama Client -> httpx). UI also runs
# translate off the Flet UI thread (see app.on_translate).
TRANSLATION_TIMEOUT_S = 60.0

# Rung 3 of the ladder (thinking ON) gets its own, much longer per-call
# timeout: observed 7/7 complete on the German long reference at 70-340s.
# Rungs 1-2 keep TRANSLATION_TIMEOUT_S untouched.
THINKING_TIMEOUT_S = 360.0

# Hybrid thinking ladder (owner-approved 2026-11-24). Evidence: lfm3 at
# reasoning=False stochastically stops mid-JSON on LONG inputs only
# (~10-20% partial on the 776-char reference, reproduced by raw /api/chat
# with no app code involved; shorts never flake — gate 115/115). The
# ladder is length-based only, deliberately model-agnostic:
#   rung 1  normal think-off call (today's behavior);
#   rung 2  immediate identical think-off retry when the parsed formal is
#           below 0.9x the input length (~8s, recovers ~2/3);
#   rung 3  still partial -> one thinking-on call at THINKING_TIMEOUT_S
#           (7/7 complete).
# Shorts (<= LADDER_MIN_INPUT_CHARS) never ladder: they must stay on the
# fast path. The 0.9 ratio separates cleanly on the measured data
# (partials <= 602/776 = 78%, fulls >= 830/776 = 107%).
LADDER_MIN_INPUT_CHARS = 300
LADDER_PARTIAL_RATIO = 0.9

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


# lfm3 long-input first-sentence stop (evidence 2026-11-23; direct
# /api/chat differential matrix at think=false, temperature 0.2,
# format=json, 776-char input): lfm3 stopped after the first sentence
# (formal ~79 chars, done_reason='stop'), deterministic. da799e2 pinned
# TWO triggers — (1) langchain's verbose pydantic instruction block bound
# at {format_instructions}, and (2) the line "Respond strictly with the
# translation of the complete input text in {language}" (9/9 short with
# it, 5/5+ full without). The German-long matrix found the THIRD
# trigger class: ANY framing around a single self-contained instruction.
# Interactions are NON-ADDITIVE — recombining framings (notably the
# "ENTIRE output ... no exceptions" line) caused 300s non-terminating
# hangs in raw probes; treat each framing add-on as independently
# re-proven, never assume linear accumulation. The differential matrix
# pins the flips, not the mechanism — WHY framing triggers the stop
# remains unpinned.
# Raw flips, same model/settings, system role unless noted: plain
# instruction alone full (877/784); + "This input is one part of a
# longer document; translate only this part" -> 79 short; a bare role
# preamble ("You are a translator." / "You are a helpful assistant.")
# before the same contract line -> 79/84 short vs contract line alone
# 890/856 full; the whole instruction in the user message instead of the
# system message -> 74 short (3/3) vs 849-877 formal full in system;
# per-field "...of the COMPLETE input" parentheticals added to the plain
# instruction -> 79 short vs 845/770 full. The old multi-line template +
# compact contract gave German long 79 short (5/5 at the app path) while
# Spanish long stayed full (843-865) — so the fix is ONE self-contained
# system instruction, proven full dual on long input for German (856/768,
# 845/770, 843/701) and Spanish (861/728, 818/724), shorts dual-present
# for both. The
# instruction states the full contract itself — single JSON object, all
# three fields — because JsonOutputParser does NOT validate in installed
# langchain_core 1.6.2 (.parse() only extracts JSON; missing/extra keys
# pass through), so the prompt contract plus _normalize() are the sole
# enforcers. Keep in sync with the Translation schema. Output-language
# intent ("Translate the following English text into {language}") lives
# in the instruction itself; the ENTIRE-output and longer-document lines
# went with the template.
#
# Informal-language fix (2026-11-25, raw-first acceptance matrix): the
# contract above never stated the LANGUAGE of the two versions, so the
# `informal` field stochastically rendered in English (Phase-1 app-path:
# EN->DE longs 4/5 English informal, shorts 1/23 — the owner's manual
# hit was a long input). Every SYSTEM-side add-on re-triggered the
# framing class and was rejected on the acceptance gate: trailing
# standalone line "Both versions must be in {language}." -> German long
# 79-85 x5 (deterministic); inline ", both in {language}" wording ->
# German long 79 + Spanish 183 partials; the earlier ", both written
# entirely in German" amendment -> 79-85 x3. The WINNER keeps this
# system instruction byte-identical (the proven framing pole) and states
# the language in the USER message tail instead — raw acceptance: German
# long 5/5 formal 840-867 AND informal German 5/5, Spanish long 5/5,
# EN->DE shorts 12/12 informal German, DE->EN 3/3 informal English.
# The gate now enforces both fields target-relatively (eval_harness
# Lang dimension; red run before this fix: 4 informal-EN cells on the
# 5x5). Evidence logs: raw candidate matrices + red/green runs
# 2026-11-25 (orchestrator-held).
_SYSTEM_TEMPLATE = "{format_instructions}"


def _compact_format_instructions(language: str) -> str:
    """The whole system message: plain lead plus the three-field contract.

    One self-contained instruction, no framing — role preambles, the old
    multi-line template, and per-field "...of the COMPLETE input"
    parentheticals are each proven first-sentence-stop triggers (see the
    evidence comment on ``_SYSTEM_TEMPLATE``), as is langchain's verbose
    pydantic block (``parser.get_format_instructions()``). States the
    full contract (single JSON object, all three ``Translation`` fields)
    because JsonOutputParser does not validate. Keep in sync with the
    Translation schema.

    Deliberately says NOTHING about the versions' language: that
    statement lives in the USER message tail (see ``_build_request``) —
    every system-side wording tried there re-triggered the framing-class
    first-sentence stop (evidence on ``_SYSTEM_TEMPLATE``).
    """
    return (
        f"Translate the following English text into {language}. Give two "
        f"versions: a formal one and an informal one. Output ONLY a JSON "
        f'object with keys "formal", "informal", "origin_language".'
    )


# User-message tail (informal-language fix, 2026-11-25): states the
# language of BOTH versions without touching the proven system pole.
# Round 4 (raw-first, owner-mandated): the round-3 tail ("Both versions
# must be in {language}.") left a stochastic ~1% wrong-language informal
# (Lang gate caught Tamil informal sentence 1 in a 23x5 matrix, 1/115;
# direct reproduction 6/6 clean). Red baseline at round-4 settings on the
# round-3 tail: 0/115 twice (230 clean cells — lucky draws sizing the
# residual below ~1%). WINNER is the strengthened trailing wording:
# German long 5/5 formal 839-859 with informal German 5/5, Spanish long
# 5/5 formal 839-864, EN->DE shorts 12/12, DE->EN 3/3, full 23x5 matrix
# 0 mismatches/115 — plus a second independent 115-cell sweep for
# confirmation. Rejected candidates: none failed — the first candidate
# cleared the full gate (later candidates untested, per the stop-at-
# winner rule). System-side equivalents failed the same gate (see
# _SYSTEM_TEMPLATE evidence). Two blank lines mirror the raw-probe
# payload that was acceptance-tested.
_HUMAN_TEMPLATE = "{text}\n\nBoth versions must be written entirely in {language}."


def _build_request(text, target_language, parser):
    """Return the v1 system+user message list with format instructions bound.

    ``parser`` stays in the signature for the callers/tests; the bound
    instructions are the compact contract above, not
    ``parser.get_format_instructions()`` (see the comment on the
    template). The user message carries the versions-language tail
    (``_HUMAN_TEMPLATE``) — the 2026-11-25 informal-language fix; the
    system message stays the proven single self-contained instruction.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(_SYSTEM_TEMPLATE),
            HumanMessagePromptTemplate.from_template(_HUMAN_TEMPLATE),
        ]
    )
    return prompt.format_prompt(
        text=text,
        language=target_language,
        format_instructions=_compact_format_instructions(target_language),
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


def _chunk_thinking(chunk) -> str:
    """Extract the reasoning delta from a stream chunk; never raises.

    Installed langchain_ollama (chat_models.py, ``_iterate_over_stream``)
    copies ``stream_resp["message"]["thinking"]`` into
    ``AIMessageChunk.additional_kwargs["reasoning_content"]`` when
    reasoning is enabled — ``.content`` stays empty during the thinking
    phase, so this is the ONLY place thinking text lives. The delta is
    routed to ``on_thinking`` and must never enter the JSON ``pieces``.
    """
    try:
        extra = getattr(chunk, "additional_kwargs", None)
        if not isinstance(extra, dict):
            return ""
        value = extra.get("reasoning_content", "")
    except Exception:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            try:
                parts.append(item if isinstance(item, str) else str(item or ""))
            except Exception:
                pass
        return "".join(parts)
    try:
        return str(value or "")
    except Exception:
        return ""


def _fire(callback, *args) -> None:
    """Invoke an optional progress callback; never raises."""
    if not callable(callback):
        return
    try:
        callback(*args)
    except Exception:
        pass


def _stop_requested(stop_event) -> bool:
    """True when the caller's Stop flag is set; never raises."""
    try:
        return bool(stop_event is not None and stop_event.is_set())
    except Exception:
        return False


def _formal_len(result) -> int:
    """Length of a parsed ``formal`` field, or -1 when absent/not a string."""
    try:
        value = result.get("formal") if isinstance(result, dict) else None
        return len(value) if isinstance(value, str) else -1
    except Exception:
        return -1


def next_ladder_action(input_len, formal_len, attempt):
    """Pure hybrid-ladder decision: what to do after ``attempt`` finished.

    ``attempt`` is the rung just completed (1-based). Returns ``"done"``
    (keep the result), ``"retry"`` (run the identical think-off call again
    — rung 2) or ``"think"`` (run the thinking-on call — rung 3).

    Inputs of ``LADDER_MIN_INPUT_CHARS`` chars or fewer never ladder:
    they never flake and must stay on the fast path. For longer inputs a
    result is partial below ``LADDER_PARTIAL_RATIO`` x input length.
    Rung 3 (``attempt >= 3``) is terminal. Pure and total: never
    raises — uncoercible junk yields ``"done"``, numeric junk coerces
    via ``int`` like any call-site value.
    """
    try:
        input_len = int(input_len)
        formal_len = int(formal_len)
        attempt = int(attempt)
    except Exception:
        return "done"
    if attempt >= 3 or input_len <= LADDER_MIN_INPUT_CHARS:
        return "done"
    if formal_len >= LADDER_PARTIAL_RATIO * input_len:
        return "done"
    return "retry" if attempt <= 1 else "think"


def _translate_single(
    text,
    target_language,
    model,
    parser,
    on_token=None,
    stop_event=None,
    on_thinking=None,
    reasoning=False,
    timeout_s=None,
):
    """One streaming LLM round trip; same single prompt, JSON parsed at end.

    Tokens accumulate into one string; ``on_token(piece, total_chars)`` fires
    per chunk for progress (never allowed to raise). Reasoning deltas (only
    present when ``reasoning=True``) fire ``on_thinking(delta)`` instead and
    never enter the accumulated JSON string. ``timeout_s`` overrides the
    per-call sync timeout (rung 3 of the ladder passes THINKING_TIMEOUT_S);
    ``reasoning`` selects the thinking-on build — both ladder knobs, both
    defaulting to today's behavior. If ``stop_event`` is set
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
            # No thinking phase by default: translation is a direct rewrite,
            # and the reasoning trace costs ~10s per call with zero quality
            # gain. The ladder's rung 3 flips this on as a last resort for
            # long inputs (see LADDER_* constants).
            reasoning=reasoning,
            # Prophylactic, not a cutoff fix: the server default caps
            # output at 128 tokens (per the installed langchain_ollama
            # docstring), so request infinite generation. Live F4 evidence
            # showed the Spanish cutoff stopping clean (done_reason='stop',
            # cap never engaged) — retry remains the affordance there.
            num_predict=-1,
            sync_client_kwargs={
                "timeout": TRANSLATION_TIMEOUT_S if timeout_s is None else timeout_s
            },
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
                # Reasoning deltas (rung 3, think-on) route to on_thinking
                # only: they must never join the JSON pieces accumulation
                # (unit-tested) or pollute the parse.
                try:
                    thinking = _chunk_thinking(chunk)
                except Exception:
                    thinking = ""
                if thinking:
                    _fire(on_thinking, thinking)
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
                            # raw_len is the running total maintained above;
                            # recomputing sum(len(p) for p in pieces) here
                            # would be O(n^2) across the whole stream.
                            on_token(piece, raw_len)
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


def translate_text(
    text,
    target_language,
    model,
    on_token=None,
    stop_event=None,
    on_thinking=None,
    on_status=None,
):
    """Translate ``text`` into ``target_language`` with the given Ollama ``model``.

    One prompt, one streamed call — tokens stream in via ``on_token(piece,
    total_chars)`` for live progress, the accumulated string parses once
    through the unchanged JSON schema — with ONE owner-approved exception:
    the hybrid thinking ladder for long inputs (see LADDER_* constants).
    Inputs of ``LADDER_MIN_INPUT_CHARS`` chars or fewer always take the
    single fast call; longer inputs whose parsed ``formal`` comes back
    below ``LADDER_PARTIAL_RATIO`` of the input length get up to two extra
    attempts: first an identical think-off retry (``on_status`` fires
    "Partial result — retrying (2/3)…"), then one thinking-on call at
    ``THINKING_TIMEOUT_S`` whose reasoning deltas stream through
    ``on_thinking`` ("Thinking…"). Every ladder transition is logged; the
    longest real result obtained is returned (partial content beats an
    error), while cancelled and transport/parse errors keep their existing
    contract untouched.

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

    try:
        stripped = text.strip()
    except Exception:
        stripped = text
    result = _translate_single(
        stripped,
        target_language,
        model,
        parser,
        on_token=on_token,
        stop_event=stop_event,
        on_thinking=on_thinking,
    )
    if not isinstance(result, dict):
        return {"error": RETRY_MESSAGE, "retryable": True}

    # ---- hybrid thinking ladder (long inputs only; LADDER_* constants) ----
    # Pure decision (next_ladder_action) drives at most two extra calls.
    # Terminal cases: short input, full-on-this-rung, rung 3 reached,
    # cancelled (existing contract), or a transport/parse error (the
    # retryable error card — or the best partial already obtained —
    # stands; errors do not ladder).
    ladder_used = False
    attempt = 1
    best = result
    try:
        while True:
            if result.get("cancelled"):
                return result
            current_len = _formal_len(result)
            if current_len < 0:
                break
            action = next_ladder_action(len(stripped), current_len, attempt)
            if action == "done":
                break
            if _stop_requested(stop_event):
                return {"cancelled": True}
            ladder_used = True
            if action == "retry":
                logger.warning(
                    "translation ladder: partial rung %d (in=%d formal=%d) "
                    "-> rung 2 think-off retry model=%s target=%s",
                    attempt,
                    len(stripped),
                    current_len,
                    model,
                    target_language,
                )
                _fire(on_status, "Partial result — retrying (2/3)…")
                result = _translate_single(
                    stripped,
                    target_language,
                    model,
                    parser,
                    on_token=on_token,
                    stop_event=stop_event,
                    on_thinking=on_thinking,
                )
            else:  # "think": rung 3, thinking ON, long per-call timeout
                logger.warning(
                    "translation ladder: partial rung %d (in=%d formal=%d) "
                    "-> rung 3 think-on timeout=%ss model=%s target=%s",
                    attempt,
                    len(stripped),
                    current_len,
                    THINKING_TIMEOUT_S,
                    model,
                    target_language,
                )
                _fire(on_status, "Thinking…")
                result = _translate_single(
                    stripped,
                    target_language,
                    model,
                    parser,
                    on_token=on_token,
                    stop_event=stop_event,
                    on_thinking=on_thinking,
                    reasoning=True,
                    timeout_s=THINKING_TIMEOUT_S,
                )
            attempt += 1
            if not isinstance(result, dict):
                result = {"error": RETRY_MESSAGE, "retryable": True}
            if _formal_len(result) > _formal_len(best):
                best = result
    except Exception:
        # Never raise beyond the existing contract: fall through with the
        # best real content obtained so far.
        pass
    if ladder_used:
        try:
            logger.warning(
                "translation ladder outcome: rungs=%d in=%d best_formal=%d "
                "model=%s target=%s",
                attempt,
                len(stripped),
                max(0, _formal_len(best)),
                model,
                target_language,
            )
        except Exception:
            pass
        if _formal_len(best) >= 0:
            result = best
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
