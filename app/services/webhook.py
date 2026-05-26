import logging
import uuid
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    async def send(
        self,
        webhook_url: str,
        payment_id: uuid.UUID,
        status: str,
        processed_at: datetime,
    ) -> None:
        payload = {
            "payment_id": str(payment_id),
            "status": status,
            "processed_at": processed_at.isoformat(),
        }
        try:
            response = await self._client.post(webhook_url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("Webhook delivered for payment %s to %s", payment_id, webhook_url)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Webhook delivery failed for payment %s: HTTP %s",
                payment_id,
                exc.response.status_code,
            )
            raise
        except Exception as exc:
            logger.warning("Webhook delivery error for payment %s: %s", payment_id, exc)
            raise
