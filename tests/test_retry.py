import pytest

from app.services import retry
from app.services.retry import with_retry


@pytest.fixture
def delays(monkeypatch):
    recorded = []

    async def fake_sleep(delay):
        recorded.append(delay)

    monkeypatch.setattr(retry.asyncio, "sleep", fake_sleep)
    return recorded


async def test_success_after_failures(delays):
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError
        return "ok"

    assert await with_retry(flaky, attempts=3, base_delay=1) == "ok"
    assert calls == 3
    assert delays == [1, 2]


async def test_raises_after_all_attempts(delays):
    calls = 0

    async def broken():
        nonlocal calls
        calls += 1
        raise ValueError

    with pytest.raises(ValueError):
        await with_retry(broken, attempts=3, base_delay=1)

    assert calls == 3
    assert delays == [1, 2]
