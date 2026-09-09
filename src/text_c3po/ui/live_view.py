"""Live mode surface: labeled placeholder (session controls arrive in E3 scope)."""

import flet as ft

from .language_pickers import build_source_dropdown, build_target_dropdown


def build_live_view() -> ft.Column:
    """Return the labeled Live placeholder surface with language pickers."""
    source = build_source_dropdown()
    target = build_target_dropdown()
    return ft.Column(
        [
            ft.Text("Live"),
            ft.Row([source, target], wrap=True),
            ft.Text("Press Start and speak \u2014 captions appear here."),
        ]
    )
