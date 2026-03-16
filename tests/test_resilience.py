"""Tests for pipeline resilience: retry, partial success, callbacks, resume, batch."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plotter.callbacks import PipelineCallback
from plotter.llm import (
    LLMConfig,
    _araw_call_with_retry,
    _MAX_NETWORK_RETRIES,
    _BACKOFF_BASE,
    acall_llm,
    acall_llm_parallel,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return LLMConfig(provider="anthropic", model="test-model")


# ---------------------------------------------------------------------------
# Step 1a: Network retry with backoff
# ---------------------------------------------------------------------------

class TestNetworkRetry:
    """_araw_call_with_retry retries transient errors with backoff."""

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self, config):
        """Transient error retried up to _MAX_NETWORK_RETRIES times."""
        import anthropic

        call_count = 0

        async def flaky_raw_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise anthropic.APIConnectionError(request=MagicMock())
            return '{"result": "ok"}'

        with patch("plotter.llm._araw_call", side_effect=flaky_raw_call), \
             patch("plotter.llm.asyncio.sleep", new_callable=AsyncMock):
            result = await _araw_call_with_retry("sys", [{}], config, False)

        assert result == '{"result": "ok"}'
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self, config):
        """After _MAX_NETWORK_RETRIES+1 attempts, the error propagates."""
        import anthropic

        async def always_fail(*args, **kwargs):
            raise anthropic.APIConnectionError(request=MagicMock())

        with patch("plotter.llm._araw_call", side_effect=always_fail), \
             patch("plotter.llm.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(anthropic.APIConnectionError):
                await _araw_call_with_retry("sys", [{}], config, False)

    @pytest.mark.asyncio
    async def test_backoff_delays(self, config):
        """Each retry waits _BACKOFF_BASE^(attempt+1) seconds."""
        import anthropic

        sleep_mock = AsyncMock()

        async def fail_twice(*args, **kwargs):
            if fail_twice.count < 2:
                fail_twice.count += 1
                raise anthropic.APIConnectionError(request=MagicMock())
            return '{"ok": true}'
        fail_twice.count = 0

        with patch("plotter.llm._araw_call", side_effect=fail_twice), \
             patch("plotter.llm.asyncio.sleep", sleep_mock):
            await _araw_call_with_retry("sys", [{}], config, False)

        # Two retries: delays should be 2^1=2 and 2^2=4
        assert sleep_mock.call_count == 2
        assert sleep_mock.call_args_list[0].args[0] == _BACKOFF_BASE ** 1
        assert sleep_mock.call_args_list[1].args[0] == _BACKOFF_BASE ** 2


# ---------------------------------------------------------------------------
# Step 1c: Partial success in parallel
# ---------------------------------------------------------------------------

class TestPartialParallel:
    """acall_llm_parallel retries failed tasks individually."""

    @pytest.mark.asyncio
    async def test_preserves_successful_retries_failed(self, config):
        """If one parallel call fails, others are preserved and failure is retried."""
        call_log = []

        async def mock_acall_llm(system, msg, cfg, *, cache_system=False, validator=None):
            call_log.append(msg)
            if msg == "fail_first" and len([c for c in call_log if c == "fail_first"]) == 1:
                raise ValueError("transient")
            return {"msg": msg}

        with patch("plotter.llm.acall_llm", side_effect=mock_acall_llm):
            results = await acall_llm_parallel(
                "sys", ["ok1", "fail_first", "ok2"], config,
            )

        assert results[0] == {"msg": "ok1"}
        assert results[1] == {"msg": "fail_first"}  # retried and succeeded
        assert results[2] == {"msg": "ok2"}


# ---------------------------------------------------------------------------
# Step 2: Callbacks
# ---------------------------------------------------------------------------

class TestCallbacks:
    """PipelineCallback methods are no-ops by default and can be overridden."""

    def test_default_methods_are_noop(self):
        cb = PipelineCallback()
        # Should not raise
        cb.on_pass0_complete(MagicMock())
        cb.on_pass1_complete([], [])
        cb.on_episode_complete(0, MagicMock())
        cb.on_pass2_complete([])
        cb.on_batch_submitted("batch-123")
        cb.on_pass3_complete([])

    def test_subclass_receives_events(self):
        events = []

        class Recorder(PipelineCallback):
            def on_pass0_complete(self, context):
                events.append(("pass0", context))
            def on_pass1_complete(self, cast, plotlines):
                events.append(("pass1", len(cast), len(plotlines)))

        cb = Recorder()
        cb.on_pass0_complete("ctx")
        cb.on_pass1_complete([1, 2], [3])

        assert events == [("pass0", "ctx"), ("pass1", 2, 1)]


# ---------------------------------------------------------------------------
# Step 3: Resume validation
# ---------------------------------------------------------------------------

class TestResumeValidation:
    """get_plotlines validates resume inputs before running."""

    def test_cast_without_plotlines_raises(self):
        from plotter.pipeline import get_plotlines
        from plotter.models import CastMember

        with pytest.raises(ValueError, match="cast and plotlines must be provided together"):
            get_plotlines(
                "Test", 1, {"S01E01": "ep1"},
                cast=[CastMember(id="a", name="A")],
                plotlines=None,
            )

    def test_plotlines_without_cast_raises(self):
        from plotter.pipeline import get_plotlines
        from plotter.models import Plotline

        with pytest.raises(ValueError, match="cast and plotlines must be provided together"):
            get_plotlines(
                "Test", 1, {"S01E01": "ep1"},
                cast=None,
                plotlines=[Plotline(
                    id="s1", name="S1", driver="a", goal="g",
                    obstacle="o", stakes="s", type="serialized", rank="A",
                    nature="plot-led", confidence="solid",
                )],
            )

    def test_breakdowns_length_mismatch_raises(self):
        from plotter.pipeline import get_plotlines
        from plotter.models import EpisodeBreakdown

        with pytest.raises(ValueError, match="breakdowns length"):
            get_plotlines(
                "Test", 1, {"S01E01": "ep1", "S01E02": "ep2"},
                breakdowns=[EpisodeBreakdown(episode="S01E01")],
            )


# ---------------------------------------------------------------------------
# Step 4c: Batch timeout
# ---------------------------------------------------------------------------

class TestBatchTimeout:
    """Batch polling raises TimeoutError after _BATCH_TIMEOUT."""

    @pytest.mark.asyncio
    async def test_batch_polling_timeout(self, config):
        import plotter.llm as llm_module

        # Temporarily set a very short timeout for testing
        original = llm_module._BATCH_TIMEOUT
        llm_module._BATCH_TIMEOUT = 0.01  # 10ms

        try:
            # Mock the anthropic client
            mock_batch = MagicMock()
            mock_batch.processing_status = "processing"  # never ends
            mock_batch.request_counts.succeeded = 0
            mock_batch.request_counts.processing = 1

            mock_client = AsyncMock()
            mock_client.messages.batches.retrieve.return_value = mock_batch

            with patch("anthropic.AsyncAnthropic", return_value=mock_client), \
                 patch("plotter.llm.asyncio.sleep", new_callable=AsyncMock):
                from plotter.llm import acall_llm_batch

                with pytest.raises(TimeoutError, match="did not complete"):
                    await acall_llm_batch(
                        "sys", ["msg"], config,
                        batch_id="existing-batch-123",
                    )
        finally:
            llm_module._BATCH_TIMEOUT = original


# ---------------------------------------------------------------------------
# Step 4a: Batch ID callback
# ---------------------------------------------------------------------------

class TestBatchCallback:
    """on_batch_submitted fires with batch ID after creation."""

    @pytest.mark.asyncio
    async def test_callback_receives_batch_id(self, config):
        submitted_ids = []

        # Mock the full batch lifecycle
        mock_batch_created = MagicMock()
        mock_batch_created.id = "batch_abc123"

        mock_batch_ended = MagicMock()
        mock_batch_ended.processing_status = "ended"

        mock_result = MagicMock()
        mock_result.custom_id = "req_0000"
        mock_result.result.type = "succeeded"
        mock_result.result.message.content = [MagicMock(text='{"ok": true}')]

        # results() is awaited, then the result is async-iterated
        class AsyncResultStream:
            def __init__(self, items):
                self._items = items
            def __aiter__(self):
                return self
            async def __anext__(self):
                if not self._items:
                    raise StopAsyncIteration
                return self._items.pop(0)

        mock_client = AsyncMock()
        mock_client.messages.batches.create.return_value = mock_batch_created
        mock_client.messages.batches.retrieve.return_value = mock_batch_ended
        mock_client.messages.batches.results.return_value = AsyncResultStream([mock_result])

        with patch("anthropic.AsyncAnthropic", return_value=mock_client):
            from plotter.llm import acall_llm_batch

            await acall_llm_batch(
                "sys", ["msg"], config,
                on_batch_submitted=lambda bid: submitted_ids.append(bid),
            )

        assert submitted_ids == ["batch_abc123"]
