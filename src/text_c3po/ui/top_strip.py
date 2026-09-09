"""Top chrome: Material AppBar plus compact mode toolbar (CAP-1/CAP-2/CAP-4).

The AppBar owns the title and the two icon actions (re-probe Ollama,
refresh the model list). The toolbar below owns the full-width
Text/Live/File SegmentedButton plus a compact status row (dot, label,
model Dropdown). Mutable refs live in toolbar.data (toggle, dot, label,
model_dropdown) and appbar.data (retry, refresh_models) so app.py can
refresh them in place.
"""

import flet as ft

from .model_picker import build_model_dropdown, refresh_model_options

SUCCESS_DOT = "#1E7E34"
WARNING_DOT = "#B45309"

CONNECTED_TEXT = "Ollama connected"
NOT_RUNNING_TEXT = "Ollama isn't running. Start `ollama serve`, then Retry."


def _status_dot(connected: bool) -> ft.Container:
    """Return the 10px status circle: green when connected, amber otherwise."""
    return ft.Container(
        width=10,
        height=10,
        border_radius=5,
        bgcolor=SUCCESS_DOT if connected else WARNING_DOT,
    )


def _status_label(connected: bool) -> ft.Text:
    """Return the status text paired with the dot (color is never the only signal)."""
    return ft.Text(CONNECTED_TEXT if connected else NOT_RUNNING_TEXT)


def build_appbar(
    ollama_connected: bool = False,
    on_retry=None,
    on_refresh_models=None,
) -> ft.AppBar:
    """Return the Material AppBar: title plus labeled Retry/Models actions.

    Labels instead of icon-only buttons: icon meaning is undiscoverable
    without hovering, and these two are the app's lifeline when Ollama is
    down or the model list changes.
    """
    retry = ft.TextButton(
        text="Retry",
        tooltip="Retry Ollama connection",
        on_click=on_retry,
    )
    if retry is not None:
        try:
            retry.autofocus = not ollama_connected
        except Exception:
            pass
    refresh = ft.TextButton(
        text="Models",
        tooltip="Refresh model list",
        on_click=on_refresh_models,
    )
    bar = ft.AppBar(
        title=ft.Text("text-c3po"),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        actions=[retry, refresh],
    )
    bar.data = {"retry": retry, "refresh_models": refresh}
    return bar


def build_toolbar(
    on_mode_change,
    ollama_connected: bool = False,
    models=None,
    selected_model=None,
    on_model_change=None,
) -> ft.Column:
    """Return the compact toolbar: full-width mode toggle plus status row."""
    toggle = ft.SegmentedButton(
        segments=[
            ft.Segment("text", label="Text"),
            ft.Segment("live", label="Live"),
            ft.Segment("file", label="File"),
        ],
        selected=["text"],
        allow_empty_selection=False,
        on_change=on_mode_change,
        expand=True,
    )
    dot = _status_dot(bool(ollama_connected))
    label = _status_label(bool(ollama_connected))
    model_dropdown = build_model_dropdown(models or [], selected_model)
    # Fixed width: never combine expand with a wrapping Row — the expanded
    # child collapses to zero size. Wrap stays so narrow windows reflow.
    model_dropdown.width = 260
    if on_model_change is not None:
        model_dropdown.on_change = on_model_change
    bar = ft.Column(
        [
            ft.Row([toggle], spacing=0),
            ft.Row(
                [dot, label, model_dropdown],
                spacing=8,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=8,
    )
    bar.data = {
        "toggle": toggle,
        "dot": dot,
        "label": label,
        "model_dropdown": model_dropdown,
    }
    return bar


def refresh_ollama_status(strip, connected: bool, appbar=None) -> None:
    """Refresh the toolbar dot/label pair in place (caller updates the page)."""
    refs = strip.data if isinstance(getattr(strip, "data", None), dict) else {}
    dot = refs.get("dot")
    label = refs.get("label")
    if dot is not None:
        dot.bgcolor = SUCCESS_DOT if connected else WARNING_DOT
    if label is not None:
        label.value = CONNECTED_TEXT if connected else NOT_RUNNING_TEXT
    if appbar is not None:
        bar_refs = (
            appbar.data if isinstance(getattr(appbar, "data", None), dict) else {}
        )
        retry = bar_refs.get("retry")
        if retry is not None:
            try:
                retry.autofocus = not connected
            except Exception:
                pass


def refresh_model_picker(strip, models, selected=None) -> None:
    """Refresh the toolbar model Dropdown options/value in place."""
    refs = strip.data if isinstance(getattr(strip, "data", None), dict) else {}
    dropdown = refs.get("model_dropdown")
    if dropdown is not None:
        refresh_model_options(dropdown, models or [], selected)
