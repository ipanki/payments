import uuid

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps import verify_api_key
from app.schemas.payment import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentResponse,
)
from app.services.payment import PaymentService

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreatePaymentResponse,
    summary="Create a payment",
)
@inject
async def create_payment(
    body: CreatePaymentRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    payment_service: PaymentService = Depends(Provide["payment_service"]),
) -> CreatePaymentResponse:
    payment = await payment_service.create_payment(body, idempotency_key)
    return CreatePaymentResponse.model_validate(payment)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get payment by ID",
)
@inject
async def get_payment(
    payment_id: uuid.UUID,
    payment_service: PaymentService = Depends(Provide["payment_service"]),
) -> PaymentResponse:
    payment = await payment_service.get_payment(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found",
        )
    return PaymentResponse.model_validate(payment)
