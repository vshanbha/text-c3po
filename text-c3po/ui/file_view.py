"""File mode surface: labeled placeholder (picker + progress arrive in E2 scope)."""

import flet as ft

from .language_pickers import build_source_dropdown, build_target_dropdown


def build_file_view() -> ft.Column:
    """Return the labeled File placeholder surface with language pickers."""
    source = build_source_dropdown()
    target = build_target_dropdown()
    return ft.Column(
        [
            ft.Text("File"),
            ft.Row([source, target]),
            ft.Text("Pick a file to begin \u2014 results appear here."),
        ]
    )
