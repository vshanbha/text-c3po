"""Model picker builders: pure-UI Dropdown over plain model names (CAP-4).

Takes only ``list[str]`` verbatim from ``/api/tags`` plus a preselected
value; never imports the lower layer. The default rule lives in the Ollama
client ``pick_default_model`` helper and arrives here as the ``selected``
argument, so this module holds no model policy.
"""

import flet as ft


def build_model_dropdown(models, selected=None) -> ft.Dropdown:
    """Return a Model Dropdown listing ``models`` verbatim with ``selected`` set."""
    names = list(models) if isinstance(models, list) else []
    return ft.Dropdown(
        label="Model",
        options=[ft.DropdownOption(key=name, text=name) for name in names],
        value=selected,
    )


def refresh_model_options(dropdown: ft.Dropdown, models, selected=None) -> None:
    """Refresh an existing model Dropdown's options/value in place."""
    names = list(models) if isinstance(models, list) else []
    dropdown.options = [ft.DropdownOption(key=name, text=name) for name in names]
    dropdown.value = selected
