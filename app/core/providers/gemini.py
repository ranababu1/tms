"""Google Gemini via the google-genai SDK (async client). The key is never logged."""

import asyncio

from google import genai
from google.genai import errors, types

from .base import PROVIDER_TIMEOUT_SECONDS, Completion, ProviderError, Usage

SAFETY_OFF = [
    types.SafetySetting(category=c, threshold=types.HarmBlockThreshold.BLOCK_NONE)
    for c in (
        types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
