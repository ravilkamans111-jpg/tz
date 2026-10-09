import asyncio
import random

from app.config import settings


class PaymentGateway:
    async def charge(self) -> bool:
        await asyncio.sleep(random.uniform(settings.gateway_min_delay, settings.gateway_max_delay))
        return random.random() < settings.gateway_success_rate
