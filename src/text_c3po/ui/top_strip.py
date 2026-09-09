"""Top chrome: Material AppBar plus mode toolbar (CAP-1/CAP-2/CAP-4).

The AppBar owns the title plus, top-right, the model picker and the Ollama
status dot with its Connected/Down label (click re-probes; hover carries
detail plus the fix). The toolbar
below is just the full-width Text/Live/File SegmentedButton. Mutable refs
live in appbar.data (model_dropdown, dot, label, status) and toolbar.data (toggle)
so app.py can refresh them in place.
"""

import flet as ft

from .model_picker import build_model_dropdown, refresh_model_options

SUCCESS_DOT = "#1E7E34"
# Material 3 error red (light scheme): a down server is an error state —
# connection loss is unrecoverable in-app (operator decision 2026-09-09),
# so it reads as an error, never amber. Never the only signal either: label
# text plus a SnackBar on disconnect carry the words.
ERROR_DOT = "#B3261E"

CONNECTED_LABEL = "Connected"
DOWN_LABEL = "Down"

CONNECTED_DETAIL = "Ollama connected at {}."
DOWN_DETAIL = (
    "Ollama isn't running — start it with `ollama serve`, then click to re-check."
)


def _status_dot(connected: bool) -> ft.Container:
    """Return the 10px status circle: green when connected, M3 error red otherwise."""
    return ft.Container(
        width=10,
        height=10,
        border_radius=5,
        bgcolor=SUCCESS_DOT if connected else ERROR_DOT,
    )


def status_detail(connected: bool, ollama_url=None) -> str:
    """Hover text for the dot: state plus what-to-do when down."""
    if connected:
        try:
            return CONNECTED_DETAIL.format(ollama_url or "loopback")
        except Exception:
            return "Ollama connected."
    return DOWN_DETAIL


def build_appbar(
    ollama_connected: bool = False,
    models=None,
    selected_model=None,
    on_model_change=None,
    on_status_click=None,
    ollama_url=None,
) -> ft.AppBar:
    """Return the Material AppBar: title plus status dot and model picker.

    Top-right cluster: status dot first, then the model picker (compact: no
    label, dense, hover explains). Clicking the dot re-probes; its hover
    carries state plus the fix. The model list refreshes on every probe.
    """
    model_dropdown = build_model_dropdown(models or [], selected_model)
    # Compact for AppBar height: no label, narrow, dense; never combine
    # expand with wrapping rows (expanded child collapses to zero size).
    try:
        model_dropdown.label = None
        model_dropdown.width = 200
        model_dropdown.dense = True
        model_dropdown.tooltip = "Ollama model — applies to the next call"
    except Exception:
        pass
    if on_model_change is not None:
        try:
            model_dropdown.on_change = on_model_change
        except Exception:
            pass
    dot = _status_dot(bool(ollama_connected))
    label = ft.Text(
        CONNECTED_LABEL if ollama_connected else DOWN_LABEL,
        size=13,
        color=None if ollama_connected else ERROR_DOT,
    )
    status = ft.GestureDetector(
        content=ft.Container(
            content=ft.Row([dot, label], spacing=6),
            alignment=ft.alignment.Alignment.CENTER,
            padding=ft.Padding.only(left=4, right=8),
        ),
        tooltip=status_detail(bool(ollama_connected), ollama_url),
        mouse_cursor=ft.MouseCursor.CLICK,
        on_tap=on_status_click,
    )
    bar = ft.AppBar(
        title=ft.Text("text-c3po"),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        # Right margin lives on the wrapper so the picker's edge aligns with
        # the pane margin below; data keeps the bare dropdown for refreshes.
        actions=[
            status,
            ft.Container(content=model_dropdown, padding=ft.Padding.only(right=12)),
        ],
    )
    bar.data = {
        "model_dropdown": model_dropdown,
        "dot": dot,
        "label": label,
        "status": status,
    }
    return bar


def build_toolbar(
    on_mode_change,
) -> ft.Column:
    """Return the mode toolbar: full-width Text/Live/File SegmentedButton."""
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
    bar = ft.Column(
        [ft.Row([toggle], spacing=0)],
        spacing=0,
    )
    bar.data = {"toggle": toggle}
    return bar


def refresh_ollama_status(
    holder, connected: bool, appbar=None, ollama_url=None
) -> None:
    """Refresh the status dot, label, and hover detail (caller updates page).

    ``holder`` is any control with .data holding dot/label/status — the
    AppBar since the cluster moved there. ``appbar`` stays for call compat.
    """
    refs = holder.data if isinstance(getattr(holder, "data", None), dict) else {}
    dot = refs.get("dot")
    label = refs.get("label")
    status = refs.get("status")
    if dot is not None:
        try:
            dot.bgcolor = SUCCESS_DOT if connected else ERROR_DOT
        except Exception:
            pass
    if label is not None:
        try:
            label.value = CONNECTED_LABEL if connected else DOWN_LABEL
            label.color = None if connected else ERROR_DOT
        except Exception:
            pass
    if status is not None:
        try:
            status.tooltip = status_detail(connected, ollama_url)
        except Exception:
            pass


def refresh_model_picker(strip, models, selected=None) -> None:
    """Refresh the toolbar model Dropdown options/value in place."""
    refs = strip.data if isinstance(getattr(strip, "data", None), dict) else {}
    dropdown = refs.get("model_dropdown")
    if dropdown is not None:
        refresh_model_options(dropdown, models or [], selected)
