# Сервис асинхронной обработки платежей

Микросервис принимает запросы на оплату, обрабатывает их через эмуляцию платежного шлюза и уведомляет клиента о результате через webhook.

Стек: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), PostgreSQL, RabbitMQ (FastStream), Alembic, Docker.

## Как это работает

1. `POST /api/v1/payments` сохраняет платеж и событие в таблицу `outbox` в одной транзакции.
2. Outbox-публикатор (работает внутри процесса consumer) отправляет неопубликованные события в RabbitMQ: exchange `payments`, очередь `payments.new`.
3. Consumer получает сообщение, эмулирует обработку (2-5 сек, 90% успех), обновляет статус и отправляет webhook.
4. Обработка повторяется до 3 раз с экспоненциальной задержкой (1 с, 2 с). Если все попытки неудачны, сообщение уходит в `payments.dlq` через `payments.dlx`.

Идемпотентность: заголовок `Idempotency-Key` уникален в БД. Повторный запрос с тем же ключом возвращает уже созданный платеж. Повторная доставка сообщения не списывает платеж второй раз, повторяется только webhook.

## Структура

```
app/
  api/            эндпоинты и зависимости (авторизация по X-API-Key)
  models/         модели SQLAlchemy (payments, outbox)
  repositories/   работа с БД
  services/       бизнес-логика, шлюз, webhook, retry
  workers/        consumer и публикатор outbox
  broker.py       обменники и очереди RabbitMQ
alembic/          миграции
tests/            тесты
```

## Запуск

```bash
docker compose up --build
```

API: http://localhost:8000 (документация: `/docs`), RabbitMQ UI: http://localhost:15672 (guest / guest).
Настройки задаются в `.env.example` (API ключ по умолчанию `secret-api-key`).

## Примеры

Создание платежа:

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: secret-api-key" \
  -H "Idempotency-Key: order-1" \
  -H "Content-Type: application/json" \
  -d '{"amount": "100.50", "currency": "RUB", "description": "Заказ 1", "metadata": {"order_id": 1}, "webhook_url": "https://example.com/hook"}'
```

Ответ `202 Accepted`:

```json
{"payment_id": "e37c4741-8abc-4f17-bf63-f261890c7dde", "status": "pending", "created_at": "2026-10-09T14:03:55.517005Z"}
```

Получение платежа:

```bash
curl http://localhost:8000/api/v1/payments/<payment_id> -H "X-API-Key: secret-api-key"
```

Для проверки webhook можно поднять любой приемник, например https://webhook.site, и указать его адрес в `webhook_url`.

## Тесты

Нужен PostgreSQL с базой `payments_test`:

```bash
docker compose up -d postgres
docker compose exec postgres psql -U payments -c "create database payments_test"
pip install -r requirements-dev.txt
pytest
```
