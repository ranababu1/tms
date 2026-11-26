"""Language codes and display names shared by the backend and the UI."""

LANGUAGE_NAMES: dict[str, str] = {
    "auto": "auto-detected language",
    "ar": "Arabic",
    "en": "English",
    "fr": "French",
    "de": "German",
    "el": "Greek",
    "ja": "Japanese",
    "zh": "Mandarin Chinese",
    "pt": "Portuguese",
    "es": "Spanish",
    "tr": "Turkish",
    "vi": "Vietnamese",
}

# Target languages that have a dedicated, hand-written prompt.
LANGUAGES_WITH_PROMPT: tuple[str, ...] = ("de", "tr", "vi")

# Order shown in the From/To selects ("auto" is source-only).
UI_LANGUAGES: list[dict[str, str]] = [
    {"code": "auto", "label": "Auto-detect"},
    *[
        {"code": code, "label": LANGUAGE_NAMES[code]}
        for code in ("ar", "en", "fr", "de", "el", "ja", "zh", "pt", "es", "tr", "vi")
    ],
]


