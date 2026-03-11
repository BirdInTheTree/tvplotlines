"""LLM client abstraction for Anthropic and OpenAI.

Async-first architecture: all LLM calls are async internally.
Sync wrappers (call_llm, call_llm_batch) provided for convenience.

Handles prompt caching, JSON parsing, retry on validation errors,
provider switching, batch processing, and parallel execution.
"""

from __future__ import annotations

import asyncio
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


# ---------------------------------------------------------------------------
# Async core
# ---------------------------------------------------------------------------

async def acall_llm(
    system_prompt: str,
    user_message: str,
    config: LLMConfig,
    *,
    cache_system: bool = False,
    validator: Callable[[dict], None] | None = None,
) -> dict:
    """Async: call LLM and return parsed JSON, retrying on errors."""
    messages = [{"role": "user", "content": user_message}]
    last_error = None

    for attempt in range(_MAX_RETRIES + 1):
        if attempt > 0:
            logger.warning("Retry %d/%d: %s", attempt, _MAX_RETRIES, last_error)

        try:
            text = await _araw_call(system_prompt, messages, config, cache_system)
            data = _extract_json(text)
        except ValueError as e:
            last_error = str(e)
            messages.append({"role": "assistant", "content": text if "text" in dir() else ""})
            messages.append({
                "role": "user",
                "content": f"Response is not valid JSON. Error: {last_error}\n\nRepeat — strictly JSON, no markdown wrapping.",
            })
            continue

        if validator:
            try:
                validator(data)
            except ValueError as e:
                last_error = str(e)
                messages.append({"role": "assistant", "content": text})
                messages.append({
                    "role": "user",
                    "content": f"JSON parsed but failed validation: {last_error}\n\nFix and repeat — strictly JSON.",
                })
                continue

        return data

    raise ValueError(
        f"LLM failed after {_MAX_RETRIES + 1} attempts. Last error: {last_error}"
    )


async def acall_llm_parallel(
    system_prompt: str,
    user_messages: list[str],
    config: LLMConfig,
    *,
    cache_system: bool = False,
    validators: list[Callable[[dict], None] | None] | None = None,
) -> list[dict]:
    """Async: send multiple LLM calls in parallel, return results in order."""
    if not user_messages:
        return []

    tasks = []
    for i, msg in enumerate(user_messages):
        validator = validators[i] if validators else None
        tasks.append(acall_llm(
            system_prompt, msg, config,
            cache_system=cache_system, validator=validator,
        ))

    return await asyncio.gather(*tasks)


async def acall_llm_batch(
    system_prompt: str,
    user_messages: list[str],
    config: LLMConfig,
    *,
    cache_system: bool = False,
    validators: list[Callable[[dict], None] | None] | None = None,
) -> list[dict]:
    """Async: send as Anthropic batch (50% cheaper, slower).

    Falls back to parallel calls for non-Anthropic providers.
    """
    if config.provider != "anthropic":
        return await acall_llm_parallel(
            system_prompt, user_messages, config,
            cache_system=cache_system, validators=validators,
        )

    if not user_messages:
        return []

    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    client = anthropic.AsyncAnthropic()

    system_content: str | list = system_prompt
    if cache_system:
        system_content = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

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
    batch = await client.messages.batches.create(requests=requests)
    batch_id = batch.id
    logger.info("Batch %s created, polling for results...", batch_id)

    while True:
        batch = await client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            break
        counts = batch.request_counts
        logger.info(
            "Batch %s: %d succeeded, %d processing",
            batch_id, counts.succeeded, counts.processing,
        )
        await asyncio.sleep(_BATCH_POLL_INTERVAL)

    # Collect results keyed by custom_id
    raw_results: dict[str, str | None] = {}
    errors: dict[str, str] = {}
    async for result in client.messages.batches.results(batch_id):
        cid = result.custom_id
        if result.result.type == "succeeded":
            raw_results[cid] = result.result.message.content[0].text
        else:
            errors[cid] = result.result.type
            raw_results[cid] = None

    if errors:
        logger.warning("Batch %s had errors: %s", batch_id, errors)

    # Parse in order, fallback to individual calls on failure
    parsed = []
    for i, user_msg in enumerate(user_messages):
        cid = f"req_{i:04d}"
        text = raw_results.get(cid)
        validator = validators[i] if validators else None

        if text is None:
            logger.warning("Batch %s failed, falling back", cid)
            parsed.append(await acall_llm(
                system_prompt, user_msg, config,
                cache_system=cache_system, validator=validator,
            ))
            continue

        try:
            data = _extract_json(text)
            if validator:
                validator(data)
            parsed.append(data)
        except ValueError as e:
            logger.warning("Batch %s validation failed: %s, retrying", cid, e)
            parsed.append(await acall_llm(
                system_prompt, user_msg, config,
                cache_system=cache_system, validator=validator,
            ))

    await client.close()
    return parsed


# ---------------------------------------------------------------------------
# Async raw calls
# ---------------------------------------------------------------------------

async def _araw_call(
    system_prompt: str,
    messages: list[dict],
    config: LLMConfig,
    cache_system: bool,
) -> str:
    """Async raw LLM call, return response text."""
    if config.provider == "anthropic":
        return await _acall_anthropic(system_prompt, messages, config, cache_system)
    elif config.provider == "openai":
        return await _acall_openai(system_prompt, messages, config)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


async def _acall_anthropic(
    system_prompt: str,
    messages: list[dict],
    config: LLMConfig,
    cache_system: bool,
) -> str:
    import anthropic

    client = anthropic.AsyncAnthropic()

    system_content: str | list = system_prompt
    if cache_system:
        system_content = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    response = await client.messages.create(
        model=config.resolved_model,
        max_tokens=8192,
        system=system_content,
        messages=messages,
    )

    await client.close()
    return response.content[0].text


async def _acall_openai(
    system_prompt: str,
    messages: list[dict],
    config: LLMConfig,
) -> str:
    import openai

    client = openai.AsyncOpenAI()

    openai_messages = [{"role": "system", "content": system_prompt}] + messages

    response = await client.chat.completions.create(
        model=config.resolved_model,
        messages=openai_messages,
        response_format={"type": "json_object"},
    )

    await client.close()
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Sync wrappers — for backward compatibility and simple usage
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in an async context (e.g. Jupyter) — use nest_asyncio or new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def call_llm(
    system_prompt: str,
    user_message: str,
    config: LLMConfig,
    *,
    cache_system: bool = False,
    validator: Callable[[dict], None] | None = None,
) -> dict:
    """Sync wrapper: call LLM and return parsed JSON response."""
    return _run_async(acall_llm(
        system_prompt, user_message, config,
        cache_system=cache_system, validator=validator,
    ))


def call_llm_parallel(
    system_prompt: str,
    user_messages: list[str],
    config: LLMConfig,
    *,
    cache_system: bool = False,
    validators: list[Callable[[dict], None] | None] | None = None,
) -> list[dict]:
    """Sync wrapper: send multiple LLM calls in parallel."""
    return _run_async(acall_llm_parallel(
        system_prompt, user_messages, config,
        cache_system=cache_system, validators=validators,
    ))


def call_llm_batch(
    system_prompt: str,
    user_messages: list[str],
    config: LLMConfig,
    *,
    cache_system: bool = False,
    validators: list[Callable[[dict], None] | None] | None = None,
) -> list[dict]:
    """Sync wrapper: send as Anthropic batch (50% cheaper)."""
    return _run_async(acall_llm_batch(
        system_prompt, user_messages, config,
        cache_system=cache_system, validators=validators,
    ))


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

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
