import uuid

BODY = {
    "amount": "100.50",
    "currency": "RUB",
    "description": "Заказ 1",
    "metadata": {"order_id": 1},
    "webhook_url": "https://example.com/hook",
}


async def create(client, key="key-1", body=BODY):
    return await client.post("/api/v1/payments", json=body, headers={"Idempotency-Key": key})


async def test_create_payment(client, count):
    response = await create(client)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert uuid.UUID(data["payment_id"])
    assert data["created_at"]
    assert await count("payments") == 1
    assert await count("outbox") == 1


async def test_idempotency_key_returns_same_payment(client, count):
    first = await create(client)
    second = await create(client)

    assert second.status_code == 202
    assert first.json()["payment_id"] == second.json()["payment_id"]
    assert await count("payments") == 1
    assert await count("outbox") == 1


async def test_different_keys_create_different_payments(client, count):
    first = await create(client, key="a")
    second = await create(client, key="b")

    assert first.json()["payment_id"] != second.json()["payment_id"]
    assert await count("payments") == 2


async def test_idempotency_key_required(client):
    response = await client.post("/api/v1/payments", json=BODY)

    assert response.status_code == 422


async def test_invalid_currency(client):
    response = await create(client, body={**BODY, "currency": "GBP"})

    assert response.status_code == 422


async def test_invalid_amount(client):
    response = await create(client, body={**BODY, "amount": "-5"})

    assert response.status_code == 422


async def test_get_payment(client):
    payment_id = (await create(client)).json()["payment_id"]

    response = await client.get(f"/api/v1/payments/{payment_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["payment_id"] == payment_id
    assert data["amount"] == "100.50"
    assert data["currency"] == "RUB"
    assert data["description"] == "Заказ 1"
    assert data["metadata"] == {"order_id": 1}
    assert data["status"] == "pending"
    assert data["webhook_url"] == "https://example.com/hook"
    assert data["processed_at"] is None


async def test_get_payment_not_found(client):
    response = await client.get(f"/api/v1/payments/{uuid.uuid4()}")

    assert response.status_code == 404


async def test_api_key_required(client):
    response = await client.get(
        f"/api/v1/payments/{uuid.uuid4()}", headers={"X-API-Key": "wrong"}
    )
    assert response.status_code == 401

    response = await client.post(
        "/api/v1/payments", json=BODY, headers={"Idempotency-Key": "k", "X-API-Key": "wrong"}
    )
    assert response.status_code == 401
