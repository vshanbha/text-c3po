"""Text mode surface: DeepL-like side-by-side panes (CAP-3).

Pure UI: language bar on top (Detect language … target picker with a swap
action), two equal cards below (input left with live char count, Formal /
Informal output right under a Material segmented toggle), and a centered Translate / Stop action row with
progress + status. Every control is exposed via ``view.data`` refs so
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
    """Return a click handler copying ``body``'s current text to the clipboard."""
    import inspect

    async def _on_copy(e):
        try:
            control = getattr(e, "control", None)
            page = getattr(control, "page", None)
            clipboard = getattr(page, "clipboard", None)
            if page is None or clipboard is None:
                return
            text = body.value or ""
            if not text.strip() or text.strip() == RETRY_HINT:
                return
            result = clipboard.set(text)
            if inspect.isawaitable(result):
                await result
        except Exception:
            pass

    return _on_copy


def _tab_page(body):
    """Return one tab page: selectable body text plus a trailing copy button."""
    copy_button = ft.IconButton(
        icon=ft.Icons.CONTENT_COPY,
        tooltip="Copy translation",
    )
    copy_button.on_click = _make_copy_handler(body)
    return ft.Column(
        [
            body,
            ft.Row([copy_button], alignment=ft.MainAxisAlignment.END),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def build_text_view() -> ft.Column:
    """Return the Text surface: language bar, two equal cards, action row.

    DeepL-shaped on purpose: the panes share one height so long input no
    longer squeezes or clips the output, the input card carries its own
    scroll plus a live char count, and Translate / Stop sit centered below
    with progress + status beside them.
    """
    field = ft.TextField(
        multiline=True,
        min_lines=14,
        max_lines=None,
        hint_text=INPUT_PLACEHOLDER,
        border=ft.InputBorder.NONE,
        filled=False,
        expand=True,
        content_padding=ft.Padding.all(4),
    )
    target = build_target_dropdown()
    target.width = 260
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

    def _on_swap(e=None) -> None:
        """Swap input with the Formal output (client-side, no LLM call)."""
        try:
            left = field.value or ""
        except Exception:
            left = ""
        try:
            right = formal_text.value or ""
        except Exception:
            right = ""
        try:
            field.value = right
        except Exception:
            pass
        try:
            formal_text.value = left
        except Exception:
            pass
        _update_count()
        for control in (field, formal_text, char_count):
            try:
                control.update()
            except Exception:
                pass

    swap_button = ft.IconButton(
        icon=ft.Icons.SWAP_HORIZ,
        tooltip="Swap input and Formal output",
        on_click=_on_swap,
    )

    formal_page = _tab_page(formal_text)
    informal_page = _tab_page(informal_text)
    informal_page.visible = False

    def _on_style_change(e=None) -> None:
        """Formal/Informal toggle: flip which page shows (Material segmented)."""
        try:
            selected = e.control.selected or ["formal"]
        except Exception:
            selected = ["formal"]
        current = selected[0]
        for name, page in (("formal", formal_page), ("informal", informal_page)):
            try:
                page.visible = name == current
            except Exception:
                pass
        for control in (formal_page, informal_page):
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

    lang_bar = ft.Row(
        [
            ft.Row([source_title, origin_caption], spacing=8),
            swap_button,
            target,
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
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
            padding=ft.Padding.all(16),
            height=460,
        ),
        elevation=1,
    )
    right_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [style_toggle],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [formal_page, informal_page],
                            expand=True,
                            spacing=0,
                        ),
                        height=360,
                    ),
                ],
                expand=True,
                spacing=8,
            ),
            padding=ft.Padding.all(16),
            height=460,
        ),
        elevation=1,
    )
    panes = ft.Row(
        [left_card, right_card],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    for card in (left_card, right_card):
        try:
            card.expand = 1
        except Exception:
            pass

    actions = ft.Row(
        [translate_button, stop_button, progress, status, hint],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
        wrap=True,
    )

    view = ft.Column(
        [lang_bar, panes, actions],
        spacing=12,
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
        "swap_button": swap_button,
        "style_toggle": style_toggle,
        "formal_page": formal_page,
        "informal_page": informal_page,
        "formal_text": formal_text,
        "informal_text": informal_text,
        "origin_caption": origin_caption,
    }
    return view
