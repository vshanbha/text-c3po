"""text-c3po v2 Flet entry point: CAP-1 shell window with mode switching.

Mounts the always-visible top strip plus the Text/Live/File mode views.
Views are built once and toggled visible so input text survives switches.
"""

import atexit
import logging
import os
import threading
import time

import flet as ft

logger = logging.getLogger(__name__)

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
from text_c3po.messages import (
    DISCONNECT_SNACKBAR_HINT,
    EMPTY_INPUT_HINT,
    NO_VARIANT_HINT,
    RETRY_HINT,
    TRUNCATED_INFORMAL_HINT,
    TRUNCATED_TALLY,
    WIRING_HINT,
)
from text_c3po.ui.text_view import SOURCE_TITLE, build_text_view
from text_c3po.ui.top_strip import (
    build_appbar,
    build_toolbar,
    refresh_model_picker,
    refresh_ollama_status,
)

WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 640

# Backward-compatible aliases: render code and tests reference these
# app-level names; every wording lives once in text_c3po.messages.
RETRY_CARD_HINT = RETRY_HINT


def _result_tally(result) -> str:
    """Status-line tally for a translate result; never raises.

    Full renders get the Translated count, truncated results name their
    partial state, and errors plus blank primaries get no tally at all
    ("Translated · 0 chars" next to an error card is a lie told by
    len("")). Shared by the text and file workers so both agree.
    """
    try:
        if not isinstance(result, dict) or result.get("error"):
            return ""
        shown = result.get("formal", "")
        # Mirror the renderer's list coercion (run_matrix proves list
        # formals occur via future service shapes): tally what the card
        # actually shows, or nothing when it shows nothing.
        if isinstance(shown, list):
            shown = ", ".join(str(part) for part in shown)
        if not (isinstance(shown, str) and shown.strip()):
            return ""
        if result.get("truncated"):
            return TRUNCATED_TALLY.format(len(shown))
        return "Translated · {} chars".format(len(shown))
    except Exception:
        return ""


# E3-9 (D3 re-decision B+, 2026-09-13; loop marshaling 2026-09-14):
# single serialized render point. Every background thread (capture drain,
# supervise, retry, poll, file worker, translate worker) funnels
# page.update() through _ui_update(page). The update itself runs on the
# session event loop via call_soon_threadsafe — a raw-thread page.update()
# is silently dropped by flet 0.86 (send-queue wakeup is loop-bound), which
# is the stuck-spinner symptom: spinner shows (UI-thread update) and then
# nothing renders until the next UI-thread event such as refocus.
# _UI_LOCK serializes concurrent renders so they cannot interleave. Only
# main-thread event handlers (mode/mode-switch, Start/Stop, Translate,
# pickers, main) call page.update() directly.
_UI_LOCK = threading.Lock()


def _locked_update(page) -> None:
    """page.update() under the render lock; never raises."""
    try:
        with _UI_LOCK:
            page.update()
    except Exception:
        pass


def _session_loop(page):
    """Return the session event loop, or None (headless fakes, torn-down pages).

    The ``page.session.connection.loop`` chain is load-bearing for the F3
    fix; a Flet upgrade renaming any link lands here, not scattered
    call-by-call.
    """
    try:
        return page.session.connection.loop
    except Exception:
        return None


def _has_session(page) -> bool:
    """True when the page carries a live session reference; never raises.

    Plain hasattr() is wrong here: flet's Page.session property raises
    RuntimeError (not AttributeError) once the session is destroyed, and
    hasattr propagates non-AttributeError — which would skip the render
    entirely on the shutdown race workers hit at exit.
    """
    try:
        return page.session is not None
    except Exception:
        return False


def _warn_loop_fallback(where: str, page) -> None:
    """Log the degraded inline render path on real pages; never raises."""
    try:
        if _has_session(page):
            # Real page, unusable loop: the marshaling regressed (e.g. a
            # Flet upgrade renamed the chain). Loud, not silent — the
            # fallback is the dropped-render path from F3.
            logger.warning("%s loop fallback; renders may drop", where)
    except Exception:
        pass


def _ui_update(page) -> None:
    """Serialized page.update() marshaled onto the session loop; never raises."""
    try:
        posted = False
        try:
            loop = _session_loop(page)
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(_locked_update, page)
                posted = True
        except Exception:
            pass
        if not posted:
            _warn_loop_fallback("_ui_update", page)
            _locked_update(page)
    except Exception:
        pass


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
        _ui_update(page)
    except Exception:
        pass


# Live set of web-spilled temp audios awaiting consumption. Daemon
# workers die abruptly at interpreter exit (finally never runs), so an
# atexit reaper — registered lazily on first spill — closes the privacy
# hole for normal quits; kill -9 remains unfixable by design.
_SPILLED_TEMPS = set()
_SPILLED_LOCK = threading.Lock()
_SPILL_REAPER_ARMED = {"armed": False}


def _reap_spilled() -> None:
    """Unlink every un-consumed spilled temp file; never raises."""
    try:
        with _SPILLED_LOCK:
            paths = list(_SPILLED_TEMPS)
            _SPILLED_TEMPS.clear()
        for path in paths:
            try:
                if path:
                    os.unlink(path)
            except Exception:
                pass
    except Exception:
        pass


def _discard_spilled(path) -> None:
    """Unlink one spilled temp file and untrack it; never raises."""
    try:
        if path:
            try:
                os.unlink(path)
            except Exception:
                pass
            with _SPILLED_LOCK:
                _SPILLED_TEMPS.discard(path)
    except Exception:
        pass


def _spill_dir(base=None) -> str:
    """App-owned spill directory (0700); created on demand; never raises.

    Spills never land bare in the shared temp dir: everything we create
    lives under one directory we own, so the startup sweep can wipe it
    without risking other processes' files. ``base`` is a test seam
    (defaults to the platform temp dir).
    """
    import tempfile as _tempfile

    parent = base or _tempfile.gettempdir()
    path = os.path.join(parent, "text-c3po-spills")
    try:
        os.makedirs(path, mode=0o700, exist_ok=True)
        try:
            os.chmod(path, 0o700)
        except Exception:
            pass
    except Exception:
        pass
    return path


def _sweep_spills(base=None) -> int:
    """Delete stale spills left by a violently-killed previous run.

    Called once at startup. Paths tracked live in ``_SPILLED_TEMPS``
    are skipped: in web-server mode all sessions share this process,
    so a sibling tab may be mid-decode on them. Cross-process
    in-flight spills (a second app instance) remain a residual race —
    ``base`` is the shared parent dir, a test seam defaulting to the
    platform temp dir. Returns the removed count. Never raises.
    """
    removed = 0
    try:
        try:
            with _SPILLED_LOCK:
                live = set(_SPILLED_TEMPS)
        except Exception:
            live = set()
        target = _spill_dir(base)
        try:
            names = os.listdir(target)
        except Exception:
            return 0
        for name in names:
            full = os.path.join(target, name)
            try:
                if full in live:
                    continue
                if os.path.isfile(full) and not os.path.islink(full):
                    os.unlink(full)
                    removed += 1
            except Exception:
                pass
    except Exception:
        pass
    return removed


def _spill_web_pick(picked_bytes, picked_name, base=None):
    """Write browser-picked bytes to a temp file; return (path, cleanup).

    Returns (None, False) on any failure. Never raises. Module-level
    (not a main() closure) so unit tests drive it directly. ``base``
    overrides the shared parent dir (test seam); the spill always
    lands in the owned ``text-c3po-spills`` child.
    """
    try:
        if not picked_bytes:
            return None, False
        import tempfile as _tempfile

        suffix = os.path.splitext(picked_name or "")[1].lower() or ".wav"
        tmp = _tempfile.NamedTemporaryFile(
            suffix=suffix, delete=False, dir=_spill_dir(base)
        )
        path = tmp.name
        # Track before writing: a write failure — or interpreter exit
        # mid-write — must still be reaped, and only tracked paths are.
        try:
            with _SPILLED_LOCK:
                _SPILLED_TEMPS.add(path)
        except Exception:
            pass
        try:
            with tmp:
                tmp.write(picked_bytes)
        except Exception:
            _discard_spilled(path)
            return None, False
        try:
            if not _SPILL_REAPER_ARMED["armed"]:
                _SPILL_REAPER_ARMED["armed"] = True
                atexit.register(_reap_spilled)
        except Exception:
            pass
        return path, True
    except Exception:
        return None, False


def _mount_overlay(page, control):
    """Append a visual control to page.overlay; Services raise TypeError.

    Runtime guard for the F1 bug class (D7): Service controls such as
    FilePicker have no visual widget — mounting one paints a red
    Unknown-control panel at client render time, on web only, long
    after the offending line ran. Fail fast here instead, in every
    environment including desktop and headless. Intentionally raising:
    a Service on the overlay is always a programming error, never a
    runtime condition to tolerate.
    """
    from flet.controls.services.service import Service

    if isinstance(control, Service):
        raise TypeError(
            "Service {} cannot mount on page.overlay — services "
            "self-register and have no visual widget".format(type(control).__name__)
        )
    overlay = getattr(page, "overlay", None)
    if overlay is None or not hasattr(overlay, "append"):
        raise TypeError("page has no usable overlay list")
    overlay.append(control)


def _overlay_snackbar(page, snack) -> None:
    """Legacy mount for headless fakes without show_dialog; never raises."""
    try:
        _mount_overlay(page, snack)
        try:
            snack.open = True
        except Exception:
            pass
    except Exception:
        pass


def _show_snackbar(page, message, on_retry, with_retry=True) -> None:
    """Render a SnackBar, with a Retry action unless suppressed; never raises.

    Material's transient-error pattern: the dot shows state, this carries
    the words plus the one-tap fix. flet 0.86 routes DialogControl via
    show_dialog (Dialogs stack), not page.overlay. The presentation runs
    through the same loop marshaling as _ui_update: retry toasts fire
    from worker threads, and show_dialog's internal _dialogs.update()
    would drop off-loop exactly like the F3 spinner did. with_retry=False
    renders a bare notice (wiring breaks: retry re-renders the same break).
    """
    try:
        snack = ft.SnackBar(
            content=ft.Text(message),
            action="Retry" if with_retry else None,
            on_action=lambda e: on_retry(),
        )

        def _present() -> None:
            try:
                show = getattr(page, "show_dialog", None)
                if callable(show):
                    try:
                        show(snack)
                    except Exception as exc:
                        # show_dialog appends to the dialog stack BEFORE its
                        # internal update, so a raise here (e.g. the update
                        # dropping off-loop, the F3 disease) leaves a fresh
                        # snack stacked-but-unrendered — never
                        # overlay-fallback, that double-presents. The update
                        # below is the recovery attempt; the warning is the
                        # diagnostic when it too drops.
                        try:
                            logger.warning("snackbar present failed: %r", exc)
                        except Exception:
                            pass
                else:
                    _overlay_snackbar(page, snack)
            except Exception:
                pass
            _locked_update(page)

        posted = False
        try:
            loop = _session_loop(page)
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(_present)
                posted = True
        except Exception:
            pass
        if not posted:
            _warn_loop_fallback("_show_snackbar", page)
            _present()
    except Exception:
        pass


def _show_retry_snackbar(page, on_retry) -> None:
    """Render the retry SnackBar; never raises (AD-12: inline plus SnackBar)."""
    _show_snackbar(page, RETRY_CARD_HINT, on_retry)


def _render_translation_result(refs, page, result, on_retry) -> None:
    """Render a translate_text result into the Formal/Informal tabs plus origin caption.

    Present fields display. A blank informal variant is NOT an error — many
    languages have no formal/informal distinction — so its tab shows
    NO_VARIANT_HINT with no toast (TRUNCATED_INFORMAL_HINT when the
    stream was cut). The SnackBar retry fires only when retry is
    actionable: a retryable ``error`` result, or a blank primary
    (formal) output. A non-retryable error (output ceiling) shows its
    own message with no retry affordance. Missing controls are wiring
    breaks: the wiring notice toasts on every path, including error
    results, so a broken view is never misattributed to the model.
    """
    try:
        refs = refs if isinstance(refs, dict) else {}
        if not isinstance(result, dict):
            result = {"error": RETRY_CARD_HINT, "retryable": True}
        try:
            wiring_broken = (
                refs.get("formal_text") is None or refs.get("informal_text") is None
            )
        except Exception:
            wiring_broken = False
        if wiring_broken:
            try:
                logger.warning("translation rendered with missing refs")
            except Exception:
                pass
            _show_snackbar(page, WIRING_HINT, on_retry, with_retry=False)
            return
        if result.get("error"):
            try:
                retryable = result.get("retryable", True)
            except Exception:
                retryable = True
            try:
                message = result.get("error")
                shown = (
                    message if isinstance(message, str) and message.strip() else None
                )
            except Exception:
                shown = None
            for key in ("formal_text", "informal_text"):
                control = refs.get(key)
                if control is not None:
                    try:
                        control.value = shown or RETRY_CARD_HINT
                        # Error prose is diagnosis, not translation — and a
                        # prior success may have left copyable=True behind.
                        control.data = {"copyable": False}
                    except Exception:
                        pass
            origin = refs.get("origin_caption")
            if origin is not None:
                try:
                    origin.value = SOURCE_TITLE
                except Exception:
                    pass
            if retryable is not False:
                _show_retry_snackbar(page, on_retry)
            else:
                try:
                    _ui_update(page)
                except Exception:
                    pass
            return
        # Primary output decides failure first: a blank formal means the
        # contract itself failed (retry is valuable). A blank informal
        # alongside a good formal is a linguistic fact — many languages
        # have no formal/informal distinction — so it gets a named
        # non-error placeholder, never a retry.
        try:
            formal_value = result.get("formal")
            if isinstance(formal_value, list):
                formal_value = ", ".join(str(part) for part in formal_value)
            formal_value_ok = isinstance(formal_value, str) and bool(
                formal_value.strip()
            )
        except Exception:
            formal_value_ok = False
        formal_ok = formal_value_ok
        pairs = (
            ("formal_text", "formal"),
            ("informal_text", "informal"),
        )
        for ref_key, field in pairs:
            control = refs.get(ref_key)
            value = result.get(field)
            if isinstance(value, list):
                value = ", ".join(str(part) for part in value)
            try:
                if isinstance(value, str) and value.strip():
                    if control is not None:
                        control.value = value
                        control.data = {"copyable": True}
                elif field == "informal" and formal_value_ok:
                    if control is not None:
                        try:
                            truncated = bool(result.get("truncated"))
                        except Exception:
                            truncated = False
                        control.value = (
                            TRUNCATED_INFORMAL_HINT if truncated else NO_VARIANT_HINT
                        )
                        control.data = {"copyable": False}
                else:
                    if control is not None:
                        control.value = RETRY_CARD_HINT
                        control.data = {"copyable": False}
            except Exception:
                pass
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
        except Exception:
            pass
        if not formal_ok:
            _show_retry_snackbar(page, on_retry)
    except Exception:
        try:
            _show_retry_snackbar(page, on_retry)
        except Exception:
            pass


def main(page: ft.Page) -> None:
    # Reap violently-killed previous runs first: nothing is in flight yet,
    # so every file in our own spill dir is definitionally orphaned.
    # Bounds the kill -9 privacy window to "until next launch".
    _sweep_spills()
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
    # model file resolves (file mode errors readably at use time) or when
    # TEXT_C3PO_NO_WHISPER is set (web-smoke tests); spawned off the UI
    # thread so first paint never waits on model load; exit cleanup
    # guarantees no orphan on exit. Crash-restart status UI arrives with
    # E3's indicators.
    whisper_manager = None
    try:
        if os.getenv("TEXT_C3PO_NO_WHISPER"):
            whisper_model = None
        else:
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
        # Serialized with the background poll's picker refresh below: a
        # user pick landing mid-refresh must not be clobbered by it.
        try:
            with poll_state["lock"]:
                current_model["value"] = new_value
        except Exception:
            try:
                current_model["value"] = new_value
            except Exception:
                pass

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
                                # Mid-stream text is unfinished (and carries
                                # a literal ellipsis): not copyable until
                                # the terminal render sets the final flag.
                                formal_control.data = {"copyable": False}
                        except Exception:
                            pass
                    _ui_update(page)

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
                tally = _result_tally(result)
                try:
                    _render_translation_result(refs, page, result, on_translate_retry)
                finally:
                    if is_current_request(my_seq, translate_seq["current"]):
                        _set_translating(refs, page, False, tally)
                    else:
                        _ui_update(page)
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

    def on_stop_translate(e=None) -> None:
        # Global stop (D4-A, 2026-09-13): signal the streaming loop, close
        # every registered stream/HTTP client so the server aborts
        # mid-generation — including any concurrent File-mode or
        # caption-retry LLM work — then bump the generation so late results
        # drop. The worker thread itself can't be killed, but it holds no
        # connection afterwards and the UI is free immediately.
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

    # E2-4: file mode — FilePicker service plus a daemon worker running the
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
            _ui_update(page)
        except Exception:
            pass

    # Browser picks are size-gated, not memory-capped: with_data=True
    # already holds the whole file in memory when pick_files returns, so
    # this cap guards the temp spill plus the decode pipeline and disk —
    # not RAM. A streaming-upload flow would be needed to cap memory.
    WEB_PICK_BYTES_CAP = 100 * 1024 * 1024

    def _run_file(path: str, cleanup: bool = False) -> None:
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
                result = {"error": RETRY_CARD_HINT}
            if isinstance(result, dict) and result.get("error"):
                _set_file_status(str(result["error"]))
                return
            try:
                shown = result.get("formal", "") if isinstance(result, dict) else ""
            except Exception:
                tally, shown = "", ""
            else:
                tally = _result_tally(result)
            _set_file_status(tally, shown if isinstance(shown, str) else "")
        except Exception:
            pass
        finally:
            file_busy["working"] = False
            if cleanup:
                # Web-spilled temp audio must not outlive the session:
                # recordings in /tmp are a storage leak and a privacy hole.
                _discard_spilled(path)
            try:
                refs = file_view.data if isinstance(file_view.data, dict) else {}
                button = refs.get("pick_button")
                if button is not None:
                    button.disabled = False
                _ui_update(page)
            except Exception:
                pass

    async def on_pick_file(e=None) -> None:
        # flet 0.86 FilePicker is awaitable-only (no on_result event):
        # pick_files returns the picked list, [] on cancel. The picker is
        # a Service: constructing it self-registers via ServiceRegistry —
        # never append it to page.overlay (the overlay builder has no
        # FilePicker widget and paints "Unknown control" in red on web).
        if file_busy["working"]:
            return
        if file_picker is None:
            _set_file_status("Audio picking is unavailable — restart the app.")
            return
        is_web = bool(getattr(page, "web", False))
        try:
            files = await file_picker.pick_files(
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=[ext.lstrip(".") for ext in supported_extensions()],
                with_data=is_web,
                # Web-only: a browser blur (alt-tab to check the file) must
                # not void an in-flight pick as a silent cancel.
                cancel_upload_on_window_blur=False,
            )
        except Exception:
            return
        try:
            picked = (files or [None])[0]
            path = getattr(picked, "path", None) if picked is not None else None
            picked_bytes = (
                getattr(picked, "bytes", None) if picked is not None else None
            )
            picked_name = getattr(picked, "name", "") if picked is not None else ""
            picked_size = getattr(picked, "size", 0) if picked is not None else 0
        except Exception:
            path, picked_bytes, picked_name, picked_size = None, None, "", 0
        cleanup = False
        if is_web and picked_bytes and not path:
            try:
                size = picked_size if isinstance(picked_size, int) else 0
                if size <= 0:
                    size = len(picked_bytes)
            except Exception:
                size = 0
            if size > WEB_PICK_BYTES_CAP:
                try:
                    cap_mb = WEB_PICK_BYTES_CAP // (1024 * 1024)
                except Exception:
                    cap_mb = 100
                _set_file_status(
                    "That file is too large for browser pick "
                    "({} MB cap) — try the desktop app.".format(cap_mb)
                )
                return
            # Web never exposes a filesystem path (FilePickerFile.path is
            # always None): spill the bytes to a temp file so the shared
            # decode → transcribe → translate pipeline can run unchanged.
            # _run_file discards it when done (cleanup=True); every early
            # return below discards it too — orphans are recordings.
            path, cleanup = _spill_web_pick(picked_bytes, picked_name)
        if not path or file_busy["working"]:
            if cleanup and path:
                _discard_spilled(path)
            if is_web and not path and picked is not None:
                _set_file_status(
                    "Couldn't read that file in the browser — try the desktop app."
                )
            return
        file_busy["working"] = True
        _set_file_status("Transcribing…", "")
        try:
            threading.Thread(
                target=_run_file, args=(path, cleanup), daemon=True
            ).start()
        except Exception:
            # Thread exhaustion after the spill: reset the latch and drop
            # the temp, or picks wedge silent (busy stuck True) and the
            # recording leaks — the two failure modes of an unguarded start.
            file_busy["working"] = False
            if cleanup:
                _discard_spilled(path)
            _set_file_status("Couldn't start transcription — retry.")
            _ui_update(page)

    try:
        # Service self-registers; do NOT page.overlay.append() it.
        file_picker = ft.FilePicker()
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
            added = live_controller.drain()
            try:
                kinds = {c.get("kind") for c in added if isinstance(c, dict)}
                # Gap rows mean whisper just failed mid-session: the dot
                # must stop claiming ready without another probe round.
                if "gap" in kinds:
                    _paint_live(True, False)
            except Exception:
                pass
            refs = _live_refs()
            pane = refs.get("captions_pane")
            if pane is not None:
                try:
                    sync_captions(pane, live_controller.captions())
                except Exception:
                    pass
            _ui_update(page)
        except Exception:
            pass

    def _on_live_ended_naturally(runner) -> None:
        # Stream died on its own (unplugged device, driver error) while no
        # Stop was pressed: reset the running chrome instead of lying
        # "Live". Skipped when a newer session already owns the slot, and
        # when the user stopped (on_stop_live owns that path).
        try:
            if live_runner.get("current") is not runner:
                return
            live_runner["current"] = None
            live_runner["thread"] = None
            try:
                live_controller.end_session()
            except Exception:
                pass
            _set_live_buttons(False)
            _paint_live(False, None)
            _ui_update(page)
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
            try:
                if not runner.was_stopped():
                    _on_live_ended_naturally(runner)
            except Exception:
                pass

    def _on_live_open(device_value, opened: bool, reason: str = "") -> None:
        try:
            if opened or reason != "open-failed":
                return
            _refuse_live_start(
                "Couldn't open {} — check the device, then retry.".format(
                    device_value or "capture device"
                )
            )
        except Exception:
            pass

    def _supervise_live(
        token, target_value, model_value, device_value, source_value
    ) -> None:
        try:
            manager = whisper_manager
            if manager is None:
                _paint_live(False, False)
                _set_live_buttons(False)
                live_state["starting"] = False
                _ui_update(page)
                return
            try:
                state = manager.ensure_running()
            except Exception:
                state = "failed"
            if state not in ("ready", "restarted"):
                _paint_live(False, False)
                _set_live_buttons(False)
                live_state["starting"] = False
                _ui_update(page)
                return
            if token != live_state["gen"]:
                # Stopped while supervising: leave stop's state alone.
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
                model_text = refs.get("model_label")
                if model_text is not None:
                    try:
                        model_text.value = "Model: {}".format(model_value)
                    except Exception:
                        pass
            except Exception:
                pass
            runner = LiveRunner(
                live_controller,
                device=device_value,
                source_lang=source_value,
                transcribe_fn=transcribe_wav,
                on_utterance=_render_session,
                on_status=lambda opened, reason="": _on_live_open(
                    device_value, opened, reason
                ),
            )
            live_runner["current"] = runner
            live_state["starting"] = False
            _paint_live(True, True)
            _set_live_buttons(True)
            _ui_update(page)
            live_runner["thread"] = threading.Thread(
                target=_run_live, args=(runner,), daemon=True
            )
            live_runner["thread"].start()
        except Exception:
            try:
                live_state["starting"] = False
                _set_live_buttons(False)
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
            _ui_update(page)
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
                        try:
                            retryable = updated.get("retryable", True)
                        except Exception:
                            retryable = True
                        if retryable is not False:
                            _show_snackbar(
                                page,
                                "Still failing — check Ollama, then retry.",
                                lambda e=None: on_caption_retry(seq),
                            )
                        else:
                            _ui_update(page)
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

    # Start latch: the guard below must hold during the whole
    # supervisor window (whisper ensure takes seconds), and Stop bumps
    # the generation so a late supervisor aborts instead of spawning.
    live_state = {"starting": False, "gen": 0}

    def on_start_live(e=None) -> None:
        try:
            refs = _live_refs()
            if live_state["starting"]:
                return
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
            live_state["gen"] += 1
            token = live_state["gen"]
            live_state["starting"] = True
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
                args=(token, target_value, model_value, device_value, source_value),
                daemon=True,
            ).start()
        except Exception:
            try:
                live_state["starting"] = False
            except Exception:
                pass

    def on_stop_live(e=None) -> None:
        try:
            try:
                live_state["gen"] += 1
                live_state["starting"] = False
            except Exception:
                pass
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
    # "lock" serializes the poll's picker refresh with the user's
    # on_select handler so a mid-refresh pick is never clobbered.
    poll_state = {"last": (connected, startup_models), "lock": threading.Lock()}

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
                            try:
                                with poll_state["lock"]:
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
                                                dropdown.value
                                                if dropdown is not None
                                                else None
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
                            except Exception:
                                pass
                        _ui_update(page)
                    if went_down:
                        _show_snackbar(page, DISCONNECT_SNACKBAR_HINT, on_retry)
            except Exception:
                return

    threading.Thread(target=_poll_ollama, daemon=True).start()


def _configure_logging() -> None:
    """Console logging so service diagnostics are operator-visible.

    Without this the root logger drops everything below WARNING, which
    makes TEST-PLAN's log cross-checks (translate_text ok-lines,
    done_reason evidence) unexecutable. Console entry points only —
    library import stays side-effect free.
    """
    try:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        )
    except Exception:
        pass


if __name__ == "__main__":
    _configure_logging()
    ft.run(main)


def run() -> None:
    """Console-script entry point (``text-c3po``): launch the Flet window."""
    _configure_logging()
    ft.run(main)
