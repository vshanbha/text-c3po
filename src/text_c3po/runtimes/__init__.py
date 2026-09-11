"""Runtimes layer: ollama_client, whisper_client, audio_devices, process_manager (AD-1)."""

from .audio_devices import (
    has_blackhole,
    list_devices,
    pick_default_device,
)
from .audio_file import (
    SUPPORTED_EXTENSIONS,
    decode_to_wav,
    supported_extensions,
)
from .process_manager import (
    AUTO_LANGUAGE,
    DEFAULT_MODEL_FILENAME,
    READY_TIMEOUT_S,
    WHISPER_HOST,
    WHISPER_INFERENCE_PATH,
    WHISPER_PORT,
    ProcessManager,
    probe_serving,
    resolve_language_code,
)
from .whisper_client import (
    TRANSCRIBE_TIMEOUT_S,
    WHISPER_INFERENCE_URL,
    transcribe_wav,
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
    "AUTO_LANGUAGE",
    "DEFAULT_MODEL_FILENAME",
    "READY_TIMEOUT_S",
    "WHISPER_HOST",
    "WHISPER_INFERENCE_PATH",
    "WHISPER_PORT",
    "ProcessManager",
    "probe_serving",
    "resolve_language_code",
    "SUPPORTED_EXTENSIONS",
    "decode_to_wav",
    "supported_extensions",
    "TRANSCRIBE_TIMEOUT_S",
    "WHISPER_INFERENCE_URL",
    "transcribe_wav",
]
