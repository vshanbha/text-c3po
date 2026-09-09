"""Top strip: always-visible single-row mode toggle plus Ollama status + model picker (CAP-1/CAP-2/CAP-4).

Hosts the Text/Live/File SegmentedButton plus a status dot paired with a
text label, a Retry action, a model Dropdown bound verbatim to /api/tags
names, and a Refresh action. The strip takes plain values and callbacks
only; later stories read the picker's current value at call time.
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


def build_top_strip(
    on_mode_change,
    ollama_connected: bool = False,
    on_retry=None,
    models=None,
    selected_model=None,
    on_model_change=None,
    on_refresh_models=None,
) -> ft.Row:
    """Return the always-visible strip row with toggle, status, Retry, picker, Refresh.

    on_mode_change switches the mode views; ollama_connected sets the
    startup dot/label pair; on_retry re-probes without restart. ``models``
    lists verbatim /api/tags names, ``selected_model`` is the preselected
    value (default rule applied by the caller), ``on_model_change`` stores
    mid-session picks for the next call, and ``on_refresh_models`` re-probes
    and refreshes the picker in place. Retry and Refresh stay visible in
    every state; Retry takes focus in the not-running state.
    """
    toggle = ft.SegmentedButton(
        segments=[
            ft.Segment("text", label="Text"),
            ft.Segment("live", label="Live"),
            ft.Segment("file", label="File"),
        ],
        selected=["text"],
        allow_empty_selection=False,
        on_change=on_mode_change,
    )
    dot = _status_dot(bool(ollama_connected))
    label = _status_label(bool(ollama_connected))
    retry = ft.TextButton(
        content=ft.Text("Retry"), on_click=on_retry, autofocus=not ollama_connected
    )
    model_dropdown = build_model_dropdown(models or [], selected_model)
    if on_model_change is not None:
        model_dropdown.on_change = on_model_change
    refresh = ft.TextButton(content=ft.Text("Refresh"), on_click=on_refresh_models)
    strip = ft.Row([toggle, dot, label, retry, model_dropdown, refresh])
    strip.data = {
        "dot": dot,
        "label": label,
        "retry": retry,
        "model_dropdown": model_dropdown,
        "refresh_models": refresh,
    }
    return strip


def refresh_ollama_status(strip: ft.Row, connected: bool) -> None:
    """Refresh an existing strip's dot/label pair in place (caller updates the page)."""
    refs = strip.data if isinstance(strip.data, dict) else {}
    dot = refs.get("dot")
    label = refs.get("label")
    retry = refs.get("retry")
    if dot is not None:
        dot.bgcolor = SUCCESS_DOT if connected else WARNING_DOT
    if label is not None:
        label.value = CONNECTED_TEXT if connected else NOT_RUNNING_TEXT
    if retry is not None:
        retry.autofocus = not connected


def refresh_model_picker(strip: ft.Row, models, selected=None) -> None:
    """Refresh an existing strip's model Dropdown options/value in place."""
    refs = strip.data if isinstance(strip.data, dict) else {}
    dropdown = refs.get("model_dropdown")
    if dropdown is not None:
        refresh_model_options(dropdown, models or [], selected)
