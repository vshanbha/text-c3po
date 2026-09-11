"""text-c3po v2 Flet entry point: CAP-1 shell window with mode switching.

Mounts the always-visible top strip plus the Text/Live/File mode views.
Views are built once and toggled visible so input text survives switches.
"""

import threading
import time

import flet as ft

from text_c3po.languages import name_for_code
from text_c3po.runtimes.ollama_client import (
    OLLAMA_BASE_URL,
    check_ollama,
    pick_default_model,
)
from text_c3po.runtimes.audio_devices import list_devices, pick_default_device
from text_c3po.services.translation import (
    cancel_inflight,
    extract_partial_formal,
    translate_text,
)
from text_c3po.ui.file_view import build_file_view
from text_c3po.ui.live_view import build_live_view
from text_c3po.ui.text_view import SOURCE_TITLE, build_text_view
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


def apply_mode_visibility(views, current):
    """Pure mode-switch helper (A8 V3 close-out): exactly one view visible.

    Mutates ``view.visible`` for each entry and returns ``current`` so the
    on_mode_change handler stays a one-liner. Unit-tested with fakes; the
    prior story-2 branching shipped without this assertion.
    """
    try:
        items = views.items()
    except Exception:
        return current
    for name, view in items:
        try:
            view.visible = name == current
        except Exception:
            pass
    return current


def ollama_state_changed(prev, ok, models) -> bool:
    """True when a fresh probe differs from the last rendered state.

    Pure helper for the background poll: the toolbar only re-renders (and
    the model picker only refreshes) on an actual flip, so idle polling
    never flickers the UI.
    """
    try:
        return prev != (bool(ok), list(models or []))
    except Exception:
        return True


def is_current_request(captured, current) -> bool:
    """True when a background result still owns the UI (cancel-by-generation).

    Stop (or a newer Translate) bumps the generation; the stale worker drops
    its result instead of overwriting the new state.
    """
    try:
        return captured == current
    except Exception:
        return False


def _set_translating(refs, page, busy: bool, status: str = "") -> None:
    """Toggle Translate/Stop/progress/status in one place; never raises."""
    try:
        translate_button = refs.get("translate_button")
        stop_button = refs.get("stop_button")
        progress = refs.get("progress_ring")
        status_text = refs.get("status_text")
        if translate_button is not None:
            try:
                translate_button.disabled = busy
            except Exception:
                pass
        if stop_button is not None:
            try:
                stop_button.visible = busy
            except Exception:
                pass
        if progress is not None:
            try:
                progress.visible = busy
            except Exception:
                pass
        if status_text is not None:
            try:
                status_text.value = status
            except Exception:
                pass
        page.update()
    except Exception:
        pass


DISCONNECT_SNACKBAR_HINT = "Ollama disconnected — start it with `ollama serve`."


def _show_snackbar(page, message, on_retry) -> None:
    """Render a SnackBar with a Retry action; never raises.

    Material's transient-error pattern: the dot shows state, this carries
    the words plus the one-tap fix.
    """
    try:
        snack = ft.SnackBar(
            content=ft.Text(message),
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


def _show_retry_snackbar(page, on_retry) -> None:
    """Render the retry SnackBar; never raises (AD-12: inline plus SnackBar)."""
    _show_snackbar(page, RETRY_CARD_HINT, on_retry)


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
                    origin.value = SOURCE_TITLE
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
                    origin_control.value = "Detected: {}".format(origin_value.strip())
            else:
                if origin_control is not None:
                    origin_control.value = SOURCE_TITLE
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
    page.bgcolor = "#EDF1F6"
    page.padding = 12
    page.spacing = 8
    # Single page-level scroller: views size to content, so a long paste or
    # tall output scrolls the window instead of clipping without a scrollbar.
    page.scroll = ft.ScrollMode.AUTO

    # E2-1: enumerate capture devices once at launch (sounddevice may be
    # absent — list_devices yields [] and never raises, so the app always
    # starts and file mode keeps working without a capture device).
    startup_devices = list_devices()
    selected_device = pick_default_device(startup_devices)
    current_device = {"value": selected_device}

    def on_device_change(e=None) -> None:
        try:
            control = getattr(e, "control", None) if e is not None else None
            new_value = control.value if control is not None else None
        except Exception:
            new_value = None
        current_device["value"] = new_value

    text_view = build_text_view()
    live_view = build_live_view(startup_devices, selected_device, on_device_change)
    file_view = build_file_view()
    live_view.visible = False
    file_view.visible = False
    views = {"text": text_view, "live": live_view, "file": file_view}

    def on_mode_change(e: ft.ControlEvent) -> None:
        selected = e.control.selected or ["text"]
        current = selected[0]
        apply_mode_visibility(views, current)
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
        holder = chrome.get("appbar")
        if holder is None:
            return
        refresh_ollama_status(holder, ok, None, OLLAMA_BASE_URL)
        if ok:
            fresh_models = list(fresh) if isinstance(fresh, list) else []
            prior = current_model.get("value")
            if prior not in fresh_models:
                try:
                    refs = holder.data if isinstance(holder.data, dict) else {}
                    dropdown = refs.get("model_dropdown")
                    dropdown_value = dropdown.value if dropdown is not None else None
                    if dropdown_value in fresh_models:
                        prior = dropdown_value
                except Exception:
                    pass
            selected = (
                prior if prior in fresh_models else pick_default_model(fresh_models)
            )
            refresh_model_picker(holder, fresh_models, selected)
            current_model["value"] = selected
        page.update()

    def on_retry(e=None) -> None:
        _reprobe_and_refresh(e)

    # Generation counter: each Translate bumps it; Stop bumps it too so the
    # running worker's result becomes stale and is dropped, never rendered.
    # The per-request stop Event is the true abort: the streaming loop polls
    # it between tokens and closes the connection, so Ollama stops generating.
    translate_seq = {"current": 0}
    translate_stop = {"event": None}

    def on_translate(e=None) -> None:
        # UI thread: validate, show progress + Stop, then run the LLM call on
        # a daemon worker so the window never freezes. translate_text itself
        # carries a 60s httpx timeout; Stop only ignores the late result (the
        # HTTP call itself is not aborted) and frees the UI for a new request.
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
        # Never fire into a dead server: fast loopback probe first. This also
        # self-heals a stale green dot the moment the user acts.
        try:
            alive, _ = check_ollama()
        except Exception:
            alive = False
        if not alive:
            _reprobe_and_refresh()
            if hint is not None:
                try:
                    hint.value = (
                        "Ollama isn't running — start it, then press Translate again."
                    )
                except Exception:
                    pass
            try:
                page.update()
            except Exception:
                pass
            return
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
        translate_seq["current"] += 1
        my_seq = translate_seq["current"]
        stop_event = threading.Event()
        translate_stop["event"] = stop_event
        snapshot = (raw_text, target_value, model_value)
        # New results stream into the Formal text: flip the toggle there
        # first so the first line is always where the user looks.
        try:
            style_toggle = refs.get("style_toggle")
            if style_toggle is not None:
                style_toggle.selected = ["formal"]
        except Exception:
            pass
        try:
            formal_control = refs.get("formal_text")
            if formal_control is not None:
                formal_control.visible = True
        except Exception:
            pass
        try:
            informal_control = refs.get("informal_text")
            if informal_control is not None:
                informal_control.visible = False
        except Exception:
            pass
        _set_translating(refs, page, True, "Translating…")

        def _work() -> None:
            try:
                text, target, model = snapshot
                progress = {"chars": 0, "at": 0.0, "raw": []}

                def on_token(piece, total) -> None:
                    # Live words, not a char count: the formal value prefix
                    # streams into its tab as it arrives; the final parsed
                    # JSON replaces it at the end.
                    if not is_current_request(my_seq, translate_seq["current"]):
                        return
                    try:
                        progress["raw"].append(piece)
                    except Exception:
                        pass
                    now = time.monotonic()
                    if total - progress["chars"] < 60 and now - progress["at"] < 0.2:
                        return
                    progress["chars"] = total
                    progress["at"] = now
                    try:
                        preview = extract_partial_formal("".join(progress["raw"]))
                    except Exception:
                        preview = ""
                    try:
                        status_text = refs.get("status_text")
                        if status_text is not None:
                            status_text.value = (
                                "Translating…"
                                if not preview
                                else "Translating… {} chars".format(total)
                            )
                    except Exception:
                        pass
                    if preview:
                        try:
                            formal_control = refs.get("formal_text")
                            if formal_control is not None:
                                formal_control.value = preview + "…"
                        except Exception:
                            pass
                    try:
                        page.update()
                    except Exception:
                        pass

                try:
                    result = translate_text(
                        text,
                        target,
                        model,
                        on_token=on_token,
                        stop_event=stop_event,
                    )
                except Exception:
                    result = {"error": RETRY_CARD_HINT, "retryable": True}
                if not is_current_request(my_seq, translate_seq["current"]):
                    return  # stopped or superseded: drop, never render
                if isinstance(result, dict) and result.get("cancelled"):
                    _set_translating(refs, page, False, "Stopped.")
                    return
                # Completeness cue: char count of what actually rendered, so
                # a short result is visible as a number, not a feeling.
                try:
                    shown = result.get("formal", "") if isinstance(result, dict) else ""
                    tally = (
                        "Translated · {} chars".format(len(shown))
                        if isinstance(shown, str)
                        else ""
                    )
                except Exception:
                    tally = ""
                try:
                    _render_translation_result(refs, page, result, on_translate_retry)
                finally:
                    if is_current_request(my_seq, translate_seq["current"]):
                        _set_translating(refs, page, False, tally)
                    else:
                        try:
                            page.update()
                        except Exception:
                            pass
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

    def on_stop_translate(e=None) -> None:
        # Full stop: signal the streaming loop, close the connection so the
        # server aborts mid-generation, then bump the generation so any late
        # result is dropped. The worker thread itself can't be killed, but it
        # holds no connection afterwards and the UI is free immediately.
        refs = text_view.data if isinstance(text_view.data, dict) else {}
        try:
            event = translate_stop.get("event")
            if event is not None:
                try:
                    event.set()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            cancel_inflight()
        except Exception:
            pass
        translate_seq["current"] += 1
        translate_stop["event"] = None
        _set_translating(refs, page, False, "Stopped.")

    def on_translate_retry(e=None) -> None:
        _reprobe_and_refresh(e)
        on_translate(e)

    try:
        translate_refs = text_view.data if isinstance(text_view.data, dict) else {}
        translate_control = translate_refs.get("translate_button")
        if translate_control is not None:
            translate_control.on_click = on_translate
        stop_control = translate_refs.get("stop_button")
        if stop_control is not None:
            stop_control.on_click = on_stop_translate
    except Exception:
        pass

    appbar = build_appbar(
        ollama_connected=connected,
        models=startup_models,
        selected_model=selected_model,
        on_model_change=on_model_change,
        on_status_click=on_retry,
        ollama_url=OLLAMA_BASE_URL,
    )
    page.appbar = appbar
    toolbar = build_toolbar(on_mode_change)
    chrome["appbar"] = appbar
    chrome["toolbar"] = toolbar
    page.add(toolbar, text_view, live_view, file_view)
    page.update()

    # Stale-status fix: Ollama can die after launch while the dot stays
    # green. A daemon poll re-probes loopback and re-renders only on a flip,
    # so shutdowns and restarts surface within seconds, never on next click.
    poll_state = {"last": (connected, startup_models)}

    def _poll_ollama() -> None:
        while True:
            try:
                time.sleep(15)
            except Exception:
                return
            try:
                ok, fresh = check_ollama()
                fresh_models = list(fresh) if isinstance(fresh, list) else []
            except Exception:
                continue
            try:
                if ollama_state_changed(poll_state["last"], ok, fresh_models):
                    went_down = poll_state["last"][0] and not ok
                    poll_state["last"] = (ok, fresh_models)
                    holder = chrome.get("appbar")
                    if holder is not None:
                        refresh_ollama_status(holder, ok, None, OLLAMA_BASE_URL)
                        if ok:
                            prior = current_model.get("value")
                            if prior not in fresh_models:
                                try:
                                    refs = (
                                        holder.data
                                        if isinstance(holder.data, dict)
                                        else {}
                                    )
                                    dropdown = refs.get("model_dropdown")
                                    dropdown_value = (
                                        dropdown.value if dropdown is not None else None
                                    )
                                    if dropdown_value in fresh_models:
                                        prior = dropdown_value
                                except Exception:
                                    pass
                            selected = (
                                prior
                                if prior in fresh_models
                                else pick_default_model(fresh_models)
                            )
                            refresh_model_picker(holder, fresh_models, selected)
                            current_model["value"] = selected
                        page.update()
                    if went_down:
                        _show_snackbar(page, DISCONNECT_SNACKBAR_HINT, on_retry)
            except Exception:
                return

    threading.Thread(target=_poll_ollama, daemon=True).start()


if __name__ == "__main__":
    ft.run(main)


def run() -> None:
    """Console-script entry point (``text-c3po``): launch the Flet window."""
    ft.run(main)
