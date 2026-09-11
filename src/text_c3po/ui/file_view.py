"""File mode surface: audio-file picker plus transcription status (E2-4).

Pick button, status line, and result text; the FilePicker overlay itself
is owned by app.py (it must mount on the page). Refs live in ``view.data``
so the file worker can update them in place.
"""

import flet as ft

from .language_pickers import build_source_dropdown, build_target_dropdown


def build_file_view(on_pick_file=None) -> ft.Column:
    """Return the File surface with picker button, status, and result."""
    source = build_source_dropdown()
    target = build_target_dropdown()
    pick_button = ft.Button("Pick audio file")
    if on_pick_file is not None:
        try:
            pick_button.on_click = on_pick_file
        except Exception:
            pass
    status = ft.Text("")
    result = ft.Text("", selectable=True)
    view = ft.Column(
        [
            ft.Text("File"),
            ft.Row([source, target], wrap=True),
            pick_button,
            status,
            result,
        ]
    )
    view.data = {
        "source_dropdown": source,
        "target_dropdown": target,
        "pick_button": pick_button,
        "status_text": status,
        "result_text": result,
    }
    return view
