import asyncio
import json
import re
import logging
import google.generativeai as genai
from app.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class GeminiAPIError(Exception):
    """Raised when the Gemini API returns an error or an invalid response."""
    pass


class GeminiRateLimitError(GeminiAPIError):
    """Raised when the Gemini API rate limit is exceeded."""
    pass


def _clean_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON object/array in the text
        for pattern in [r'\{.*\}', r'\[.*\]']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
        raise ValueError("Unable to parse AI response as JSON")


def _generate_sync(prompt: str) -> dict:
    """Synchronous helper that calls the Gemini API and parses the JSON response."""
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.85, "top_p": 0.9},
    )

    if not response.text:
        raise GeminiAPIError("Gemini API returned an empty response.")

    try:
        return _clean_json_response(response.text)
    except ValueError as exc:
        raise GeminiAPIError(f"Failed to parse Gemini response as JSON: {exc}") from exc


async def generate_with_gemini_stream(prompt: str):
    """Stream text tokens from Gemini API, yielding each token as it arrives."""
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.85, "top_p": 0.9},
        stream=True,
    )
    for chunk in response:
        if hasattr(chunk, "text") and chunk.text:
            yield chunk.text
    # After streaming, re-generate non-streaming to get proper JSON for final result
    final = _generate_sync(prompt)
    yield final


async def generate_with_gemini(prompt: str, max_retries: int = 2) -> dict:
    """Call Gemini API asynchronously with retry on rate-limit errors."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.to_thread(_generate_sync, prompt)
        except GeminiRateLimitError:
            if attempt < max_retries:
                wait = 2 ** attempt  # 1s, 2s
                logger.warning("Gemini rate limited, retrying in %ds...", wait)
                await asyncio.sleep(wait)
                continue
            raise
        except GeminiAPIError:
            raise
        except Exception as exc:
            error_message = str(exc).lower()
            if "rate limit" in error_message or "quota" in error_message or "429" in error_message:
                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning("Gemini rate limited, retrying in %ds...", wait)
                    await asyncio.sleep(wait)
                    continue
                raise GeminiRateLimitError(
                    "Gemini API rate limit exceeded. Please try again later."
                ) from exc
            raise GeminiAPIError(f"Gemini API call failed: {exc}") from exc
    raise last_error or GeminiAPIError("Gemini API call failed after retries")
