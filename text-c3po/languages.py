"""AD-10 single language list: 23 {code, name} pairs verbatim from blueprint 2.1.

Pure data. Imports nothing from other product layers. Every picker binds here.
"""

LANGUAGES = [
    {"code": "af", "name": "Afrikaans"},
    {"code": "ar", "name": "Arabic"},
    {"code": "bn", "name": "Bangla"},
    {"code": "zh", "name": "Chinese"},
    {"code": "da", "name": "Danish"},
    {"code": "nl", "name": "Dutch"},
    {"code": "en", "name": "English"},
    {"code": "fr", "name": "French"},
    {"code": "de", "name": "German"},
    {"code": "el", "name": "Greek"},
    {"code": "gu", "name": "Gujarati"},
    {"code": "hi", "name": "Hindi"},
    {"code": "kn", "name": "Kannada"},
    {"code": "mr", "name": "Marathi"},
    {"code": "fa", "name": "Persian"},
    {"code": "pt", "name": "Portuguese"},
    {"code": "ru", "name": "Russian"},
    {"code": "es", "name": "Spanish"},
    {"code": "sv", "name": "Swedish"},
    {"code": "ta", "name": "Tamil"},
    {"code": "te", "name": "Telugu"},
    {"code": "ur", "name": "Urdu"},
    {"code": "vi", "name": "Vietnamese"},
]

LANGUAGE_CODES = tuple(entry["code"] for entry in LANGUAGES)


def name_for_code(code):
    """Return the language name for a picker ``code`` (e.g. "de" -> "German").

    The translation service contract is language names (the tested path), so
    UI layers convert picker codes through here at call time. Unknown or
    blank codes yield "" and callers treat that as missing target. Never
    raises.
    """
    try:
        if not isinstance(code, str) or not code.strip():
            return ""
        wanted = code.strip().lower()
        for entry in LANGUAGES:
            if entry.get("code", "").lower() == wanted:
                return entry.get("name", "")
        return ""
    except Exception:
        return ""
