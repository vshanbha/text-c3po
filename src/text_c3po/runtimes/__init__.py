"""Runtimes layer: ollama_client, whisper_client, audio_devices, process_manager (AD-1)."""

from .audio_devices import (
    has_blackhole,
    list_devices,
    pick_default_device,
)
from .ollama_client import (
    DEFAULT_MODEL_PREFIX,
    OLLAMA_BASE_URL,
    OLLAMA_TAGS_URL,
    PROBE_TIMEOUT_S,
    check_ollama,
    list_models,
    pick_default_model,
)

__all__ = [
    "OLLAMA_BASE_URL",
    "OLLAMA_TAGS_URL",
    "PROBE_TIMEOUT_S",
    "DEFAULT_MODEL_PREFIX",
    "check_ollama",
    "list_models",
    "pick_default_model",
    "has_blackhole",
    "list_devices",
    "pick_default_device",
]
