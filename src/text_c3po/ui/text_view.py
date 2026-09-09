"""Text mode surface: DeepL-like side-by-side panes (CAP-3).

Pure UI: language bar on top (detected source left, target picker plus
Translate/Stop right), two equal cards below (input left with live char
count, Formal/Informal output right under a Material segmented toggle),
and a slim status line. Every control is exposed via ``view.data`` refs so
``app.py`` can attach handlers and read values at call time. Imports only
the language pickers plus Flet; never the lower Ollama/audio layers.
"""

import flet as ft

from .language_pickers import build_target_dropdown

EMPTY_HINT = "Type or paste something first."
RETRY_HINT = "Couldn't parse that one. Retry."
INPUT_PLACEHOLDER = "Type or paste text to translate"
INPUT_SOFT_LIMIT = 5000

SOURCE_TITLE = "Detect language"


def _make_copy_handler(body):
    """Return a click handler copying the current body text to the clipboard.

    ``body`` may be a control or a zero-arg callable resolving to one, so a
    single header copy button can follow the visible Formal/Informal text.
    """

    async def _on_copy(e):
        try:
            target = body() if callable(body) else body
            control = getattr(e, "control", None)
            page = getattr(control, "page", None)
            clipboard = getattr(page, "clipboard", None)
            if page is None or clipboard is None:
                return
            text = target.value or ""
            if not text.strip() or text.strip() == RETRY_HINT:
                return
            result = clipboard.set(text)
            import inspect

            if inspect.isawaitable(result):
                await result
        except Exception:
            pass

    return _on_copy


def build_text_view() -> ft.Column:
    """Return the Text surface: language bar, two equal cards, status line.

    DeepL-shaped on purpose: the panes share one height so long input no
    longer squeezes or clips the output, the input card carries its own
    scroll plus a live char count, and Translate / Stop live in the language
    bar so they are always visible without scrolling.
    """
    field = ft.TextField(
        multiline=True,
        min_lines=8,
        max_lines=None,
        hint_text=INPUT_PLACEHOLDER,
        border=ft.InputBorder.NONE,
        filled=False,
        expand=True,
        content_padding=ft.Padding.all(4),
    )
    target = build_target_dropdown()
    # Narrow: shares the header row with Translate plus the style toggle.
    target.width = 200
    translate_button = ft.FilledButton(content=ft.Text("Translate"))
    stop_button = ft.OutlinedButton(content=ft.Text("Stop"))
    stop_button.visible = False
    progress = ft.ProgressRing(width=16, height=16)
    progress.visible = False
    status = ft.Text("", size=12)
    hint = ft.Text("", size=12)
    char_count = ft.Text("0 / {}".format(INPUT_SOFT_LIMIT), size=12)
    formal_text = ft.Text("", selectable=True, size=15)
    informal_text = ft.Text("", selectable=True, size=15)
    source_title = ft.Text(SOURCE_TITLE, weight=ft.FontWeight.W_600)
    origin_caption = ft.Text("", size=12)

    def _update_count() -> None:
        try:
            n = len(field.value or "")
        except Exception:
            n = 0
        try:
            char_count.value = "{} / {}".format(n, INPUT_SOFT_LIMIT)
        except Exception:
            pass

    def _on_field_change(e=None) -> None:
        _update_count()
        try:
            char_count.update()
        except Exception:
            pass

    field.on_change = _on_field_change

    informal_text.visible = False

    def _visible_body():
        try:
            if formal_text.visible:
                return formal_text
        except Exception:
            pass
        return informal_text

    copy_current = ft.IconButton(
        icon=ft.Icons.CONTENT_COPY,
        tooltip="Copy shown translation",
    )
    copy_current.on_click = _make_copy_handler(_visible_body)

    def _on_style_change(e=None) -> None:
        """Formal/Informal toggle: flip which text shows (Material segmented)."""
        try:
            selected = e.control.selected or ["formal"]
        except Exception:
            selected = ["formal"]
        current = selected[0]
        for name, body in (("formal", formal_text), ("informal", informal_text)):
            try:
                body.visible = name == current
            except Exception:
                pass
        for control in (formal_text, informal_text):
            try:
                control.update()
            except Exception:
                pass

    style_toggle = ft.SegmentedButton(
        segments=[
            ft.Segment("formal", label="Formal"),
            ft.Segment("informal", label="Informal"),
        ],
        selected=["formal"],
        allow_empty_selection=False,
        on_change=_on_style_change,
    )

    # One header line, never wrapped: source label above the input pane,
    # target picker plus actions above the output pane they control. An
    # earlier spaceBetween bar wrapped into two lines at window width and
    # cost more vertical space than the two rows it replaced.
    left_head = ft.Row([source_title, origin_caption], spacing=8, expand=True)
    right_head = ft.Row(
        [target, style_toggle, translate_button, stop_button, progress, copy_current],
        spacing=8,
        alignment=ft.MainAxisAlignment.END,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    lang_bar = ft.Row(
        [left_head, right_head],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )

    left_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    field,
                    ft.Row(
                        [char_count],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                expand=True,
                spacing=8,
            ),
            padding=ft.Padding.all(12),
            height=360,
        ),
        elevation=1,
    )
    right_card = ft.Card(
        content=ft.Container(
            # Body starts at the card top: no header row, so the first line
            # can never sit beside chrome or hide behind it.
            content=ft.Column(
                [formal_text, informal_text],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=0,
            ),
            padding=ft.Padding.all(12),
            height=360,
        ),
        elevation=1,
    )
    # Plain symmetric flex: the Stack overlay experiment collapsed the right
    # pane to a sliver (Stack shrink-wraps instead of flexing), so chrome
    # lives in rows and both cards just split the width.
    panes = ft.Row(
        [left_card, right_card],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    for pane in (left_card, right_card):
        try:
            pane.expand = 1
        except Exception:
            pass

    status_line = ft.Row(
        [status, hint],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
    )

    view = ft.Column(
        [lang_bar, panes, status_line],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    view.data = {
        "input_field": field,
        "target_dropdown": target,
        "translate_button": translate_button,
        "stop_button": stop_button,
        "progress_ring": progress,
        "status_text": status,
        "hint": hint,
        "char_count": char_count,
        "copy_button": copy_current,
        "style_toggle": style_toggle,
        "formal_text": formal_text,
        "informal_text": informal_text,
        "origin_caption": origin_caption,
    }
    return view
