import asyncio
import json
import logging
import re
import urllib.error
import urllib.request

from app.config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL
from app.services.ai_errors import AIServiceError, AIRateLimitError

logger = logging.getLogger(__name__)


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
        for pattern in [r"\{.*\}", r"\[.*\]"]:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
        raise ValueError("Unable to parse AI response as JSON")


def _generate_sync(prompt: str) -> dict:
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Return only valid JSON. Do not wrap JSON in markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.85,
        "top_p": 0.9,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{GROQ_BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "StartingUP/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 429:
            raise AIRateLimitError("Groq API rate limit exceeded.") from exc
        if exc.code == 403 and "1010" in body:
            raise AIServiceError(
                "Groq blocked this request with 403/1010. This is usually an account, region, network, or provider access restriction rather than a bad API key. Try another network/VPN, confirm the key works in Groq Playground, or switch AI_PROVIDER back to gemini."
            ) from exc
        raise AIServiceError(f"Groq API error {exc.code}. Please try again.") from exc
    except urllib.error.URLError as exc:
        raise AIServiceError("Groq API connection failed. Please try again.") from exc

    data = json.loads(raw)
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise AIServiceError("Groq API returned an empty response.")
    try:
        return _clean_json_response(content)
    except ValueError as exc:
        raise AIServiceError(f"Failed to parse Groq response as JSON: {exc}") from exc


async def generate_with_groq_stream(prompt: str):
    """Stream text tokens from Groq API."""
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Return only valid JSON. Do not wrap JSON in markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.85,
        "top_p": 0.9,
        "stream": True,
        "response_format": {"type": "json_object"},
    }
    import http.client
    import urllib.parse
    url = urllib.parse.urlparse(GROQ_BASE_URL.rstrip("/"))
    conn = http.client.HTTPSConnection(url.hostname, url.port or 443, timeout=90)
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "StartingUP/1.0",
    }
    try:
        conn.request("POST", f"{url.path}/chat/completions", json.dumps(payload), headers)
        resp = conn.getresponse()
        if resp.status != 200:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status == 429:
                raise AIRateLimitError("Groq API rate limit exceeded.")
            raise AIServiceError(f"Groq API error {resp.status}: {body}")
        full_text = ""
        while True:
            line = resp.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace").strip()
            if decoded.startswith("data: "):
                data_str = decoded[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        full_text += content
                        yield content
                except json.JSONDecodeError:
                    continue
        try:
            result = _clean_json_response(full_text)
            yield result
        except ValueError as exc:
            raise AIServiceError(f"Failed to parse Groq stream: {exc}") from exc
    finally:
        conn.close()


async def generate_with_groq(prompt: str, max_retries: int = 2) -> dict:
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.to_thread(_generate_sync, prompt)
        except AIRateLimitError:
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning("Groq rate limited, retrying in %ds...", wait)
                await asyncio.sleep(wait)
                continue
            raise
    raise AIServiceError("Groq API call failed after retries.")
