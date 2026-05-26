import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.models.payment import Currency


class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2, examples=["100.00"])
    currency: Currency
    description: str | None = Field(default=None, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: str | None = Field(default=None, max_length=2048)


class CreatePaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: uuid.UUID = Field(validation_alias="id")
    status: str
    created_at: datetime


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    amount: Decimal
    currency: str
    description: str | None
    metadata: dict[str, Any] = Field(validation_alias=AliasChoices("metadata_", "metadata"))
    status: str
    idempotency_key: str
    webhook_url: str | None
    created_at: datetime
    processed_at: datetime | None
