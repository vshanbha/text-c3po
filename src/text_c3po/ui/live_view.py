"""Live mode surface: device picker plus language pickers (E2-1).

Session controls (Start/Stop, captions) arrive in E3 scope; this module
owns only the capture-device Dropdown, enumerated at launch.
"""

import flet as ft

from .device_picker import build_device_dropdown
from .language_pickers import build_source_dropdown, build_target_dropdown


def build_live_view(
    devices=None, selected_device=None, on_device_change=None
) -> ft.Column:
    """Return the Live surface with device picker plus language pickers."""
    source = build_source_dropdown()
    target = build_target_dropdown()
    device_dropdown = build_device_dropdown(devices or [], selected_device)
    if on_device_change is not None:
        try:
            # Dropdown emits on_select in flet 0.86 (no on_change event).
            device_dropdown.on_select = on_device_change
        except Exception:
            pass
    view = ft.Column(
        [
            ft.Text("Live"),
            ft.Row([source, target], wrap=True),
            device_dropdown,
            ft.Text("Press Start and speak \u2014 captions appear here."),
        ]
    )
    view.data = {"device_dropdown": device_dropdown}
    return view
