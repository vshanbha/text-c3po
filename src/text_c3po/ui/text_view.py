"""Text mode surface: input on the left, Formal/Informal tabs right (CAP-3).

Pure UI: mounts the multiline input field, the target-language picker row
with the Translate button, and a tabbed output pane (Formal plus Informal,
each with a copy button) plus the origin-language caption. Every control is
exposed via ``view.data`` refs so ``app.py`` can attach the Translate
handler and read values at call time. Imports only the language pickers
plus Flet; never the lower Ollama/audio layers (AD-1/AD-2).
"""

import inspect

import flet as ft

from .language_pickers import build_target_dropdown

EMPTY_HINT = "Type or paste something first."
RETRY_HINT = "Couldn't parse that one. Retry."


def _make_copy_handler(body):
    """Return a click handler copying ``body``'s current text to the clipboard."""

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
    """Return one tab page: selectable body text plus a trailing copy button.

    Scrolls internally; the TabBarView gives it a bounded height.
    """
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
    )


def build_text_view() -> ft.Column:
    """Return the Text surface: input column left, tabbed output right.

    Natural height throughout — the page scrolls as one unit, so the input
    never squeezes the output. Halves share the width; the redundant
    per-mode header is gone (AppBar plus toggle carry the context).
    """
    field = ft.TextField(
        multiline=True,
        min_lines=4,
        max_lines=8,
        hint_text=EMPTY_HINT,
        filled=True,
    )
    target = build_target_dropdown()
    # Fixed width (see top_strip: expand collapses inside wrapping Rows).
    target.width = 260
    translate_button = ft.FilledButton(content=ft.Text("Translate"))
    hint = ft.Text("")
    formal_text = ft.Text("", selectable=True)
    informal_text = ft.Text("", selectable=True)
    origin_caption = ft.Text("")
    tabs = ft.Tabs(
        length=2,
        selected_index=0,
        content=ft.Column(
            [
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Formal"),
                        ft.Tab(label="Informal"),
                    ]
                ),
                # Fixed height: TabBarView requires a bounded height, and an
                # explicit pane keeps long translations scrolling in place
                # instead of pushing the page around.
                ft.Column(
                    [
                        ft.TabBarView(
                            controls=[
                                _tab_page(formal_text),
                                _tab_page(informal_text),
                            ],
                            expand=True,
                        ),
                    ],
                    height=420,
                ),
            ]
        ),
    )
    left = ft.Column(
        [
            field,
            ft.Row([target, translate_button], wrap=True),
            hint,
        ],
        expand=1,
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    right = ft.Column(
        [
            tabs,
            origin_caption,
        ],
        expand=1,
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    view = ft.Column(
        [
            ft.Row(
                [left, right],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    view.data = {
        "input_field": field,
        "target_dropdown": target,
        "translate_button": translate_button,
        "hint": hint,
        "tabs": tabs,
        "formal_text": formal_text,
        "informal_text": informal_text,
        "origin_caption": origin_caption,
    }
    return view
