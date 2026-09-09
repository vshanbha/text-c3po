"""Top chrome: Material AppBar plus compact mode toolbar (CAP-1/CAP-2/CAP-4).

The AppBar owns the title only. The toolbar below owns the full-width
Text/Live/File SegmentedButton plus a compact status row (dot, model
Dropdown): the dot alone signals state, and its hover tooltip carries the
detail plus the fix. Mutable refs live in toolbar.data (toggle, dot,
status, model_dropdown) so app.py can refresh them in place.
"""

import flet as ft

from .model_picker import build_model_dropdown, refresh_model_options

SUCCESS_DOT = "#1E7E34"
# Material 3 error red (light scheme): a down server is an error state, so
# the dot reads as one — never amber, never the only signal (tooltip text
# plus a SnackBar on disconnect carry the words).
ERROR_DOT = "#B3261E"

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
    on_retry=None,
    on_refresh_models=None,
) -> ft.AppBar:
    """Return the Material AppBar: title only.

    Retry/Models used to live here as buttons; they now live on the toolbar
    status row (click the Ollama status to re-check, model list refreshes on
    every probe), so the bar carries no actions. Params stay for call compat.
    """
    bar = ft.AppBar(
        title=ft.Text("text-c3po"),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
    )
    bar.data = {}
    return bar


def build_toolbar(
    on_mode_change,
    ollama_connected: bool = False,
    models=None,
    selected_model=None,
    on_model_change=None,
    on_status_click=None,
    ollama_url=None,
) -> ft.Column:
    """Return the compact toolbar: full-width mode toggle plus status row.

    The dot alone signals Ollama state (click re-probes; hover tooltip
    carries the detail plus the fix) and the model list refreshes on every
    probe — no separate buttons, no status sentence eating width.
    ``ollama_url`` is a plain display string so ui/ never imports
    runtimes (layering rule); app.py passes it in.
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
        expand=True,
    )
    dot = _status_dot(bool(ollama_connected))
    status = ft.GestureDetector(
        content=dot,
        tooltip=status_detail(bool(ollama_connected), ollama_url),
        mouse_cursor=ft.MouseCursor.CLICK,
        on_tap=on_status_click,
    )
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
                [model_dropdown, status],
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
        "status": status,
        "model_dropdown": model_dropdown,
    }
    return bar


def refresh_ollama_status(strip, connected: bool, appbar=None, ollama_url=None) -> None:
    """Refresh the toolbar dot plus its hover detail (caller updates the page).

    ``appbar`` stays for call compat and is ignored (title-only bar).
    """
    refs = strip.data if isinstance(getattr(strip, "data", None), dict) else {}
    dot = refs.get("dot")
    status = refs.get("status")
    if dot is not None:
        try:
            dot.bgcolor = SUCCESS_DOT if connected else ERROR_DOT
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
