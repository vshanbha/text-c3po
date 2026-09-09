"""Shared language picker builders (AD-10).

One builder module feeds all three mode views so picker options never drift.
Every Dropdown lists all 23 LANGUAGES verbatim with no filtering and no
gating on any code/name combo. Source pickers default to English until the
E2/E3 pipeline brings auto-detect behavior.
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
    """Return a source-override Dropdown defaulting to English."""
    return ft.Dropdown(
        label="Source language",
        options=_language_options(),
        value="en",
    )
