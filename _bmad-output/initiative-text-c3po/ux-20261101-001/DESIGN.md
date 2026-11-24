---
name: "TextC3PO Translate Overlay"
status: final
sources:
  - "UX brainstorm (Grammarly-like system-wide translation overlay)"
updated: 2026-11-01
---

# TextC3PO Translate Overlay — Design Spine

> Visual identity for the system-wide translation overlay. This design spine owns *how it looks*. Behavior lives in `EXPERIENCE.md`. For v1 (personal utility, prototype to ship), the goal is minimal, unobtrusive, and readable without getting in the way.

## Brand & Style

- **Posture:** Utility-first, invisible until needed. Borrows the "ambient helper" feeling of Grammarly, but even more minimal.
- **Principles:**
  - **Unobtrusive:** Appear only on demand (via global hotkey after selection). Never nag.
  - **Contextual:** Overlays near the selection, styled distinctly from app chrome.
  - **Clear:** High legibility, even when layered directly over text.
  - **Local-first:** Fits `text-c3po`'s no-cloud aesthetic (functional, not flashy).

## Colors

All colors should be defined as tokens. For a direct overlay layer (like Google Images on mobile), contrast against arbitrary backgrounds is critical.

| Token | Value (suggestion) | Usage |
|---|---|---|
| `color.overlay.bg` | `rgba(28, 28, 30, 0.95)` | Primary overlay background (dark, high contrast) |
| `color.overlay.bg.light` | `rgba(255, 255, 255, 0.98)` | Alternative for light contexts (if we detect later), but v1 can start with one and ensure contrast |
| `color.overlay.text.primary` | `rgba(255, 255, 255, 0.98)` | Primary text (prompt, translated text) |
| `color.overlay.text.secondary` | `rgba(255, 255, 255, 0.7)` | Secondary text (labels, hints) |
| `color.overlay.accent` | `rgba(10, 132, 255, 1)` | Action elements (e.g. "Translate", confirm) |
| `color.overlay.border` | `rgba(255, 255, 255, 0.12)` | Subtle border for definition |
| `color.overlay.highlight` | `rgba(255, 214, 10, 0.25)` | Optional subtle highlight when toggling between original/translated (use sparingly) |

> [ASSUMPTION] Start with a dark overlay background by default (like Google Images) to maximize contrast over arbitrary text backgrounds. May revisit for accessibility in different contexts.

## Typography

Keep typography minimal and system-native where possible for cross-platform feel.

| Token | Value | Usage |
|---|---|---|
| `typography.font.family` | `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif` | System font stack |
| `typography.size.body` | `13px` | Main overlay text (prompt, translation) |
| `typography.size.label` | `12px` | Labels, language picker |
| `typography.weight.regular` | `400` | Body text |
| `typography.weight.medium` | `500` | Actions, labels |
| `typography.lineHeight.body` | `1.4` | Readable for short translations |

## Layout & Spacing

| Token | Value | Usage |
|---|---|---|
| `spacing.xs` | `4px` | Tight gaps |
| `spacing.sm` | `8px` | Inner padding elements |
| `spacing.md` | `12px` | Standard padding |
| `spacing.lg` | `16px` | Section gaps |
| `radius.sm` | `6px` | Small elements (buttons) |
| `radius.md` | `8px` | Dropdown items |
| `radius.lg` | `10px` | Overlay container corners |

> [ASSUMPTION] Overlay has no large card padding chrome - keep it tight like a direct layer over text.

## Elevation & Depth

| Token | Value | Usage |
|---|---|---|
| `elevation.overlay` | `0 4px 24px rgba(0, 0, 0, 0.4)` | Subtle shadow for separation when layered over busy backgrounds |
| `zIndex.overlay` | `999999` | Always on top of all app windows |

## Shapes

- **Overlay shape:** Rectangular with rounded corners (`radius.lg`), no heavy border. Direct layer style (Google Images on mobile) - not a floating card with large margins, more like text overlaying the selection area.
- **Language dropdown:** Rounded (`radius.md`), with items having `radius.sm`.

## Components

Behavioral details live in `EXPERIENCE.md`. Visual specs here.

| Component | Visual spec | Notes |
|---|---|---|
| **Overlay Container** | Background `color.overlay.bg`, text `color.overlay.text.primary`, padding `spacing.md`, radius `radius.lg`, shadow `elevation.overlay` | Direct layer over selection. Positioned outside when possible, else directly over. |
| **Prompt View ("Translate this?")** | Shows source text preview (truncated if long), "Translate to:" label, language picker, "Translate" button (accent color) | Confirmation-first. |
| **Result View** | Shows translated text, "Original / Translated" toggle indicator, "Copy" button | Toggle visibility between original and translated. |
| **Language Dropdown** | Dark background matching overlay, items with hover state, recent items separated/grouped at top, type-to-filter input inside | Recent at top, rest below, type-to-filter. |
| **Action Buttons** | Accent background for primary ("Translate"), subtle/transparent for secondary ("Copy", "Cancel") | Keep minimal. |
| **Toggle Control** | Small inline control to switch between original/translated views | Must be easy to toggle post-translation. |

## Do's and Don'ts

**Do:**
- Keep high contrast for readability over any background
- Use system fonts for native feel
- Keep padding tight - this is a layer, not a modal dialog
- Make the overlay feel like it's part of the translation action, not a separate app window

**Don't:**
- Don't add heavy chrome (no title bar, no large card frame)
- Don't use bright saturated colors that clash with arbitrary backgrounds
- Don't animate heavily - keep transitions snappy or instant
- Don't make it look like a tooltip/pill with arrows pointing to selection (Google Images style is just a layer)
