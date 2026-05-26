import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.webhook import WebhookService

WEBHOOK_URL = "https://example.com/webhook"
PAYMENT_ID = uuid.uuid4()
PROCESSED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def http_client():
    return MagicMock(spec=httpx.AsyncClient)


@pytest.fixture
def service(http_client):
    return WebhookService(http_client=http_client)


async def _send(service):
    await service.send(
        webhook_url=WEBHOOK_URL,
        payment_id=PAYMENT_ID,
        status="succeeded",
        processed_at=PROCESSED_AT,
    )


class TestWebhookService:
    async def test_sends_correct_payload(self, service, http_client):
        http_client.post = AsyncMock(
            return_value=MagicMock(status_code=200, raise_for_status=MagicMock())
        )

        await _send(service)

        http_client.post.assert_awaited_once_with(
            WEBHOOK_URL,
            json={
                "payment_id": str(PAYMENT_ID),
                "status": "succeeded",
                "processed_at": PROCESSED_AT.isoformat(),
            },
            timeout=10.0,
        )

    async def test_raises_on_http_error(self, service, http_client):
        response = MagicMock(status_code=500)
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=response
        )
        http_client.post = AsyncMock(return_value=response)

        with pytest.raises(httpx.HTTPStatusError):
            await _send(service)

    async def test_raises_on_connection_error(self, service, http_client):
        http_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(httpx.ConnectError):
            await _send(service)

    async def test_raises_on_timeout(self, service, http_client):
        http_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(httpx.TimeoutException):
            await _send(service)
