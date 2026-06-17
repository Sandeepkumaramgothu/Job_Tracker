# backend/services/ai_service.py

"""
Job-description extraction via an LLM.

The user's API key is stored on their NotificationSettings row. This module
just takes (key, model, jd_text) and returns a parsed JSON object matching
AIExtractResponse. Currently OpenAI-only; adding Anthropic etc. is a
parallel `_call_<provider>` function plus a branch in `extract_fields`.

We call the OpenAI REST API directly via httpx instead of the openai SDK
to keep the install lean.
"""

import json
import logging
from typing import Optional

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# JSON schema that pins what the model is allowed to return. Using OpenAI's
# Structured Outputs (`response_format=json_schema`) means we never need to
# parse free-form prose — the model is forced to emit valid JSON with these
# keys.
_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "job_title":    {"type": ["string", "null"]},
        "company":      {"type": ["string", "null"]},
        "location":     {"type": ["string", "null"]},
        "salary_range": {"type": ["string", "null"]},
        "source":       {"type": ["string", "null"]},
        "notes":        {"type": ["string", "null"]},
    },
    "required": ["job_title", "company", "location", "salary_range", "source", "notes"],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = (
    "You extract structured fields from a job description. "
    "Return null for any field that isn't clearly present in the text. "
    "For salary_range, copy the salary string as written (e.g. '$120k - $150k'). "
    "For source, only fill it if the JD explicitly mentions where the user found "
    "it (LinkedIn, Indeed, etc.); otherwise null. "
    "For notes, write a 1-2 sentence summary of the key requirements."
)


async def _call_openai(api_key: str, model: str, jd: str) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": jd},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "extracted_job",
                "schema": _EXTRACTION_SCHEMA,
                "strict": True,
            },
        },
        "temperature": 0,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if resp.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenAI rejected your API key. Check it under Settings → AI.",
        )
    if resp.status_code != 200:
        logger.error("OpenAI error %s: %s", resp.status_code, resp.text[:500])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI returned {resp.status_code}: {resp.text[:200]}",
        )

    body = resp.json()
    try:
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, json.JSONDecodeError) as exc:
        logger.error("Could not parse OpenAI response: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM returned unparseable output.",
        )


async def extract_fields(
    provider: Optional[str],
    api_key: Optional[str],
    model: Optional[str],
    jd: str,
) -> dict:
    """
    Dispatch to the right provider. Raises 400 if the user hasn't configured
    a key, 502 if the upstream LLM fails.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No AI key configured. Open Settings → AI to paste an OpenAI "
                "API key, then try again."
            ),
        )

    provider = (provider or "openai").lower()
    if provider == "openai":
        return await _call_openai(
            api_key=api_key,
            model=model or "gpt-4o-mini",
            jd=jd,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported AI provider: {provider!r}. Only 'openai' is wired up.",
    )
