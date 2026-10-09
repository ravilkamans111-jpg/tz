from fastapi import FastAPI

from app.api.payments import router

app = FastAPI(title="Сервис обработки платежей")
app.include_router(router)
