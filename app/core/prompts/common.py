"""Shared prompt strings from Appendix B — verbatim. Do not edit wording."""

from . import de, tr, vi

TEMPLATES = {"de": de, "tr": tr, "vi": vi}

# B.1 — prefix for targets without a dedicated prompt (German prompt follows).
FALLBACK_OVERRIDE = (
    "## TARGET LANGUAGE OVERRIDE (read first)\n"
    "The target language is {LangName}, NOT German. Everything below was written for German: "
    'wherever it says "German", read "{LangName}". Apply its principles (naturalness, '
    "benefit-first, trustworthy tone, active voice, short sentences, natural CTAs, consistent "
    "informal-professional address) using what is natural for {LangName}. Ignore German-only "
    "grammar, spelling, pronoun, glossary and compound-word rules and the German example "
    "sentences; use the closest natural {LangName} equivalents instead. Output ONLY {LangName}.\n"
    "\n"
)

# B.3 — extra note for the verifier when the German checklist is borrowed.
CHECKLIST_NOTE = (
    "\nNote: this checklist was written for German. Where an item mentions German-specific "
    'rules (e.g. "du"/"ihr", German capitalization, "-ung" nouns), judge the {LangName} '
    "equivalent instead.\n"
)

VERIFY_PROMPT = """You are an independent quality reviewer checking a {LangName} marketing translation you did NOT write. You have no memory of producing it — grade it strictly and honestly on its own merits.

You will receive the ORIGINAL source text and the FINAL translated text.

Grade the FINAL text against every item below. Mark each PASS only if it is genuinely satisfied — do not give the benefit of the doubt.
