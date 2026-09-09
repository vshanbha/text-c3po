"""text-c3po v2 Flet entry point: CAP-1 shell window with mode switching.

Mounts the always-visible top strip plus the Text/Live/File mode views.
Views are built once and toggled visible so input text survives switches.
"""

import flet as ft

from text_c3po.languages import name_for_code
from text_c3po.runtimes.ollama_client import check_ollama, pick_default_model
from text_c3po.services.translation import translate_text
from text_c3po.ui.file_view import build_file_view
from text_c3po.ui.live_view import build_live_view
from text_c3po.ui.text_view import build_text_view
from text_c3po.ui.top_strip import (
    build_appbar,
    build_toolbar,
    refresh_model_picker,
    refresh_ollama_status,
)

WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 640

RETRY_CARD_HINT = "Couldn't parse that one. Retry."
EMPTY_INPUT_HINT = "Type or paste something first."


def _show_retry_snackbar(page, on_retry) -> None:
    """Render the retry SnackBar; never raises (AD-12: inline plus SnackBar)."""
    try:
        snack = ft.SnackBar(
            content=ft.Text(RETRY_CARD_HINT),
            action="Retry",
            on_action=lambda e: on_retry(),
        )
        overlay = getattr(page, "overlay", None)
        if overlay is not None and hasattr(overlay, "append"):
            overlay.append(snack)
            try:
                snack.open = True
            except Exception:
                pass
        page.update()
    except Exception:
        pass


def _render_translation_result(refs, page, result, on_retry) -> None:
    """Render a translate_text result into the Formal/Informal tabs plus origin caption.

    Present fields display; only a missing/blank field's tab shows the retry
    hint. Any failure also raises the SnackBar retry; retry re-issues the same
    prompt without retyping.
    """
    try:
        refs = refs if isinstance(refs, dict) else {}
        if not isinstance(result, dict):
            result = {"error": RETRY_CARD_HINT, "retryable": True}
        if result.get("error"):
            for key in ("formal_text", "informal_text"):
                control = refs.get(key)
                if control is not None:
                    try:
                        control.value = RETRY_CARD_HINT
                    except Exception:
                        pass
            origin = refs.get("origin_caption")
            if origin is not None:
                try:
                    origin.value = ""
                except Exception:
                    pass
            _show_retry_snackbar(page, on_retry)
            return
        failed = False
        pairs = (
            ("formal_text", "formal"),
            ("informal_text", "informal"),
        )
        for ref_key, field in pairs:
            control = refs.get(ref_key)
            if control is None:
                failed = True
                continue
            value = result.get(field)
            if isinstance(value, list):
                value = ", ".join(str(part) for part in value)
            try:
                if isinstance(value, str) and value.strip():
                    control.value = value
                else:
                    control.value = RETRY_CARD_HINT
                    failed = True
            except Exception:
                failed = True
        origin_control = refs.get("origin_caption")
        origin_value = result.get("origin_language", "")
        if isinstance(origin_value, list):
            origin_value = ", ".join(str(part) for part in origin_value)
        try:
            if isinstance(origin_value, str) and origin_value.strip():
                if origin_control is not None:
                    origin_control.value = "origin: {}".format(origin_value.strip())
            else:
                if origin_control is not None:
                    origin_control.value = ""
                failed = True
        except Exception:
            failed = True
        if failed:
            _show_retry_snackbar(page, on_retry)
    except Exception:
        try:
            _show_retry_snackbar(page, on_retry)
        except Exception:
            pass


def main(page: ft.Page) -> None:
    page.title = "text-c3po"
    page.window.min_width = WINDOW_MIN_WIDTH
    page.window.min_height = WINDOW_MIN_HEIGHT
    # Material theme (DESIGN.md brand layer): primary blue seed, light mode,
    # comfortable page padding. All Material controls (buttons, dropdowns,
    # segmented toggle, fields, cards, snackbar) pick this up automatically.
    page.theme = ft.Theme(color_scheme_seed="blue")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 12
    page.spacing = 8
    # Single page-level scroller: views size to content, so a long paste or
    # tall output scrolls the window instead of clipping without a scrollbar.
    page.scroll = ft.ScrollMode.AUTO

    text_view = build_text_view()
    live_view = build_live_view()
    file_view = build_file_view()
    live_view.visible = False
    file_view.visible = False
    views = {"text": text_view, "live": live_view, "file": file_view}

    def on_mode_change(e: ft.ControlEvent) -> None:
        selected = e.control.selected or ["text"]
        current = selected[0]
        for name, view in views.items():
            view.visible = name == current
        page.update()

    connected, _startup_models = check_ollama()
    startup_models = list(_startup_models) if isinstance(_startup_models, list) else []
    selected_model = pick_default_model(startup_models)
    current_model = {"value": selected_model}
    chrome: dict = {}

    def on_model_change(e=None) -> None:
        try:
            control = getattr(e, "control", None) if e is not None else None
            new_value = control.value if control is not None else None
        except Exception:
            new_value = None
        current_model["value"] = new_value

    def _reprobe_and_refresh(e=None) -> None:
        ok, fresh = check_ollama()
        toolbar = chrome.get("toolbar")
        appbar = chrome.get("appbar")
        if toolbar is None:
            return
        refresh_ollama_status(toolbar, ok, appbar)
        if ok:
            fresh_models = list(fresh) if isinstance(fresh, list) else []
            prior = current_model.get("value")
            if prior not in fresh_models:
                try:
                    refs = toolbar.data if isinstance(toolbar.data, dict) else {}
                    dropdown = refs.get("model_dropdown")
                    dropdown_value = dropdown.value if dropdown is not None else None
                    if dropdown_value in fresh_models:
                        prior = dropdown_value
                except Exception:
                    pass
            selected = (
                prior if prior in fresh_models else pick_default_model(fresh_models)
            )
            refresh_model_picker(toolbar, fresh_models, selected)
            current_model["value"] = selected
        page.update()

    def on_retry(e=None) -> None:
        _reprobe_and_refresh(e)

    def on_refresh_models(e=None) -> None:
        _reprobe_and_refresh(e)

    def on_translate(e=None) -> None:
        refs = text_view.data if isinstance(text_view.data, dict) else {}
        input_field = refs.get("input_field")
        hint = refs.get("hint")
        translate_button = refs.get("translate_button")
        target_dropdown = refs.get("target_dropdown")
        try:
            if translate_button is not None and translate_button.disabled:
                return
        except Exception:
            pass
        try:
            raw_text = input_field.value if input_field is not None else ""
        except Exception:
            raw_text = ""
        if not isinstance(raw_text, str) or not raw_text.strip():
            if hint is not None:
                try:
                    hint.value = EMPTY_INPUT_HINT
                except Exception:
                    pass
            try:
                page.update()
            except Exception:
                pass
            return
        if hint is not None:
            try:
                hint.value = ""
            except Exception:
                pass
        if translate_button is not None:
            try:
                translate_button.disabled = True
            except Exception:
                pass
        try:
            page.update()
        except Exception:
            pass
        try:
            try:
                target_value = (
                    target_dropdown.value if target_dropdown is not None else None
                )
            except Exception:
                target_value = None
            # Picker values are codes ("de"); the translation contract (and
            # the gated test path) is language names ("German").
            target_value = name_for_code(target_value)
            model_value = current_model.get("value")
            result = translate_text(raw_text, target_value, model_value)
        except Exception:
            result = {"error": RETRY_CARD_HINT, "retryable": True}
        try:
            _render_translation_result(refs, page, result, on_translate_retry)
        finally:
            if translate_button is not None:
                try:
                    translate_button.disabled = False
                except Exception:
                    pass
            try:
                page.update()
            except Exception:
                pass

    def on_translate_retry(e=None) -> None:
        _reprobe_and_refresh(e)
        on_translate(e)

    try:
        translate_refs = text_view.data if isinstance(text_view.data, dict) else {}
        translate_control = translate_refs.get("translate_button")
        if translate_control is not None:
            translate_control.on_click = on_translate
    except Exception:
        pass

    appbar = build_appbar(
        ollama_connected=connected,
        on_retry=on_retry,
        on_refresh_models=on_refresh_models,
    )
    page.appbar = appbar
    toolbar = build_toolbar(
        on_mode_change,
        ollama_connected=connected,
        models=startup_models,
        selected_model=selected_model,
        on_model_change=on_model_change,
    )
    chrome["appbar"] = appbar
    chrome["toolbar"] = toolbar
    page.add(toolbar, text_view, live_view, file_view)
    page.update()


if __name__ == "__main__":
    ft.run(main)
