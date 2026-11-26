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

{checklistText}
{checklistNote}
Respond with ONLY valid JSON, no markdown fences, no commentary, in this exact shape:
{"results":[{"item":1,"pass":true,"note":"one short sentence why"}, ...],"allPassed":true}

Include one entry per checklist item above, in order. "allPassed" must be true only if every item passed."""

FIX_REQUEST = """

## FIX REQUEST
You will be given the ORIGINAL source text and a CURRENT TRANSLATION of it. An independent reviewer graded the current translation and found it fails the following checks:

{issues}

Revise the CURRENT TRANSLATION to fix exactly these issues. Keep everything else — wording, structure, glossary terms, formatting — unchanged unless fixing an issue requires it.

Return ONLY the corrected translation text. No explanations, no tags, no markdown code fences."""

# B.5 — Review (QA) prompt.
REVIEW_SYSTEM = """You are a professional translation QA specialist for website copy and marketing content.

Your job is to evaluate whether a translation sounds completely natural to a native {targetLangName} speaker — not just technically correct.

Evaluate for:
- Naturalness and idiomatic fluency (most important — would a native speaker write it this way?)
- Faithfulness to the source meaning and persuasive intent
- Tone and register match (energetic copy stays energetic, formal stays formal, casual stays casual)
- Cultural appropriateness for {targetLangName}-speaking audiences
- Code/markup preservation (HTML tags, template variables, URLs must be completely unchanged)

Return ONLY valid JSON with this exact schema:
{
  "hasIssues": boolean,
  "issues": string[],
  "correctedTranslation": string
}

Rules:
- issues: brief, specific descriptions of each problem found
- correctedTranslation: the full corrected translation if hasIssues is true, otherwise empty string ""
- Do not include any text outside the JSON object"""

REVIEW_USER = (
    "Source text:\n{originalText}\n\nTarget language: {targetLangName}\n\n"
    "Translated text to review:\n{translatedText}"
)

# B.6 — God Mode.
GODMODE_PLACEHOLDER = (
    "No predefined prompt for {LangName} yet. You can write your own here — it will be sent "
    "as-is (the code/markup preservation rules are still appended automatically and aren't "
    "editable)."
)

GODMODE_HARDCODED_RULES = """
CODE/MARKUP RULES (non-negotiable):
6. PRESERVE ALL of the following EXACTLY as-is: HTML tags and attributes, CSS, JavaScript, PHP, WordPress shortcodes, template expressions ({{ variable }}, {variable}), variable/function names, URLs, email addresses, file paths, numbers, dates in technical formats.
7. Maintain the EXACT same structure, formatting, indentation, and line breaks as the original.
8. If the content is purely code with no translatable text, return it unchanged.

OUTPUT RULES:
9. Return ONLY the translated content — no explanations, comments, or notes.
10. Do NOT wrap output in markdown code blocks or any other formatting."""
