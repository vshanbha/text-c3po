"""Shared language picker builders (AD-10).

One builder module feeds all three mode views so picker options never drift.
Target Dropdowns list all 23 LANGUAGES verbatim with no filtering and no
gating on any code/name combo. Source pickers are read-only Auto-detect
(D2-A, 2026-09-13): whisper-server runs `-l auto` and the picked value was
never consumed, so the honest UI is a disabled single-option control.
Functional per-language ASR restart is deferred out of v1.
"""

import flet as ft

from text_c3po.languages import LANGUAGES


def _language_options() -> list:
    """Return a fresh option list covering every LANGUAGES entry."""
    return [
        ft.DropdownOption(key=entry["code"], text=entry["name"]) for entry in LANGUAGES
    ]


def build_target_dropdown() -> ft.Dropdown:
    """Return a target-language Dropdown defaulting to English."""
    return ft.Dropdown(
        label="Target language",
        options=_language_options(),
        value="en",
    )


def build_source_dropdown() -> ft.Dropdown:
    """Return a read-only Auto-detect source control (D2-A).

    Whisper runs transcribe-only with `-l auto`; no source value is ever
    sent to ASR, so an editable 23-language picker over-promises. The
    disabled single option keeps the layout stable while telling the truth.
    """
    return ft.Dropdown(
        label="Source language (auto-detect)",
        options=[ft.DropdownOption(key="auto", text="Auto-detect")],
        value="auto",
        disabled=True,
    )
