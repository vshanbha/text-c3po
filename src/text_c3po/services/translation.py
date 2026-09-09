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

# Small context window: single-sentence prompts need <2k tokens, and small
# local models are memory- and latency-bound (a 128k default keeps ~8GB
# resident and turns the 25-call gate into an hour). Never raise this
# without re-running the gate; most small local models are like this.
TRANSLATION_NUM_CTX = 4096


class Translation(BaseModel):
    """Full text-mode translation schema (AD-5)."""

    formal: str = Field(description="Formal version of the translated output")
    informal: str = Field(description="Informal version of the translated output")
    commentary: str = Field(description="Special commentary about the translation")
    origin_language: Union[str, List[str]] = Field(
        description="Autodetected language(s) of the input text"
    )


_SYSTEM_TEMPLATE = """You are a translator who translates from many languages to {language}.
Autodetect the origin language in the input text.
Respond strictly with the translation of the complete input text in {language}.
Where possible provide both formal and informal versions.
Provide multiple translations where possible with relevant commentary in {language}.
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
    """Return the four schema fields as a plain dict, or None when shapeless."""
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
        "commentary": _as_text(lowered.get("commentary", "")),
        "origin_language": _as_text(lowered.get("origin_language", "")),
    }


def translate_text(text, target_language, model):
    """Translate ``text`` into ``target_language`` with the given Ollama ``model``.

    Returns a parsed ``{formal, informal, commentary, origin_language}`` dict
    on success, or ``{error, retryable}`` on any transport/parse failure.
    Never raises and never returns raw model payloads.
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
        llm = ChatOllama(
            model=model,
            format="json",
            base_url=OLLAMA_BASE_URL,
            temperature=TRANSLATION_TEMPERATURE,
            num_ctx=TRANSLATION_NUM_CTX,
        )
        parser = JsonOutputParser(pydantic_object=Translation)
        messages = _build_request(text, target_language, parser)
    except Exception as exc:
        logger.error("translate_text setup failure: %r", exc)
        return {"error": RETRY_MESSAGE, "retryable": True}

    try:
        response = llm.invoke(messages)
    except Exception as exc:
        logger.error("translate_text transport failure: %r", exc)
        return {"error": RETRY_MESSAGE, "retryable": True}

    try:
        raw = getattr(response, "content", "")
    except Exception:
        raw = ""
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
