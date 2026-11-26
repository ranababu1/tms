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
