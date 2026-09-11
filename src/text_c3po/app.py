"""text-c3po v2 Flet entry point: CAP-1 shell window with mode switching.

Mounts the always-visible top strip plus the Text/Live/File mode views.
Views are built once and toggled visible so input text survives switches.
"""

import os
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
from text_c3po.runtimes.audio_file import supported_extensions
from text_c3po.runtimes.process_manager import (
    ProcessManager,
    default_model_path,
    install_exit_cleanup,
)
from text_c3po.runtimes.whisper_client import transcribe_wav
from text_c3po.services.asr import transcribe_file
from text_c3po.services.live_runner import LiveRunner
from text_c3po.services.session import SessionController
from text_c3po.ui.captions import reset_pane, sync_captions
from text_c3po.ui.status import LIVE_GREEN, LIVE_RED, paint_status
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

    # E2-3: own whisper-server for the session. Skipped silently when no
    # model file resolves (file mode errors readably at use time); spawned
    # off the UI thread so first paint never waits on model load; atexit
    # guarantees no orphan on exit. Crash-restart status UI arrives with
    # E3's indicators.
    whisper_manager = None
    try:
        whisper_model = default_model_path()
        if whisper_model:
            whisper_manager = ProcessManager(model_path=whisper_model)
            # atexit plus SIGTERM/SIGINT so kills never orphan the server.
            install_exit_cleanup(whisper_manager)

            def _start_whisper() -> None:
                try:
                    whisper_manager.start()
                    whisper_manager.wait_ready()
                except Exception:
                    pass

            threading.Thread(target=_start_whisper, daemon=True).start()
    except Exception:
        whisper_manager = None

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

    # E2-4: file mode — FilePicker overlay plus a daemon worker running the
    # shared decode → transcribe → translate pipeline off the UI thread.
    file_busy = {"working": False}

    def _set_file_status(message: str, result=None) -> None:
        try:
            refs = file_view.data if isinstance(file_view.data, dict) else {}
            status = refs.get("status_text")
            if status is not None:
                status.value = message
            result_control = refs.get("result_text")
            if result_control is not None and result is not None:
                result_control.value = result if isinstance(result, str) else ""
            button = refs.get("pick_button")
            if button is not None:
                button.disabled = file_busy["working"]
            page.update()
        except Exception:
            pass

    def _run_file(path: str) -> None:
        try:
            refs = file_view.data if isinstance(file_view.data, dict) else {}
            target_dropdown = refs.get("target_dropdown")
            try:
                target_value = (
                    target_dropdown.value if target_dropdown is not None else None
                )
            except Exception:
                target_value = None
            target_value = name_for_code(target_value)
            try:
                result = transcribe_file(path, target_value, current_model.get("value"))
            except Exception:
                result = {"error": "Couldn't parse that one. Retry."}
            if isinstance(result, dict) and result.get("error"):
                _set_file_status(str(result["error"]))
                return
            try:
                shown = result.get("formal", "") if isinstance(result, dict) else ""
                tally = (
                    "Translated · {} chars".format(len(shown))
                    if isinstance(shown, str)
                    else ""
                )
            except Exception:
                tally, shown = "", ""
            _set_file_status(tally, shown if isinstance(shown, str) else "")
        except Exception:
            pass
        finally:
            file_busy["working"] = False
            try:
                refs = file_view.data if isinstance(file_view.data, dict) else {}
                button = refs.get("pick_button")
                if button is not None:
                    button.disabled = False
                page.update()
            except Exception:
                pass

    async def on_pick_file(e=None) -> None:
        # flet 0.86 FilePicker is awaitable-only (no on_result event):
        # pick_files returns the picked list, [] on cancel.
        if file_busy["working"]:
            return
        try:
            files = await file_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=[ext.lstrip(".") for ext in supported_extensions()],
            )
        except Exception:
            return
        try:
            picked = (files or [None])[0]
            path = getattr(picked, "path", None) if picked is not None else None
        except Exception:
            path = None
        if not path or file_busy["working"]:
            return
        file_busy["working"] = True
        _set_file_status("Transcribing…", "")
        threading.Thread(target=_run_file, args=(path,), daemon=True).start()

    try:
        file_picker = ft.FilePicker()
        page.overlay.append(file_picker)
    except Exception:
        file_picker = None
    try:
        file_refs = file_view.data if isinstance(file_view.data, dict) else {}
        file_pick_control = file_refs.get("pick_button")
        if file_pick_control is not None:
            file_pick_control.on_click = on_pick_file
    except Exception:
        pass

    # E3-3: live session — Start/Stop toggle plus capture/whisper status.
    # Threading note (AD-4): the runner only posts dicts to the controller
    # queue; _render_session is the single point that drains, syncs rows,
    # and updates the page (same worker-update tolerance E1 ships).
    live_controller = SessionController(target_language="English", model=selected_model)
    live_runner = {"current": None, "thread": None}

    def _live_refs() -> dict:
        try:
            refs = live_view.data if isinstance(live_view.data, dict) else {}
            return refs if isinstance(refs, dict) else {}
        except Exception:
            return {}

    def _set_live_buttons(running: bool) -> None:
        try:
            refs = _live_refs()
            start_control = refs.get("start_button")
            stop_control = refs.get("stop_button")
            if start_control is not None:
                try:
                    start_control.disabled = running
                except Exception:
                    pass
            if stop_control is not None:
                try:
                    stop_control.visible = running
                except Exception:
                    pass
        except Exception:
            pass

    def _paint_live(capture_on: bool, whisper_ok=None) -> None:
        try:
            refs = _live_refs()
            if capture_on:
                paint_status(
                    refs.get("capture_dot"),
                    refs.get("capture_label"),
                    LIVE_RED,
                    "Live",
                )
            else:
                paint_status(
                    refs.get("capture_dot"),
                    refs.get("capture_label"),
                    None,
                    "Idle",
                )
            if whisper_ok is True:
                paint_status(
                    refs.get("whisper_dot"),
                    refs.get("whisper_label"),
                    LIVE_GREEN,
                    "Whisper: ready",
                )
            elif whisper_ok is False:
                paint_status(
                    refs.get("whisper_dot"),
                    refs.get("whisper_label"),
                    ft.Colors.ERROR,
                    "Whisper: down",
                )
        except Exception:
            pass

    def _render_session() -> None:
        try:
            live_controller.drain()
            refs = _live_refs()
            pane = refs.get("captions_pane")
            if pane is not None:
                try:
                    sync_captions(pane, live_controller.captions())
                except Exception:
                    pass
            page.update()
        except Exception:
            pass

    def _run_live(runner) -> None:
        try:
            runner.run()
        except Exception:
            pass
        finally:
            try:
                _render_session()
            except Exception:
                pass

    def _supervise_live(target_value, model_value, device_value, source_value) -> None:
        try:
            manager = whisper_manager
            if manager is None:
                _paint_live(False, False)
                _set_live_buttons(False)
                try:
                    page.update()
                except Exception:
                    pass
                return
            try:
                state = manager.ensure_running()
            except Exception:
                state = "failed"
            if state not in ("ready", "restarted"):
                _paint_live(False, False)
                _set_live_buttons(False)
                try:
                    page.update()
                except Exception:
                    pass
                return
            try:
                live_controller.target_language = target_value
                live_controller.model = model_value
            except Exception:
                pass
            live_controller.start_session()
            try:
                refs = _live_refs()
                pane = refs.get("captions_pane")
                if pane is not None:
                    reset_pane(pane)
            except Exception:
                pass
            runner = LiveRunner(
                live_controller,
                device=device_value,
                source_lang=source_value,
                transcribe_fn=transcribe_wav,
                on_utterance=_render_session,
            )
            live_runner["current"] = runner
            _paint_live(True, True)
            _set_live_buttons(True)
            try:
                page.update()
            except Exception:
                pass
            live_runner["thread"] = threading.Thread(
                target=_run_live, args=(runner,), daemon=True
            )
            live_runner["thread"].start()
        except Exception:
            pass

    def _refuse_live_start(message: str) -> None:
        try:
            refs = _live_refs()
            label = refs.get("capture_label")
            if label is not None:
                try:
                    label.value = message
                except Exception:
                    pass
            _set_live_buttons(False)
            _paint_live(False, None)
            page.update()
        except Exception:
            pass

    def on_caption_retry(seq=None) -> None:
        try:
            if seq is None:
                return

            def _work() -> None:
                try:
                    updated = live_controller.retry_caption(seq)
                except Exception:
                    updated = None
                try:
                    _render_session()
                except Exception:
                    pass
                try:
                    if isinstance(updated, dict) and updated.get("kind") == "error":
                        _show_snackbar(
                            page,
                            "Still failing — check Ollama, then retry.",
                            lambda e=None: on_caption_retry(seq),
                        )
                except Exception:
                    pass

            threading.Thread(target=_work, daemon=True).start()
        except Exception:
            pass

    try:
        refs = _live_refs()
        pane = refs.get("captions_pane")
        if pane is not None:
            try:
                pane_data = pane.data if isinstance(pane.data, dict) else None
                if pane_data is not None:
                    pane_data["on_retry"] = on_caption_retry
            except Exception:
                pass
    except Exception:
        pass

    def on_start_live(e=None) -> None:
        try:
            refs = _live_refs()
            if (
                live_runner.get("current") is not None
                and live_runner["current"].is_running()
            ):
                return
            if not current_device.get("value"):
                _refuse_live_start("No capture device — plug in a mic, then retry.")
                return
            if not current_model.get("value"):
                _refuse_live_start("Pick a model first.")
                return
            try:
                target_dropdown = refs.get("target_dropdown")
                target_value = (
                    target_dropdown.value if target_dropdown is not None else None
                )
            except Exception:
                target_value = None
            target_value = name_for_code(target_value) or "English"
            try:
                source_dropdown = refs.get("source_dropdown")
                source_value = (
                    source_dropdown.value if source_dropdown is not None else None
                )
            except Exception:
                source_value = None
            source_value = name_for_code(source_value)
            model_value = current_model.get("value")
            device_value = current_device.get("value")
            _set_live_buttons(True)
            _paint_live(True, None)
            try:
                page.update()
            except Exception:
                pass
            threading.Thread(
                target=_supervise_live,
                args=(target_value, model_value, device_value, source_value),
                daemon=True,
            ).start()
        except Exception:
            pass

    def on_stop_live(e=None) -> None:
        try:
            runner = live_runner.get("current")
            if runner is not None:
                try:
                    runner.request_stop()
                except Exception:
                    pass
                try:
                    thread = live_runner.get("thread")
                    if thread is not None:
                        thread.join(timeout=2.0)
                except Exception:
                    pass
            live_runner["current"] = None
            live_runner["thread"] = None
            try:
                live_controller.end_session()
            except Exception:
                pass
            _set_live_buttons(False)
            _paint_live(False, None)
            try:
                page.update()
            except Exception:
                pass
        except Exception:
            pass

    try:
        live_refs = _live_refs()
        live_start = live_refs.get("start_button")
        if live_start is not None:
            live_start.on_click = on_start_live
        live_stop = live_refs.get("stop_button")
        if live_stop is not None:
            live_stop.on_click = on_stop_live
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
