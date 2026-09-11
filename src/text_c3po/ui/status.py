"""Live status indicators (E3-3): dot-plus-label painters.

Live Red marks capture-running only; errors use the Material error
color; every dot pairs with a text label (DESIGN.md). Pure mutation
helpers over control refs — headless-testable with fakes, never raise.
"""

# Live Red: capture-running is its own signal, never the error red.
LIVE_RED = "#D64541"
LIVE_GREEN = "#1E7E34"


def paint_status(dot, label, color, text) -> None:
    """Paint one dot-plus-label indicator. Never raises."""
    try:
        if dot is not None:
            try:
                dot.bgcolor = color
            except Exception:
                pass
        if label is not None:
            try:
                label.value = text
            except Exception:
                pass
    except Exception:
        pass


def status_dot(color) -> "object":
    """Return a 10px status circle in the given color. Never raises."""
    import flet as ft

    try:
        return ft.Container(width=10, height=10, border_radius=5, bgcolor=color)
    except Exception:
        return None
