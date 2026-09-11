"""Capture-device picker builders: pure-UI Dropdown over plain device names.

Takes only ``list[str]`` verbatim from ``runtimes.list_devices`` plus a
preselected value; never imports the lower layer. The default rule lives
in ``runtimes.audio_devices.pick_default_device`` and arrives here as the
``selected`` argument, so this module holds no device policy.
"""

import flet as ft


def build_device_dropdown(devices, selected=None) -> ft.Dropdown:
    """Return a capture-device Dropdown listing ``devices`` verbatim."""
    names = list(devices) if isinstance(devices, list) else []
    return ft.Dropdown(
        label="Device",
        options=[ft.DropdownOption(key=name, text=name) for name in names],
        value=selected,
    )


def refresh_device_options(dropdown: ft.Dropdown, devices, selected=None) -> None:
    """Refresh an existing device Dropdown's options/value in place."""
    names = list(devices) if isinstance(devices, list) else []
    dropdown.options = [ft.DropdownOption(key=name, text=name) for name in names]
    dropdown.value = selected
