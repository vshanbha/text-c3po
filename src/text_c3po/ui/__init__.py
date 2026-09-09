"""Flet UI layer: mode views + top strip (AD-1/AD-2). Runtime access only via services."""

from .file_view import build_file_view
from .language_pickers import build_source_dropdown, build_target_dropdown
from .live_view import build_live_view
from .model_picker import build_model_dropdown, refresh_model_options
from .text_view import build_text_view
from .top_strip import (
    build_appbar,
    build_toolbar,
    refresh_model_picker,
    refresh_ollama_status,
)

__all__ = [
    "build_appbar",
    "build_toolbar",
    "refresh_ollama_status",
    "refresh_model_picker",
    "build_model_dropdown",
    "refresh_model_options",
    "build_text_view",
    "build_live_view",
    "build_file_view",
    "build_target_dropdown",
    "build_source_dropdown",
]
