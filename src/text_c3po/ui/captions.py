"""Captions pane (E3-2): ordered utterance rows with timestamps.

Renders controller state (AD-3): ``sync_captions`` appends only rows whose
``seq`` is not yet rendered, so re-renders never duplicate and mode
switches never clear the list. Utterance granularity only — no token
streaming. Each row carries a screen-reader announcement (EXPERIENCE.md).

Auto-follow: the ListView tracks the newest row while ``follow`` is on;
any user scroll turns follow off and reveals Jump-to-latest, which
re-enables follow and scrolls to the last row. Error rows use the
Material error color and carry an inline Retry affordance (AD-12).
"""

import flet as ft

JUMP_LABEL = "Jump to latest"


def _row_key(seq) -> str:
    """Return the stable scroll key for a caption row."""
    try:
        return "caption-{}".format(int(seq))
    except Exception:
        return "caption-?"


def _announce(caption) -> str:
    """Return the screen-reader text for one caption. Never raises."""
    try:
        kind = caption.get("kind", "caption")
        at = caption.get("at", "")
        if kind == "gap":
            return "Gap in captions, {}. {}".format(caption.get("text", ""), at)
        if kind == "error":
            return "Translation failed, {}. {}".format(caption.get("text", ""), at)
        spoken = caption.get("translation") or caption.get("text", "")
        announcement = "{}, {}".format(spoken, at).strip(" ,")
        return announcement
    except Exception:
        return ""


def _row_for(caption, on_retry=None):
    """Build one announcement-wrapped row control. Never raises."""
    try:
        kind = (
            caption.get("kind", "caption") if isinstance(caption, dict) else "caption"
        )
        at = caption.get("at", "") if isinstance(caption, dict) else ""
        stamp = ft.Text(str(at), size=11, color=ft.Colors.ON_SURFACE_VARIANT)
        if kind == "gap":
            body = ft.Text(
                str(caption.get("text", "")),
                italic=True,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
            row = ft.Column([stamp, body], spacing=0)
        elif kind == "error":
            body = ft.Text(
                str(caption.get("text", "")), color=ft.Colors.ERROR, selectable=True
            )
            items = [stamp, body]
            if on_retry is not None:
                try:
                    seq = caption.get("seq")
                except Exception:
                    seq = None

                def _fire(e=None, _seq=seq) -> None:
                    try:
                        on_retry(_seq)
                    except Exception:
                        pass

                try:
                    retry = ft.TextButton("Retry", on_click=_fire)
                except Exception:
                    retry = None
                if retry is not None:
                    items.append(retry)
            row = ft.Column(items, spacing=0)
        else:
            text = caption.get("translation") or caption.get("text", "")
            body = ft.Text(str(text), selectable=True)
            row = ft.Column([stamp, body], spacing=0)
        try:
            row.key = _row_key(caption.get("seq"))
        except Exception:
            pass
        try:
            return ft.Semantics(label=_announce(caption), live_region=True, content=row)
        except Exception:
            return row
    except Exception:
        try:
            return ft.Text("")
        except Exception:
            return None


def build_captions_pane(on_retry=None) -> ft.Column:
    """Return the captions Column (ListView plus Jump button).

    Refs live in ``pane.data``: list, jump, follow flag, rendered seqs,
    and the retry callback for error rows.
    """
    pane_data = {
        "follow": {"on": True},
        "rendered": [],
        "rendered_set": set(),
        "rendered_sig": {},
        "on_retry": on_retry,
    }
    jump = ft.Button(JUMP_LABEL, visible=False)
    feed = ft.ListView(expand=True, spacing=8, auto_scroll=True)
    pane = ft.Column([feed, jump], expand=True, spacing=4)
    pane_data["list"] = feed
    pane_data["jump"] = jump
    pane.data = pane_data

    async def _on_jump(e=None) -> None:
        await jump_to_latest_async(pane)

    try:
        jump.on_click = _on_jump
    except Exception:
        pass

    def _on_scroll(e=None) -> None:
        on_pane_scroll(pane, e)

    try:
        feed.on_scroll = _on_scroll
    except Exception:
        pass
    return pane


def _row_sig(caption) -> tuple:
    """Return the content signature identifying a row's rendered state."""
    try:
        if not isinstance(caption, dict):
            return ()
        return (
            caption.get("kind"),
            caption.get("text"),
            caption.get("translation"),
        )
    except Exception:
        return ()


def sync_captions(pane, captions) -> int:
    """Sync the pane with controller snapshots; return rows added+updated.

    New seqs append in order; already-rendered seqs whose content changed
    (e.g. a retried error row) rebuild in place at the same position, so a
    successful retry visibly flips the row instead of vanishing into the
    dedupe. Never raises; empty input is a no-op.
    """
    try:
        data = pane.data if isinstance(getattr(pane, "data", None), dict) else None
        if data is None:
            return 0
        feed = data.get("list")
        if feed is None:
            return 0
        rendered = data.get("rendered")
        if not isinstance(rendered, list):
            rendered = data["rendered"] = []
        seen = data.get("rendered_set")
        if not isinstance(seen, set):
            seen = data["rendered_set"] = set(rendered)
        sigs = data.get("rendered_sig")
        if not isinstance(sigs, dict):
            sigs = data["rendered_sig"] = {}
        changed = 0
        for caption in captions or []:
            try:
                seq = caption.get("seq") if isinstance(caption, dict) else None
            except Exception:
                continue
            if seq is None:
                continue
            sig = _row_sig(caption)
            if seq not in seen:
                row = _row_for(caption, data.get("on_retry"))
                if row is None:
                    continue
                try:
                    feed.controls.append(row)
                except Exception:
                    continue
                seen.add(seq)
                rendered.append(seq)
                sigs[seq] = sig
                changed += 1
            elif sig != sigs.get(seq):
                row = _row_for(caption, data.get("on_retry"))
                if row is None:
                    continue
                try:
                    index = next(
                        i
                        for i, existing in enumerate(feed.controls)
                        if getattr(existing, "key", None) == _row_key(seq)
                        or getattr(getattr(existing, "content", None), "key", None)
                        == _row_key(seq)
                    )
                    feed.controls[index] = row
                    sigs[seq] = sig
                    changed += 1
                except Exception:
                    continue
        try:
            follow = data.get("follow", {})
            feed.auto_scroll = bool(follow.get("on", True))
            jump = data.get("jump")
            if jump is not None:
                jump.visible = not bool(follow.get("on", True))
        except Exception:
            pass
        return changed
    except Exception:
        return 0


def reset_pane(pane) -> None:
    """Clear a pane for a new session: rows, seqs, follow on. Never raises."""
    try:
        data = pane.data if isinstance(getattr(pane, "data", None), dict) else None
        if data is None:
            return
        try:
            data["list"].controls.clear()
        except Exception:
            pass
        try:
            data["rendered"] = []
        except Exception:
            pass
        try:
            data["rendered_set"] = set()
        except Exception:
            pass
        try:
            data["rendered_sig"] = {}
        except Exception:
            pass
        follow = data.get("follow")
        if isinstance(follow, dict):
            try:
                follow["on"] = True
            except Exception:
                pass
        try:
            data["list"].auto_scroll = True
        except Exception:
            pass
        try:
            data["jump"].visible = False
        except Exception:
            pass
    except Exception:
        pass


def _is_user_scroll(event) -> bool:
    """True only for genuine user scrolls (review: programmatic pins and
    auto-scrolls must never disable follow). Missing/unknown shapes
    default to user so headless callers keep working."""
    try:
        if event is None:
            return True
        event_type = getattr(event, "event_type", None)
        if event_type is None:
            return True
        try:
            name = event_type.name
        except Exception:
            name = str(event_type)
        return str(name).upper() == "USER"
    except Exception:
        return True


def on_pane_scroll(pane, event=None) -> None:
    """User scrolled: leave follow mode and reveal Jump-to-latest."""
    try:
        data = pane.data if isinstance(getattr(pane, "data", None), dict) else None
        if data is None:
            return
        if not _is_user_scroll(event):
            return
        follow = data.get("follow")
        if isinstance(follow, dict):
            follow["on"] = False
        try:
            data["list"].auto_scroll = False
        except Exception:
            pass
        try:
            data["jump"].visible = True
        except Exception:
            pass
    except Exception:
        pass


def jump_to_latest(pane) -> None:
    """Re-enable follow mode (sync state half). Never raises.

    The scroll itself is awaitable-only in flet 0.86 — see
    ``jump_to_latest_async`` which the Jump button actually calls.
    """
    try:
        data = pane.data if isinstance(getattr(pane, "data", None), dict) else None
        if data is None:
            return
        follow = data.get("follow")
        if isinstance(follow, dict):
            follow["on"] = True
        try:
            data["list"].auto_scroll = True
        except Exception:
            pass
        try:
            data["jump"].visible = False
        except Exception:
            pass
    except Exception:
        pass


async def jump_to_latest_async(pane) -> None:
    """Full jump: follow state plus awaited scroll to the last row."""
    try:
        jump_to_latest(pane)
        data = pane.data if isinstance(getattr(pane, "data", None), dict) else None
        if data is None:
            return
        try:
            rendered = data.get("rendered") or []
            if rendered:
                await data["list"].scroll_to(scroll_key=_row_key(rendered[-1]))
        except Exception:
            pass
    except Exception:
        pass
