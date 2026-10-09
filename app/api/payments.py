import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps import check_api_key, get_payment_service
from app.schemas import PaymentAccepted, PaymentCreate, PaymentOut
from app.services.payments import PaymentService

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(check_api_key)],
)


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=PaymentAccepted)
async def create_payment(
    data: PaymentCreate,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=255)],
    service: PaymentService = Depends(get_payment_service),
):
    return await service.create(data, idempotency_key)


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: uuid.UUID,
    service: PaymentService = Depends(get_payment_service),
):
    payment = await service.get(payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Платеж не найден")
    return payment
