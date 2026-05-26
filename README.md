# Payments Service

Асинхронный микросервис процессинга платежей на FastAPI + RabbitMQ + PostgreSQL.

### Ключевые паттерны

- **Outbox Pattern** - платёж и событие создаются в одной транзакции; фоновый publisher читает outbox и публикует в RabbitMQ
- **Idempotency Key** - повторный запрос с тем же ключом возвращает исходный платёж без дублирования
- **Dead Letter Queue** - после 3 неудачных попыток сообщение уходит в `payments.dlq`
- **Exponential backoff** - задержки 5с -> 10с -> 20c через per-message TTL в очереди `payments.retry`

## Запуск

### Docker

```bash
# Клонировать и запустить всё
cp .env.template .env
docker compose up --build
```

Swagger:
```
http://localhost:8000/docs
```

### Локальная разработка

```bash
# Зависимости
uv sync

# PostgreSQL и RabbitMQ через docker
docker compose up postgres rabbitmq -d

# Применить миграции
uv run alembic upgrade head

# API
uv run uvicorn app.main:app --reload

# Consumer (отдельный терминал)
uv run python -m app.consumer
```

## API

Все эндпоинты требуют заголовок `X-API-Key`.

### Создать платёж

```http
POST /api/v1/payments
X-API-Key: dev-secret-key
Idempotency-Key: unique-key-123
Content-Type: application/json

{
  "amount": "100.00",
  "currency": "RUB",
  "description": "Test payment",
  "metadata": {"order_id": "42"},
  "webhook_url": "https://example.com/webhook"
}
```

**Ответ 202:**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2026-01-01T00:00:00Z"
}
```

### Получить платёж

```http
GET /api/v1/payments/{payment_id}
X-API-Key: dev-secret-key
```

**Ответ 200:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": "100.00",
  "currency": "RUB",
  "description": "Test payment",
  "metadata": {"order_id": "42"},
  "status": "succeeded",
  "idempotency_key": "unique-key-123",
  "webhook_url": "https://example.com/webhook",
  "created_at": "2026-01-01T00:00:00Z",
  "processed_at": "2026-01-01T00:00:04Z"
}
```

## Стек

- **FastAPI** + **Pydantic v2** - HTTP API
- **SQLAlchemy 2.0** (async) + **asyncpg** - работа с БД
- **PostgreSQL 16** - хранилище
- **FastStream** + **aio-pika** - RabbitMQ consumer/publisher
- **Alembic** - миграции
- **dependency-injector** - DI контейнер
- **uv** - управление зависимостями
- **Docker Compose** - оркестрация