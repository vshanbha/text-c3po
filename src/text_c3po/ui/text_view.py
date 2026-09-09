"""Text mode surface: input plus target picker plus Translate plus output cards (CAP-3).

Pure UI: mounts the multiline input field, the target-language picker row
with the Translate button, the three independent output cards (each a
Container with a title, body text, and copy button), and the origin-language
caption. Every control is exposed via ``view.data`` refs so ``app.py`` can
attach the Translate handler and read values at call time. Imports only the
language pickers plus Flet; never the lower Ollama/audio layers (AD-1/AD-2).
"""

import inspect

import flet as ft

from .language_pickers import build_target_dropdown

EMPTY_HINT = "Type or paste something first."
RETRY_HINT = "Couldn't parse that one. Retry."

CARD_BORDER_COLOR = "#E2E0DA"


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


def _output_card(title, body):
    """Return one output card: Container plus title Text plus body plus copy button."""
    copy_button = ft.IconButton(
        icon=ft.Icons.CONTENT_COPY,
        tooltip="Copy {}".format(title.lower()),
    )
    copy_button.on_click = _make_copy_handler(body)
    card = ft.Container(
        content=ft.Column(
            [
                ft.Row([ft.Text(title), copy_button]),
                body,
            ]
        ),
        border=ft.Border.all(1, CARD_BORDER_COLOR),
        border_radius=8,
        padding=16,
    )
    card.data = {"title": title, "body": body, "copy_button": copy_button}
    return card


def build_text_view() -> ft.Column:
    """Return the Text surface with input, Translate, three cards, origin caption."""
    field = ft.TextField(
        multiline=True,
        min_lines=6,
        hint_text=EMPTY_HINT,
    )
    target = build_target_dropdown()
    translate_button = ft.FilledButton(content=ft.Text("Translate"))
    hint = ft.Text("")
    formal_text = ft.Text("", selectable=True)
    informal_text = ft.Text("", selectable=True)
    commentary_text = ft.Text("", selectable=True)
    origin_caption = ft.Text("")
    formal_card = _output_card("Formal", formal_text)
    informal_card = _output_card("Informal", informal_text)
    commentary_card = _output_card("Commentary", commentary_text)
    view = ft.Column(
        [
            ft.Text("Text"),
            field,
            ft.Row([target, translate_button]),
            hint,
            formal_card,
            informal_card,
            commentary_card,
            origin_caption,
        ]
    )
    view.data = {
        "input_field": field,
        "target_dropdown": target,
        "translate_button": translate_button,
        "hint": hint,
        "formal_card": formal_card,
        "informal_card": informal_card,
        "commentary_card": commentary_card,
        "formal_text": formal_text,
        "informal_text": informal_text,
        "commentary_text": commentary_text,
        "origin_caption": origin_caption,
    }
    return view
