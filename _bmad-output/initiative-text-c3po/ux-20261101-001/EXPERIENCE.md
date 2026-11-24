---
name: "TextC3PO Translate Overlay"
status: final
sources:
  - "UX brainstorm (Grammarly-like system-wide translation overlay)"
updated: 2026-11-01
---

# TextC3PO Translate Overlay — Experience Spine

> Experience owns *how it works*. Visual identity lives in `DESIGN.md` (tokens referenced as `{color.overlay.*}`, `{typography.*}`, etc.). This is a system-wide utility, manual-launch only via global hotkey, with direct-layer overlay behavior.

## Foundation

- **Form factor:** System-wide utility (macOS first). Works across any app.
- **Architecture:** Menu bar/system tray app running in background. Handles hotkey registration, selection capture (Accessibility APIs), overlay rendering (always-on-top borderless window/layer), and translation via existing `text-c3po` backend (Ollama + lfm3, reasoning disabled).
- **UI System:** None named. Custom overlay layer. `DESIGN.md` is the visual identity reference.
- **Permissions:** Requires Accessibility permission on macOS to read selected text system-wide. Menu bar app provides place to explain/link to System Settings.
- **Backend:** Reuse existing Ollama setup and dependencies. Only frontend/UX surface changes.

## Information Architecture

| Surface | Reached from | Purpose |
|---|---|---|
| Menu Bar / System Tray | System tray/menu bar icon | Status, preferences (hotkey, default languages), enable/disable, quit |
| Translation Overlay - Prompt | Global hotkey pressed with text selected (and guards pass) | Confirmation "Translate this?" with language picker, source auto-detected |
| Translation Overlay - Result | After successful translation from Prompt view | Show translation, toggle between original/translated, copy to clipboard |
| Preferences (minimal) | Menu bar → Preferences | Set default language pair, change hotkey (with conflict detection), view permissions status |

No app windows for translation flow - everything is overlay + menu bar.

## Voice and Tone

Microcopy. Brand voice lives in `DESIGN.md`.

| Do | Don't |
|---|---|
| "Translate this?" | "Would you like to translate the selected text?" (keep short) |
| "Translate to:" | Long explanatory text |
| "Copy" | "Copy to clipboard" (keep minimal) |
| "Original" / "Translated" | Verbose toggle labels |
| Clear, direct, utility-focused | Cheerful/exclamatory, nagging |

## Component Patterns

Behavioral. Visual specs live in `DESIGN.md.Components`.

| Component | Use | Behavioral rules |
|---|---|---|
| **Global Hotkey** | Manual launch | User-configurable, must not conflict with existing shortcuts. Check for conflicts on registration; warn if conflict detected. |
| **Selection Capture** | On hotkey | Read current selection via Accessibility APIs. Skip if empty, in password/secure field, or very long (configurable threshold). |
| **Overlay Positioning** | On show | Try to appear outside selection bounds when possible. If insufficient screen real estate (e.g. full screen selection near edges), layer directly over the selection area (Google Images style). Always stay on screen. |
| **Prompt View** | Initial overlay state | Show source text preview (truncated if very long), source language (auto-detected, shown as label), "Translate to:" with language dropdown, "Translate" button. Remember last used language pair. |
| **Language Dropdown** | Language selection | Dropdown with recent selections at top, rest below, type-to-filter/search box inside dropdown. Easy to change. Source language shown as auto-detected (not freely editable in v1 to keep it simple). |
| **Translate Action** | Confirm translation | Call backend with selected text, source (auto-detected), target language. Show loading state briefly. On success, switch to Result view. |
| **Result View** | Post-translation | Show translated text. Provide toggle to flip between original and translated views. "Copy" button copies current visible text to clipboard. Keep overlay visible (no auto-dismiss). |
| **Toggle Control** | Flip original/translated | Easy toggle between original and translated views post-translation. |
| **Copy Action** | Copy translation | Copy currently visible text to clipboard. Provide subtle feedback (e.g. button text change briefly) or just rely on system behavior. v1 keeps it simple. |
| **Dismissal** | Close overlay | Click outside overlay → dismiss. Escape key → dismiss. New selection started or focus changed → dismiss. Small X not strictly necessary if dismissal is easy, but can be added if needed. |

## State Patterns

| State | Context | Treatment |
|---|---|---|
| **Idle** | No selection/overlay | App running in menu bar, waiting for hotkey |
| **Guarded** | Hotkey pressed but guards fail (password field, empty selection, etc.) | Do not show overlay. Optionally show brief menu bar notification or just silently ignore. No nagging. |
| **Prompt** | Overlay shown, awaiting confirmation | Show "Translate this?" view with language picker. Source auto-detected. Last pair pre-selected. |
| **Translating** | User clicked Translate | Show loading/processing state in overlay. Disable buttons to prevent double-click. |
| **Result - Translated** | Translation succeeded | Show translated text by default. Toggle available to see original. |
| **Result - Original** | User toggled to see original | Show original text. Toggle back to translated. |
| **Error** | Translation failed (Ollama down, etc.) | Show error message in overlay with option to dismiss or retry. Keep it simple. |

## Interaction Primitives

- **Manual activation only:** Global hotkey is the only primary trigger (no auto on selection).
- **Direct layer:** Overlay is a borderless, always-on-top layer directly over/near selection (Google Images style). Not a tooltip with arrow, not a card with large chrome.
- **Non-blocking:** Overlay doesn't steal focus in a disruptive way; dismissal is frictionless.
- **Toggle pattern:** Post-translation, toggle between original and translated easily (primary post-translate action).
- **Clipboard-first:** Copy to clipboard is the only output action in v1.
- **Graceful dismissal:** Multiple dismissal paths, no auto-timeout.

## Accessibility Floor

Behavioral. Visual contrast lives in `DESIGN.md`.

- **Keyboard:** Escape dismisses. Tab navigation should work within overlay (language dropdown, buttons). Hotkey must be configurable.
- **Screen readers:** Basic accessibility - overlay elements should be focusable/navigable. Menu bar app needs accessible menu items.
- **Permissions:** Clear explanation when Accessibility permission missing; guide to System Settings.
- **Contrast:** High contrast overlay background/text per `{color.overlay.*}` tokens.
- **Focus management:** When overlay appears, manage focus appropriately. Dismissal returns focus to previous app.
- **Guardrails:** Respect secure fields (passwords) - never capture or show translation UI there.

## Platform & Implementation Notes

- **macOS first:** Use pyobjc/AppKit for Accessibility API (AXUIElement) to get selected text and focused element info. Use hotkey libraries (e.g. pynput, Quartz) for global hotkeys. Overlay as borderless NSWindow/NSPanel or Flet window configured as overlay.
- **Cross-platform design:** Abstract selection capture, hotkey registration, and overlay rendering behind interfaces so they can be swapped for Windows/Linux later.
- **Menu bar:** Use rumps or pystray/Flet system tray integration for menu bar presence.
- **Reuse backend:** Import/use existing translation service from `text_c3po.services.translation` or equivalent. Same Ollama client setup.
- **Configuration:** Store preferences (hotkey, default languages, recent languages) locally (e.g. simple JSON config).
- **Conflicts:** Check hotkey registration; if conflicts, warn user and suggest alternative.

## Key Flows

### Flow 1 — Translate selected text in Notes (Alex, reading foreign text)

1. Alex selects German text in Notes app.
2. Presses global hotkey (e.g. `Cmd+Shift+T`).
3. App checks guards - selection valid, not in secure field.
4. Overlay appears as a direct layer near/over the selection (Google Images style). Shows "Translate this?" with source auto-detected as German, target pre-selected as English (last used).
5. Alex confirms language (or leaves as-is). Clicks "Translate".
6. Overlay shows loading briefly, then switches to Result view showing English translation.
7. **Climax:** Alex clicks "Copy" to copy translation, then toggles to see original vs translated to verify. Dismisses with Escape or by clicking outside.

### Flow 2 — Change language on the fly (Alex, wants French translation)

1. Alex selects text and triggers overlay via hotkey.
2. In Prompt view, opens language dropdown.
3. Types "fr" in type-to-filter box, sees French in filtered results (and French may appear in recent if used before).
4. Selects French. Clicks "Translate".
5. **Climax:** Translation appears in French in Result view.

### Flow 3 — Quick dismiss without translating (Alex, triggered accidentally)

1. Alex accidentally triggers hotkey with selection.
2. Overlay appears in Prompt view.
3. Alex presses Escape or clicks outside.
4. **Climax:** Overlay dismissed immediately, no translation performed, no nagging. Focus returns to Notes.

### Flow 4 — Toggle between original and translated (Alex, wants to compare)

1. After translation shown in Result view, Alex clicks toggle to switch to "Original".
2. Overlay now shows original German text.
3. Alex clicks toggle again to switch back to "Translated".
4. **Climax:** Easy comparison without dismissing and re-triggering.

### Flow 5 — Tight screen real estate (Alex, selects text near edge of screen)

1. Alex selects text near right edge of screen where there's no room to place overlay outside.
2. Triggers hotkey.
3. Overlay positions itself as a direct layer over the selection area (Google Images style) since outside placement isn't possible.
4. **Climax:** Overlay remains readable and usable despite tight constraints.
