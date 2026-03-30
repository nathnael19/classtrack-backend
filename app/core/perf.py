import os
import time
from contextvars import ContextVar
from typing import Optional

from sqlalchemy import event


_enabled: bool = os.getenv("PERF_METRICS", "0") == "1"

# Per-request query count (safe across async via ContextVar).
_query_count: ContextVar[int] = ContextVar("query_count", default=0)


def perf_enabled() -> bool:
    return _enabled


def reset_query_count() -> None:
    _query_count.set(0)


def inc_query_count() -> None:
    _query_count.set(_query_count.get() + 1)


def get_query_count() -> int:
    return _query_count.get()


def install_sqlalchemy_query_counter(engine) -> None:
    """
    Install a lightweight SQLAlchemy hook that increments a per-request counter.
    No-op unless PERF_METRICS=1.
    """
    if not perf_enabled():
        return

    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        inc_query_count()


class PerfTimer:
    def __init__(self) -> None:
        self._start: Optional[float] = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False

    @property
    def elapsed_ms(self) -> float:
        if self._start is None:
            return 0.0
        return (time.perf_counter() - self._start) * 1000.0

