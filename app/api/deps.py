import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.services.payments import PaymentService

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def check_api_key(key: str | None = Security(api_key_header)) -> None:
    if not key or not secrets.compare_digest(key, settings.api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный API ключ")


def get_payment_service(session: AsyncSession = Depends(get_session)) -> PaymentService:
    return PaymentService(session)
