import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models.outbox import OutboxEvent
from app.models.payment import Payment, PaymentStatus


async def test_create_payment_saves_to_db(payment_service, db, create_request):
    result = await payment_service.create_payment(create_request, idempotency_key="idem-1")

    async with db.session() as session:
        saved = await session.get(Payment, result.id)

    assert saved is not None
    assert saved.amount == create_request.amount
    assert saved.currency == create_request.currency
    assert saved.description == create_request.description
    assert saved.webhook_url == create_request.webhook_url
    assert saved.idempotency_key == "idem-1"
    assert saved.status == PaymentStatus.PENDING


async def test_create_payment_creates_outbox_event(payment_service, db, create_request):
    result = await payment_service.create_payment(create_request, idempotency_key="idem-1")

    async with db.session() as session:
        events = list((await session.execute(select(OutboxEvent))).scalars())

    assert len(events) == 1
    assert events[0].event_type == "payment.created"
    assert events[0].payload["payment_id"] == str(result.id)
    assert events[0].published is False


async def test_create_payment_idempotency_returns_existing(payment_service, db, create_request):
    first = await payment_service.create_payment(create_request, idempotency_key="dup-key")
    second = await payment_service.create_payment(create_request, idempotency_key="dup-key")

    assert first.id == second.id

    async with db.session() as session:
        count = (await session.execute(select(func.count()).select_from(Payment))).scalar()

    assert count == 1


async def test_create_payment_idempotency_no_duplicate_outbox(payment_service, db, create_request):
    await payment_service.create_payment(create_request, idempotency_key="dup-key")
    await payment_service.create_payment(create_request, idempotency_key="dup-key")

    async with db.session() as session:
        count = (await session.execute(select(func.count()).select_from(OutboxEvent))).scalar()

    assert count == 1


async def test_get_payment_returns_saved(payment_service, db, create_request):
    created = await payment_service.create_payment(create_request, idempotency_key="idem-1")

    result = await payment_service.get_payment(created.id)

    assert result is not None
    assert result.id == created.id


async def test_get_payment_returns_none_when_not_found(payment_service):
    result = await payment_service.get_payment(uuid.uuid4())

    assert result is None


async def test_update_status_saves_to_db(payment_service, db, create_request):
    payment = await payment_service.create_payment(create_request, idempotency_key="idem-1")
    processed_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    await payment_service.update_status(payment.id, PaymentStatus.SUCCEEDED, processed_at)

    async with db.session() as session:
        updated = await session.get(Payment, payment.id)

    assert updated.status == PaymentStatus.SUCCEEDED
    assert updated.processed_at == processed_at


async def test_update_status_sets_processed_at_if_none(payment_service, db, create_request):
    payment = await payment_service.create_payment(create_request, idempotency_key="idem-1")

    await payment_service.update_status(payment.id, PaymentStatus.FAILED)

    async with db.session() as session:
        updated = await session.get(Payment, payment.id)

    assert updated.processed_at is not None
    assert updated.processed_at.tzinfo is not None
