import uuid

from httpx import ASGITransport, AsyncClient

PAYMENT_BODY = {
    "amount": "250.00",
    "currency": "RUB",
    "description": "Test payment",
    "metadata": {"order_id": "42"},
    "webhook_url": "https://example.com/webhook",
}


async def test_create_payment_returns_202(client):
    response = await client.post(
        "/api/v1/payments",
        json=PAYMENT_BODY,
        headers={"Idempotency-Key": "idem-1"},
    )
    assert response.status_code == 202


async def test_create_payment_response_shape(client):
    response = await client.post(
        "/api/v1/payments",
        json=PAYMENT_BODY,
        headers={"Idempotency-Key": "idem-1"},
    )
    data = response.json()
    assert "payment_id" in data
    assert data["status"] == "pending"
    assert "created_at" in data


async def test_create_payment_idempotency(client):
    headers = {"Idempotency-Key": "dup-key"}
    r1 = await client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)
    r2 = await client.post("/api/v1/payments", json=PAYMENT_BODY, headers=headers)

    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["payment_id"] == r2.json()["payment_id"]


async def test_create_payment_missing_idempotency_key_returns_422(client):
    response = await client.post("/api/v1/payments", json=PAYMENT_BODY)
    assert response.status_code == 422


async def test_create_payment_invalid_amount_returns_422(client):
    response = await client.post(
        "/api/v1/payments",
        json={**PAYMENT_BODY, "amount": "-10.00"},
        headers={"Idempotency-Key": "idem-1"},
    )
    assert response.status_code == 422


async def test_get_payment_returns_200(client):
    created = (
        await client.post(
            "/api/v1/payments",
            json=PAYMENT_BODY,
            headers={"Idempotency-Key": "idem-1"},
        )
    ).json()

    response = await client.get(f"/api/v1/payments/{created['payment_id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["payment_id"]
    assert data["status"] == "pending"
    assert data["amount"] == "250.00"


async def test_get_payment_not_found_returns_404(client):
    response = await client.get(f"/api/v1/payments/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_payment_invalid_uuid_returns_422(client):
    response = await client.get("/api/v1/payments/not-a-uuid")
    assert response.status_code == 422


async def test_missing_api_key_returns_401(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/payments",
            json=PAYMENT_BODY,
            headers={"Idempotency-Key": "idem-1"},
        )
    assert response.status_code == 401


async def test_wrong_api_key_returns_401(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "wrong-key"},
    ) as ac:
        response = await ac.post(
            "/api/v1/payments",
            json=PAYMENT_BODY,
            headers={"Idempotency-Key": "idem-1"},
        )
    assert response.status_code == 401
