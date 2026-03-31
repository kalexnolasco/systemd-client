"""Sync wrappers: run_sync() and sync generator bridge."""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterator

T = TypeVar("T")


def run_sync(coro: object) -> object:
    """Run an async coroutine synchronously.

    If there's already a running event loop, creates a new thread.
    Otherwise, uses asyncio.run().
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We're inside an async context — run in a new thread
        result: object = None
        exception: BaseException | None = None

        def _run() -> None:
            nonlocal result, exception
            try:
                result = asyncio.run(coro)  # type: ignore[arg-type]
            except BaseException as exc:
                exception = exc

        thread = threading.Thread(target=_run)
        thread.start()
        thread.join()
        if exception is not None:
            raise exception
        return result
    else:
        return asyncio.run(coro)  # type: ignore[arg-type]


def sync_generator_bridge(async_gen_factory: object) -> Iterator[T]:
    """Bridge an async generator to a synchronous iterator.

    Uses a background thread running its own event loop to pull from
    the async generator and feed items through a queue.
    """
    import queue

    _SENTINEL = object()
    q: queue.Queue[object] = queue.Queue(maxsize=64)

    async def _consume() -> None:
        try:
            async for item in async_gen_factory():  # type: ignore[operator]
                q.put(item)
        except BaseException as exc:
            q.put(exc)
            return
        q.put(_SENTINEL)

    def _thread_target() -> None:
        asyncio.run(_consume())

    thread = threading.Thread(target=_thread_target, daemon=True)
    thread.start()

    try:
        while True:
            item = q.get()
            if item is _SENTINEL:
                break
            if isinstance(item, BaseException):
                raise item
            yield item  # type: ignore[misc]
    finally:
        # Thread is daemon, will be cleaned up
        pass
