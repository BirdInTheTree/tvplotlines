"""LLM client abstraction for Anthropic and OpenAI.

Handles prompt caching, JSON parsing, retry on validation errors,
provider switching, and batch processing.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_BATCH_POLL_INTERVAL = 10  # seconds between batch status checks


@dataclass
class LLMConfig:
    """Configuration for LLM calls."""

    provider: str = "anthropic"  # "anthropic" | "openai"
    model: str | None = None  # None = provider default

    @property
    def resolved_model(self) -> str:
        if self.model:
            return self.model
        defaults = {
            "anthropic": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
        }
        return defaults[self.provider]


def call_llm(
    system_prompt: str,
    user_message: str,
    config: LLMConfig,
    *,
    cache_system: bool = False,
    validator: Callable[[dict], None] | None = None,
) -> dict:
    """Call LLM and return parsed JSON response, retrying on errors.

    Args:
        system_prompt: System prompt text (from prompt .md file).
        user_message: User message with data (JSON-formatted input).
        config: LLM provider and model settings.
        cache_system: Enable prompt caching for system prompt (Anthropic only).
        validator: Optional function that raises ValueError if output is invalid.
            On failure, LLM is re-called with the error message appended.

    Returns:
        Parsed JSON dict from LLM response.

    Raises:
        ValueError: If response is not valid JSON after retries.
        RuntimeError: If LLM call fails.
    """
    messages = [{"role": "user", "content": user_message}]
    last_error = None

    for attempt in range(_MAX_RETRIES + 1):
        if attempt > 0:
            logger.warning("Retry %d/%d: %s", attempt, _MAX_RETRIES, last_error)

        try:
            text = _raw_call(system_prompt, messages, config, cache_system)
            data = _extract_json(text)
        except ValueError as e:
            last_error = str(e)
            messages.append({"role": "assistant", "content": text if 'text' in dir() else ""})
            messages.append({
                "role": "user",
                "content": f"Ответ не является валидным JSON. Ошибка: {last_error}\n\nПовтори ответ — строго JSON, без markdown-обёртки.",
            })
            continue

        # JSON parsed — now validate structure
        if validator:
            try:
                validator(data)
            except ValueError as e:
                last_error = str(e)
                messages.append({"role": "assistant", "content": text})
                messages.append({
                    "role": "user",
                    "content": f"JSON распарсился, но не прошёл валидацию: {last_error}\n\nИсправь и повтори — строго JSON.",
                })
                continue

        return data

    raise ValueError(
        f"LLM failed after {_MAX_RETRIES + 1} attempts. Last error: {last_error}"
    )


def call_llm_batch(
    system_prompt: str,
    user_messages: list[str],
    config: LLMConfig,
    *,
    cache_system: bool = False,
    validators: list[Callable[[dict], None] | None] | None = None,
) -> list[dict]:
    """Send multiple LLM calls as a batch (Anthropic only, 50% cheaper).

    Args:
        system_prompt: Shared system prompt for all requests.
        user_messages: List of user messages (one per request).
        config: LLM provider and model settings.
        cache_system: Enable prompt caching for system prompt.
        validators: Optional list of validators, one per message.
            Failed validations fall back to individual call_llm retries.

    Returns:
        List of parsed JSON dicts, in same order as user_messages.

    Raises:
        ValueError: If provider is not anthropic.
    """
    if config.provider != "anthropic":
        # Fallback: sequential calls for non-Anthropic providers
        results = []
        for i, msg in enumerate(user_messages):
            validator = validators[i] if validators else None
            results.append(call_llm(system_prompt, msg, config,
                                    cache_system=cache_system, validator=validator))
        return results

    if not user_messages:
        return []

    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    client = anthropic.Anthropic()

    system_content: str | list = system_prompt
    if cache_system:
        system_content = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    # Build batch requests
    requests = []
    for i, user_msg in enumerate(user_messages):
        requests.append(Request(
            custom_id=f"req_{i:04d}",
            params=MessageCreateParamsNonStreaming(
                model=config.resolved_model,
                max_tokens=8192,
                system=system_content,
                messages=[{"role": "user", "content": user_msg}],
            ),
        ))

    logger.info("Submitting batch of %d requests", len(requests))
    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id
    logger.info("Batch %s created, polling for results...", batch_id)

    # Poll until complete
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            break
        counts = batch.request_counts
        logger.info(
            "Batch %s: %d succeeded, %d processing",
            batch_id, counts.succeeded, counts.processing,
        )
        time.sleep(_BATCH_POLL_INTERVAL)

    # Collect results, keyed by custom_id
    raw_results: dict[str, str | None] = {}
    errors: dict[str, str] = {}
    for result in client.messages.batches.results(batch_id):
        cid = result.custom_id
        if result.result.type == "succeeded":
            raw_results[cid] = result.result.message.content[0].text
        else:
            errors[cid] = f"{result.result.type}"
            raw_results[cid] = None

    if errors:
        logger.warning("Batch %s had errors: %s", batch_id, errors)

    # Parse results in order, with validation and fallback
    parsed = []
    for i, user_msg in enumerate(user_messages):
        cid = f"req_{i:04d}"
        text = raw_results.get(cid)
        validator = validators[i] if validators else None

        if text is None:
            # Batch request failed — fallback to individual call
            logger.warning("Batch request %s failed, falling back to individual call", cid)
            parsed.append(call_llm(system_prompt, user_msg, config,
                                   cache_system=cache_system, validator=validator))
            continue

        try:
            data = _extract_json(text)
            if validator:
                validator(data)
            parsed.append(data)
        except ValueError as e:
            # Validation failed — fallback to individual call with retries
            logger.warning("Batch request %s failed validation: %s, retrying individually", cid, e)
            parsed.append(call_llm(system_prompt, user_msg, config,
                                   cache_system=cache_system, validator=validator))

    return parsed


def _raw_call(
    system_prompt: str,
    messages: list[dict],
    config: LLMConfig,
    cache_system: bool,
) -> str:
    """Make raw LLM call, return response text."""
    if config.provider == "anthropic":
        return _call_anthropic(system_prompt, messages, config, cache_system)
    elif config.provider == "openai":
        return _call_openai(system_prompt, messages, config)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


def _call_anthropic(
    system_prompt: str,
    messages: list[dict],
    config: LLMConfig,
    cache_system: bool,
) -> str:
    import anthropic

    client = anthropic.Anthropic()

    system_content: str | list = system_prompt
    if cache_system:
        system_content = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    response = client.messages.create(
        model=config.resolved_model,
        max_tokens=8192,
        system=system_content,
        messages=messages,
    )

    return response.content[0].text


def _call_openai(
    system_prompt: str,
    messages: list[dict],
    config: LLMConfig,
) -> str:
    import openai

    client = openai.OpenAI()

    openai_messages = [{"role": "system", "content": system_prompt}] + messages

    response = client.chat.completions.create(
        model=config.resolved_model,
        messages=openai_messages,
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response:\n{text[:500]}")
