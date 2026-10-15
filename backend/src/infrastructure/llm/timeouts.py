"""Timeouts for LLM / agent calls and a keep-alive for SSE streams.

All values are seconds and can be overridden with environment variables.
Cloud Run allows 900s per request; Cloudflare (Free) drops a connection that
stays silent for 100s, so streams send a heartbeat well inside that window.
"""
import asyncio
import os
from typing import AsyncGenerator, AsyncIterator, TypeVar

from google.genai.types import HttpOptions


def _env_seconds(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, default))
    except ValueError:
        return default
    return value if value > 0 else default


# One HTTP request to an LLM provider (litellm and Google ADK / genai).
LLM_REQUEST_TIMEOUT_S = _env_seconds("LLM_REQUEST_TIMEOUT_S", 60)
# A whole NLQ run: SQL agent + MCP tool calls + chart + narration.
NLQ_TIMEOUT_S = _env_seconds("NLQ_TIMEOUT_S", 150)
# A whole Report Builder run: planner + extraction + writer + reflection.
REPORT_TIMEOUT_S = _env_seconds("REPORT_TIMEOUT_S", 600)
# Max silence on an SSE stream before a ": ping" comment is sent.
SSE_HEARTBEAT_S = _env_seconds("SSE_HEARTBEAT_S", 15)

SSE_PING = ": ping\n\n"

T = TypeVar("T")


def adk_http_options() -> HttpOptions:
    """Per-request timeout for ADK LlmAgents (genai expects milliseconds)."""
    return HttpOptions(timeout=int(LLM_REQUEST_TIMEOUT_S * 1000))


def is_timeout_error(exc: BaseException) -> bool:
    """True for asyncio/httpx/aiohttp/litellm timeouts, whatever the wrapper."""
    if isinstance(exc, TimeoutError):
        return True
    name = exc.__class__.__name__.lower()
    return "timeout" in name or "timed out" in str(exc).lower()


async def iterate_with_deadline(agen: AsyncIterator[T], seconds: float) -> AsyncGenerator[T, None]:
    """Yield from `agen`, raising TimeoutError once `seconds` have passed in total.

    Each step is awaited with asyncio.wait_for, which on Python 3.12+ runs in
    the current task, so context vars used by ADK / tracing stay intact.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TimeoutError(f"timed out after {int(seconds)}s")
            try:
                item = await asyncio.wait_for(agen.__anext__(), timeout=remaining)
            except StopAsyncIteration:
                return
            except TimeoutError:
                if loop.time() < deadline:
                    raise  # a timeout raised inside agen (e.g. an HTTP read timeout)
                raise TimeoutError(f"timed out after {int(seconds)}s") from None
            yield item
    finally:
        aclose = getattr(agen, "aclose", None)
        if aclose:
            try:
                await aclose()
            except Exception:
                pass


async def with_heartbeat(agen: AsyncIterator[str], interval: float = SSE_HEARTBEAT_S) -> AsyncGenerator[str, None]:
    """Forward SSE chunks from `agen`, sending SSE_PING whenever it is silent for `interval`s.

    The source generator runs in one producer task for its whole life, so
    blocking steps inside it don't stop the pings and its context stays stable.
    """
    queue: asyncio.Queue = asyncio.Queue()
    done = object()

    async def produce():
        try:
            async for chunk in agen:
                await queue.put(chunk)
        except Exception as e:  # forwarded to the consumer below
            await queue.put(e)
            return
        await queue.put(done)

    producer = asyncio.create_task(produce())
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=interval)
            except TimeoutError:
                yield SSE_PING
                continue
            if item is done:
                return
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        if not producer.done():
            producer.cancel()
            try:
                await producer
            except BaseException:
                pass
