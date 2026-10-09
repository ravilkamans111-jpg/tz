import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


async def with_retry[T](
    func: Callable[[], Awaitable[T]], attempts: int, base_delay: float
) -> T:
    for attempt in range(1, attempts + 1):
        try:
            return await func()
        except Exception:
            logger.exception("Попытка %s из %s не удалась", attempt, attempts)
            if attempt == attempts:
                raise
            await asyncio.sleep(base_delay * 2 ** (attempt - 1))
    raise RuntimeError("unreachable")
