"""Live mode surface: device picker plus language pickers (E2-1).

Session controls (Start/Stop, captions) arrive in E3 scope; this module
owns only the capture-device Dropdown, enumerated at launch.
"""

import flet as ft

from .captions import build_captions_pane
from .device_picker import build_device_dropdown
from .language_pickers import build_source_dropdown, build_target_dropdown
from .status import status_dot


def build_live_view(
    devices=None,
    selected_device=None,
    on_device_change=None,
    on_caption_retry=None,
    on_start=None,
    on_stop=None,
) -> ft.Column:
    """Return the Live surface: pickers, session controls, status, captions."""
    source = build_source_dropdown()
    target = build_target_dropdown()
    device_dropdown = build_device_dropdown(devices or [], selected_device)
    if on_device_change is not None:
        try:
            # Dropdown emits on_select in flet 0.86 (no on_change event).
            device_dropdown.on_select = on_device_change
        except Exception:
            pass
    start_button = ft.Button("Start")
    stop_button = ft.Button("Stop", visible=False)
    if on_start is not None:
        try:
            start_button.on_click = on_start
        except Exception:
            pass
    if on_stop is not None:
        try:
            stop_button.on_click = on_stop
        except Exception:
            pass
    capture_dot = status_dot(None)
    capture_label = ft.Text("Idle")
    whisper_dot = status_dot(None)
    whisper_label = ft.Text("Whisper: ?")
    status_row = ft.Row(
        [capture_dot, capture_label, whisper_dot, whisper_label], spacing=6
    )
    captions_pane = build_captions_pane(on_retry=on_caption_retry)
    view = ft.Column(
        [
            ft.Text("Live"),
            ft.Row([source, target], wrap=True),
            device_dropdown,
            ft.Row([start_button, stop_button], spacing=8),
            status_row,
            captions_pane,
            ft.Text("Press Start and speak \u2014 captions appear here."),
        ],
        expand=True,
    )
    view.data = {
        "device_dropdown": device_dropdown,
        "captions_pane": captions_pane,
        "source_dropdown": source,
        "target_dropdown": target,
        "start_button": start_button,
        "stop_button": stop_button,
        "capture_dot": capture_dot,
        "capture_label": capture_label,
        "whisper_dot": whisper_dot,
        "whisper_label": whisper_label,
    }
    return view
